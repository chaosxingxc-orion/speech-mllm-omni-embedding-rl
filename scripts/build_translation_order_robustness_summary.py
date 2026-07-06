"""Summarize CoVoST2 translation memory-use order robustness.

This is an offline synthesis over existing result JSON files.  It checks
whether the translation-target memory-use policy remains useful after
candidate-order perturbation, and whether order self-consistency is a viable
repair.  No model or API is called.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def by_label(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("label")): item for item in items}


def by_pair(items: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(item.get("candidate")), str(item.get("baseline"))): item
        for item in items
    }


def accept_delta(row: dict[str, Any], *, strict_lcb: bool = True) -> bool:
    ci95 = row.get("ci95", [0.0, 0.0])
    lower = float(ci95[0])
    return (
        float(row.get("delta", 0.0)) > 0.0
        and (lower > 0.0 if strict_lcb else lower >= 0.0)
        and float(row.get("regression_rate", 1.0)) <= 0.03
    )


def summarize_dataset(
    *,
    dataset: str,
    shuffle_path: Path,
    self_consistency_path: Path,
) -> dict[str, Any]:
    shuffle = read_json(shuffle_path)
    self_consistency = read_json(self_consistency_path)
    summaries = by_label(shuffle.get("summaries", []))
    paired = by_pair(shuffle.get("paired", []))
    self_summaries = by_label(self_consistency.get("summaries", []))
    self_paired = by_pair(self_consistency.get("paired", []))

    base_pair = paired[("trans_base", "generic_base")]
    seed_pairs = [
        paired[("trans_s7", "generic_s7")],
        paired[("trans_s17", "generic_s17")],
        paired[("trans_s29", "generic_s29")],
    ]
    seed_deltas = [float(item["delta"]) for item in seed_pairs]
    seed_ci_lowers = [float(item["ci95"][0]) for item in seed_pairs]
    seed_regressions = [int(item["regressions"]) for item in seed_pairs]
    seed_regression_rates = [float(item["regression_rate"]) for item in seed_pairs]
    seed_accept_count = sum(accept_delta(item) for item in seed_pairs)
    self_pair = self_paired[("self", "generic")]
    self_summary = self_summaries["self"]
    generic_summary = self_summaries["generic"]
    all_shuffle_strict = seed_accept_count == len(seed_pairs)
    same_order_accepted = accept_delta(base_pair)
    self_strict = accept_delta(self_pair)
    self_weak = accept_delta(self_pair, strict_lcb=False)

    if all_shuffle_strict:
        decision = "order_robust_accept"
    elif self_strict:
        decision = "self_consistency_positive_but_costly"
    elif self_weak:
        decision = "self_consistency_weak_costly_diagnostic"
    elif same_order_accepted:
        decision = "same_order_positive_order_sensitive"
    else:
        decision = "reject_translation_memory_use_policy"

    return {
        "dataset": dataset,
        "n": int(base_pair["n"]),
        "generic_base_success": summaries["generic_base"]["success"],
        "translation_base_success": summaries["trans_base"]["success"],
        "same_order_delta": base_pair["delta"],
        "same_order_ci95": base_pair["ci95"],
        "same_order_fixes": base_pair["fixes"],
        "same_order_regressions": base_pair["regressions"],
        "same_order_regression_rate": base_pair["regression_rate"],
        "same_order_accepted": same_order_accepted,
        "shuffle_delta_mean": sum(seed_deltas) / len(seed_deltas),
        "shuffle_delta_min": min(seed_deltas),
        "shuffle_delta_max": max(seed_deltas),
        "shuffle_ci_lower_min": min(seed_ci_lowers),
        "shuffle_seed_accept_count": seed_accept_count,
        "shuffle_seed_count": len(seed_pairs),
        "shuffle_regressions_total": sum(seed_regressions),
        "shuffle_regression_rate_max": max(seed_regression_rates),
        "order_robust": all_shuffle_strict,
        "self_consistency_success": self_summary["success"],
        "self_consistency_delta": self_pair["delta"],
        "self_consistency_ci95": self_pair["ci95"],
        "self_consistency_fixes": self_pair["fixes"],
        "self_consistency_regressions": self_pair["regressions"],
        "self_consistency_regression_rate": self_pair["regression_rate"],
        "self_consistency_mean_latency_ms": self_summary["mean_latency_ms"],
        "generic_mean_latency_ms": generic_summary["mean_latency_ms"],
        "self_consistency_call_multiplier": self_summary["mean_audio_cost"],
        "self_consistency_strict_accept": self_strict,
        "self_consistency_weak_accept": self_weak,
        "decision": decision,
        "sources": {
            "shuffle": str(shuffle_path),
            "self_consistency": str(self_consistency_path),
        },
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = [
        summarize_dataset(
            dataset="CoVoST2 ar->en",
            shuffle_path=args.covost_ar_shuffle,
            self_consistency_path=args.covost_ar_self_consistency,
        ),
        summarize_dataset(
            dataset="CoVoST2 zh-CN->en",
            shuffle_path=args.covost_zh_shuffle,
            self_consistency_path=args.covost_zh_self_consistency,
        ),
    ]
    output = {
        "experiment": "translation_order_robustness_summary",
        "note": "Offline order-robustness synthesis for CoVoST2 translation memory-use.",
        "accept_rule": {
            "same_order": "delta > 0, CI lower > 0, regression_rate <= 0.03",
            "order_robust": "same rule must hold for all candidate-order shuffle seeds",
            "self_consistency": "same rule over majority vote vs generic baseline; cost reported separately",
        },
        "rows": rows,
        "takeaways": [
            "Translation-target memory-use is positive on the base candidate order.",
            "The policy is not order-robust across all shuffle seeds.",
            "Order self-consistency can recover a positive signal, especially for zh-CN->en, but costs four calls per row.",
            "This should be reported as an order-sensitive diagnostic, not as a headline deployed policy.",
        ],
    }
    write_json(args.output, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/translation_order_robustness_summary.json"))
    parser.add_argument(
        "--covost-ar-shuffle",
        type=Path,
        default=Path("outputs/omni_memory_v0/summary_shuffle_covost2_ar_translation_vs_generic.json"),
    )
    parser.add_argument(
        "--covost-zh-shuffle",
        type=Path,
        default=Path("outputs/omni_memory_v0/summary_shuffle_covost2_zh_translation_vs_generic.json"),
    )
    parser.add_argument(
        "--covost-ar-self-consistency",
        type=Path,
        default=Path("outputs/omni_memory_v0/summary_order_self_consistency_covost2_ar_vs_generic.json"),
    )
    parser.add_argument(
        "--covost-zh-self-consistency",
        type=Path,
        default=Path("outputs/omni_memory_v0/summary_order_self_consistency_covost2_zh_vs_generic.json"),
    )
    return parser


def main() -> None:
    result = build(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
