"""Build compact evidence-packed memory-use manifests.

This is a training-free memory-use transformation.  It rewrites each retrieved
candidate memory into a shorter answer/evidence card so a frozen main model can
choose among candidate memories without reading long passages verbatim.

The script also emits a prompt-budget diagnostic using the existing
``omni_memory_use_eval`` prompt renderer.  No model or API is called.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import omni_memory_use_eval


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sentence_split(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def choose_evidence(text: str, answer: str, max_chars: int) -> str:
    answer_norm = str(answer).strip().lower()
    sentences = sentence_split(text)
    if answer_norm:
        for sentence in sentences:
            if answer_norm in sentence.lower():
                return sentence[:max_chars].strip()
    if sentences:
        return sentences[0][:max_chars].strip()
    return str(text)[:max_chars].strip()


def pack_candidate(candidate: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    out = dict(candidate)
    answer = str(candidate.get("label") or candidate.get("answer") or "")
    source = str(candidate.get("context") or candidate.get("summary") or "")
    evidence = choose_evidence(source, answer, args.max_evidence_chars)
    if args.style == "answer_evidence":
        summary = f"Candidate answer: {answer}. Evidence: {evidence}"
    elif args.style == "question_answer_evidence":
        summary = f"Candidate answer: {answer}. Supporting passage evidence: {evidence}"
    elif args.style == "answer_only":
        summary = f"Candidate answer: {answer}"
    else:
        raise ValueError(f"Unsupported style: {args.style}")
    out["summary"] = summary
    out["packing_style"] = args.style
    out["packed_evidence"] = evidence
    out["packed_answer"] = answer
    return out


def prompt_stats(rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    lengths = []
    overflow_count = 0
    for row in rows:
        prompt = omni_memory_use_eval.build_prompt(
            row,
            args.policy,
            args.fixed_output_protocol,
            args.prompt_style,
            args.flatten_prompt,
            args.query_text_hint,
            args.memory_audio_limit,
        )
        token_count = len(prompt.split())
        lengths.append(token_count)
        overflow_count += token_count > args.context_token_budget
    if not lengths:
        return {}
    sorted_lengths = sorted(lengths)
    n = len(lengths)
    return {
        "n": n,
        "mean_prompt_tokens": sum(lengths) / n,
        "max_prompt_tokens": max(lengths),
        "p50_prompt_tokens": sorted_lengths[n // 2],
        "p95_prompt_tokens": sorted_lengths[min(n - 1, int(0.95 * n))],
        "context_token_budget": args.context_token_budget,
        "overflow_count": overflow_count,
        "overflow_rate": overflow_count / n,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_rows = read_jsonl(args.input)
    if args.max_samples:
        source_rows = source_rows[: args.max_samples]
    packed_rows = []
    for row in source_rows:
        out = dict(row)
        out["candidate_memories"] = [
            pack_candidate(candidate, args)
            for candidate in row.get("candidate_memories", [])
        ]
        out["memory_packing_policy"] = args.style
        packed_rows.append(out)

    write_jsonl(args.output, packed_rows)
    original_stats = prompt_stats(source_rows, args)
    packed_stats = prompt_stats(packed_rows, args)
    report = {
        "experiment": "build_memory_evidence_packing",
        "input": str(args.input),
        "output": str(args.output),
        "style": args.style,
        "row_count": len(packed_rows),
        "max_evidence_chars": args.max_evidence_chars,
        "original_prompt_stats": original_stats,
        "packed_prompt_stats": packed_stats,
        "token_reduction": (
            original_stats.get("mean_prompt_tokens", 0.0)
            - packed_stats.get("mean_prompt_tokens", 0.0)
        ),
        "examples": packed_rows[:2],
    }
    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument(
        "--style",
        choices=["answer_evidence", "question_answer_evidence", "answer_only"],
        default="answer_evidence",
    )
    parser.add_argument("--max-evidence-chars", type=int, default=260)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--policy", default="text_summary_only")
    parser.add_argument("--fixed-output-protocol", choices=["letter", "json", "anti_answer"], default="anti_answer")
    parser.add_argument("--prompt-style", choices=["verbose", "compact"], default="compact")
    parser.add_argument("--flatten-prompt", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--query-text-hint", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--memory-audio-limit", type=int, default=-1)
    parser.add_argument("--context-token-budget", type=int, default=1800)
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
