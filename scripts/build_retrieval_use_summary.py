"""Summarize retrieve-then-use memory experiments.

The input files are row-level outputs from ``omni_memory_use_eval.py`` plus the
manifest construction reports from ``build_memory_use_manifest_from_retrieval``.
The script is fully offline: it does not call models or APIs.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RUNS = [
    {
        "label": "heysquad_raw_top5",
        "result": Path("outputs/omni_memory_v0/heysquad_retrieval_raw_top5_use_gemma4e4b_server_200.json"),
        "report": Path("outputs/omni_memory_v0/heysquad_retrieval_raw_top5_memory_use_200.report.json"),
    },
    {
        "label": "heysquad_policy_grounding_top5",
        "result": Path(
            "outputs/omni_memory_v0/heysquad_retrieval_policy_grounding_top5_use_gemma4e4b_server_200.json"
        ),
        "report": Path("outputs/omni_memory_v0/heysquad_retrieval_policy_grounding_top5_memory_use_200.report.json"),
    },
]


@dataclass(frozen=True)
class RunSpec:
    label: str
    result: Path
    report: Path | None = None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bootstrap_ci(diffs: list[int], rounds: int = 5000, seed: int = 13) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def gold_in_context(row: dict[str, Any]) -> bool:
    gold = str(row.get("gold_memory_id") or "")
    candidates = [str(item) for item in row.get("candidate_memory_ids", [])]
    return bool(gold) and gold in candidates


def is_context_overflow(row: dict[str, Any]) -> bool:
    output = str(row.get("model_output") or "")
    return "exceeds the available context size" in output or "exceed_context_size" in output


def summarize_run(spec: RunSpec) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    result = read_json(spec.result)
    report = read_json(spec.report) if spec.report and spec.report.exists() else {}
    rows = result.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError(f"{spec.result} has no row list")

    by_id = {str(row.get("query_id") or row.get("sample_id")): row for row in rows}
    n = len(rows)
    if n == 0:
        raise ValueError(f"{spec.result} has no rows")

    hits = [gold_in_context(row) for row in rows]
    success = [bool(row.get("task_success")) for row in rows]
    invalid = [bool(row.get("invalid_output")) for row in rows]
    wrong = [bool(row.get("wrong_memory")) for row in rows]
    overflow = [is_context_overflow(row) for row in rows]
    hit_but_use_fail = [hits[i] and not success[i] for i in range(n)]
    retrieval_miss = [not hits[i] for i in range(n)]
    miss_but_success = [not hits[i] and success[i] for i in range(n)]

    return (
        {
            "label": spec.label,
            "result": str(spec.result),
            "report": str(spec.report) if spec.report else "",
            "n": n,
            "top_k": report.get("top_k"),
            "retrieval_hit_at_k": sum(hits) / n,
            "reported_retrieval_hit_at_k": report.get("retrieval_hit_at_k"),
            "memory_use_success": sum(success) / n,
            "hit_but_use_fail": sum(hit_but_use_fail) / n,
            "retrieval_miss": sum(retrieval_miss) / n,
            "miss_but_success": sum(miss_but_success) / n,
            "invalid_output": sum(invalid) / n,
            "wrong_memory": sum(wrong) / n,
            "context_overflow_rate": sum(overflow) / n,
            "mean_text_cost": result.get("mean_text_cost"),
            "mean_audio_cost": result.get("mean_audio_cost"),
            "mean_latency_ms": result.get("mean_latency_ms"),
        },
        by_id,
    )


def paired_compare(
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    *,
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    invalid_diffs: list[int] = []
    for key, base in baseline.items():
        cand = candidate.get(key)
        if not cand:
            continue
        diff = int(bool(cand.get("task_success"))) - int(bool(base.get("task_success")))
        diffs.append(diff)
        fixes += diff > 0
        regressions += diff < 0
        invalid_diffs.append(int(bool(cand.get("invalid_output"))) - int(bool(base.get("invalid_output"))))
    return {
        "paired_n": len(diffs),
        "success_delta": sum(diffs) / len(diffs) if diffs else 0.0,
        "ci95": bootstrap_ci(diffs, rounds=rounds, seed=seed),
        "fixes": fixes,
        "regressions": regressions,
        "invalid_delta": sum(invalid_diffs) / len(invalid_diffs) if invalid_diffs else 0.0,
    }


def parse_run_specs(path: Path | None) -> list[RunSpec]:
    if not path:
        return [RunSpec(label=item["label"], result=item["result"], report=item["report"]) for item in DEFAULT_RUNS]
    payload = read_json(path)
    specs = []
    for item in payload.get("runs", []):
        specs.append(
            RunSpec(
                label=str(item["label"]),
                result=Path(str(item["result"])),
                report=Path(str(item["report"])) if item.get("report") else None,
            )
        )
    return specs


def run(args: argparse.Namespace) -> dict[str, Any]:
    specs = parse_run_specs(args.run_config)
    rows = []
    row_maps: dict[str, dict[str, dict[str, Any]]] = {}
    for spec in specs:
        summary, by_id = summarize_run(spec)
        rows.append(summary)
        row_maps[spec.label] = by_id

    comparisons = []
    baseline_label = args.baseline.strip()
    if baseline_label.lower() in {"", "none", "null"}:
        baseline_label = ""
    if baseline_label and baseline_label in row_maps:
        baseline = row_maps[baseline_label]
        for spec in specs:
            if spec.label == baseline_label:
                continue
            comparisons.append(
                {
                    "baseline": baseline_label,
                    "candidate": spec.label,
                    **paired_compare(
                        baseline,
                        row_maps[spec.label],
                        rounds=args.bootstrap_rounds,
                        seed=args.bootstrap_seed,
                    ),
                }
            )
    elif baseline_label:
        comparisons.append(
            {
                "baseline": baseline_label,
                "error": "baseline label not found in run_config; skipped paired comparison",
            }
        )

    output = {
        "experiment": "retrieval_use_summary",
        "rows": rows,
        "comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/retrieval_use_summary.json"))
    parser.add_argument("--run-config", type=Path)
    parser.add_argument("--baseline", default="heysquad_raw_top5")
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=13)
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
