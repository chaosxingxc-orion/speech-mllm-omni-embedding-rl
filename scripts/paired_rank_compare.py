"""Paired bootstrap comparison for row-level ranking outputs."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = report.get("rows", [])
    out = {}
    for row in rows:
        sample_id = str(row.get("sample_id", ""))
        if sample_id:
            out[sample_id] = row
    return out


def _hit(row: dict[str, Any]) -> float:
    if "hit_at_1" in row:
        return 1.0 if row.get("hit_at_1") else 0.0
    if "sample_hit_at_1" in row:
        return 1.0 if row.get("sample_hit_at_1") else 0.0
    if "text_hit_at_1" in row:
        return 1.0 if row.get("text_hit_at_1") else 0.0
    return 1.0 if int(row.get("rank", row.get("sample_rank", 10**9))) == 1 else 0.0


def _reciprocal_rank(row: dict[str, Any]) -> float:
    rank = int(row.get("rank", row.get("sample_rank", row.get("text_rank", 10**9))))
    return 1.0 / rank if rank > 0 else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compare(
    baseline_path: Path,
    candidate_path: Path,
    output_path: Path,
    bootstrap_rounds: int,
    seed: int,
) -> dict[str, Any]:
    baseline = _load_rows(baseline_path)
    candidate = _load_rows(candidate_path)
    ids = sorted(set(baseline) & set(candidate))
    if not ids:
        raise ValueError("no overlapping sample_id values")

    hit_deltas = [_hit(candidate[sid]) - _hit(baseline[sid]) for sid in ids]
    mrr_deltas = [_reciprocal_rank(candidate[sid]) - _reciprocal_rank(baseline[sid]) for sid in ids]
    fixes = [sid for sid in ids if _hit(candidate[sid]) > _hit(baseline[sid])]
    regressions = [sid for sid in ids if _hit(candidate[sid]) < _hit(baseline[sid])]

    rng = random.Random(seed)
    boot_hit = []
    boot_mrr = []
    for _ in range(bootstrap_rounds):
        draw = [rng.randrange(len(ids)) for _ in ids]
        boot_hit.append(_mean([hit_deltas[index] for index in draw]))
        boot_mrr.append(_mean([mrr_deltas[index] for index in draw]))
    boot_hit.sort()
    boot_mrr.sort()

    def ci(values: list[float]) -> list[float]:
        if not values:
            return [0.0, 0.0]
        lo = values[int(0.025 * (len(values) - 1))]
        hi = values[int(0.975 * (len(values) - 1))]
        return [lo, hi]

    report = {
        "experiment": "paired_rank_compare",
        "baseline": str(baseline_path),
        "candidate": str(candidate_path),
        "n": len(ids),
        "hit_at_1": {
            "baseline": _mean([_hit(baseline[sid]) for sid in ids]),
            "candidate": _mean([_hit(candidate[sid]) for sid in ids]),
            "delta": _mean(hit_deltas),
            "bootstrap_ci95": ci(boot_hit),
        },
        "mrr": {
            "baseline": _mean([_reciprocal_rank(baseline[sid]) for sid in ids]),
            "candidate": _mean([_reciprocal_rank(candidate[sid]) for sid in ids]),
            "delta": _mean(mrr_deltas),
            "bootstrap_ci95": ci(boot_mrr),
        },
        "fix_count": len(fixes),
        "regression_count": len(regressions),
        "fix_examples": fixes[:20],
        "regression_examples": regressions[:20],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(
        json.dumps(
            compare(args.baseline, args.candidate, args.output, args.bootstrap_rounds, args.seed),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
