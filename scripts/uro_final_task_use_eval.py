#!/usr/bin/env python
"""Evaluate URO retrieval reports as deterministic final-task memory use.

URO retrieval rows often rank candidate answer cards.  Retrieval Acc@1 tells us
whether the exact candidate was selected; this script checks the next interface
step: can the selected candidate memory be converted into the final answer?

The evaluator is intentionally local and deterministic.  It parses answer text
from cards such as ``Candidate answer: ...`` or ``Answer: ...`` and compares it
with the gold answer/card.  It also reports whether the gold memory was present
in the top-k context, whether the selected memory is exactly grounded, and
whether failures are retrieval misses or memory-use misses.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any


ANSWER_PATTERNS = [
    re.compile(
        r"Candidate answer:\s*(?P<answer>.*?)(?:\n\s*Use this candidate|\n\s*Task:|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"Answer:\s*(?P<answer>.*?)(?:\n\s*Task:|$)", re.IGNORECASE | re.DOTALL),
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def collapse_ws(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def extract_answer(card_or_text: Any) -> str:
    text = str(card_or_text or "").strip()
    for pattern in ANSWER_PATTERNS:
        match = pattern.search(text)
        if match:
            return collapse_ws(match.group("answer"))
    return collapse_ws(text)


def normalize_answer(text: Any) -> str:
    value = extract_answer(text).lower()
    value = value.replace("；", ";").replace("，", ",").replace("。", ".")
    value = re.sub(r"\s+", " ", value).strip()
    # Remove punctuation that is usually formatting rather than semantics for
    # short answer cards.  Keep CJK characters and alphanumerics.
    value = re.sub(r"^[\s\"'`]+|[\s\"'`]+$", "", value)
    value = re.sub(r"\s*;\s*$", "", value)
    return value


def selected_memory(row: dict[str, Any], mode: str) -> tuple[str, str]:
    if mode == "selected" and row.get("selected_sample_id"):
        return str(row.get("selected_sample_id", "")), str(row.get("selected_text", ""))
    return str(row.get("top_sample_id", "")), str(row.get("top_text", ""))


def top_context_ids(row: dict[str, Any], context_k: int) -> list[str]:
    scores = row.get("scores") or []
    ids = [str(candidate.get("sample_id", "")) for candidate in scores[:context_k]]
    return [item for item in ids if item]


def top_context_texts(row: dict[str, Any], context_k: int) -> list[str]:
    scores = row.get("scores") or []
    return [str(candidate.get("text", "")) for candidate in scores[:context_k]]


def answer_matches(candidate_answer: str, gold_answer: str) -> bool:
    cand = normalize_answer(candidate_answer)
    gold = normalize_answer(gold_answer)
    if not cand or not gold:
        return False
    if cand == gold:
        return True
    # Multiple-choice cards sometimes include only the letter or the expanded
    # letter plus text.  A bare-letter gold should match an expanded candidate
    # only when it starts with the same option label.
    if re.fullmatch(r"[a-d]", gold) and re.match(rf"^{re.escape(gold)}(?:[\.\):;\s]|$)", cand):
        return True
    if re.fullmatch(r"[a-d]", cand) and re.match(rf"^{re.escape(cand)}(?:[\.\):;\s]|$)", gold):
        return True
    return False


def evaluate_row(row: dict[str, Any], selected_mode: str, context_k: int) -> dict[str, Any]:
    gold_memory_id = str(row.get("sample_id", ""))
    gold_card = str(row.get("target_text", ""))
    selected_id, selected_text = selected_memory(row, selected_mode)
    selected_answer = extract_answer(selected_text)
    gold_answer = extract_answer(gold_card)
    used_ids = top_context_ids(row, context_k)
    if selected_id and selected_id not in used_ids:
        used_ids = [selected_id] + used_ids
    used_texts = top_context_texts(row, context_k)

    context_has_gold = gold_memory_id in used_ids
    grounded_target_pass = selected_id == gold_memory_id or collapse_ws(selected_text) == collapse_ws(gold_card)
    answer_pass = answer_matches(selected_answer, gold_answer)
    if answer_pass:
        error_type = "none"
    elif not context_has_gold:
        error_type = "retrieval_miss"
    elif not grounded_target_pass:
        error_type = "wrong_memory_selected"
    else:
        error_type = "answer_parse_or_generation_miss"

    return {
        "sample_id": gold_memory_id,
        "dataset_config": row.get("dataset_config", ""),
        "query_text": row.get("query_text", ""),
        "gold_memory_id": gold_memory_id,
        "gold_answer": gold_answer,
        "gold_card": gold_card,
        "used_candidate_ids": used_ids,
        "used_candidate_texts": used_texts,
        "selected_memory_id": selected_id,
        "selected_memory_text": selected_text,
        "answer_text": selected_answer,
        "answer_pass": answer_pass,
        "grounded_target_pass": grounded_target_pass,
        "context_has_gold": context_has_gold,
        "wrong_memory_answer": (not grounded_target_pass) and (not answer_pass),
        "generation_miss": context_has_gold and not answer_pass,
        "retrieval_miss": not context_has_gold,
        "error_type": error_type,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "answer_pass": 0.0,
            "grounded_target_acc": 0.0,
            "context_gold_rate": 0.0,
            "generation_miss_rate": 0.0,
            "retrieval_miss_rate": 0.0,
            "wrong_memory_answer_rate": 0.0,
            "error_type_counts": {},
        }
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("error_type", "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return {
        "n": n,
        "answer_pass": sum(bool(row["answer_pass"]) for row in rows) / n,
        "grounded_target_acc": sum(bool(row["grounded_target_pass"]) for row in rows) / n,
        "context_gold_rate": sum(bool(row["context_has_gold"]) for row in rows) / n,
        "generation_miss_rate": sum(bool(row["generation_miss"]) for row in rows) / n,
        "retrieval_miss_rate": sum(bool(row["retrieval_miss"]) for row in rows) / n,
        "wrong_memory_answer_rate": sum(bool(row["wrong_memory_answer"]) for row in rows) / n,
        "error_type_counts": counts,
    }


def bootstrap_ci(diffs: list[int], rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def paired_against(baseline_path: Path, candidate_rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    baseline_report = read_json(baseline_path)
    baseline_rows = [
        evaluate_row(row, args.baseline_selected_mode, args.context_k)
        for row in baseline_report.get("rows", [])
    ]
    baseline_by_id = {str(row["sample_id"]): row for row in baseline_rows}
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    for row in candidate_rows:
        base = baseline_by_id.get(str(row["sample_id"]))
        if not base:
            continue
        diff = int(bool(row["answer_pass"])) - int(bool(base["answer_pass"]))
        diffs.append(diff)
        fixes += int(diff > 0)
        regressions += int(diff < 0)
    return {
        "baseline": str(baseline_path),
        "paired_n": len(diffs),
        "answer_pass_delta": sum(diffs) / len(diffs) if diffs else 0.0,
        "ci95": bootstrap_ci(diffs, args.bootstrap_rounds, args.bootstrap_seed),
        "fixes": fixes,
        "regressions": regressions,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    report = read_json(args.input)
    input_rows = report.get("rows", [])
    if args.max_rows > 0:
        input_rows = input_rows[: args.max_rows]
    rows = [evaluate_row(row, args.selected_mode, args.context_k) for row in input_rows]
    result = {
        "experiment": "uro_final_task_use_eval",
        "input": str(args.input),
        "config": {
            "selected_mode": args.selected_mode,
            "context_k": args.context_k,
            "max_rows": args.max_rows,
        },
        "metrics": summarize(rows),
        "rows": rows,
    }
    if args.baseline:
        result["paired_vs_baseline"] = paired_against(args.baseline, rows, args)
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selected-mode", choices=["top", "selected"], default="top")
    parser.add_argument("--context-k", type=int, default=3)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--baseline-selected-mode", choices=["top", "selected"], default="top")
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=31)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
