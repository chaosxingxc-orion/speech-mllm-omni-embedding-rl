"""Build an audited clean-vs-dialect route summary from legacy artifacts.

The underlying row-level/model outputs live in the legacy archive under
``omni_embedding/``.  This script extracts only aggregate numbers needed by the
paper-facing route-reliability table and writes a sanitized outer-repo output.

It intentionally does not preserve absolute paths found inside legacy JSON
files, because tracked docs should remain machine-independent.
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


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def policy_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("policy")): item for item in data.get("leaderboard", [])}


def summarize_dataset(
    *,
    dataset: str,
    condition: str,
    route_path: Path,
    hybrid_path: Path,
    preferred_policy: str,
    rejected_policy: str,
    source_note: str,
) -> dict[str, Any]:
    route = read_json(route_path)
    hybrid = read_json(hybrid_path)
    policies = policy_map(route)
    preferred = policies[preferred_policy]
    rejected = policies[rejected_policy]
    asr = policies["asr_primary"]
    omni = policies["omni_primary"]
    rrf = policies["rrf"]
    return {
        "dataset": dataset,
        "condition": condition,
        "n": route.get("n"),
        "legacy_sources": {
            "route": str(route_path).replace("\\", "/"),
            "hybrid": str(hybrid_path).replace("\\", "/"),
        },
        "source_note": source_note,
        "asr_quality_test": {
            "mean_wer": nested(hybrid, "asr", "quality_test", "mean_wer"),
            "mean_cer": nested(hybrid, "asr", "quality_test", "mean_cer"),
            "exact_text_match": nested(hybrid, "asr", "quality_test", "exact_text_match"),
        },
        "route_signal": {
            "disagreement_route_rate": nested(route, "source_metrics", "routing", "disagreement", "route_rate"),
            "disagreement_failure_recall": nested(route, "source_metrics", "routing", "disagreement", "failure_recall"),
            "low_confidence_route_rate": nested(route, "source_metrics", "routing", "low_confidence", "route_rate"),
            "low_asr_margin_route_rate": nested(route, "source_metrics", "routing", "low_asr_margin", "route_rate"),
        },
        "policies": {
            "asr_primary": {
                "acc_at_1": asr.get("acc_at_1"),
                "recall_at_3": asr.get("recall_at_3"),
                "mrr": asr.get("mrr"),
            },
            "omni_primary": {
                "acc_at_1": omni.get("acc_at_1"),
                "recall_at_3": omni.get("recall_at_3"),
                "mrr": omni.get("mrr"),
                "delta_vs_asr": omni.get("delta_vs_asr"),
                "ci95_vs_asr": [omni.get("lcb_vs_asr"), omni.get("ucb_vs_asr")],
                "rescues": omni.get("rescue_count"),
                "regressions": omni.get("regression_count"),
            },
            "rrf": {
                "acc_at_1": rrf.get("acc_at_1"),
                "recall_at_3": rrf.get("recall_at_3"),
                "mrr": rrf.get("mrr"),
                "delta_vs_asr": rrf.get("delta_vs_asr"),
                "ci95_vs_asr": [rrf.get("lcb_vs_asr"), rrf.get("ucb_vs_asr")],
                "rescues": rrf.get("rescue_count"),
                "regressions": rrf.get("regression_count"),
            },
            preferred_policy: {
                "acc_at_1": preferred.get("acc_at_1"),
                "recall_at_3": preferred.get("recall_at_3"),
                "mrr": preferred.get("mrr"),
                "route_rate": preferred.get("route_rate"),
                "delta_vs_asr": preferred.get("delta_vs_asr"),
                "ci95_vs_asr": [preferred.get("lcb_vs_asr"), preferred.get("ucb_vs_asr")],
                "rescues": preferred.get("rescue_count"),
                "regressions": preferred.get("regression_count"),
            },
            rejected_policy: {
                "acc_at_1": rejected.get("acc_at_1"),
                "recall_at_3": rejected.get("recall_at_3"),
                "mrr": rejected.get("mrr"),
                "route_rate": rejected.get("route_rate"),
                "delta_vs_asr": rejected.get("delta_vs_asr"),
                "ci95_vs_asr": [rejected.get("lcb_vs_asr"), rejected.get("ucb_vs_asr")],
                "rescues": rejected.get("rescue_count"),
                "regressions": rejected.get("regression_count"),
            },
        },
        "decision": {
            "preferred_policy": preferred_policy,
            "rejected_default": rejected_policy,
            "reason": (
                "ASR remains primary on clean Mandarin; direct omni becomes primary under "
                "Wu dialect ASR collapse. Naive RRF is not a universal repair."
            ),
        },
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = [
        summarize_dataset(
            dataset="AISHELL-1",
            condition="clean_mandarin",
            route_path=args.aishell_route,
            hybrid_path=args.aishell_hybrid,
            preferred_policy="asr_primary",
            rejected_policy="omni_primary",
            source_note="Legacy recognized-source clean Mandarin route evaluation.",
        ),
        summarize_dataset(
            dataset="WenetSpeech-Wu",
            condition="dialect_stress",
            route_path=args.wu_route,
            hybrid_path=args.wu_hybrid,
            preferred_policy="omni_primary",
            rejected_policy="rrf",
            source_note="Legacy Wu/Shanghainese dialect stress route evaluation.",
        ),
    ]
    output = {
        "experiment": "dialect_route_summary",
        "note": (
            "Offline sanitized summary of legacy AISHELL/WenetSpeech-Wu route "
            "artifacts. No model or API is called."
        ),
        "rows": rows,
        "headline": {
            "aishell_asr_acc": rows[0]["policies"]["asr_primary"]["acc_at_1"],
            "aishell_omni_acc": rows[0]["policies"]["omni_primary"]["acc_at_1"],
            "aishell_omni_delta": rows[0]["policies"]["omni_primary"]["delta_vs_asr"],
            "aishell_omni_regressions": rows[0]["policies"]["omni_primary"]["regressions"],
            "wu_asr_acc": rows[1]["policies"]["asr_primary"]["acc_at_1"],
            "wu_omni_acc": rows[1]["policies"]["omni_primary"]["acc_at_1"],
            "wu_omni_delta": rows[1]["policies"]["omni_primary"]["delta_vs_asr"],
            "wu_omni_regressions": rows[1]["policies"]["omni_primary"]["regressions"],
            "wu_rrf_acc": rows[1]["policies"]["rrf"]["acc_at_1"],
            "wu_rrf_delta": rows[1]["policies"]["rrf"]["delta_vs_asr"],
            "wu_asr_test_cer": rows[1]["asr_quality_test"]["mean_cer"],
        },
    }
    write_json(args.output, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/dialect_route_summary.json"))
    parser.add_argument(
        "--aishell-route",
        type=Path,
        default=Path("omni_embedding/experiments/results/agentic_route_policy_aishell1_hf_180.json"),
    )
    parser.add_argument(
        "--aishell-hybrid",
        type=Path,
        default=Path("omni_embedding/experiments/results/audio_memory_hybrid_aishell1_hf_180_qwen3_asr_omni_rrf.json"),
    )
    parser.add_argument(
        "--wu-route",
        type=Path,
        default=Path("omni_embedding/experiments/results/agentic_route_policy_wenetspeech_wu_bench_60.json"),
    )
    parser.add_argument(
        "--wu-hybrid",
        type=Path,
        default=Path(
            "omni_embedding/experiments/results/audio_memory_hybrid_wenetspeech_wu_bench_60_qwen3_asr_omni_rrf.json"
        ),
    )
    return parser


def main() -> None:
    result = build(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
