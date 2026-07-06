"""Verify paper-facing evidence numbers against row-level/result JSON files.

This script is intentionally small and conservative.  It does not call any
model or API.  It reads existing ignored outputs and checks that the core
numbers used by `docs/paper_evidence_tables.md` still match their source
artifacts within a small tolerance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


TOL = 7e-4


@dataclass(frozen=True)
class Check:
    name: str
    source: Path
    extractor: Callable[[dict[str, Any]], dict[str, Any]]
    expected: dict[str, Any]
    note: str = ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def is_close(observed: Any, expected: Any) -> bool:
    if isinstance(expected, float):
        return isinstance(observed, (int, float)) and abs(float(observed) - expected) <= TOL
    if isinstance(expected, list):
        return (
            isinstance(observed, list)
            and len(observed) == len(expected)
            and all(is_close(obs, exp) for obs, exp in zip(observed, expected, strict=True))
        )
    return observed == expected


def compare(observed: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, list[str]]:
    mismatches = []
    for key, exp_value in expected.items():
        obs_value = observed.get(key)
        if not is_close(obs_value, exp_value):
            mismatches.append(f"{key}: expected {exp_value!r}, observed {obs_value!r}")
    return not mismatches, mismatches


def low_margin_metrics(data: dict[str, Any]) -> dict[str, Any]:
    out = {
        "n": data.get("sample_count"),
        "raw_acc": nested(data, "base_metrics", "accuracy_at_1"),
        "policy_acc": nested(data, "metrics", "accuracy_at_1"),
        "delta": nested(data, "delta", "accuracy_at_1"),
        "ci95": nested(data, "delta", "ci95"),
        "route_rate": data.get("route_rate"),
        "fixes": data.get("fix_count"),
        "regressions": data.get("regression_count"),
    }
    tool_utility = data.get("tool_utility")
    if isinstance(tool_utility, dict):
        out.update(
            {
                "tool_call_success": tool_utility.get("tool_call_success"),
                "unsafe_wrong_tool_rate": tool_utility.get("unsafe_wrong_tool_rate"),
                "boundary_error_rate": tool_utility.get("boundary_error_rate"),
            }
        )
    return out


def low_margin_ablation_policy_metric(policy: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("policy")): item for item in data.get("summaries", [])}
        item = rows[policy]
        return {
            "sample_count": item.get("sample_count"),
            "route_rate": item.get("route_rate"),
            "policy_acc": nested(item, "metrics", "accuracy_at_1"),
            "delta": nested(item, "delta", "accuracy_at_1"),
            "ci95": nested(item, "delta", "ci95"),
            "fixes": item.get("fix_count"),
            "regressions": item.get("regression_count"),
        }

    return extract


def slurp_gate_metrics(data: dict[str, Any]) -> dict[str, Any]:
    locked = data["locked"]
    return {
        "n": locked.get("n"),
        "policy_acc": locked.get("accuracy_at_1"),
        "delta": locked.get("delta"),
        "ci95": locked.get("ci95"),
        "route_rate": locked.get("route_rate"),
        "fixes": locked.get("fixes"),
        "regressions": locked.get("regressions"),
    }


def paired_compare_metric(label: str, baseline_label: str | None = None) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summaries = {item["label"]: item for item in data.get("summaries", [])}
        summary = summaries[label]
        metrics = summary["metrics"]
        out = {
            "answer_pass": metrics.get("answer_pass"),
            "generation_miss": metrics.get("generation_error_rate"),
        }
        if baseline_label:
            for comparison in data.get("comparisons", []):
                if comparison.get("candidate") == label and comparison.get("baseline") == baseline_label:
                    answer = comparison["answer_pass"]
                    context = comparison["context_gold"]
                    grounded = comparison["grounded_exact"]
                    out.update(
                        {
                            "delta": answer.get("delta"),
                            "ci95": answer.get("ci95"),
                            "fixes": answer.get("fixes"),
                            "regressions": answer.get("regressions"),
                            "context_delta": context.get("delta"),
                            "context_ci95": context.get("ci95"),
                            "grounded_delta": grounded.get("delta"),
                            "grounded_ci95": grounded.get("ci95"),
                            "grounded_fixes": grounded.get("fixes"),
                            "grounded_regressions": grounded.get("regressions"),
                        }
                    )
                    break
        return out

    return extract


def paired_compare_decomposition_metric(
    label: str,
    baseline_label: str | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summaries = {item["label"]: item for item in data.get("summaries", [])}
        summary = summaries[label]
        out = {
            "answer_pass": nested(summary, "metrics", "answer_pass"),
            "generation_miss_rate": nested(summary, "decomposition", "generation_miss_rate"),
            "context_gold_rate": nested(summary, "decomposition", "context_gold_rate"),
        }
        if baseline_label:
            for comparison in data.get("comparisons", []):
                if comparison.get("candidate") == label and comparison.get("baseline") == baseline_label:
                    answer = comparison["answer_pass"]
                    context = comparison["context_gold"]
                    grounded = comparison["grounded_exact"]
                    out.update(
                        {
                            "delta": answer.get("delta"),
                            "ci95": answer.get("ci95"),
                            "fixes": answer.get("fixes"),
                            "regressions": answer.get("regressions"),
                            "context_delta": context.get("delta"),
                            "context_ci95": context.get("ci95"),
                            "grounded_delta": grounded.get("delta"),
                            "grounded_ci95": grounded.get("ci95"),
                            "grounded_fixes": grounded.get("fixes"),
                            "grounded_regressions": grounded.get("regressions"),
                        }
                    )
                    break
        return out

    return extract


def answer_order_shuffle_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summaries = data.get("summaries", [])
        base = summaries[0]
        shuffles = summaries[1:]
        shuffle_scores = [nested(item, "metrics", "answer_pass") for item in shuffles]
        comparisons = data.get("comparisons", [])
        deltas = [nested(item, "answer_pass", "delta") for item in comparisons]
        ci_lowers = [nested(item, "answer_pass", "ci95", default=[0.0, 0.0])[0] for item in comparisons]
        fixes = [nested(item, "answer_pass", "fixes") for item in comparisons]
        regressions = [nested(item, "answer_pass", "regressions") for item in comparisons]
        context_deltas = [nested(item, "context_gold", "delta") for item in comparisons]
        return {
            "n": nested(base, "metrics", "n"),
            "base_answer_pass": nested(base, "metrics", "answer_pass"),
            "shuffle_count": len(shuffles),
            "shuffle_answer_pass_mean": sum(shuffle_scores) / len(shuffle_scores) if shuffle_scores else 0.0,
            "shuffle_answer_pass_min": min(shuffle_scores) if shuffle_scores else 0.0,
            "shuffle_answer_pass_max": max(shuffle_scores) if shuffle_scores else 0.0,
            "max_abs_delta": max(abs(float(delta)) for delta in deltas) if deltas else 0.0,
            "worst_ci_lower": min(ci_lowers) if ci_lowers else 0.0,
            "total_fixes": sum(fixes),
            "total_regressions": sum(regressions),
            "max_context_gold_delta": max(abs(float(delta)) for delta in context_deltas) if context_deltas else 0.0,
        }

    return extract


def gate_summary_metric(gate: str, paired_gate: str | None = None) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summaries = {item["gate"]: item for item in data.get("summaries", [])}
        summary = summaries[gate]
        out = {
            "n": summary.get("n"),
            "success": summary.get("success"),
            "gate_rate": summary.get("gate_rate"),
            "audio_cost": summary.get("mean_decision_audio_cost"),
            "regressions": summary.get("regressions"),
        }
        if paired_gate:
            paired = {item["gate"]: item for item in data.get("paired_vs_text", [])}
            item = paired[paired_gate]
            out.update(
                {
                    "delta": item.get("delta"),
                    "ci95": item.get("ci95"),
                    "fixes": item.get("fixes"),
                    "paired_regressions": item.get("regressions"),
                }
            )
        return out

    return extract


def gate_mixture_metric(dataset: str, gate: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {
            (str(item.get("dataset")), str(item.get("gate"))): item
            for item in data.get("rows", [])
        }
        item = rows[(dataset, gate)]
        return {
            "n": item.get("n"),
            "success": item.get("mixed_success"),
            "delta": item.get("delta_vs_text"),
            "ci95": item.get("ci95"),
            "gate_rate": item.get("mixed_gate_rate"),
            "audio_cost": item.get("mixed_audio_cost"),
            "fixes": item.get("fixes"),
            "regressions": item.get("regressions"),
        }

    return extract


def query_audio_gate_selector_metric(dataset: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("dataset")): item for item in data.get("selections", [])}
        item = rows[dataset]
        return {
            "decision": item.get("decision"),
            "selected_gate": item.get("selected_gate"),
            "selected_success": item.get("selected_success"),
            "selected_delta": item.get("selected_delta"),
            "selected_ci95": item.get("selected_ci95"),
            "selected_audio_cost": item.get("selected_audio_cost"),
            "selected_gate_rate": item.get("selected_gate_rate"),
            "selected_fixes": item.get("selected_fixes"),
            "selected_regressions": item.get("selected_regressions"),
            "selected_regression_rate": item.get("selected_regression_rate"),
            "accepted_count": item.get("accepted_count"),
        }

    return extract


def query_audio_gate_deployability_metric(data: dict[str, Any]) -> dict[str, Any]:
    rows = {str(item.get("dataset")): item for item in data.get("rows", [])}
    summary = data.get("summary", {})
    covost = rows["CoVoST2 ar"]
    minds = rows["MInDS"]
    heysquad = rows["HeySQuAD"]
    return {
        "dataset_count": summary.get("dataset_count"),
        "accepted_count": summary.get("accepted_count"),
        "mean_selected_delta": summary.get("mean_selected_delta"),
        "mean_selected_audio_cost": summary.get("mean_selected_audio_cost"),
        "mean_audio_cost_reduction_rate": summary.get("mean_audio_cost_reduction_rate"),
        "covost_selected_gate": covost.get("selected_gate"),
        "covost_delta": covost.get("selected_delta_vs_text"),
        "covost_clean_delta": covost.get("clean_delta_vs_text"),
        "covost_stress_delta": covost.get("stress_delta_vs_text"),
        "covost_audio_cost": covost.get("selected_audio_cost"),
        "minds_selected_gate": minds.get("selected_gate"),
        "minds_delta": minds.get("selected_delta_vs_text"),
        "minds_clean_delta": minds.get("clean_delta_vs_text"),
        "minds_stress_delta": minds.get("stress_delta_vs_text"),
        "minds_audio_cost": minds.get("selected_audio_cost"),
        "heysquad_selected_gate": heysquad.get("selected_gate"),
        "heysquad_delta": heysquad.get("selected_delta_vs_text"),
        "heysquad_clean_delta": heysquad.get("clean_delta_vs_text"),
        "heysquad_stress_delta": heysquad.get("stress_delta_vs_text"),
        "heysquad_audio_cost": heysquad.get("selected_audio_cost"),
        "total_regressions": sum(int(item.get("selected_regressions", 0)) for item in rows.values()),
    }


def tool_call_utility_metric(dataset: str, policy: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        datasets = {str(item.get("dataset")): item for item in data.get("datasets", [])}
        item = datasets[dataset]
        rows = {str(row.get("policy")): row for row in item.get("rows", [])}
        row = rows[policy]
        return {
            "sample_count": item.get("sample_count"),
            "decision": item.get("decision"),
            "seed_count": row.get("seed_count"),
            "tool_call_success": row.get("mean_tool_call_success"),
            "unsafe_wrong_tool_rate": row.get("mean_unsafe_wrong_tool_rate"),
            "boundary_error_rate": row.get("mean_boundary_error_rate"),
            "route_rate": row.get("mean_route_rate"),
            "delta": row.get("mean_delta"),
            "ci_lower": row.get("mean_ci_lower"),
            "regression_rate": row.get("mean_regression_rate"),
        }

    return extract


def uro_compare_metric(data: dict[str, Any]) -> dict[str, Any]:
    hit = data["hit_at_1"]
    return {
        "n": data.get("n"),
        "raw_acc": hit.get("baseline"),
        "policy_acc": hit.get("candidate"),
        "delta": hit.get("delta"),
        "ci95": hit.get("bootstrap_ci95"),
        "fixes": data.get("fix_count"),
        "regressions": data.get("regression_count"),
    }


def uro_final_task_use_metric(data: dict[str, Any]) -> dict[str, Any]:
    metrics = data["metrics"]
    paired = data.get("paired_vs_baseline", {})
    return {
        "n": metrics.get("n"),
        "answer_pass": metrics.get("answer_pass"),
        "grounded_target_acc": metrics.get("grounded_target_acc"),
        "context_gold_rate": metrics.get("context_gold_rate"),
        "generation_miss_rate": metrics.get("generation_miss_rate"),
        "retrieval_miss_rate": metrics.get("retrieval_miss_rate"),
        "delta": paired.get("answer_pass_delta"),
        "ci95": paired.get("ci95"),
        "fixes": paired.get("fixes"),
        "regressions": paired.get("regressions"),
    }


def uro_family_breakdown_metric(data: dict[str, Any]) -> dict[str, Any]:
    summary = data["summary"]
    families = {str(item["family"]): item for item in data.get("families", [])}
    storal = families["StoralEval"]
    hsk = families["HSK5-zh"]
    squad = families["SQuAD-zh"]
    gsm = families["Gsm8kEval"]
    return {
        "family_count": summary.get("family_count"),
        "n": summary.get("n"),
        "positive_family_count": summary.get("positive_family_count"),
        "zero_delta_family_count": summary.get("zero_delta_family_count"),
        "negative_family_count": summary.get("negative_family_count"),
        "total_fixes": summary.get("total_fixes"),
        "total_regressions": summary.get("total_regressions"),
        "max_delta": summary.get("max_delta"),
        "min_delta": summary.get("min_delta"),
        "hardest_remaining_family": summary.get("hardest_remaining_family"),
        "hardest_remaining_policy_answer_pass": summary.get("hardest_remaining_policy_answer_pass"),
        "hsk_delta": hsk.get("delta"),
        "squad_delta": squad.get("delta"),
        "storal_delta": storal.get("delta"),
        "gsm_delta": gsm.get("delta"),
    }


def candidate_order_stability_metric(dataset: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("dataset")): item for item in data.get("rows", [])}
        item = rows[dataset]
        return {
            "n": item.get("n"),
            "base_success": item.get("base_success"),
            "shuffle_success_mean": item.get("shuffle_success_mean"),
            "shuffle_success_min": item.get("shuffle_success_min"),
            "shuffle_success_max": item.get("shuffle_success_max"),
            "max_abs_delta": item.get("max_abs_delta"),
            "total_regressions": item.get("total_regressions"),
            "max_regression_rate": item.get("max_regression_rate"),
            "decision": item.get("decision"),
        }

    return extract


def retrieval_use_metric(label: str, comparison_candidate: str | None = None) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("label")): item for item in data.get("rows", [])}
        item = rows[label]
        out = {
            "n": item.get("n"),
            "retrieval_hit_at_k": item.get("retrieval_hit_at_k"),
            "memory_use_success": item.get("memory_use_success"),
            "hit_but_use_fail": item.get("hit_but_use_fail"),
            "retrieval_miss": item.get("retrieval_miss"),
            "invalid_output": item.get("invalid_output"),
            "context_overflow_rate": item.get("context_overflow_rate"),
        }
        if comparison_candidate:
            comparisons = {
                (str(row.get("baseline")), str(row.get("candidate"))): row
                for row in data.get("comparisons", [])
            }
            comparison = comparisons[(label, comparison_candidate)]
            out.update(
                {
                    "success_delta": comparison.get("success_delta"),
                    "ci95": comparison.get("ci95"),
                    "fixes": comparison.get("fixes"),
                    "regressions": comparison.get("regressions"),
                    "invalid_delta": comparison.get("invalid_delta"),
                }
            )
        return out

    return extract


def result_compare_summary_metric(
    *,
    base_label: str,
    compare_pairs: list[tuple[str, str]],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summaries = {str(item.get("label")): item for item in data.get("summaries", [])}
        paired = {
            (str(item.get("candidate")), str(item.get("baseline"))): item
            for item in data.get("paired", [])
        }
        base = summaries[base_label]
        out: dict[str, Any] = {
            "n": base.get("n"),
            "base_success": base.get("task_success"),
        }
        for candidate, baseline in compare_pairs:
            item = paired[(candidate, baseline)]
            prefix = f"{candidate}_vs_{baseline}"
            out[f"{prefix}_n"] = item.get("n")
            out[f"{prefix}_delta"] = item.get("delta")
            out[f"{prefix}_ci95"] = item.get("ci95")
            out[f"{prefix}_fixes"] = item.get("fixes")
            out[f"{prefix}_regressions"] = item.get("regressions")
        return out

    return extract


def self_consistency_gate_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        best = data.get("best_policy", {})
        rows = {str(item.get("policy")): item for item in data.get("rows", [])}
        majority = rows["majority"]
        return {
            "best_policy": best.get("policy"),
            "best_success": best.get("success"),
            "best_delta": best.get("delta"),
            "best_ci95": best.get("ci95"),
            "best_fixes": best.get("fixes"),
            "best_regressions": best.get("regressions"),
            "best_regression_rate": best.get("regression_rate"),
            "best_route_rate": best.get("route_rate"),
            "best_decision": best.get("decision"),
            "majority_success": majority.get("success"),
            "majority_delta": majority.get("delta"),
            "majority_ci95": majority.get("ci95"),
            "majority_fixes": majority.get("fixes"),
            "majority_regressions": majority.get("regressions"),
            "majority_regression_rate": majority.get("regression_rate"),
        }

    return extract


def memory_packing_metric(label: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("label")): item for item in data.get("rows", [])}
        item = rows[label]
        return {
            "n": item.get("n"),
            "original_mean_prompt_tokens": item.get("original_mean_prompt_tokens"),
            "packed_mean_prompt_tokens": item.get("packed_mean_prompt_tokens"),
            "mean_token_reduction": item.get("mean_token_reduction"),
            "original_max_prompt_tokens": item.get("original_max_prompt_tokens"),
            "packed_max_prompt_tokens": item.get("packed_max_prompt_tokens"),
            "original_overflow_rate": item.get("original_overflow_rate"),
            "packed_overflow_rate": item.get("packed_overflow_rate"),
            "original_p95_prompt_tokens": item.get("original_p95_prompt_tokens"),
            "packed_p95_prompt_tokens": item.get("packed_p95_prompt_tokens"),
        }

    return extract


def end_to_end_chain_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        headline = data.get("headline", {})
        rows = {str(item.get("label")): item for item in data.get("rows", [])}
        controls = {str(item.get("label")): item for item in data.get("controls", [])}
        heysquad_order = controls["heysquad_top3_evidence_order_shuffle"]
        spoken_order = controls["spoken_squad_top3_evidence_order_shuffle"]
        return {
            "heysquad_retrieval_hit_at_5": headline.get("heysquad_retrieval_hit_at_5"),
            "heysquad_original_memory_use_success": headline.get("heysquad_original_memory_use_success"),
            "heysquad_packed_memory_use_success": headline.get("heysquad_packed_memory_use_success"),
            "heysquad_top3_evidence_answer_pass": headline.get("heysquad_top3_evidence_answer_pass"),
            "heysquad_top5_evidence_answer_pass": headline.get("heysquad_top5_evidence_answer_pass"),
            "heysquad_original_hit_but_use_fail": rows["heysquad_top5_original_memory_use"].get("hit_but_use_fail"),
            "heysquad_packed_hit_but_use_fail": rows["heysquad_top5_packed_memory_use"].get("hit_but_use_fail"),
            "heysquad_top5_generation_miss_rate": rows["heysquad_top5_evidence_final_answer"].get(
                "generation_miss_rate"
            ),
            "spoken_squad_default_answer_pass": headline.get("spoken_squad_default_answer_pass"),
            "spoken_squad_evidence_answer_pass": headline.get("spoken_squad_evidence_answer_pass"),
            "heysquad_order_max_abs_delta": heysquad_order.get("max_abs_delta"),
            "spoken_order_max_abs_delta": spoken_order.get("max_abs_delta"),
        }

    return extract


def dialect_route_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("dataset")): item for item in data.get("rows", [])}
        aishell = rows["AISHELL-1"]
        wu = rows["WenetSpeech-Wu"]
        headline = data.get("headline", {})
        return {
            "aishell_n": aishell.get("n"),
            "aishell_asr_test_cer": nested(aishell, "asr_quality_test", "mean_cer"),
            "aishell_asr_acc": headline.get("aishell_asr_acc"),
            "aishell_omni_acc": headline.get("aishell_omni_acc"),
            "aishell_omni_delta": headline.get("aishell_omni_delta"),
            "aishell_omni_ci95": nested(aishell, "policies", "omni_primary", "ci95_vs_asr"),
            "aishell_omni_regressions": headline.get("aishell_omni_regressions"),
            "aishell_disagreement_route_rate": nested(aishell, "route_signal", "disagreement_route_rate"),
            "wu_n": wu.get("n"),
            "wu_asr_test_cer": headline.get("wu_asr_test_cer"),
            "wu_asr_acc": headline.get("wu_asr_acc"),
            "wu_omni_acc": headline.get("wu_omni_acc"),
            "wu_omni_delta": headline.get("wu_omni_delta"),
            "wu_omni_ci95": nested(wu, "policies", "omni_primary", "ci95_vs_asr"),
            "wu_omni_regressions": headline.get("wu_omni_regressions"),
            "wu_rrf_acc": headline.get("wu_rrf_acc"),
            "wu_rrf_delta": headline.get("wu_rrf_delta"),
            "wu_disagreement_route_rate": nested(wu, "route_signal", "disagreement_route_rate"),
        }

    return extract


def controller_component_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {
            (str(item.get("component")), str(item.get("dataset"))): item
            for item in data.get("rows", [])
        }
        uro = rows[("omni_instruction", "URO QA/reasoning")]
        slurp = rows[("low_margin_verifier", "SLURP intent")]
        covost = rows[("low_margin_verifier", "CoVoST2 ar->en locked test")]
        aishell = rows[("route_boundary", "AISHELL-1 clean Mandarin")]
        wu = rows[("route_boundary", "WenetSpeech-Wu dialect")]
        covost_gate = rows[("query_audio_gate", "CoVoST2 mixed clean+stress")]
        heysquad_gate = rows[("query_audio_gate", "HeySQuAD mixed clean+drift")]
        packing = rows[("memory_packing", "HeySQuAD retrieval-to-use")]
        heysquad_answer = rows[("evidence_protocol", "HeySQuAD final answer")]
        spoken_answer = rows[("evidence_protocol", "Spoken-SQuAD final answer")]
        return {
            "row_count": len(data.get("rows", [])),
            "uro_delta": uro.get("delta"),
            "uro_ci95": uro.get("ci95"),
            "uro_regressions": uro.get("regressions"),
            "slurp_delta": slurp.get("delta"),
            "slurp_ci95": slurp.get("ci95"),
            "slurp_regressions": slurp.get("regressions"),
            "covost_delta": covost.get("delta"),
            "covost_ci95": covost.get("ci95"),
            "covost_regressions": covost.get("regressions"),
            "aishell_delta": aishell.get("delta"),
            "aishell_regressions": aishell.get("regressions"),
            "wu_delta": wu.get("delta"),
            "wu_regressions": wu.get("regressions"),
            "covost_gate_delta": covost_gate.get("delta"),
            "covost_gate_regressions": covost_gate.get("regressions"),
            "heysquad_gate_delta": heysquad_gate.get("delta"),
            "heysquad_gate_regressions": heysquad_gate.get("regressions"),
            "packing_delta": packing.get("delta"),
            "packing_regressions": packing.get("regressions"),
            "heysquad_answer_delta": heysquad_answer.get("delta"),
            "heysquad_answer_regressions": heysquad_answer.get("regressions"),
            "spoken_answer_delta": spoken_answer.get("delta"),
            "spoken_answer_regressions": spoken_answer.get("regressions"),
        }

    return extract


def translation_order_robustness_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {str(item.get("dataset")): item for item in data.get("rows", [])}
        ar = rows["CoVoST2 ar->en"]
        zh = rows["CoVoST2 zh-CN->en"]
        return {
            "ar_same_order_delta": ar.get("same_order_delta"),
            "ar_same_order_ci95": ar.get("same_order_ci95"),
            "ar_shuffle_delta_mean": ar.get("shuffle_delta_mean"),
            "ar_shuffle_delta_min": ar.get("shuffle_delta_min"),
            "ar_shuffle_seed_accept_count": ar.get("shuffle_seed_accept_count"),
            "ar_order_robust": ar.get("order_robust"),
            "ar_self_consistency_delta": ar.get("self_consistency_delta"),
            "ar_self_consistency_ci95": ar.get("self_consistency_ci95"),
            "ar_self_consistency_weak_accept": ar.get("self_consistency_weak_accept"),
            "ar_decision": ar.get("decision"),
            "zh_same_order_delta": zh.get("same_order_delta"),
            "zh_same_order_ci95": zh.get("same_order_ci95"),
            "zh_shuffle_delta_mean": zh.get("shuffle_delta_mean"),
            "zh_shuffle_delta_min": zh.get("shuffle_delta_min"),
            "zh_shuffle_seed_accept_count": zh.get("shuffle_seed_accept_count"),
            "zh_order_robust": zh.get("order_robust"),
            "zh_self_consistency_delta": zh.get("self_consistency_delta"),
            "zh_self_consistency_ci95": zh.get("self_consistency_ci95"),
            "zh_self_consistency_strict_accept": zh.get("self_consistency_strict_accept"),
            "zh_decision": zh.get("decision"),
        }

    return extract


def controller_cost_budget_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {
            (str(item.get("component")), str(item.get("dataset")), str(item.get("policy"))): item
            for item in data.get("rows", [])
        }
        slurp_tau01 = rows[("low_margin_verifier", "SLURP intent", "tau=0.01 top-3 verifier")]
        slurp_tau02 = rows[("low_margin_verifier", "SLURP intent", "tau=0.02 top-3 verifier")]
        minds = rows[("low_margin_verifier", "MInDS intent", "tau=0.02 top-3 verifier")]
        covost = rows[("low_margin_verifier", "CoVoST2 ar->en locked test", "tau=0.02 top-3 verifier")]
        covost_gate = rows[("query_audio_gate", "CoVoST2 mixed clean+stress", "audio_on_hint_pred_overlap_ge_0_80")]
        minds_gate = rows[("query_audio_gate", "MInDS mixed clean+stress", "audio_on_text_first_candidate")]
        heysquad_gate = rows[("query_audio_gate", "HeySQuAD mixed clean+drift", "audio_on_text_equals_noquery")]
        packing = rows[("memory_packing", "HeySQuAD retrieval-to-use", "answer/evidence packed memory cards")]
        heysquad_answer = rows[("evidence_protocol", "HeySQuAD final answer", "evidence-then-answer")]
        spoken_answer = rows[("evidence_protocol", "Spoken-SQuAD final answer", "evidence-then-answer")]
        ar_self = rows[("order_self_consistency", "CoVoST2 ar->en", "base+3 shuffled orders majority vote")]
        zh_self = rows[("order_self_consistency", "CoVoST2 zh-CN->en", "base+3 shuffled orders majority vote")]
        gemma12b = rows[("cross_model_backend", "CoVoST2 ar->en partial", "Gemma 4 12B partial backend")]
        return {
            "row_count": len(data.get("rows", [])),
            "slurp_tau01_delta": slurp_tau01.get("delta"),
            "slurp_tau01_route": slurp_tau01.get("cost_value"),
            "slurp_tau02_delta": slurp_tau02.get("delta"),
            "slurp_tau02_route": slurp_tau02.get("cost_value"),
            "slurp_tau02_marginal_benefit": slurp_tau02.get("marginal_benefit_per_route"),
            "minds_delta": minds.get("delta"),
            "minds_route": minds.get("cost_value"),
            "covost_test_delta": covost.get("delta"),
            "covost_test_route": covost.get("cost_value"),
            "covost_gate_delta": covost_gate.get("delta"),
            "covost_gate_audio_cost": covost_gate.get("cost_value"),
            "minds_gate_delta": minds_gate.get("delta"),
            "minds_gate_audio_cost": minds_gate.get("cost_value"),
            "heysquad_gate_delta": heysquad_gate.get("delta"),
            "heysquad_gate_audio_cost": heysquad_gate.get("cost_value"),
            "packing_delta": packing.get("delta"),
            "packing_text_token_delta": packing.get("cost_value"),
            "heysquad_answer_delta": heysquad_answer.get("delta"),
            "spoken_answer_delta": spoken_answer.get("delta"),
            "ar_self_cost": ar_self.get("cost_value"),
            "ar_self_latency_ratio": ar_self.get("latency_ratio"),
            "zh_self_cost": zh_self.get("cost_value"),
            "zh_self_latency_ratio": zh_self.get("latency_ratio"),
            "gemma12b_delta": gemma12b.get("delta"),
            "gemma12b_latency_ratio": gemma12b.get("cost_value"),
            "gemma12b_regressions": gemma12b.get("regressions"),
        }

    return extract


def badcase_audit_sample_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        stats = data.get("source_stats", {})
        slurp = stats["SLURP verifier"]
        covost = stats["CoVoST2 ar verifier"]
        heysquad = stats["HeySQuAD memory packing"]
        return {
            "case_count": data.get("case_count"),
            "slurp_routed": slurp.get("routed"),
            "slurp_fixes_total": slurp.get("fixes_total"),
            "slurp_regressions_total": slurp.get("regressions_total"),
            "covost_routed": covost.get("routed"),
            "covost_fixes_total": covost.get("fixes_total"),
            "covost_regressions_total": covost.get("regressions_total"),
            "heysquad_compared": heysquad.get("compared"),
            "heysquad_fixes_total": heysquad.get("fixes_total"),
            "heysquad_regressions_total": heysquad.get("regressions_total"),
        }

    return extract


def runtime_latency_summary_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        rows = {
            (str(item.get("component")), str(item.get("dataset")), str(item.get("policy"))): item
            for item in data.get("rows", [])
        }
        covost_full_audio = rows[
            (
                "candidate_audio_memory",
                "CoVoST2 ar->en fixed-candidate memory use",
                "full candidate audio",
            )
        ]
        minds_full_audio = rows[
            (
                "candidate_audio_memory",
                "MInDS fixed-candidate tool memory use",
                "full candidate audio",
            )
        ]
        packing = rows[
            (
                "memory_packing_runtime",
                "HeySQuAD retrieval-to-use",
                "answer/evidence packed cards",
            )
        ]
        pg_packing = rows[
            (
                "memory_packing_runtime",
                "HeySQuAD retrieval-to-use",
                "policy_grounding packed cards",
            )
        ]
        backend = rows[
            (
                "cross_model_backend_runtime",
                "CoVoST2 ar->en partial backend check",
                "Gemma 4 12B partial",
            )
        ]
        return {
            "row_count": data.get("row_count"),
            "covost_full_audio_success_delta": nested(covost_full_audio, "delta", "success_delta"),
            "covost_full_audio_latency_ratio": nested(covost_full_audio, "delta", "latency_ratio"),
            "minds_full_audio_success_delta": nested(minds_full_audio, "delta", "success_delta"),
            "minds_full_audio_latency_ratio": nested(minds_full_audio, "delta", "latency_ratio"),
            "packing_success_delta": nested(packing, "delta", "success_delta"),
            "packing_text_cost_delta": nested(packing, "delta", "text_cost_delta"),
            "packing_latency_ratio": nested(packing, "delta", "latency_ratio"),
            "pg_packing_text_cost_delta": nested(pg_packing, "delta", "text_cost_delta"),
            "pg_packing_latency_ratio": nested(pg_packing, "delta", "latency_ratio"),
            "backend_success_delta": nested(backend, "delta", "success_delta"),
            "backend_latency_ratio": nested(backend, "delta", "latency_ratio"),
        }

    return extract


def cross_model_backend_readiness_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summary = data.get("summary", {})
        embedding_rows = data.get("embedding_backend_rows", [])
        stability_rows = data.get("embedding_stability_rows", [])
        system_rows = data.get("system_side_rows", [])
        generative_rows = data.get("generative_backend_rows", [])

        generative_by_model = {
            (str(row.get("model")), str(row.get("readiness"))): row
            for row in generative_rows
        }
        e4b_formal = generative_by_model[("Gemma 4 E4B GGUF", "main_backend_small_formal_positive")]
        gemma12b = generative_by_model[("Gemma 4 12B GGUF", "rejected_backend_reference")]
        qwen3 = generative_by_model[("Qwen3-Omni GGUF", "backend_smoke_only")]
        qwen3_chat = generative_by_model[("Qwen3-Omni GGUF", "chat_backend_timeout_blocker")]
        voxtral = generative_by_model[("Voxtral Mini 3B 2507 GGUF", "cli_audio_hang_blocker")]
        voxtral_chat = generative_by_model.get(
            ("Voxtral Mini 3B 2507 GGUF", "extended_chat_runnable_underpowered")
        ) or generative_by_model[("Voxtral Mini 3B 2507 GGUF", "small_chat_smoke_positive")]

        slurp_system = next(row for row in system_rows if row.get("task") == "Jina SLURP boundary tool card")
        minds_system = next(row for row in system_rows if row.get("task") == "Jina MInDS boundary tool card")

        return {
            "embedding_backend_count": summary.get("embedding_backend_count"),
            "embedding_raw_fallback_count": summary.get("embedding_raw_fallback_count"),
            "embedding_stability_no_positive_count": summary.get("embedding_stability_no_positive_count"),
            "system_side_positive_count": summary.get("system_side_positive_count"),
            "generative_backend_count": summary.get("generative_backend_count"),
            "main_backend_ready": summary.get("main_backend_ready"),
            "stable_second_generative_backend_ready": summary.get("stable_second_generative_backend_ready"),
            "second_backend_smoke_positive": summary.get("second_backend_smoke_positive"),
            "jina_selector_tasks": len(embedding_rows),
            "jina_stability_tasks": len(stability_rows),
            "e4b_formal_n": e4b_formal.get("n"),
            "e4b_formal_raw": e4b_formal.get("raw_acc_at_1"),
            "e4b_formal_best": e4b_formal.get("best_acc_at_1"),
            "e4b_formal_delta": e4b_formal.get("delta_vs_raw"),
            "gemma12b_partial_n": gemma12b.get("partial_n"),
            "gemma12b_delta": gemma12b.get("delta_vs_e4b"),
            "gemma12b_latency_ratio": gemma12b.get("latency_ratio"),
            "qwen3_smoke_n": qwen3.get("n"),
            "qwen3_smoke_accuracy": qwen3.get("accuracy"),
            "qwen3_chat_n": qwen3_chat.get("n"),
            "qwen3_chat_valid_rate": qwen3_chat.get("valid_rate"),
            "qwen3_chat_parse_rate": qwen3_chat.get("parse_rate"),
            "qwen3_chat_timeout_count": qwen3_chat.get("timeout_count"),
            "qwen3_chat_mean_latency_ms": qwen3_chat.get("mean_latency_ms"),
            "voxtral_attempted_rows": voxtral.get("attempted_rows"),
            "voxtral_completed_rows": voxtral.get("completed_rows"),
            "voxtral_valid_rate": voxtral.get("valid_rate"),
            "voxtral_parse_rate": voxtral.get("parse_rate"),
            "voxtral_timeout_count": voxtral.get("timeout_count"),
            "voxtral_timeout_s": voxtral.get("timeout_s"),
            "voxtral_minimal_log_bytes": voxtral.get("minimal_log_bytes"),
            "voxtral_chat_n": voxtral_chat.get("n"),
            "voxtral_chat_valid_rate": voxtral_chat.get("valid_rate"),
            "voxtral_chat_parse_rate": voxtral_chat.get("parse_rate"),
            "voxtral_chat_accuracy": voxtral_chat.get("accuracy"),
            "voxtral_chat_mean_latency_ms": voxtral_chat.get("mean_latency_ms"),
            "jina_slurp_system_delta": slurp_system.get("delta"),
            "jina_minds_system_delta": minds_system.get("delta"),
        }

    return extract


def translation_order_gate_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        datasets = {str(item.get("dataset")): item for item in data.get("datasets", [])}

        def policy(dataset: str, policy_name: str) -> dict[str, Any]:
            rows = {
                str(item.get("policy")): item
                for item in datasets[dataset].get("policy_summaries", [])
            }
            return rows[policy_name]

        ar_gate = policy("CoVoST2 ar->en", "translation_if_original_top1_else_generic")
        ar_rank_deviation_gate = policy(
            "CoVoST2 ar->en",
            "translation_if_original_top1_or_generic_not_original_top1_else_generic",
        )
        zh_gate = policy("CoVoST2 zh-CN->en", "translation_if_original_top1_else_generic")
        zh_rank_deviation_gate = policy(
            "CoVoST2 zh-CN->en",
            "translation_if_original_top1_or_generic_not_original_top1_else_generic",
        )
        ar_top1 = policy("CoVoST2 ar->en", "translation_if_original_top1_else_retrieval_top1")
        zh_top1 = policy("CoVoST2 zh-CN->en", "translation_if_original_top1_else_retrieval_top1")
        ar_always = policy("CoVoST2 ar->en", "always_translation")
        zh_always = policy("CoVoST2 zh-CN->en", "always_translation")
        return {
            "dataset_count": len(data.get("datasets", [])),
            "ar_always_shuffle_strict_accept": ar_always.get("shuffle_strict_accept_count"),
            "ar_gate_mean_delta": ar_gate.get("mean_delta"),
            "ar_gate_min_delta": ar_gate.get("min_delta"),
            "ar_gate_shuffle_strict_accept": ar_gate.get("shuffle_strict_accept_count"),
            "ar_gate_shuffle_weak_accept": ar_gate.get("shuffle_weak_accept_count"),
            "ar_gate_max_regression_rate": ar_gate.get("max_regression_rate"),
            "ar_gate_decision": ar_gate.get("decision"),
            "ar_rank_deviation_gate_mean_delta": ar_rank_deviation_gate.get("mean_delta"),
            "ar_rank_deviation_gate_min_delta": ar_rank_deviation_gate.get("min_delta"),
            "ar_rank_deviation_gate_shuffle_strict_accept": ar_rank_deviation_gate.get(
                "shuffle_strict_accept_count"
            ),
            "ar_rank_deviation_gate_shuffle_weak_accept": ar_rank_deviation_gate.get(
                "shuffle_weak_accept_count"
            ),
            "ar_rank_deviation_gate_max_regression_rate": ar_rank_deviation_gate.get(
                "max_regression_rate"
            ),
            "ar_rank_deviation_gate_decision": ar_rank_deviation_gate.get("decision"),
            "zh_always_shuffle_strict_accept": zh_always.get("shuffle_strict_accept_count"),
            "zh_gate_mean_delta": zh_gate.get("mean_delta"),
            "zh_gate_min_delta": zh_gate.get("min_delta"),
            "zh_gate_shuffle_strict_accept": zh_gate.get("shuffle_strict_accept_count"),
            "zh_gate_shuffle_weak_accept": zh_gate.get("shuffle_weak_accept_count"),
            "zh_gate_max_regression_rate": zh_gate.get("max_regression_rate"),
            "zh_gate_decision": zh_gate.get("decision"),
            "zh_rank_deviation_gate_mean_delta": zh_rank_deviation_gate.get("mean_delta"),
            "zh_rank_deviation_gate_min_delta": zh_rank_deviation_gate.get("min_delta"),
            "zh_rank_deviation_gate_shuffle_strict_accept": zh_rank_deviation_gate.get(
                "shuffle_strict_accept_count"
            ),
            "zh_rank_deviation_gate_shuffle_weak_accept": zh_rank_deviation_gate.get(
                "shuffle_weak_accept_count"
            ),
            "zh_rank_deviation_gate_max_regression_rate": zh_rank_deviation_gate.get(
                "max_regression_rate"
            ),
            "zh_rank_deviation_gate_decision": zh_rank_deviation_gate.get("decision"),
            "ar_retrieval_top1_mean_delta": ar_top1.get("mean_delta"),
            "ar_retrieval_top1_decision": ar_top1.get("decision"),
            "zh_retrieval_top1_mean_delta": zh_top1.get("mean_delta"),
            "zh_retrieval_top1_decision": zh_top1.get("decision"),
        }

    return extract


def translation_multivote_gate_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        datasets = {str(item.get("dataset")): item for item in data.get("datasets", [])}

        def policy(dataset: str, policy_name: str) -> dict[str, Any]:
            rows = {str(item.get("policy")): item for item in datasets[dataset].get("policies", [])}
            return rows[policy_name]

        ar_always = policy("CoVoST2 ar->en", "always_multivote")
        ar_strict = policy("CoVoST2 ar->en", "multivote_if_original_top1_else_generic")
        ar_standard = policy(
            "CoVoST2 ar->en",
            "multivote_if_original_top1_or_generic_not_original_top1_else_generic",
        )
        zh_always = policy("CoVoST2 zh-CN->en", "always_multivote")
        zh_strict = policy("CoVoST2 zh-CN->en", "multivote_if_original_top1_else_generic")
        zh_standard = policy(
            "CoVoST2 zh-CN->en",
            "multivote_if_original_top1_or_generic_not_original_top1_else_generic",
        )
        return {
            "dataset_count": len(data.get("datasets", [])),
            "ar_always_delta": ar_always.get("delta_vs_generic"),
            "ar_always_regressions": ar_always.get("regressions"),
            "ar_strict_success": ar_strict.get("success"),
            "ar_strict_delta": ar_strict.get("delta_vs_generic"),
            "ar_strict_ci95": ar_strict.get("ci95"),
            "ar_strict_fixes": ar_strict.get("fixes"),
            "ar_strict_regressions": ar_strict.get("regressions"),
            "ar_strict_route_rate": ar_strict.get("route_rate"),
            "ar_strict_mean_audio_cost": ar_strict.get("mean_audio_cost"),
            "ar_standard_delta": ar_standard.get("delta_vs_generic"),
            "ar_standard_regressions": ar_standard.get("regressions"),
            "zh_always_delta": zh_always.get("delta_vs_generic"),
            "zh_always_regressions": zh_always.get("regressions"),
            "zh_strict_success": zh_strict.get("success"),
            "zh_strict_delta": zh_strict.get("delta_vs_generic"),
            "zh_strict_ci95": zh_strict.get("ci95"),
            "zh_strict_fixes": zh_strict.get("fixes"),
            "zh_strict_regressions": zh_strict.get("regressions"),
            "zh_strict_route_rate": zh_strict.get("route_rate"),
            "zh_strict_mean_audio_cost": zh_strict.get("mean_audio_cost"),
            "zh_standard_delta": zh_standard.get("delta_vs_generic"),
            "zh_standard_regressions": zh_standard.get("regressions"),
        }

    return extract


def experiment_coverage_summary_metric() -> Callable[[dict[str, Any]], dict[str, Any]]:
    def extract(data: dict[str, Any]) -> dict[str, Any]:
        summary = data.get("summary", {})
        return {
            "block_count": summary.get("block_count"),
            "verified_block_count": summary.get("verified_block_count"),
            "ready_block_count": summary.get("ready_block_count"),
            "partial_block_count": summary.get("partial_block_count"),
            "blocker_count": summary.get("blocker_count"),
            "out_of_scope_count": summary.get("out_of_scope_count"),
            "deferred_count": summary.get("deferred_count"),
            "verifier_check_count": summary.get("verifier_check_count"),
            "verifier_pass_count": summary.get("verifier_pass_count"),
            "paper_decision": data.get("paper_decision"),
        }

    return extract


def build_checks() -> list[Check]:
    return [
        Check(
            name="uro_policy_grounding_full200",
            source=Path("outputs/uro_qa_omni_side_audio_query_200/raw_vs_policy_grounding_compare.json"),
            extractor=uro_compare_metric,
            expected={
                "n": 200,
                "raw_acc": 0.380,
                "policy_acc": 0.465,
                "delta": 0.085,
                "ci95": [0.045, 0.130],
                "fixes": 18,
                "regressions": 1,
            },
            note="Full-200 URO instruction evidence; locked selector row is documented separately.",
        ),
        Check(
            name="uro_exact_condition_full200",
            source=Path("outputs/uro_qa_omni_side_audio_query_200/raw_vs_exact_condition_matching_compare.json"),
            extractor=uro_compare_metric,
            expected={
                "n": 200,
                "raw_acc": 0.380,
                "policy_acc": 0.450,
                "delta": 0.070,
                "ci95": [0.035, 0.110],
                "fixes": 14,
                "regressions": 0,
            },
        ),
        Check(
            name="slurp_same_family_gate_locked",
            source=Path("outputs/omni_memory_v0/retrieval/slurp_tool_family_gate_changed_same_family.json"),
            extractor=slurp_gate_metrics,
            expected={
                "n": 200,
                "policy_acc": 0.665,
                "delta": 0.045,
                "ci95": [0.010, 0.080],
                "route_rate": 0.075,
                "fixes": 11,
                "regressions": 2,
            },
        ),
        Check(
            name="slurp_tool_call_utility_multiseed",
            source=Path("outputs/tool_call_utility_summary.json"),
            extractor=tool_call_utility_metric("SLURP", "same_family_changed_gate"),
            expected={
                "sample_count": 500,
                "decision": "accepted",
                "seed_count": 5,
                "tool_call_success": 0.619,
                "unsafe_wrong_tool_rate": 0.271,
                "boundary_error_rate": 0.110,
                "route_rate": 0.097,
                "delta": 0.065,
                "ci_lower": 0.027,
                "regression_rate": 0.008,
            },
        ),
        Check(
            name="minds_tool_call_raw_fallback_multiseed",
            source=Path("outputs/tool_call_utility_summary.json"),
            extractor=tool_call_utility_metric("MInDS", "raw_fallback_gate_reject"),
            expected={
                "sample_count": 180,
                "decision": "fallback_or_reject",
                "seed_count": 5,
                "tool_call_success": 0.8638888888888889,
                "unsafe_wrong_tool_rate": 0.13611111111111113,
                "boundary_error_rate": 0.0,
                "route_rate": 0.0,
                "delta": 0.0,
                "ci_lower": 0.0,
                "regression_rate": 0.0,
            },
        ),
        Check(
            name="minds_fixed_candidate_tool_memory_use_query_signal",
            source=Path("outputs/omni_memory_v0/summary_minds14_fixed_candidate_memory_use.json"),
            extractor=result_compare_summary_metric(
                base_label="text",
                compare_pairs=[("audio", "text"), ("text", "noquery")],
            ),
            expected={
                "n": 180,
                "base_success": 0.9666666666666667,
                "audio_vs_text_delta": 0.03333333333333333,
                "audio_vs_text_ci95": [0.011111111111111112, 0.06111111111111111],
                "audio_vs_text_fixes": 6,
                "audio_vs_text_regressions": 0,
                "text_vs_noquery_delta": 0.8166666666666667,
                "text_vs_noquery_ci95": [0.7611111111111111, 0.8666666666666667],
                "text_vs_noquery_fixes": 147,
                "text_vs_noquery_regressions": 0,
            },
        ),
        Check(
            name="minds_retrieval_top5_tool_memory_use",
            source=Path("outputs/omni_memory_v0/summary_tool_retrieval_use.json"),
            extractor=retrieval_use_metric("minds14_raw_top5_tool_use"),
            expected={
                "n": 180,
                "retrieval_hit_at_k": 0.9833333333333333,
                "memory_use_success": 0.9666666666666667,
                "hit_but_use_fail": 0.016666666666666666,
                "retrieval_miss": 0.016666666666666666,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
            },
        ),
        Check(
            name="slurp_retrieval_top5_tool_memory_use",
            source=Path("outputs/omni_memory_v0/summary_tool_retrieval_use.json"),
            extractor=retrieval_use_metric("slurp_raw_top5_tool_use"),
            expected={
                "n": 500,
                "retrieval_hit_at_k": 0.802,
                "memory_use_success": 0.574,
                "hit_but_use_fail": 0.228,
                "retrieval_miss": 0.198,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
            },
        ),
        Check(
            name="minds_tool_boundary_memory_card_regression",
            source=Path("outputs/omni_memory_v0/summary_tool_retrieval_use_boundary_compare.json"),
            extractor=result_compare_summary_metric(
                base_label="minds_raw",
                compare_pairs=[("minds_boundary", "minds_raw")],
            ),
            expected={
                "n": 180,
                "base_success": 0.9666666666666667,
                "minds_boundary_vs_minds_raw_n": 180,
                "minds_boundary_vs_minds_raw_delta": -0.03888888888888889,
                "minds_boundary_vs_minds_raw_ci95": [
                    -0.07222222222222222,
                    -0.011111111111111112,
                ],
                "minds_boundary_vs_minds_raw_fixes": 1,
                "minds_boundary_vs_minds_raw_regressions": 8,
            },
        ),
        Check(
            name="slurp_tool_boundary_memory_card_weak_trend",
            source=Path("outputs/omni_memory_v0/summary_tool_retrieval_use_boundary_compare.json"),
            extractor=result_compare_summary_metric(
                base_label="slurp_raw",
                compare_pairs=[("slurp_boundary", "slurp_raw")],
            ),
            expected={
                "n": 500,
                "base_success": 0.574,
                "slurp_boundary_vs_slurp_raw_n": 500,
                "slurp_boundary_vs_slurp_raw_delta": 0.024,
                "slurp_boundary_vs_slurp_raw_ci95": [-0.006, 0.054],
                "slurp_boundary_vs_slurp_raw_fixes": 35,
                "slurp_boundary_vs_slurp_raw_regressions": 23,
            },
        ),
        Check(
            name="slurp_tool_retrieval_use_order_shuffle_negative_control",
            source=Path("outputs/omni_memory_v0/summary_shuffle_slurp_tool_retrieval_use.json"),
            extractor=result_compare_summary_metric(
                base_label="base",
                compare_pairs=[
                    ("seed7", "base"),
                    ("seed17", "base"),
                    ("seed29", "base"),
                ],
            ),
            expected={
                "n": 500,
                "base_success": 0.574,
                "seed7_vs_base_n": 500,
                "seed7_vs_base_delta": -0.072,
                "seed7_vs_base_ci95": [-0.112, -0.032],
                "seed7_vs_base_fixes": 33,
                "seed7_vs_base_regressions": 69,
                "seed17_vs_base_n": 500,
                "seed17_vs_base_delta": -0.102,
                "seed17_vs_base_ci95": [-0.14, -0.064],
                "seed17_vs_base_fixes": 24,
                "seed17_vs_base_regressions": 75,
                "seed29_vs_base_n": 500,
                "seed29_vs_base_delta": -0.082,
                "seed29_vs_base_ci95": [-0.122, -0.044],
                "seed29_vs_base_fixes": 30,
                "seed29_vs_base_regressions": 71,
            },
        ),
        Check(
            name="slurp_tool_retrieval_use_self_consistency_rejected",
            source=Path("outputs/omni_memory_v0/summary_slurp_tool_retrieval_use_self_consistency_gate.json"),
            extractor=self_consistency_gate_metric(),
            expected={
                "best_policy": "self_if_agreement_ge_0.5_margin_ge_2",
                "best_success": 0.576,
                "best_delta": 0.002,
                "best_ci95": [-0.016, 0.022],
                "best_fixes": 12,
                "best_regressions": 11,
                "best_regression_rate": 0.022,
                "best_route_rate": 0.08,
                "best_decision": "weak_trend_rejected",
                "majority_success": 0.55,
                "majority_delta": -0.024,
                "majority_ci95": [-0.05, 0.002],
                "majority_fixes": 16,
                "majority_regressions": 28,
                "majority_regression_rate": 0.056,
            },
        ),
        Check(
            name="slurp_low_margin_llm_top3_tau0p02",
            source=Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p02.json"),
            extractor=low_margin_metrics,
            expected={
                "n": 500,
                "raw_acc": 0.55,
                "policy_acc": 0.69,
                "delta": 0.1399999999999999,
                "ci95": [0.11, 0.17],
                "route_rate": 0.666,
                "fixes": 70,
                "regressions": 0,
                "tool_call_success": 0.69,
                "unsafe_wrong_tool_rate": 0.21,
                "boundary_error_rate": 0.1,
            },
        ),
        Check(
            name="slurp_low_margin_llm_top3_tau0p01",
            source=Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p01.json"),
            extractor=low_margin_metrics,
            expected={
                "n": 500,
                "raw_acc": 0.55,
                "policy_acc": 0.676,
                "delta": 0.126,
                "ci95": [0.098, 0.156],
                "route_rate": 0.496,
                "fixes": 63,
                "regressions": 0,
                "tool_call_success": 0.676,
                "unsafe_wrong_tool_rate": 0.22,
                "boundary_error_rate": 0.104,
            },
        ),
        Check(
            name="slurp_low_margin_oracle_ablation_tau0p02",
            source=Path("outputs/low_margin_verifier/ablation_slurp_top3_with_llm_cost_curve.json"),
            extractor=low_margin_ablation_policy_metric("oracle_low_margin_top3_tau=0.02"),
            expected={
                "sample_count": 500,
                "route_rate": 0.666,
                "policy_acc": 0.762,
                "delta": 0.21199999999999997,
                "ci95": [0.178, 0.248],
                "fixes": 106,
                "regressions": 0,
            },
        ),
        Check(
            name="minds_low_margin_llm_180",
            source=Path("outputs/low_margin_verifier/minds_llm_top3_tau0p02.json"),
            extractor=low_margin_metrics,
            expected={
                "n": 180,
                "raw_acc": 0.8833333333333333,
                "policy_acc": 0.9555555555555556,
                "delta": 0.0722222222222223,
                "ci95": [0.03888888888888889, 0.1111111111111111],
                "route_rate": 0.350,
                "fixes": 13,
                "regressions": 0,
            },
        ),
        Check(
            name="covost_ar_low_margin_llm_test_full",
            source=Path("outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json"),
            extractor=low_margin_metrics,
            expected={
                "n": 1695,
                "raw_acc": 0.6407079646017699,
                "policy_acc": 0.7510324483775811,
                "delta": 0.11032448377581117,
                "ci95": [0.09616519174041298, 0.1256637168141593],
                "route_rate": 0.49734513274336284,
                "fixes": 193,
                "regressions": 6,
            },
        ),
        Check(
            name="uro_final_task_low_margin_llm_boundary",
            source=Path("outputs/uro_final_task_use/llm_low_margin_boundary_top3.json"),
            extractor=uro_final_task_use_metric,
            expected={
                "n": 200,
                "answer_pass": 0.845,
                "grounded_target_acc": 0.845,
                "context_gold_rate": 0.865,
                "generation_miss_rate": 0.020,
                "retrieval_miss_rate": 0.135,
                "delta": 0.130,
                "ci95": [0.085, 0.180],
                "fixes": 26,
                "regressions": 0,
            },
        ),
        Check(
            name="uro_final_task_family_breakdown",
            source=Path("outputs/uro_family_breakdown_summary.json"),
            extractor=uro_family_breakdown_metric,
            expected={
                "family_count": 8,
                "n": 200,
                "positive_family_count": 7,
                "zero_delta_family_count": 1,
                "negative_family_count": 0,
                "total_fixes": 26,
                "total_regressions": 0,
                "max_delta": 0.24,
                "min_delta": 0.0,
                "hardest_remaining_family": "StoralEval",
                "hardest_remaining_policy_answer_pass": 0.28,
                "hsk_delta": 0.24,
                "squad_delta": 0.24,
                "storal_delta": 0.16,
                "gsm_delta": 0.0,
            },
        ),
        Check(
            name="heysquad_default_llm_top3",
            source=Path("outputs/rag_final_answer_compare_heysquad_val200_llm_prompt.json"),
            extractor=paired_compare_metric("raw_retrieval_omni_top3_llm_default"),
            expected={"answer_pass": 0.790, "generation_miss": 0.145},
        ),
        Check(
            name="heysquad_evidence_then_answer_top3",
            source=Path("outputs/rag_final_answer_compare_heysquad_val200_llm_prompt.json"),
            extractor=paired_compare_metric(
                "raw_retrieval_omni_top3_llm_evidence_then_answer",
                "raw_retrieval_omni_top3_llm_default",
            ),
            expected={
                "answer_pass": 0.885,
                "generation_miss": 0.045,
                "delta": 0.095,
                "ci95": [0.045, 0.145],
                "fixes": 23,
                "regressions": 4,
            },
        ),
        Check(
            name="heysquad_policy_grounding_evidence_negative",
            source=Path("outputs/rag_final_answer_compare_heysquad_val200_evidence_policy_context.json"),
            extractor=paired_compare_metric(
                "policy_grounding_retrieval_omni_top3_llm_evidence_then_answer",
                "raw_retrieval_omni_top3_llm_evidence_then_answer",
            ),
            expected={
                "answer_pass": 0.855,
                "generation_miss": 0.050,
                "delta": -0.030,
                "ci95": [-0.055, -0.010],
                "fixes": 0,
                "regressions": 6,
            },
        ),
        Check(
            name="heysquad_top5_evidence_weak_trend",
            source=Path("outputs/rag_final_answer_compare_heysquad_val200_evidence_policy_context.json"),
            extractor=paired_compare_metric(
                "raw_retrieval_omni_top5_llm_evidence_then_answer",
                "raw_retrieval_omni_top3_llm_evidence_then_answer",
            ),
            expected={
                "answer_pass": 0.895,
                "generation_miss": 0.050,
                "delta": 0.010,
                "ci95": [-0.010, 0.030],
                "fixes": 3,
                "regressions": 1,
            },
        ),
        Check(
            name="heysquad_val422_direct_omni_public_proxy",
            source=Path("outputs/rag_final_answer_compare_heysquad_val422_firstdoc_local.json"),
            extractor=paired_compare_decomposition_metric(
                "oracle_text_plus_omni_context_omni_top3_first_document_default",
                "oracle_text_plus_omni_context_asr_top3_first_document_default",
            ),
            expected={
                "answer_pass": 0.9834123222748815,
                "generation_miss_rate": 0.016587677725118485,
                "context_gold_rate": 1.0,
                "delta": 0.04028436018957346,
                "ci95": [0.016587677725118485, 0.06398104265402843],
                "fixes": 21,
                "regressions": 4,
            },
            note="Public HeySQuAD answerable validation-shard local first-document proxy; strengthens scale but does not replace LLM final-answer rows.",
        ),
        Check(
            name="heysquad_val422_direct_omni_llm_scale_caveat",
            source=Path("outputs/rag_final_answer_compare_heysquad_val422_llm_evidence.json"),
            extractor=paired_compare_decomposition_metric(
                "oracle_text_plus_omni_context_omni_top3_llm_evidence_then_answer",
                "oracle_text_plus_omni_context_asr_top3_llm_evidence_then_answer",
            ),
            expected={
                "answer_pass": 0.9549763033175356,
                "generation_miss_rate": 0.045023696682464455,
                "context_gold_rate": 1.0,
                "delta": 0.004739336492890996,
                "ci95": [-0.009478672985781991, 0.018957345971563982],
                "fixes": 6,
                "regressions": 4,
                "grounded_delta": 0.04265402843601896,
                "grounded_ci95": [0.02132701421800948, 0.06635071090047394],
                "grounded_fixes": 22,
                "grounded_regressions": 4,
            },
            note="Public HeySQuAD 422 LLM evidence run: direct audio improves grounding, while final answer-pass gain is small and not significant.",
        ),
        Check(
            name="spoken_squad_200_evidence_then_answer_transfer",
            source=Path("outputs/rag_final_answer_compare_spoken_squad_test200.json"),
            extractor=paired_compare_decomposition_metric(
                "oracle_text_plus_omni_context_omni_top3_llm_evidence_then_answer",
                "oracle_text_plus_omni_context_omni_top3_llm_default",
            ),
            expected={
                "answer_pass": 0.925,
                "generation_miss_rate": 0.075,
                "context_gold_rate": 1.0,
                "delta": 0.055,
                "ci95": [0.020, 0.090],
                "fixes": 12,
                "regressions": 1,
            },
        ),
        Check(
            name="heysquad_evidence_answer_order_shuffle_control",
            source=Path("outputs/rag_final_answer_order_shuffle_heysquad_val200_evidence.json"),
            extractor=answer_order_shuffle_metric(),
            expected={
                "n": 200,
                "base_answer_pass": 0.885,
                "shuffle_count": 3,
                "shuffle_answer_pass_mean": 0.8783333333333333,
                "shuffle_answer_pass_min": 0.87,
                "shuffle_answer_pass_max": 0.885,
                "max_abs_delta": 0.015,
                "worst_ci_lower": -0.035,
                "total_fixes": 2,
                "total_regressions": 6,
                "max_context_gold_delta": 0.0,
            },
        ),
        Check(
            name="spoken_squad_evidence_answer_order_shuffle_control",
            source=Path("outputs/rag_final_answer_order_shuffle_spoken_squad_test200_evidence.json"),
            extractor=answer_order_shuffle_metric(),
            expected={
                "n": 200,
                "base_answer_pass": 0.925,
                "shuffle_count": 3,
                "shuffle_answer_pass_mean": 0.9333333333333332,
                "shuffle_answer_pass_min": 0.93,
                "shuffle_answer_pass_max": 0.94,
                "max_abs_delta": 0.015,
                "worst_ci_lower": -0.015,
                "total_fixes": 8,
                "total_regressions": 3,
                "max_context_gold_delta": 0.0,
            },
        ),
        Check(
            name="query_audio_gate_heysquad_drift_text_equals_noquery",
            source=Path("outputs/omni_memory_v0/query_audio_gate_heysquad_natural_drift_manifest_60.json"),
            extractor=gate_summary_metric("audio_on_text_equals_noquery", "audio_on_text_equals_noquery"),
            expected={
                "n": 60,
                "success": 0.850,
                "gate_rate": 0.300,
                "audio_cost": 0.300,
                "delta": 0.06666666666666667,
                "ci95": [0.016666666666666666, 0.13333333333333333],
                "fixes": 4,
                "paired_regressions": 0,
            },
        ),
        Check(
            name="query_audio_gate_covost_neighbor_overlap",
            source=Path("outputs/omni_memory_v0/query_audio_gate_covost2_neighbor_text_manifest_60.json"),
            extractor=gate_summary_metric(
                "audio_on_hint_pred_overlap_ge_0_80",
                "audio_on_hint_pred_overlap_ge_0_80",
            ),
            expected={
                "n": 60,
                "success": 0.8166666666666667,
                "gate_rate": 1.000,
                "audio_cost": 1.000,
                "delta": 0.8166666666666667,
                "ci95": [0.7166666666666667, 0.9166666666666666],
                "fixes": 49,
                "paired_regressions": 0,
            },
        ),
        Check(
            name="query_audio_gate_minds_neighbor_overlap",
            source=Path("outputs/omni_memory_v0/query_audio_gate_minds14_neighbor_text_manifest_60.json"),
            extractor=gate_summary_metric(
                "audio_on_hint_pred_overlap_ge_0_80",
                "audio_on_hint_pred_overlap_ge_0_80",
            ),
            expected={
                "n": 60,
                "success": 0.850,
                "gate_rate": 0.8666666666666667,
                "audio_cost": 0.8666666666666667,
                "delta": 0.850,
                "ci95": [0.750, 0.9333333333333333],
                "fixes": 51,
                "paired_regressions": 0,
            },
        ),
        Check(
            name="query_audio_gate_covost_mixed_overlap",
            source=Path("outputs/query_audio_gate_mixture_summary.json"),
            extractor=gate_mixture_metric("CoVoST2 ar", "audio_on_hint_pred_overlap_ge_0_80"),
            expected={
                "n": 260,
                "success": 0.9538461538461539,
                "delta": 0.18846153846153846,
                "ci95": [0.1423076923076923, 0.23846153846153847],
                "gate_rate": 0.23076923076923078,
                "audio_cost": 0.23076923076923078,
                "fixes": 49,
                "regressions": 0,
            },
        ),
        Check(
            name="query_audio_gate_minds_mixed_overlap",
            source=Path("outputs/query_audio_gate_mixture_summary.json"),
            extractor=gate_mixture_metric("MInDS", "audio_on_hint_pred_overlap_ge_0_80"),
            expected={
                "n": 240,
                "success": 0.9375,
                "delta": 0.2125,
                "ci95": [0.1625, 0.26666666666666666],
                "gate_rate": 0.9416666666666667,
                "audio_cost": 0.9416666666666667,
                "fixes": 51,
                "regressions": 0,
            },
        ),
        Check(
            name="query_audio_gate_heysquad_mixed_text_equals_noquery",
            source=Path("outputs/query_audio_gate_mixture_summary.json"),
            extractor=gate_mixture_metric("HeySQuAD", "audio_on_text_equals_noquery"),
            expected={
                "n": 260,
                "success": 0.8923076923076924,
                "delta": 0.046153846153846156,
                "ci95": [0.019230769230769232, 0.07307692307692308],
                "gate_rate": 0.3,
                "audio_cost": 0.3,
                "fixes": 13,
                "regressions": 1,
            },
        ),
        Check(
            name="query_audio_gate_selector_covost_budgeted",
            source=Path("outputs/query_audio_gate_selector_summary.json"),
            extractor=query_audio_gate_selector_metric("CoVoST2 ar"),
            expected={
                "decision": "accepted",
                "selected_gate": "audio_on_hint_pred_overlap_ge_0_80",
                "selected_success": 0.9538461538461539,
                "selected_delta": 0.18846153846153846,
                "selected_ci95": [0.1423076923076923, 0.23846153846153847],
                "selected_audio_cost": 0.23076923076923078,
                "selected_gate_rate": 0.23076923076923078,
                "selected_fixes": 49,
                "selected_regressions": 0,
                "selected_regression_rate": 0.0,
                "accepted_count": 4,
            },
        ),
        Check(
            name="query_audio_gate_selector_minds_budgeted",
            source=Path("outputs/query_audio_gate_selector_summary.json"),
            extractor=query_audio_gate_selector_metric("MInDS"),
            expected={
                "decision": "accepted",
                "selected_gate": "audio_on_text_first_candidate",
                "selected_success": 0.8708333333333333,
                "selected_delta": 0.14583333333333334,
                "selected_ci95": [0.10416666666666667, 0.19166666666666668],
                "selected_audio_cost": 0.32916666666666666,
                "selected_gate_rate": 0.32916666666666666,
                "selected_fixes": 35,
                "selected_regressions": 0,
                "selected_regression_rate": 0.0,
                "accepted_count": 2,
            },
        ),
        Check(
            name="query_audio_gate_selector_heysquad_budgeted",
            source=Path("outputs/query_audio_gate_selector_summary.json"),
            extractor=query_audio_gate_selector_metric("HeySQuAD"),
            expected={
                "decision": "accepted",
                "selected_gate": "audio_on_text_equals_noquery",
                "selected_success": 0.8923076923076924,
                "selected_delta": 0.046153846153846156,
                "selected_ci95": [0.019230769230769232, 0.07307692307692308],
                "selected_audio_cost": 0.3,
                "selected_gate_rate": 0.3,
                "selected_fixes": 13,
                "selected_regressions": 1,
                "selected_regression_rate": 0.0038461538461538464,
                "accepted_count": 2,
            },
        ),
        Check(
            name="query_audio_gate_deployability_summary",
            source=Path("outputs/query_audio_gate_deployability_summary.json"),
            extractor=query_audio_gate_deployability_metric,
            expected={
                "dataset_count": 3,
                "accepted_count": 3,
                "mean_selected_delta": 0.1268162393162394,
                "mean_selected_audio_cost": 0.2866452991452992,
                "mean_audio_cost_reduction_rate": 0.7133547008547009,
                "covost_selected_gate": "audio_on_hint_pred_overlap_ge_0_80",
                "covost_delta": 0.18846153846153857,
                "covost_clean_delta": 0.0,
                "covost_stress_delta": 0.8166666666666667,
                "covost_audio_cost": 0.23076923076923078,
                "minds_selected_gate": "audio_on_text_first_candidate",
                "minds_delta": 0.14583333333333337,
                "minds_clean_delta": 0.011111111111111072,
                "minds_stress_delta": 0.55,
                "minds_audio_cost": 0.32916666666666666,
                "heysquad_selected_gate": "audio_on_text_equals_noquery",
                "heysquad_delta": 0.04615384615384621,
                "heysquad_clean_delta": 0.040000000000000036,
                "heysquad_stress_delta": 0.06666666666666665,
                "heysquad_audio_cost": 0.3,
                "total_regressions": 1,
            },
        ),
        Check(
            name="aishell_wu_dialect_route_summary",
            source=Path("outputs/dialect_route_summary.json"),
            extractor=dialect_route_metric(),
            expected={
                "aishell_n": 63,
                "aishell_asr_test_cer": 0.36374239497352584,
                "aishell_asr_acc": 0.9523809523809523,
                "aishell_omni_acc": 0.7619047619047619,
                "aishell_omni_delta": -0.19047619047619047,
                "aishell_omni_ci95": [-0.30158730158730157, -0.07936507936507936],
                "aishell_omni_regressions": 14,
                "aishell_disagreement_route_rate": 0.2698412698412698,
                "wu_n": 21,
                "wu_asr_test_cer": 0.8146834335909967,
                "wu_asr_acc": 0.3333333333333333,
                "wu_omni_acc": 0.9047619047619048,
                "wu_omni_delta": 0.5714285714285714,
                "wu_omni_ci95": [0.38095238095238093, 0.7619047619047619],
                "wu_omni_regressions": 0,
                "wu_rrf_acc": 0.5238095238095238,
                "wu_rrf_delta": 0.19047619047619047,
                "wu_disagreement_route_rate": 0.6666666666666666,
            },
        ),
        Check(
            name="controller_component_summary",
            source=Path("outputs/controller_component_summary.json"),
            extractor=controller_component_metric(),
            expected={
                "row_count": 10,
                "uro_delta": 0.085,
                "uro_ci95": [0.045, 0.13],
                "uro_regressions": 1,
                "slurp_delta": 0.126,
                "slurp_ci95": [0.098, 0.156],
                "slurp_regressions": 0,
                "covost_delta": 0.11032448377581117,
                "covost_ci95": [0.09616519174041298, 0.1256637168141593],
                "covost_regressions": 6,
                "aishell_delta": -0.19047619047619047,
                "aishell_regressions": 14,
                "wu_delta": 0.5714285714285714,
                "wu_regressions": 0,
                "covost_gate_delta": 0.18846153846153846,
                "covost_gate_regressions": 0,
                "heysquad_gate_delta": 0.046153846153846156,
                "heysquad_gate_regressions": 1,
                "packing_delta": 0.315,
                "packing_regressions": 5,
                "heysquad_answer_delta": 0.095,
                "heysquad_answer_regressions": 4,
                "spoken_answer_delta": 0.055,
                "spoken_answer_regressions": 1,
            },
        ),
        Check(
            name="covost_translation_order_robustness_summary",
            source=Path("outputs/translation_order_robustness_summary.json"),
            extractor=translation_order_robustness_metric(),
            expected={
                "ar_same_order_delta": 0.055,
                "ar_same_order_ci95": [0.02, 0.09],
                "ar_shuffle_delta_mean": 0.023333333333333334,
                "ar_shuffle_delta_min": 0.0,
                "ar_shuffle_seed_accept_count": 1,
                "ar_order_robust": False,
                "ar_self_consistency_delta": 0.035,
                "ar_self_consistency_ci95": [0.0, 0.07],
                "ar_self_consistency_weak_accept": True,
                "ar_decision": "self_consistency_weak_costly_diagnostic",
                "zh_same_order_delta": 0.045,
                "zh_same_order_ci95": [0.015, 0.08],
                "zh_shuffle_delta_mean": 0.005000000000000001,
                "zh_shuffle_delta_min": -0.015,
                "zh_shuffle_seed_accept_count": 0,
                "zh_order_robust": False,
                "zh_self_consistency_delta": 0.05,
                "zh_self_consistency_ci95": [0.015, 0.09],
                "zh_self_consistency_strict_accept": True,
                "zh_decision": "self_consistency_positive_but_costly",
            },
        ),
        Check(
            name="controller_cost_budget_summary",
            source=Path("outputs/controller_cost_budget_summary.json"),
            extractor=controller_cost_budget_metric(),
            expected={
                "row_count": 13,
                "slurp_tau01_delta": 0.126,
                "slurp_tau01_route": 0.496,
                "slurp_tau02_delta": 0.1399999999999999,
                "slurp_tau02_route": 0.666,
                "slurp_tau02_marginal_benefit": 0.08235294117646999,
                "minds_delta": 0.0722222222222223,
                "minds_route": 0.35,
                "covost_test_delta": 0.11032448377581117,
                "covost_test_route": 0.49734513274336284,
                "covost_gate_delta": 0.18846153846153846,
                "covost_gate_audio_cost": 0.23076923076923078,
                "minds_gate_delta": 0.14583333333333334,
                "minds_gate_audio_cost": 0.32916666666666666,
                "heysquad_gate_delta": 0.046153846153846156,
                "heysquad_gate_audio_cost": 0.3,
                "packing_delta": 0.315,
                "packing_text_token_delta": -542.995,
                "heysquad_answer_delta": 0.09499999999999997,
                "spoken_answer_delta": 0.05500000000000005,
                "ar_self_cost": 4.0,
                "ar_self_latency_ratio": 8.842676061202638,
                "zh_self_cost": 4.0,
                "zh_self_latency_ratio": 6.509505317393842,
                "gemma12b_delta": -0.30612244897959184,
                "gemma12b_latency_ratio": 60.6921373200443,
                "gemma12b_regressions": 19,
            },
        ),
        Check(
            name="badcase_audit_samples",
            source=Path("outputs/badcase_audit_samples.json"),
            extractor=badcase_audit_sample_metric(),
            expected={
                "case_count": 35,
                "slurp_routed": 248,
                "slurp_fixes_total": 63,
                "slurp_regressions_total": 0,
                "covost_routed": 843,
                "covost_fixes_total": 193,
                "covost_regressions_total": 6,
                "heysquad_compared": 200,
                "heysquad_fixes_total": 68,
                "heysquad_regressions_total": 5,
            },
            note="Qualitative audit sample count guardrail; not a new metric table.",
        ),
        Check(
            name="runtime_latency_summary",
            source=Path("outputs/runtime_latency_summary.json"),
            extractor=runtime_latency_summary_metric(),
            expected={
                "row_count": 9,
                "covost_full_audio_success_delta": -0.125,
                "covost_full_audio_latency_ratio": 2.806764896998648,
                "minds_full_audio_success_delta": -0.17222222222222228,
                "minds_full_audio_latency_ratio": 2.752199434741648,
                "packing_success_delta": 0.31499999999999995,
                "packing_text_cost_delta": -542.995,
                "packing_latency_ratio": 0.7350095868921038,
                "pg_packing_text_cost_delta": -591.825,
                "pg_packing_latency_ratio": 0.6974972698309552,
                "backend_success_delta": -0.30612244897959184,
                "backend_latency_ratio": 60.6921373200443,
            },
            note="Runtime-like cost evidence from existing memory-use outputs.",
        ),
        Check(
            name="cross_model_backend_readiness_summary",
            source=Path("outputs/cross_model_backend_readiness_summary.json"),
            extractor=cross_model_backend_readiness_metric(),
            expected={
                "embedding_backend_count": 3,
                "embedding_raw_fallback_count": 3,
                "embedding_stability_no_positive_count": 2,
                "system_side_positive_count": 2,
                "generative_backend_count": 8,
                "main_backend_ready": True,
                "stable_second_generative_backend_ready": False,
                "second_backend_smoke_positive": True,
                "jina_selector_tasks": 3,
                "jina_stability_tasks": 2,
                "e4b_formal_n": 30,
                "e4b_formal_raw": 0.06666666666666667,
                "e4b_formal_best": 0.5333333333333333,
                "e4b_formal_delta": 0.4666666666666667,
                "gemma12b_partial_n": 49,
                "gemma12b_delta": -0.30612244897959184,
                "gemma12b_latency_ratio": 60.6921373200443,
                "qwen3_smoke_n": 2,
                "qwen3_smoke_accuracy": 0.0,
                "qwen3_chat_n": 2,
                "qwen3_chat_valid_rate": 0.0,
                "qwen3_chat_parse_rate": 0.0,
                "qwen3_chat_timeout_count": 2,
                "qwen3_chat_mean_latency_ms": 360000.0,
                "voxtral_attempted_rows": 1,
                "voxtral_completed_rows": 0,
                "voxtral_valid_rate": 0.0,
                "voxtral_parse_rate": 0.0,
                "voxtral_timeout_count": 1,
                "voxtral_timeout_s": 300,
                "voxtral_minimal_log_bytes": 0,
                "voxtral_chat_n": 60,
                "voxtral_chat_valid_rate": 1.0,
                "voxtral_chat_parse_rate": 1.0,
                "voxtral_chat_accuracy": 0.6166666666666667,
                "voxtral_chat_mean_latency_ms": 39910.17986338556,
                "jina_slurp_system_delta": 0.27,
                "jina_minds_system_delta": 0.15555555555555556,
            },
            note="Cross-model/backend readiness guardrail; separates raw fallback, system-side gains, and backend blockers.",
        ),
        Check(
            name="translation_order_gate_repair_summary",
            source=Path("outputs/translation_order_gate_summary.json"),
            extractor=translation_order_gate_metric(),
            expected={
                "dataset_count": 2,
                "ar_always_shuffle_strict_accept": 1,
                "ar_gate_mean_delta": 0.025,
                "ar_gate_min_delta": 0.01,
                "ar_gate_shuffle_strict_accept": 2,
                "ar_gate_shuffle_weak_accept": 2,
                "ar_gate_max_regression_rate": 0.005,
                "ar_gate_decision": "partial_order_repair",
                "ar_rank_deviation_gate_mean_delta": 0.03875,
                "ar_rank_deviation_gate_min_delta": 0.02,
                "ar_rank_deviation_gate_shuffle_strict_accept": 2,
                "ar_rank_deviation_gate_shuffle_weak_accept": 3,
                "ar_rank_deviation_gate_max_regression_rate": 0.005,
                "ar_rank_deviation_gate_decision": "weak_order_robust_accept",
                "zh_always_shuffle_strict_accept": 0,
                "zh_gate_mean_delta": 0.03125,
                "zh_gate_min_delta": 0.01,
                "zh_gate_shuffle_strict_accept": 2,
                "zh_gate_shuffle_weak_accept": 3,
                "zh_gate_max_regression_rate": 0.0,
                "zh_gate_decision": "weak_order_robust_accept",
                "zh_rank_deviation_gate_mean_delta": 0.03125,
                "zh_rank_deviation_gate_min_delta": 0.01,
                "zh_rank_deviation_gate_shuffle_strict_accept": 2,
                "zh_rank_deviation_gate_shuffle_weak_accept": 3,
                "zh_rank_deviation_gate_max_regression_rate": 0.0,
                "zh_rank_deviation_gate_decision": "weak_order_robust_accept",
                "ar_retrieval_top1_mean_delta": -0.02125,
                "ar_retrieval_top1_decision": "diagnostic_only",
                "zh_retrieval_top1_mean_delta": 0.11,
                "zh_retrieval_top1_decision": "strict_order_robust_accept",
            },
            note="Cheap order-risk gate for CoVoST2 translation memory-use; retrieval-top1 fallback is system-side diagnostic.",
        ),
        Check(
            name="translation_multivote_gate_repair_summary",
            source=Path("outputs/translation_multivote_gate_summary.json"),
            extractor=translation_multivote_gate_metric(),
            expected={
                "dataset_count": 2,
                "ar_always_delta": 0.035,
                "ar_always_regressions": 3,
                "ar_strict_success": 0.83,
                "ar_strict_delta": 0.025,
                "ar_strict_ci95": [0.005, 0.05],
                "ar_strict_fixes": 5,
                "ar_strict_regressions": 0,
                "ar_strict_route_rate": 0.785,
                "ar_strict_mean_audio_cost": 3.355,
                "ar_standard_delta": 0.04,
                "ar_standard_regressions": 1,
                "zh_always_delta": 0.05,
                "zh_always_regressions": 3,
                "zh_strict_success": 0.925,
                "zh_strict_delta": 0.065,
                "zh_strict_ci95": [0.035, 0.1],
                "zh_strict_fixes": 13,
                "zh_strict_regressions": 0,
                "zh_strict_route_rate": 0.91,
                "zh_strict_mean_audio_cost": 3.73,
                "zh_standard_delta": 0.065,
                "zh_standard_regressions": 0,
            },
            note="Expensive four-order translation gate; strict no-regression repair for CoVoST2 ar/zh memory-use order sensitivity.",
        ),
        Check(
            name="candidate_order_covost2_stable_exact",
            source=Path("outputs/candidate_order_stability_summary.json"),
            extractor=candidate_order_stability_metric("CoVoST2 ar->en"),
            expected={
                "n": 200,
                "base_success": 1.0,
                "shuffle_success_mean": 1.0,
                "shuffle_success_min": 1.0,
                "shuffle_success_max": 1.0,
                "max_abs_delta": 0.0,
                "total_regressions": 0,
                "max_regression_rate": 0.0,
                "decision": "stable_exact",
            },
        ),
        Check(
            name="candidate_order_minds_stable_bounded",
            source=Path("outputs/candidate_order_stability_summary.json"),
            extractor=candidate_order_stability_metric("MInDS-14"),
            expected={
                "n": 180,
                "base_success": 1.0,
                "shuffle_success_mean": 0.9981481481481481,
                "shuffle_success_min": 0.9944444444444445,
                "shuffle_success_max": 1.0,
                "max_abs_delta": 0.005555555555555556,
                "total_regressions": 1,
                "max_regression_rate": 0.005555555555555556,
                "decision": "stable_bounded",
            },
        ),
        Check(
            name="candidate_order_heysquad_mild_sensitivity",
            source=Path("outputs/candidate_order_stability_summary.json"),
            extractor=candidate_order_stability_metric("HeySQuAD"),
            expected={
                "n": 200,
                "base_success": 0.91,
                "shuffle_success_mean": 0.91,
                "shuffle_success_min": 0.905,
                "shuffle_success_max": 0.92,
                "max_abs_delta": 0.01,
                "total_regressions": 19,
                "max_regression_rate": 0.035,
                "decision": "mild_order_sensitivity_control",
            },
        ),
        Check(
            name="heysquad_retrieval_use_raw_top5_bottleneck",
            source=Path("outputs/retrieval_use_summary.json"),
            extractor=retrieval_use_metric("heysquad_raw_top5", "heysquad_policy_grounding_top5"),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 0.78,
                "memory_use_success": 0.28,
                "hit_but_use_fail": 0.5,
                "retrieval_miss": 0.22,
                "invalid_output": 0.035,
                "context_overflow_rate": 0.035,
                "success_delta": -0.025,
                "ci95": [-0.06, 0.005],
                "fixes": 3,
                "regressions": 8,
                "invalid_delta": 0.025,
            },
        ),
        Check(
            name="heysquad_raw_top5_packed_memory_use_gain",
            source=Path("outputs/retrieval_use_packed_summary.json"),
            extractor=retrieval_use_metric("heysquad_raw_top5_original", "heysquad_raw_top5_packed"),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 0.78,
                "memory_use_success": 0.28,
                "hit_but_use_fail": 0.5,
                "retrieval_miss": 0.22,
                "invalid_output": 0.035,
                "context_overflow_rate": 0.035,
                "success_delta": 0.315,
                "ci95": [0.245, 0.385],
                "fixes": 68,
                "regressions": 5,
                "invalid_delta": -0.035,
            },
        ),
        Check(
            name="heysquad_spoken_squad_end_to_end_chain_summary",
            source=Path("outputs/end_to_end_chain_summary.json"),
            extractor=end_to_end_chain_metric(),
            expected={
                "heysquad_retrieval_hit_at_5": 0.78,
                "heysquad_original_memory_use_success": 0.28,
                "heysquad_packed_memory_use_success": 0.595,
                "heysquad_top3_evidence_answer_pass": 0.885,
                "heysquad_top5_evidence_answer_pass": 0.895,
                "heysquad_original_hit_but_use_fail": 0.5,
                "heysquad_packed_hit_but_use_fail": 0.185,
                "heysquad_top5_generation_miss_rate": 0.045,
                "spoken_squad_default_answer_pass": 0.87,
                "spoken_squad_evidence_answer_pass": 0.925,
                "heysquad_order_max_abs_delta": 0.015,
                "spoken_order_max_abs_delta": 0.015,
            },
        ),
        Check(
            name="covost2_ar_retrieval_use_raw_top5",
            source=Path("outputs/retrieval_use_translation_summary.json"),
            extractor=retrieval_use_metric("covost2_ar_raw_top5"),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 0.965,
                "memory_use_success": 0.805,
                "hit_but_use_fail": 0.160,
                "retrieval_miss": 0.035,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
            },
        ),
        Check(
            name="covost2_ar_translation_target_text_memory_use_gain",
            source=Path("outputs/retrieval_use_translation_policy_ar_summary.json"),
            extractor=retrieval_use_metric(
                "covost2_ar_raw_top5",
                "covost2_ar_translation_target_text_top5",
            ),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 0.965,
                "memory_use_success": 0.805,
                "hit_but_use_fail": 0.160,
                "retrieval_miss": 0.035,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
                "success_delta": 0.055,
                "ci95": [0.020, 0.090],
                "fixes": 12,
                "regressions": 1,
                "invalid_delta": 0.0,
            },
        ),
        Check(
            name="covost2_zh_retrieval_use_raw_top5",
            source=Path("outputs/retrieval_use_translation_summary.json"),
            extractor=retrieval_use_metric("covost2_zh_raw_top5"),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 1.0,
                "memory_use_success": 0.860,
                "hit_but_use_fail": 0.140,
                "retrieval_miss": 0.0,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
            },
        ),
        Check(
            name="covost2_zh_translation_target_text_memory_use_gain",
            source=Path("outputs/retrieval_use_translation_policy_zh_summary.json"),
            extractor=retrieval_use_metric(
                "covost2_zh_raw_top5",
                "covost2_zh_translation_target_text_top5",
            ),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 1.0,
                "memory_use_success": 0.860,
                "hit_but_use_fail": 0.140,
                "retrieval_miss": 0.0,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
                "success_delta": 0.045,
                "ci95": [0.010, 0.080],
                "fixes": 11,
                "regressions": 2,
                "invalid_delta": 0.0,
            },
        ),
        Check(
            name="covost2_ar_translation_policy_shuffle_control",
            source=Path("outputs/omni_memory_v0/summary_shuffle_covost2_ar_translation_vs_generic.json"),
            extractor=result_compare_summary_metric(
                base_label="generic_base",
                compare_pairs=[
                    ("trans_base", "generic_base"),
                    ("trans_s7", "generic_s7"),
                    ("trans_s17", "generic_s17"),
                    ("trans_s29", "generic_s29"),
                ],
            ),
            expected={
                "n": 200,
                "base_success": 0.805,
                "trans_base_vs_generic_base_delta": 0.055,
                "trans_base_vs_generic_base_ci95": [0.020, 0.090],
                "trans_base_vs_generic_base_fixes": 12,
                "trans_base_vs_generic_base_regressions": 1,
                "trans_s7_vs_generic_s7_delta": 0.0,
                "trans_s7_vs_generic_s7_ci95": [-0.030, 0.030],
                "trans_s7_vs_generic_s7_fixes": 5,
                "trans_s7_vs_generic_s7_regressions": 5,
                "trans_s17_vs_generic_s17_delta": 0.035,
                "trans_s17_vs_generic_s17_ci95": [0.0, 0.070],
                "trans_s17_vs_generic_s17_fixes": 11,
                "trans_s17_vs_generic_s17_regressions": 4,
                "trans_s29_vs_generic_s29_delta": 0.035,
                "trans_s29_vs_generic_s29_ci95": [0.005, 0.070],
                "trans_s29_vs_generic_s29_fixes": 9,
                "trans_s29_vs_generic_s29_regressions": 2,
            },
        ),
        Check(
            name="covost2_zh_translation_policy_shuffle_control",
            source=Path("outputs/omni_memory_v0/summary_shuffle_covost2_zh_translation_vs_generic.json"),
            extractor=result_compare_summary_metric(
                base_label="generic_base",
                compare_pairs=[
                    ("trans_base", "generic_base"),
                    ("trans_s7", "generic_s7"),
                    ("trans_s17", "generic_s17"),
                    ("trans_s29", "generic_s29"),
                ],
            ),
            expected={
                "n": 200,
                "base_success": 0.860,
                "trans_base_vs_generic_base_delta": 0.045,
                "trans_base_vs_generic_base_ci95": [0.015, 0.080],
                "trans_base_vs_generic_base_fixes": 11,
                "trans_base_vs_generic_base_regressions": 2,
                "trans_s7_vs_generic_s7_delta": 0.025,
                "trans_s7_vs_generic_s7_ci95": [-0.005, 0.055],
                "trans_s7_vs_generic_s7_fixes": 8,
                "trans_s7_vs_generic_s7_regressions": 3,
                "trans_s17_vs_generic_s17_delta": 0.005,
                "trans_s17_vs_generic_s17_ci95": [-0.020, 0.030],
                "trans_s17_vs_generic_s17_fixes": 4,
                "trans_s17_vs_generic_s17_regressions": 3,
                "trans_s29_vs_generic_s29_delta": -0.015,
                "trans_s29_vs_generic_s29_ci95": [-0.045, 0.015],
                "trans_s29_vs_generic_s29_fixes": 3,
                "trans_s29_vs_generic_s29_regressions": 6,
            },
        ),
        Check(
            name="covost2_ar_translation_order_self_consistency",
            source=Path("outputs/omni_memory_v0/summary_order_self_consistency_covost2_ar_vs_generic.json"),
            extractor=result_compare_summary_metric(
                base_label="generic",
                compare_pairs=[("self", "generic")],
            ),
            expected={
                "n": 200,
                "base_success": 0.805,
                "self_vs_generic_delta": 0.035,
                "self_vs_generic_ci95": [0.0, 0.070],
                "self_vs_generic_fixes": 10,
                "self_vs_generic_regressions": 3,
            },
        ),
        Check(
            name="covost2_zh_translation_order_self_consistency",
            source=Path("outputs/omni_memory_v0/summary_order_self_consistency_covost2_zh_vs_generic.json"),
            extractor=result_compare_summary_metric(
                base_label="generic",
                compare_pairs=[("self", "generic")],
            ),
            expected={
                "n": 200,
                "base_success": 0.860,
                "self_vs_generic_delta": 0.050,
                "self_vs_generic_ci95": [0.015, 0.090],
                "self_vs_generic_fixes": 13,
                "self_vs_generic_regressions": 3,
            },
        ),
        Check(
            name="gemma12b_partial_covost2_memory_use_backend_diagnostic",
            source=Path("outputs/omni_memory_v0/summary_gemma12b_partial_covost2_vs_e4b.json"),
            extractor=result_compare_summary_metric(
                base_label="e4b",
                compare_pairs=[("gemma12b_partial", "e4b")],
            ),
            expected={
                "n": 200,
                "base_success": 0.835,
                "gemma12b_partial_vs_e4b_n": 49,
                "gemma12b_partial_vs_e4b_delta": -0.30612244897959184,
                "gemma12b_partial_vs_e4b_ci95": [
                    -0.4897959183673469,
                    -0.14285714285714285,
                ],
                "gemma12b_partial_vs_e4b_fixes": 4,
                "gemma12b_partial_vs_e4b_regressions": 19,
            },
        ),
        Check(
            name="heysquad_packed_policy_grounding_no_gain",
            source=Path("outputs/retrieval_use_packed_vs_packed_summary.json"),
            extractor=retrieval_use_metric("heysquad_raw_top5_packed", "heysquad_policy_grounding_top5_packed"),
            expected={
                "n": 200,
                "retrieval_hit_at_k": 0.78,
                "memory_use_success": 0.595,
                "hit_but_use_fail": 0.185,
                "retrieval_miss": 0.22,
                "invalid_output": 0.0,
                "context_overflow_rate": 0.0,
                "success_delta": -0.005,
                "ci95": [-0.035, 0.025],
                "fixes": 4,
                "regressions": 5,
                "invalid_delta": 0.0,
            },
        ),
        Check(
            name="heysquad_raw_top5_answer_evidence_packing_budget",
            source=Path("outputs/memory_packing_summary.json"),
            extractor=memory_packing_metric("heysquad_raw_top5"),
            expected={
                "n": 200,
                "original_mean_prompt_tokens": 789.415,
                "packed_mean_prompt_tokens": 246.42,
                "mean_token_reduction": 542.995,
                "original_max_prompt_tokens": 2757,
                "packed_max_prompt_tokens": 332,
                "original_overflow_rate": 0.03,
                "packed_overflow_rate": 0.0,
                "original_p95_prompt_tokens": 1459,
                "packed_p95_prompt_tokens": 326,
            },
        ),
        Check(
            name="heysquad_policy_grounding_top5_answer_evidence_packing_budget",
            source=Path("outputs/memory_packing_summary.json"),
            extractor=memory_packing_metric("heysquad_policy_grounding_top5"),
            expected={
                "n": 200,
                "original_mean_prompt_tokens": 837.36,
                "packed_mean_prompt_tokens": 245.535,
                "mean_token_reduction": 591.825,
                "original_max_prompt_tokens": 2757,
                "packed_max_prompt_tokens": 332,
                "original_overflow_rate": 0.045,
                "packed_overflow_rate": 0.0,
                "original_p95_prompt_tokens": 1736,
                "packed_p95_prompt_tokens": 326,
            },
        ),
        Check(
            name="experiment_coverage_summary",
            source=Path("outputs/experiment_coverage_summary.json"),
            extractor=experiment_coverage_summary_metric(),
            expected={
                "block_count": 11,
                "verified_block_count": 9,
                "ready_block_count": 8,
                "partial_block_count": 0,
                "blocker_count": 1,
                "out_of_scope_count": 1,
                "deferred_count": 1,
                "verifier_check_count": 65,
                "verifier_pass_count": 65,
                "paper_decision": "core_evidence_ready",
            },
            note="Coverage guardrail over evidence blocks; excludes this self-check from its verifier count.",
        ),
    ]


def run(output: Path) -> dict[str, Any]:
    rows = []
    for check in build_checks():
        if not check.source.exists():
            rows.append(
                {
                    "name": check.name,
                    "source": str(check.source),
                    "status": "missing_source",
                    "expected": check.expected,
                    "note": check.note,
                }
            )
            continue
        data = read_json(check.source)
        observed = check.extractor(data)
        passed, mismatches = compare(observed, check.expected)
        rows.append(
            {
                "name": check.name,
                "source": str(check.source),
                "status": "pass" if passed else "mismatch",
                "observed": observed,
                "expected": check.expected,
                "mismatches": mismatches,
                "note": check.note,
            }
        )
    summary = {
        "check_count": len(rows),
        "pass_count": sum(row["status"] == "pass" for row in rows),
        "mismatch_count": sum(row["status"] == "mismatch" for row in rows),
        "missing_source_count": sum(row["status"] == "missing_source" for row in rows),
    }
    result = {
        "experiment": "verify_paper_evidence",
        "tolerance": TOL,
        "summary": summary,
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/paper_evidence_verification.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
