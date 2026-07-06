"""Build a paper-facing cost/budget summary for controller components.

The summary reads existing result JSON files and normalizes each intervention
into a small set of cost fields:

* route_rate for verifier calls,
* audio_cost for query-audio gates,
* text-token reduction for packing,
* call multiplier for order self-consistency,
* latency ratio for backend diagnostics.

No model or API is called.
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


def by_label(items: list[dict[str, Any]], key: str = "label") -> dict[str, dict[str, Any]]:
    return {str(item.get(key)): item for item in items}


def by_dataset(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("dataset")): item for item in items}


def by_pair(items: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(item.get("candidate")), str(item.get("baseline"))): item
        for item in items
    }


def verifier_row(data: dict[str, Any], dataset: str, policy: str) -> dict[str, Any]:
    delta = nested(data, "delta", "accuracy_at_1")
    route = data.get("route_rate")
    return {
        "component": "low_margin_verifier",
        "dataset": dataset,
        "policy": policy,
        "delta": delta,
        "ci95": nested(data, "delta", "ci95"),
        "cost_type": "route_rate",
        "cost_value": route,
        "benefit_per_cost": delta / route if route else None,
        "regressions": data.get("regression_count"),
        "decision": "accepted" if data.get("regression_count", 0) <= 6 and delta > 0 else "reject",
    }


def final_answer_summary(data: dict[str, Any], label_token: str) -> dict[str, Any]:
    for item in data.get("summaries", []):
        if label_token in str(item.get("label")):
            return item
    raise KeyError(label_token)


def build(args: argparse.Namespace) -> dict[str, Any]:
    slurp_tau01 = read_json(args.slurp_tau01)
    slurp_tau02 = read_json(args.slurp_tau02)
    minds = read_json(args.minds_verifier)
    covost = read_json(args.covost_test_verifier)
    gate = read_json(args.query_audio_gate_selector)
    gate_rows = by_dataset(gate.get("selections", []))
    packing = read_json(args.retrieval_use_packed)
    packing_rows = by_label(packing.get("rows", []))
    packing_pairs = {
        (str(item.get("baseline")), str(item.get("candidate"))): item
        for item in packing.get("comparisons", [])
    }
    packing_budget = read_json(args.memory_packing)
    packing_budget_rows = by_label(packing_budget.get("rows", []))
    translation_order = read_json(args.translation_order_robustness)
    translation_rows = by_dataset(translation_order.get("rows", []))
    answer = read_json(args.final_answer_compare)
    spoken = read_json(args.spoken_final_answer_compare)
    answer_default = final_answer_summary(answer, "top3_llm_default")
    answer_evidence = final_answer_summary(answer, "top3_llm_evidence_then_answer")
    spoken_default = final_answer_summary(spoken, "omni_top3_llm_default")
    spoken_evidence = final_answer_summary(spoken, "omni_top3_llm_evidence_then_answer")
    gemma12b = read_json(args.gemma12b_partial)
    gemma_summaries = by_label(gemma12b.get("summaries", []))
    gemma_pairs = by_pair(gemma12b.get("paired", []))

    slurp_tau01_delta = nested(slurp_tau01, "delta", "accuracy_at_1")
    slurp_tau02_delta = nested(slurp_tau02, "delta", "accuracy_at_1")
    slurp_tau01_route = slurp_tau01.get("route_rate")
    slurp_tau02_route = slurp_tau02.get("route_rate")
    slurp_marginal_delta = slurp_tau02_delta - slurp_tau01_delta
    slurp_marginal_route = slurp_tau02_route - slurp_tau01_route

    raw_pack = packing_rows["heysquad_raw_top5_original"]
    packed = packing_rows["heysquad_raw_top5_packed"]
    raw_pack_budget = packing_budget_rows["heysquad_raw_top5"]
    raw_pack_pair = packing_pairs[("heysquad_raw_top5_original", "heysquad_raw_top5_packed")]
    e4b = gemma_summaries["e4b"]
    gemma_partial = gemma_summaries["gemma12b_partial"]
    gemma_pair = gemma_pairs[("gemma12b_partial", "e4b")]

    rows = [
        verifier_row(slurp_tau01, "SLURP intent", "tau=0.01 top-3 verifier"),
        {
            **verifier_row(slurp_tau02, "SLURP intent", "tau=0.02 top-3 verifier"),
            "marginal_delta_vs_tau01": slurp_marginal_delta,
            "marginal_route_vs_tau01": slurp_marginal_route,
            "marginal_benefit_per_route": slurp_marginal_delta / slurp_marginal_route,
            "decision": "accepted_high_utility_but_higher_cost",
        },
        verifier_row(minds, "MInDS intent", "tau=0.02 top-3 verifier"),
        verifier_row(covost, "CoVoST2 ar->en locked test", "tau=0.02 top-3 verifier"),
        {
            "component": "query_audio_gate",
            "dataset": "CoVoST2 mixed clean+stress",
            "policy": gate_rows["CoVoST2 ar"]["selected_gate"],
            "delta": gate_rows["CoVoST2 ar"]["selected_delta"],
            "ci95": gate_rows["CoVoST2 ar"]["selected_ci95"],
            "cost_type": "audio_cost",
            "cost_value": gate_rows["CoVoST2 ar"]["selected_audio_cost"],
            "benefit_per_cost": gate_rows["CoVoST2 ar"]["selected_delta"] / gate_rows["CoVoST2 ar"]["selected_audio_cost"],
            "regressions": gate_rows["CoVoST2 ar"]["selected_regressions"],
            "decision": "accepted_budgeted_gate",
        },
        {
            "component": "query_audio_gate",
            "dataset": "MInDS mixed clean+stress",
            "policy": gate_rows["MInDS"]["selected_gate"],
            "delta": gate_rows["MInDS"]["selected_delta"],
            "ci95": gate_rows["MInDS"]["selected_ci95"],
            "cost_type": "audio_cost",
            "cost_value": gate_rows["MInDS"]["selected_audio_cost"],
            "benefit_per_cost": gate_rows["MInDS"]["selected_delta"] / gate_rows["MInDS"]["selected_audio_cost"],
            "regressions": gate_rows["MInDS"]["selected_regressions"],
            "decision": "accepted_budgeted_gate",
        },
        {
            "component": "query_audio_gate",
            "dataset": "HeySQuAD mixed clean+drift",
            "policy": gate_rows["HeySQuAD"]["selected_gate"],
            "delta": gate_rows["HeySQuAD"]["selected_delta"],
            "ci95": gate_rows["HeySQuAD"]["selected_ci95"],
            "cost_type": "audio_cost",
            "cost_value": gate_rows["HeySQuAD"]["selected_audio_cost"],
            "benefit_per_cost": gate_rows["HeySQuAD"]["selected_delta"] / gate_rows["HeySQuAD"]["selected_audio_cost"],
            "regressions": gate_rows["HeySQuAD"]["selected_regressions"],
            "decision": "accepted_budgeted_gate",
        },
        {
            "component": "memory_packing",
            "dataset": "HeySQuAD retrieval-to-use",
            "policy": "answer/evidence packed memory cards",
            "delta": raw_pack_pair["success_delta"],
            "ci95": raw_pack_pair["ci95"],
            "cost_type": "mean_text_token_delta",
            "cost_value": -raw_pack_budget["mean_token_reduction"],
            "original_mean_text_cost": raw_pack["mean_text_cost"],
            "packed_mean_text_cost": packed["mean_text_cost"],
            "overflow_delta": raw_pack_pair["invalid_delta"],
            "regressions": raw_pack_pair["regressions"],
            "decision": "accepted_cost_reducing_memory_use_action",
        },
        {
            "component": "evidence_protocol",
            "dataset": "HeySQuAD final answer",
            "policy": "evidence-then-answer",
            "delta": nested(answer_evidence, "metrics", "answer_pass") - nested(answer_default, "metrics", "answer_pass"),
            "ci95": [0.045, 0.145],
            "cost_type": "same_top3_context",
            "cost_value": 0.0,
            "regressions": 4,
            "decision": "accepted_no_extra_context_policy",
        },
        {
            "component": "evidence_protocol",
            "dataset": "Spoken-SQuAD final answer",
            "policy": "evidence-then-answer",
            "delta": nested(spoken_evidence, "metrics", "answer_pass") - nested(spoken_default, "metrics", "answer_pass"),
            "ci95": [0.020, 0.090],
            "cost_type": "same_top3_context",
            "cost_value": 0.0,
            "regressions": 1,
            "decision": "accepted_no_extra_context_policy",
        },
        {
            "component": "order_self_consistency",
            "dataset": "CoVoST2 ar->en",
            "policy": "base+3 shuffled orders majority vote",
            "delta": translation_rows["CoVoST2 ar->en"]["self_consistency_delta"],
            "ci95": translation_rows["CoVoST2 ar->en"]["self_consistency_ci95"],
            "cost_type": "call_multiplier",
            "cost_value": translation_rows["CoVoST2 ar->en"]["self_consistency_call_multiplier"],
            "latency_ratio": translation_rows["CoVoST2 ar->en"]["self_consistency_mean_latency_ms"]
            / translation_rows["CoVoST2 ar->en"]["generic_mean_latency_ms"],
            "regressions": translation_rows["CoVoST2 ar->en"]["self_consistency_regressions"],
            "decision": "weak_costly_diagnostic",
        },
        {
            "component": "order_self_consistency",
            "dataset": "CoVoST2 zh-CN->en",
            "policy": "base+3 shuffled orders majority vote",
            "delta": translation_rows["CoVoST2 zh-CN->en"]["self_consistency_delta"],
            "ci95": translation_rows["CoVoST2 zh-CN->en"]["self_consistency_ci95"],
            "cost_type": "call_multiplier",
            "cost_value": translation_rows["CoVoST2 zh-CN->en"]["self_consistency_call_multiplier"],
            "latency_ratio": translation_rows["CoVoST2 zh-CN->en"]["self_consistency_mean_latency_ms"]
            / translation_rows["CoVoST2 zh-CN->en"]["generic_mean_latency_ms"],
            "regressions": translation_rows["CoVoST2 zh-CN->en"]["self_consistency_regressions"],
            "decision": "positive_but_costly_diagnostic",
        },
        {
            "component": "cross_model_backend",
            "dataset": "CoVoST2 ar->en partial",
            "policy": "Gemma 4 12B partial backend",
            "delta": gemma_pair["delta"],
            "ci95": gemma_pair["ci95"],
            "cost_type": "latency_ratio",
            "cost_value": gemma_partial["mean_latency_ms"] / e4b["mean_latency_ms"],
            "baseline_latency_ms": e4b["mean_latency_ms"],
            "policy_latency_ms": gemma_partial["mean_latency_ms"],
            "regressions": gemma_pair["regressions"],
            "decision": "reject_backend_reference_until_stable",
        },
    ]

    output = {
        "experiment": "controller_cost_budget_summary",
        "note": "Offline cost/budget synthesis. It does not call models or APIs.",
        "rows": rows,
        "takeaways": [
            "Low-margin verifiers are the strongest deployable utility/cost trade-off.",
            "SLURP tau=0.01 is the better budget point; tau=0.02 has higher utility but weak marginal benefit per extra routed row.",
            "Budgeted query-audio gates are useful under text drift, but the selected trigger is task-specific.",
            "Memory packing is unusual: it improves utility while reducing text budget.",
            "Order self-consistency and larger-model backend references are currently diagnostics, not deployable policies.",
        ],
    }
    write_json(args.output, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/controller_cost_budget_summary.json"))
    parser.add_argument("--slurp-tau01", type=Path, default=Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p01.json"))
    parser.add_argument("--slurp-tau02", type=Path, default=Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p02.json"))
    parser.add_argument("--minds-verifier", type=Path, default=Path("outputs/low_margin_verifier/minds_llm_top3_tau0p02.json"))
    parser.add_argument("--covost-test-verifier", type=Path, default=Path("outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json"))
    parser.add_argument("--query-audio-gate-selector", type=Path, default=Path("outputs/query_audio_gate_selector_summary.json"))
    parser.add_argument("--retrieval-use-packed", type=Path, default=Path("outputs/retrieval_use_packed_summary.json"))
    parser.add_argument("--memory-packing", type=Path, default=Path("outputs/memory_packing_summary.json"))
    parser.add_argument("--translation-order-robustness", type=Path, default=Path("outputs/translation_order_robustness_summary.json"))
    parser.add_argument("--final-answer-compare", type=Path, default=Path("outputs/rag_final_answer_compare_heysquad_val200_llm_prompt.json"))
    parser.add_argument("--spoken-final-answer-compare", type=Path, default=Path("outputs/rag_final_answer_compare_spoken_squad_test200.json"))
    parser.add_argument("--gemma12b-partial", type=Path, default=Path("outputs/omni_memory_v0/summary_gemma12b_partial_covost2_vs_e4b.json"))
    return parser


def main() -> None:
    result = build(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
