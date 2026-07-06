#!/usr/bin/env python
"""Build clean+stress mixture summaries for query-audio gates.

The query-audio gate evaluator emits per-condition summaries and paired
fix/regression counts.  This script combines clean and stress reports into a
deployment-style mixture without rerunning any model.  It reconstructs paired
diff lists from fix/regression counts so the combined delta still has a
bootstrap confidence interval.
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


def by_gate(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["gate"]): item for item in items}


def bootstrap_ci(diffs: list[int], rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def diff_list(paired: dict[str, Any]) -> list[int]:
    n = int(paired.get("paired_n", 0))
    fixes = int(paired.get("fixes", 0))
    regressions = int(paired.get("regressions", paired.get("paired_regressions", 0)))
    zeros = max(0, n - fixes - regressions)
    return [1] * fixes + [-1] * regressions + [0] * zeros


def weighted_metric(parts: list[dict[str, Any]], key: str) -> float:
    total = sum(int(part.get("n", 0)) for part in parts)
    if total == 0:
        return 0.0
    return sum(float(part.get(key, 0.0)) * int(part.get("n", 0)) for part in parts) / total


def combine_pair(dataset: str, clean_path: Path, stress_path: Path, gates: list[str], args: argparse.Namespace) -> list[dict[str, Any]]:
    clean = read_json(clean_path)
    stress = read_json(stress_path)
    clean_summary = by_gate(clean["summaries"])
    stress_summary = by_gate(stress["summaries"])
    clean_paired = by_gate(clean.get("paired_vs_text", []))
    stress_paired = by_gate(stress.get("paired_vs_text", []))

    rows: list[dict[str, Any]] = []
    for gate in gates:
        c_sum = clean_summary[gate]
        s_sum = stress_summary[gate]
        diffs = diff_list(clean_paired.get(gate, {})) + diff_list(stress_paired.get(gate, {}))
        n = len(diffs)
        rows.append(
            {
                "dataset": dataset,
                "gate": gate,
                "clean_n": c_sum.get("n"),
                "stress_n": s_sum.get("n"),
                "n": n,
                "mixed_success": weighted_metric([c_sum, s_sum], "success"),
                "mixed_wrong_memory": weighted_metric([c_sum, s_sum], "wrong_memory"),
                "mixed_gate_rate": weighted_metric([c_sum, s_sum], "gate_rate"),
                "mixed_audio_cost": weighted_metric([c_sum, s_sum], "mean_decision_audio_cost"),
                "mixed_latency_ms": weighted_metric([c_sum, s_sum], "mean_decision_latency_ms"),
                "delta_vs_text": sum(diffs) / n if n else 0.0,
                "ci95": bootstrap_ci(diffs, args.bootstrap_rounds, args.bootstrap_seed),
                "fixes": sum(1 for item in diffs if item > 0),
                "regressions": sum(1 for item in diffs if item < 0),
                "regression_rate": sum(1 for item in diffs if item < 0) / n if n else 0.0,
                "clean_success": c_sum.get("success"),
                "stress_success": s_sum.get("success"),
            }
        )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    gates = args.gate or [
        "audio_only",
        "audio_on_text_audio_disagreement",
        "audio_on_text_equals_noquery",
        "audio_on_hint_pred_overlap_ge_0_80",
    ]
    rows: list[dict[str, Any]] = []
    rows.extend(combine_pair("CoVoST2 ar", args.covost_clean, args.covost_stress, gates, args))
    rows.extend(combine_pair("MInDS", args.minds_clean, args.minds_stress, gates, args))
    rows.extend(combine_pair("HeySQuAD", args.heysquad_clean, args.heysquad_stress, gates, args))
    result = {
        "experiment": "build_query_audio_gate_mixture",
        "inputs": {
            "covost_clean": str(args.covost_clean),
            "covost_stress": str(args.covost_stress),
            "minds_clean": str(args.minds_clean),
            "minds_stress": str(args.minds_stress),
            "heysquad_clean": str(args.heysquad_clean),
            "heysquad_stress": str(args.heysquad_stress),
        },
        "gates": gates,
        "rows": rows,
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/query_audio_gate_mixture_summary.json"))
    parser.add_argument("--covost-clean", type=Path, default=Path("outputs/omni_memory_v0/query_audio_gate_covost2_clean_manifest_200.json"))
    parser.add_argument("--covost-stress", type=Path, default=Path("outputs/omni_memory_v0/query_audio_gate_covost2_neighbor_text_manifest_60.json"))
    parser.add_argument("--minds-clean", type=Path, default=Path("outputs/omni_memory_v0/query_audio_gate_minds14_clean_manifest_180.json"))
    parser.add_argument("--minds-stress", type=Path, default=Path("outputs/omni_memory_v0/query_audio_gate_minds14_neighbor_text_manifest_60.json"))
    parser.add_argument("--heysquad-clean", type=Path, default=Path("outputs/omni_memory_v0/query_audio_gate_heysquad_clean_manifest_200.json"))
    parser.add_argument("--heysquad-stress", type=Path, default=Path("outputs/omni_memory_v0/query_audio_gate_heysquad_natural_drift_manifest_60.json"))
    parser.add_argument("--gate", action="append")
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=37)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
