"""Compare retrieval-to-final-answer RAG evaluation reports.

The final-answer evaluator already emits row-level JSON.  This script turns a
set of those reports into a compact decomposition:

* whether the gold memory/document is present in the used context,
* whether the selected/grounded memory is exactly correct,
* whether the final answer passes rule-based evaluation,
* generation misses when gold is in context but the answer fails,
* retrieval misses when gold is absent from context,
* paired answer-pass deltas against a baseline report.

It does not call any model or API.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def report_label(path: Path, report: dict[str, Any]) -> str:
    config = report.get("config", {})
    retrieval = config.get("retrieval_result")
    retrieval_part = Path(str(retrieval)).stem if retrieval else path.stem
    order = config.get("candidate_order")
    generator = config.get("generator_mode")
    prompt = config.get("answer_prompt_style")
    context_count = config.get("answer_context_count")
    shuffle_seed = config.get("context_shuffle_seed", -1)
    shuffle_part = f"_ctxshuffle{shuffle_seed}" if isinstance(shuffle_seed, int) and shuffle_seed >= 0 else ""
    if order:
        generator_part = generator or "generator"
        return f"{retrieval_part}_{order}_top{context_count}{shuffle_part}_{generator_part}_{prompt or 'prompt'}"
    return path.stem


def doc_id(row: dict[str, Any]) -> str:
    return str(row.get("document_id") or row.get("sample_id") or "")


def context_has_gold(row: dict[str, Any]) -> bool:
    target = doc_id(row)
    used = [str(item) for item in row.get("used_candidate_ids", [])]
    return target in used


def bootstrap_ci(diffs: list[int], rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {}
    answer_pass = [bool(row.get("answer_pass")) for row in rows]
    context_pass = [context_has_gold(row) for row in rows]
    grounded_pass = [bool(row.get("grounded_target_pass") or row.get("grounded_sample_pass")) for row in rows]
    generation_miss = [context_pass[i] and not answer_pass[i] for i in range(n)]
    retrieval_miss = [not context_pass[i] for i in range(n)]
    error_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("error_type") or "unknown")
        error_counts[key] = error_counts.get(key, 0) + 1
    answer_given_gold_context = (
        sum(answer_pass[i] for i in range(n) if context_pass[i]) / sum(context_pass)
        if any(context_pass)
        else 0.0
    )
    return {
        "n": n,
        "answer_pass": sum(answer_pass) / n,
        "context_gold_rate": sum(context_pass) / n,
        "grounded_exact_rate": sum(grounded_pass) / n,
        "answer_given_gold_context": answer_given_gold_context,
        "retrieval_miss_rate": sum(retrieval_miss) / n,
        "generation_miss_rate": sum(generation_miss) / n,
        "api_error_count": sum(bool(row.get("api_error")) for row in rows),
        "error_type_counts": error_counts,
    }


def rows_by_id(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("report has no row list")
    return {str(row.get("sample_id")): row for row in rows}


def paired_delta(
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    field: str,
    bootstrap_rounds: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    for sample_id, base in baseline_rows.items():
        cand = candidate_rows.get(sample_id)
        if not cand:
            continue
        if field == "context_has_gold":
            b = context_has_gold(base)
            c = context_has_gold(cand)
        else:
            b = bool(base.get(field))
            c = bool(cand.get(field))
        diff = int(c) - int(b)
        diffs.append(diff)
        fixes += diff > 0
        regressions += diff < 0
    return {
        "paired_n": len(diffs),
        "delta": sum(diffs) / len(diffs) if diffs else 0.0,
        "ci95": bootstrap_ci(diffs, bootstrap_rounds, bootstrap_seed),
        "fixes": fixes,
        "regressions": regressions,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    reports: list[tuple[Path, dict[str, Any]]] = [(path, read_json(path)) for path in args.inputs]
    summaries = []
    for path, report in reports:
        rows = report.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"{path} has no rows")
        summaries.append(
            {
                "label": report_label(path, report),
                "path": str(path),
                "metrics": report.get("metrics", {}),
                "decomposition": summarize_rows(rows),
            }
        )

    comparisons = []
    if args.baseline:
        baseline = read_json(args.baseline)
        base_rows = rows_by_id(baseline)
        base_label = report_label(args.baseline, baseline)
        for path, report in reports:
            label = report_label(path, report)
            if path == args.baseline:
                continue
            cand_rows = rows_by_id(report)
            comparisons.append(
                {
                    "baseline": base_label,
                    "candidate": label,
                    "answer_pass": paired_delta(
                        base_rows,
                        cand_rows,
                        "answer_pass",
                        args.bootstrap_rounds,
                        args.bootstrap_seed,
                    ),
                    "context_gold": paired_delta(
                        base_rows,
                        cand_rows,
                        "context_has_gold",
                        args.bootstrap_rounds,
                        args.bootstrap_seed + 1,
                    ),
                    "grounded_exact": paired_delta(
                        base_rows,
                        cand_rows,
                        "grounded_target_pass",
                        args.bootstrap_rounds,
                        args.bootstrap_seed + 2,
                    ),
                }
            )

    result = {
        "experiment": "rag_final_answer_compare",
        "inputs": [str(path) for path, _ in reports],
        "baseline": str(args.baseline) if args.baseline else "",
        "summaries": summaries,
        "comparisons": comparisons,
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=13)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
