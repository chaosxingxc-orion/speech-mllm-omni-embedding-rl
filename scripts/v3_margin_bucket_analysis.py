"""Analyze low-margin rescue and high-margin regression for policy candidates.

The script reads row-level retrieval JSON files produced by the frozen
retrieval runners.  It does not run models and does not modify weights.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(report.get("rows"), list):
        return report["rows"]
    metrics = report.get("metrics", {})
    if isinstance(metrics, dict):
        for key in ("test", "omni_audio"):
            payload = metrics.get(key)
            if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
                return payload["rows"]
    raise ValueError("Result JSON does not contain a supported row-level payload.")


def sample_id(row: dict[str, Any]) -> str:
    value = row.get("sample_id", row.get("id"))
    if value is None:
        raise ValueError(f"Row has no sample_id/id: {row}")
    return str(value)


def rank_value(row: dict[str, Any], hit_mode: str) -> int:
    if hit_mode == "text" and "text_rank" in row:
        return int(row["text_rank"])
    if hit_mode == "sample" and "sample_rank" in row:
        return int(row["sample_rank"])
    for key in ("text_rank", "sample_rank", "rank", "omni_rank"):
        if key in row:
            return int(row[key])
    raise ValueError(f"Cannot infer rank from row keys: {sorted(row)}")


def hit_at_1(row: dict[str, Any], hit_mode: str) -> int:
    if hit_mode == "text" and "text_hit_at_1" in row:
        return 1 if row["text_hit_at_1"] else 0
    if hit_mode == "sample" and "sample_hit_at_1" in row:
        return 1 if row["sample_hit_at_1"] else 0
    if "hit_at_1" in row:
        return 1 if row["hit_at_1"] else 0
    return 1 if rank_value(row, hit_mode) == 1 else 0


def reciprocal_rank(row: dict[str, Any], hit_mode: str) -> float:
    rank = rank_value(row, hit_mode)
    return 1.0 / rank if rank > 0 else 0.0


def score_margin(row: dict[str, Any]) -> float | None:
    scores = row.get("scores")
    if not isinstance(scores, list) or len(scores) < 2:
        return None
    try:
        return float(scores[0]["score"]) - float(scores[1]["score"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_candidate(text: str) -> tuple[str, Path]:
    if "=" not in text:
        raise ValueError(f"candidate must be name=path, got {text!r}")
    name, path = text.split("=", 1)
    return name.strip(), Path(path.strip())


def bucket_for_rank(rank: int, bucket_count: int) -> str:
    return f"q{rank + 1}"


def safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline_name, baseline_path = parse_candidate(args.baseline)
    baseline_rows = {
        sample_id(row): row for row in rows_from_report(read_json(baseline_path))
    }
    candidates = []
    for item in args.candidate:
        name, path = parse_candidate(item)
        candidates.append((name, {sample_id(row): row for row in rows_from_report(read_json(path))}))

    common_ids = sorted(set(baseline_rows).intersection(*(set(rows) for _, rows in candidates)))
    margins = [(sample, score_margin(baseline_rows[sample])) for sample in common_ids]
    margins = [(sample, margin) for sample, margin in margins if margin is not None]
    if not margins:
        raise ValueError("No baseline rows have top-2 score margins.")
    margins.sort(key=lambda item: item[1])
    bucket_count = min(args.bucket_count, len(margins))
    bucket_by_id = {}
    for idx, (sample, _) in enumerate(margins):
        bucket_rank = min(bucket_count - 1, idx * bucket_count // len(margins))
        bucket_by_id[sample] = bucket_for_rank(bucket_rank, bucket_count)

    rows: list[dict[str, Any]] = []
    for name, candidate_rows in candidates:
        for bucket in [bucket_for_rank(index, bucket_count) for index in range(bucket_count)]:
            ids = [sample for sample, label in bucket_by_id.items() if label == bucket]
            base_hits = [hit_at_1(baseline_rows[sample], args.hit_mode) for sample in ids]
            cand_hits = [hit_at_1(candidate_rows[sample], args.hit_mode) for sample in ids]
            hit_delta = [cand - base for base, cand in zip(base_hits, cand_hits, strict=True)]
            mrr_delta = [
                reciprocal_rank(candidate_rows[sample], args.hit_mode)
                - reciprocal_rank(baseline_rows[sample], args.hit_mode)
                for sample in ids
            ]
            rows.append(
                {
                    "candidate": name,
                    "bucket": bucket,
                    "n": len(ids),
                    "baseline_acc": safe_mean([float(value) for value in base_hits]),
                    "candidate_acc": safe_mean([float(value) for value in cand_hits]),
                    "hit_delta": safe_mean([float(value) for value in hit_delta]),
                    "mrr_delta": safe_mean(mrr_delta),
                    "fix_count": sum(1 for value in hit_delta if value > 0),
                    "regression_count": sum(1 for value in hit_delta if value < 0),
                    "mean_margin": safe_mean([float(score_margin(baseline_rows[sample]) or 0) for sample in ids]),
                }
            )

    summary_rows = []
    high_bucket = bucket_for_rank(bucket_count - 1, bucket_count)
    low_bucket = bucket_for_rank(0, bucket_count)
    for name, _ in candidates:
        candidate_bucket_rows = [row for row in rows if row["candidate"] == name]
        low = next(row for row in candidate_bucket_rows if row["bucket"] == low_bucket)
        high = next(row for row in candidate_bucket_rows if row["bucket"] == high_bucket)
        all_ids = list(bucket_by_id)
        cand_rows = dict(candidates)[name]
        all_hit_delta = [
            hit_at_1(cand_rows[sample], args.hit_mode) - hit_at_1(baseline_rows[sample], args.hit_mode)
            for sample in all_ids
        ]
        summary_rows.append(
            {
                "candidate": name,
                "n": len(all_ids),
                "overall_hit_delta": safe_mean([float(value) for value in all_hit_delta]),
                "overall_fix_count": sum(1 for value in all_hit_delta if value > 0),
                "overall_regression_count": sum(1 for value in all_hit_delta if value < 0),
                "low_margin_hit_delta": low["hit_delta"],
                "low_margin_fix_count": low["fix_count"],
                "low_margin_regression_count": low["regression_count"],
                "high_margin_hit_delta": high["hit_delta"],
                "high_margin_fix_count": high["fix_count"],
                "high_margin_regression_count": high["regression_count"],
            }
        )

    report = {
        "experiment": "v3_margin_bucket_analysis",
        "baseline": {"name": baseline_name, "path": str(baseline_path)},
        "config": {
            "bucket_count": bucket_count,
            "hit_mode": args.hit_mode,
            "margin_source": "baseline_top2_score_gap",
        },
        "summary": summary_rows,
        "buckets": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = args.output.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="name=path")
    parser.add_argument("--candidate", action="append", required=True, help="name=path")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hit-mode", choices=("text", "sample", "auto"), default="text")
    parser.add_argument("--bucket-count", type=int, default=4)
    return parser


def main() -> None:
    report = run(build_parser().parse_args())
    print(json.dumps({"experiment": report["experiment"], "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
