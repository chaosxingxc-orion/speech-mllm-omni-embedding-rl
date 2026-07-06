"""Export high-value bad-case samples for manual audit.

This script does not call models or APIs.  It reads existing row-level result
JSON files and writes:

- a structured JSON sample set under outputs/
- a compact Markdown audit sheet under docs/

The goal is to make the paper claims inspectable: verifier fixes, verifier
regressions, memory-packing fixes, and memory-packing regressions should have
concrete examples that a human can review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_COVOST = Path(
    "outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json"
)
DEFAULT_SLURP = Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p01.json")
DEFAULT_HEYSQUAD_BASE = Path(
    "outputs/omni_memory_v0/heysquad_retrieval_raw_top5_use_gemma4e4b_server_200.json"
)
DEFAULT_HEYSQUAD_PACKED = Path(
    "outputs/omni_memory_v0/heysquad_retrieval_raw_top5_packed_use_gemma4e4b_server_200.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def truncate(value: Any, limit: int = 260) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def markdown_cell(value: Any, limit: int = 120) -> str:
    text = truncate(value, limit)
    text = "".join(ch if ord(ch) < 128 else "?" for ch in text)
    return text.replace("|", "\\|")


def top_candidates(row: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    if isinstance(row.get("top_labels"), list):
        return [
            {
                "rank": item.get("rank"),
                "candidate": item.get("label"),
                "score": item.get("score"),
            }
            for item in row["top_labels"][:limit]
        ]
    if isinstance(row.get("scores"), list):
        return [
            {
                "rank": item.get("rank"),
                "candidate": item.get("text"),
                "score": item.get("score"),
            }
            for item in row["scores"][:limit]
        ]
    return []


def verifier_cases(
    *,
    path: Path,
    task: str,
    max_fixes: int,
    max_regressions: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    data = load_json(path)
    fixes: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    routed_count = 0

    for row in data.get("rows", []):
        verifier = row.get("low_margin_verifier") or {}
        if not verifier.get("routed"):
            continue
        routed_count += 1
        base_hit = bool(verifier.get("base_hit_at_1"))
        policy_hit = bool(verifier.get("hit_at_1"))
        if base_hit == policy_hit:
            continue

        case = {
            "task": task,
            "case_type": "fix" if policy_hit else "regression",
            "sample_id": row.get("sample_id"),
            "query_text": row.get("text") or row.get("query_text"),
            "gold": row.get("target") or row.get("target_text"),
            "base_prediction": verifier.get("base_prediction"),
            "policy_prediction": verifier.get("selected_candidate"),
            "margin": verifier.get("margin"),
            "selected_choice": verifier.get("selected_choice"),
            "verifier_reason": (verifier.get("detail") or {}).get("reason"),
            "candidates": top_candidates(row),
        }
        if policy_hit:
            fixes.append(case)
        else:
            regressions.append(case)

    fixes.sort(key=lambda item: (item.get("margin") is None, item.get("margin", 1.0)))
    regressions.sort(key=lambda item: (item.get("margin") is None, item.get("margin", 1.0)))
    selected = fixes[:max_fixes] + regressions[:max_regressions]
    stats = {
        "routed": routed_count,
        "fixes_total": len(fixes),
        "regressions_total": len(regressions),
        "fixes_selected": min(max_fixes, len(fixes)),
        "regressions_selected": min(max_regressions, len(regressions)),
    }
    return selected, stats


def heysquad_packing_cases(
    *,
    base_path: Path,
    packed_path: Path,
    max_fixes: int,
    max_regressions: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    base_rows = load_json(base_path).get("rows", [])
    packed_rows = load_json(packed_path).get("rows", [])
    base_by_id = {row["query_id"]: row for row in base_rows}

    fixes: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []

    for packed in packed_rows:
        query_id = packed.get("query_id")
        base = base_by_id.get(query_id)
        if not base:
            continue
        base_hit = bool(base.get("task_success"))
        packed_hit = bool(packed.get("task_success"))
        if base_hit == packed_hit:
            continue
        base_output = truncate(base.get("model_output"), 220)
        packed_output = truncate(packed.get("model_output"), 220)
        base_invalid = bool(base.get("invalid_output")) or "exceeds the available context" in base_output
        case = {
            "task": "HeySQuAD memory packing",
            "case_type": "fix" if packed_hit else "regression",
            "sample_id": query_id,
            "gold": base.get("gold_memory_id"),
            "gold_answer": base.get("gold_answer"),
            "base_prediction": base.get("prediction"),
            "policy_prediction": packed.get("prediction"),
            "base_text_cost": base.get("text_cost"),
            "packed_text_cost": packed.get("text_cost"),
            "base_invalid_or_overflow": base_invalid,
            "candidate_memory_ids": base.get("candidate_memory_ids"),
            "base_output": base_output,
            "packed_output": packed_output,
        }
        if packed_hit:
            fixes.append(case)
        else:
            regressions.append(case)

    fixes.sort(key=lambda item: (not item.get("base_invalid_or_overflow"), item.get("sample_id") or ""))
    regressions.sort(key=lambda item: item.get("sample_id") or "")
    selected = fixes[:max_fixes] + regressions[:max_regressions]
    stats = {
        "compared": len(packed_rows),
        "fixes_total": len(fixes),
        "regressions_total": len(regressions),
        "fixes_selected": min(max_fixes, len(fixes)),
        "regressions_selected": min(max_regressions, len(regressions)),
    }
    return selected, stats


def markdown_table(cases: list[dict[str, Any]]) -> str:
    lines = [
        "| Task | Type | Sample | Gold | Base | Policy | Why audit |",
        "|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        reason = case.get("verifier_reason")
        if not reason:
            reason = (
                "packing repaired overflow"
                if case.get("base_invalid_or_overflow")
                else f"text cost {case.get('base_text_cost')} -> {case.get('packed_text_cost')}"
            )
        lines.append(
            "| {task} | {case_type} | {sample_id} | {gold} | {base} | {policy} | {reason} |".format(
                task=markdown_cell(case.get("task"), 48),
                case_type=case.get("case_type"),
                sample_id=markdown_cell(case.get("sample_id"), 48),
                gold=markdown_cell(case.get("gold"), 80),
                base=markdown_cell(case.get("base_prediction"), 80),
                policy=markdown_cell(case.get("policy_prediction"), 80),
                reason=markdown_cell(reason, 120),
            )
        )
    return "\n".join(lines)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Bad-Case Audit Samples",
        "",
        "Last updated: 2026-07-03",
        "",
        "This is a paper-support audit sheet generated from ignored row-level",
        "experiment outputs.  It does not call any model or API.  The purpose is",
        "to provide concrete examples for human inspection of the strongest",
        "training-free controller claims.",
        "",
        "Generated by:",
        "",
        "```text",
        "python scripts/build_badcase_audit_samples.py",
        "```",
        "",
        "## Source Counts",
        "",
        "| Source | Routed / Compared | Fixes total | Regressions total | Selected |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, stats in payload["source_stats"].items():
        compared = stats.get("routed", stats.get("compared", "n/a"))
        selected = stats["fixes_selected"] + stats["regressions_selected"]
        lines.append(
            f"| {name} | {compared} | {stats['fixes_total']} | "
            f"{stats['regressions_total']} | {selected} |"
        )

    lines.extend(
        [
            "",
            "## Selected Cases",
            "",
            markdown_table(payload["cases"]),
            "",
            "## How To Use This Audit",
            "",
            "- Use the verifier fixes to show that low-margin top-k verification repairs",
            "  semantic near misses rather than random errors.",
            "- Use the CoVoST2 verifier regressions to discuss acceptable paraphrase",
            "  conflicts and why regression accounting is required.",
            "- Use the HeySQuAD packing fixes/regressions to show that memory-use",
            "  formatting changes both context budget and answer grounding.",
            "- Do not treat this as a new metric table; it is qualitative support for",
            "  the audited quantitative tables.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--covost", type=Path, default=DEFAULT_COVOST)
    parser.add_argument("--slurp", type=Path, default=DEFAULT_SLURP)
    parser.add_argument("--heysquad-base", type=Path, default=DEFAULT_HEYSQUAD_BASE)
    parser.add_argument("--heysquad-packed", type=Path, default=DEFAULT_HEYSQUAD_PACKED)
    parser.add_argument("--json-output", type=Path, default=Path("outputs/badcase_audit_samples.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("docs/badcase_audit_samples.md"))
    parser.add_argument("--max-fixes", type=int, default=8)
    parser.add_argument("--max-regressions", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases: list[dict[str, Any]] = []
    source_stats: dict[str, dict[str, int]] = {}

    slurp_cases, slurp_stats = verifier_cases(
        path=args.slurp,
        task="SLURP low-margin verifier",
        max_fixes=args.max_fixes,
        max_regressions=args.max_regressions,
    )
    source_stats["SLURP verifier"] = slurp_stats
    cases.extend(slurp_cases)

    covost_cases, covost_stats = verifier_cases(
        path=args.covost,
        task="CoVoST2 ar->en low-margin verifier",
        max_fixes=args.max_fixes,
        max_regressions=args.max_regressions,
    )
    source_stats["CoVoST2 ar verifier"] = covost_stats
    cases.extend(covost_cases)

    packing_cases, packing_stats = heysquad_packing_cases(
        base_path=args.heysquad_base,
        packed_path=args.heysquad_packed,
        max_fixes=args.max_fixes,
        max_regressions=args.max_regressions,
    )
    source_stats["HeySQuAD memory packing"] = packing_stats
    cases.extend(packing_cases)

    payload = {
        "experiment": "badcase_audit_samples",
        "note": "Qualitative audit sample generated from existing row-level outputs; no model/API calls.",
        "source_stats": source_stats,
        "case_count": len(cases),
        "cases": cases,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown_output, payload)
    print(json.dumps({"case_count": len(cases), "json": str(args.json_output), "markdown": str(args.markdown_output)}, indent=2))


if __name__ == "__main__":
    main()
