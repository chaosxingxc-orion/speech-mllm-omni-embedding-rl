"""Summarize and compare omni memory-use row-level results.

The script is intentionally offline: it reads existing JSON outputs produced by
``omni_memory_use_eval.py`` or gate-composed outputs, computes aggregate
metrics, and optionally reports paired bootstrap confidence intervals.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def load_result(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "rows" not in data:
        raise ValueError(f"result has no rows: {path}")
    return data


def parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, path = value.split("=", 1)
    if not label:
        raise argparse.ArgumentTypeError("empty label")
    return label, Path(path)


def summarize(label: str, data: dict[str, Any], *, success_field: str) -> dict[str, Any]:
    rows = data.get("rows", [])
    n = len(rows)
    if not n:
        return {"label": label, "n": 0}
    return {
        "label": label,
        "n": n,
        "success_field": success_field,
        "success": sum(bool(row.get(success_field)) for row in rows) / n,
        "task_success": sum(bool(row.get("task_success")) for row in rows) / n,
        "answer_pass": sum(bool(row.get("answer_pass")) for row in rows) / n,
        "invalid_output": sum(bool(row.get("invalid_output")) for row in rows) / n,
        "wrong_memory": sum(bool(row.get("wrong_memory")) for row in rows) / n,
        "http_error_count": sum(row.get("parse_method") == "http_error" for row in rows),
        "regression_count": sum(bool(row.get("regression_vs_text_only")) for row in rows),
        "mean_latency_ms": sum(float(row.get("latency_ms", 0.0)) for row in rows) / n,
        "mean_text_cost": sum(float(row.get("text_cost", 0.0)) for row in rows) / n,
        "mean_audio_cost": sum(float(row.get("audio_cost", 0.0)) for row in rows) / n,
    }


def paired_delta(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    *,
    success_field: str,
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    def key(row: dict[str, Any]) -> str:
        return str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")

    baseline_rows = {key(row): row for row in baseline.get("rows", [])}
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    missing = 0
    for row in candidate.get("rows", []):
        base = baseline_rows.get(key(row))
        if base is None:
            missing += 1
            continue
        cand_ok = bool(row.get(success_field))
        base_ok = bool(base.get(success_field))
        diffs.append(int(cand_ok) - int(base_ok))
        fixes += cand_ok and not base_ok
        regressions += base_ok and not cand_ok
    if not diffs:
        return {"n": 0, "missing": missing}
    rng = random.Random(seed)
    n = len(diffs)
    boot = [
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(rounds)
    ]
    boot.sort()
    lower = boot[int(0.025 * rounds)]
    upper = boot[max(0, int(0.975 * rounds) - 1)]
    return {
        "n": n,
        "delta": sum(diffs) / n,
        "ci95": [lower, upper],
        "fixes": fixes,
        "regressions": regressions,
        "regression_rate": regressions / n,
        "missing": missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=parse_named_path, required=True)
    parser.add_argument(
        "--paired",
        action="append",
        default=[],
        help="CandidateLabel:BaselineLabel. Labels must come from --run.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--success-field", default="task_success")
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    loaded = {label: load_result(path) for label, path in args.run}
    report: dict[str, Any] = {
        "experiment": "omni_memory_result_compare",
        "success_field": args.success_field,
        "summaries": [
            summarize(label, data, success_field=args.success_field)
            for label, data in loaded.items()
        ],
        "paired": [],
    }
    for item in args.paired:
        if ":" not in item:
            raise ValueError(f"--paired must be Candidate:Baseline, got {item!r}")
        candidate_label, baseline_label = item.split(":", 1)
        report["paired"].append(
            {
                "candidate": candidate_label,
                "baseline": baseline_label,
                **paired_delta(
                    loaded[candidate_label],
                    loaded[baseline_label],
                    success_field=args.success_field,
                    rounds=args.bootstrap_rounds,
                    seed=args.seed,
                ),
            }
        )

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
