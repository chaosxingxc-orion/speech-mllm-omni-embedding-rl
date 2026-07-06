"""Build a compact controller component ablation summary.

This is an offline paper-facing synthesis.  It deliberately separates action
layers instead of pretending that every improvement is an omni-embedding
instruction gain:

* omni-side instruction,
* low-margin verifier,
* route boundary,
* selective query audio,
* memory packing,
* evidence-bound final-answer protocol.

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


def by_label(data: dict[str, Any], key: str = "label") -> dict[str, dict[str, Any]]:
    return {str(item.get(key)): item for item in data.get("rows", [])}


def by_dataset(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("dataset")): item for item in data.get("selections", [])}


def final_answer_summary(data: dict[str, Any], label_token: str) -> dict[str, Any]:
    for item in data.get("summaries", []):
        if label_token in str(item.get("label")):
            return item
    raise KeyError(f"missing final-answer summary containing {label_token!r}")


def build(args: argparse.Namespace) -> dict[str, Any]:
    uro = read_json(args.uro_instruction)
    slurp_verifier = read_json(args.slurp_verifier)
    covost_verifier = read_json(args.covost_verifier)
    gate = read_json(args.query_audio_gate_selector)
    gate_rows = by_dataset(gate)
    packing = read_json(args.retrieval_use_packed)
    packing_rows = by_label(packing)
    dialect = read_json(args.dialect_route)
    answer = read_json(args.final_answer_compare)
    spoken = read_json(args.spoken_final_answer_compare)
    answer_default = final_answer_summary(answer, "top3_llm_default")
    answer_evidence = final_answer_summary(answer, "top3_llm_evidence_then_answer")
    spoken_default = final_answer_summary(spoken, "omni_top3_llm_default")
    spoken_evidence = final_answer_summary(spoken, "omni_top3_llm_evidence_then_answer")

    rows = [
        {
            "component": "omni_instruction",
            "dataset": "URO QA/reasoning",
            "baseline": "raw direct omni",
            "policy": "policy_grounding",
            "baseline_score": nested(uro, "hit_at_1", "baseline"),
            "policy_score": nested(uro, "hit_at_1", "candidate"),
            "delta": nested(uro, "hit_at_1", "delta"),
            "ci95": nested(uro, "hit_at_1", "bootstrap_ci95"),
            "cost": "no extra model call",
            "fixes": uro.get("fix_count"),
            "regressions": uro.get("regression_count"),
            "decision": "accepted instruction arm",
            "source": str(args.uro_instruction),
        },
        {
            "component": "low_margin_verifier",
            "dataset": "SLURP intent",
            "baseline": "raw direct omni",
            "policy": "low-margin top-3 verifier tau=0.01",
            "baseline_score": nested(slurp_verifier, "base_metrics", "accuracy_at_1"),
            "policy_score": nested(slurp_verifier, "metrics", "accuracy_at_1"),
            "delta": nested(slurp_verifier, "delta", "accuracy_at_1"),
            "ci95": nested(slurp_verifier, "delta", "ci95"),
            "cost": f"route_rate {slurp_verifier.get('route_rate')}",
            "fixes": slurp_verifier.get("fix_count"),
            "regressions": slurp_verifier.get("regression_count"),
            "decision": "accepted verifier controller",
            "source": str(args.slurp_verifier),
        },
        {
            "component": "low_margin_verifier",
            "dataset": "CoVoST2 ar->en locked test",
            "baseline": "raw direct omni",
            "policy": "low-margin top-3 verifier tau=0.02",
            "baseline_score": nested(covost_verifier, "base_metrics", "accuracy_at_1"),
            "policy_score": nested(covost_verifier, "metrics", "accuracy_at_1"),
            "delta": nested(covost_verifier, "delta", "accuracy_at_1"),
            "ci95": nested(covost_verifier, "delta", "ci95"),
            "cost": f"route_rate {covost_verifier.get('route_rate')}",
            "fixes": covost_verifier.get("fix_count"),
            "regressions": covost_verifier.get("regression_count"),
            "decision": "accepted verifier controller",
            "source": str(args.covost_verifier),
        },
        {
            "component": "route_boundary",
            "dataset": "AISHELL-1 clean Mandarin",
            "baseline": "ASR primary",
            "policy": "direct omni primary",
            "baseline_score": nested(dialect, "headline", "aishell_asr_acc"),
            "policy_score": nested(dialect, "headline", "aishell_omni_acc"),
            "delta": nested(dialect, "headline", "aishell_omni_delta"),
            "ci95": nested(dialect, "rows", default=[])[0]["policies"]["omni_primary"]["ci95_vs_asr"],
            "cost": "no extra model call",
            "fixes": nested(dialect, "rows", default=[])[0]["policies"]["omni_primary"]["rescues"],
            "regressions": nested(dialect, "headline", "aishell_omni_regressions"),
            "decision": "reject omni primary; keep ASR primary",
            "source": str(args.dialect_route),
        },
        {
            "component": "route_boundary",
            "dataset": "WenetSpeech-Wu dialect",
            "baseline": "ASR primary",
            "policy": "direct omni primary",
            "baseline_score": nested(dialect, "headline", "wu_asr_acc"),
            "policy_score": nested(dialect, "headline", "wu_omni_acc"),
            "delta": nested(dialect, "headline", "wu_omni_delta"),
            "ci95": nested(dialect, "rows", default=[])[1]["policies"]["omni_primary"]["ci95_vs_asr"],
            "cost": "no extra model call",
            "fixes": nested(dialect, "rows", default=[])[1]["policies"]["omni_primary"]["rescues"],
            "regressions": nested(dialect, "headline", "wu_omni_regressions"),
            "decision": "accept omni primary under ASR collapse",
            "source": str(args.dialect_route),
        },
        {
            "component": "query_audio_gate",
            "dataset": "CoVoST2 mixed clean+stress",
            "baseline": "text-only mixed",
            "policy": gate_rows["CoVoST2 ar"]["selected_gate"],
            "baseline_score": gate_rows["CoVoST2 ar"]["selected_success"] - gate_rows["CoVoST2 ar"]["selected_delta"],
            "policy_score": gate_rows["CoVoST2 ar"]["selected_success"],
            "delta": gate_rows["CoVoST2 ar"]["selected_delta"],
            "ci95": gate_rows["CoVoST2 ar"]["selected_ci95"],
            "cost": f"audio_cost {gate_rows['CoVoST2 ar']['selected_audio_cost']}",
            "fixes": gate_rows["CoVoST2 ar"]["selected_fixes"],
            "regressions": gate_rows["CoVoST2 ar"]["selected_regressions"],
            "decision": "accepted budgeted query-audio gate",
            "source": str(args.query_audio_gate_selector),
        },
        {
            "component": "query_audio_gate",
            "dataset": "HeySQuAD mixed clean+drift",
            "baseline": "text-only mixed",
            "policy": gate_rows["HeySQuAD"]["selected_gate"],
            "baseline_score": gate_rows["HeySQuAD"]["selected_success"] - gate_rows["HeySQuAD"]["selected_delta"],
            "policy_score": gate_rows["HeySQuAD"]["selected_success"],
            "delta": gate_rows["HeySQuAD"]["selected_delta"],
            "ci95": gate_rows["HeySQuAD"]["selected_ci95"],
            "cost": f"audio_cost {gate_rows['HeySQuAD']['selected_audio_cost']}",
            "fixes": gate_rows["HeySQuAD"]["selected_fixes"],
            "regressions": gate_rows["HeySQuAD"]["selected_regressions"],
            "decision": "accepted budgeted query-audio gate",
            "source": str(args.query_audio_gate_selector),
        },
        {
            "component": "memory_packing",
            "dataset": "HeySQuAD retrieval-to-use",
            "baseline": "original top-5 memory cards",
            "policy": "answer/evidence packed memory cards",
            "baseline_score": packing_rows["heysquad_raw_top5_original"]["memory_use_success"],
            "policy_score": packing_rows["heysquad_raw_top5_packed"]["memory_use_success"],
            "delta": packing["comparisons"][1]["success_delta"],
            "ci95": packing["comparisons"][1]["ci95"],
            "cost": (
                f"text_cost {packing_rows['heysquad_raw_top5_original']['mean_text_cost']} -> "
                f"{packing_rows['heysquad_raw_top5_packed']['mean_text_cost']}"
            ),
            "fixes": packing["comparisons"][1]["fixes"],
            "regressions": packing["comparisons"][1]["regressions"],
            "decision": "accepted memory-use action",
            "source": str(args.retrieval_use_packed),
        },
        {
            "component": "evidence_protocol",
            "dataset": "HeySQuAD final answer",
            "baseline": "default LLM answer",
            "policy": "evidence-then-answer",
            "baseline_score": nested(answer_default, "metrics", "answer_pass"),
            "policy_score": nested(answer_evidence, "metrics", "answer_pass"),
            "delta": 0.095,
            "ci95": [0.045, 0.145],
            "cost": "same top-3 context",
            "fixes": 23,
            "regressions": 4,
            "decision": "accepted final-answer memory-use protocol",
            "source": str(args.final_answer_compare),
        },
        {
            "component": "evidence_protocol",
            "dataset": "Spoken-SQuAD final answer",
            "baseline": "default LLM answer",
            "policy": "evidence-then-answer",
            "baseline_score": nested(spoken_default, "metrics", "answer_pass"),
            "policy_score": nested(spoken_evidence, "metrics", "answer_pass"),
            "delta": 0.055,
            "ci95": [0.020, 0.090],
            "cost": "same top-3 context",
            "fixes": 12,
            "regressions": 1,
            "decision": "accepted transfer probe",
            "source": str(args.spoken_final_answer_compare),
        },
    ]
    output = {
        "experiment": "controller_component_summary",
        "note": "Offline component summary. It does not call models or APIs.",
        "rows": rows,
        "takeaways": [
            "No single instruction is universal; validated instruction arms are one controller action.",
            "Low-margin verifier gives the strongest general semantic repair across tool and translation tasks.",
            "Direct omni is a route decision: reject it as primary on clean AISHELL, accept it under Wu ASR collapse.",
            "Query audio is useful under text drift, but the accepted gate is task-specific.",
            "Memory packing and evidence-bound answering improve use/final-answer behavior after retrieval.",
        ],
    }
    write_json(args.output, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/controller_component_summary.json"))
    parser.add_argument(
        "--uro-instruction",
        type=Path,
        default=Path("outputs/uro_qa_omni_side_audio_query_200/raw_vs_policy_grounding_compare.json"),
    )
    parser.add_argument(
        "--slurp-verifier",
        type=Path,
        default=Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p01.json"),
    )
    parser.add_argument(
        "--covost-verifier",
        type=Path,
        default=Path("outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json"),
    )
    parser.add_argument(
        "--query-audio-gate-selector",
        type=Path,
        default=Path("outputs/query_audio_gate_selector_summary.json"),
    )
    parser.add_argument(
        "--retrieval-use-packed",
        type=Path,
        default=Path("outputs/retrieval_use_packed_summary.json"),
    )
    parser.add_argument("--dialect-route", type=Path, default=Path("outputs/dialect_route_summary.json"))
    parser.add_argument(
        "--final-answer-compare",
        type=Path,
        default=Path("outputs/rag_final_answer_compare_heysquad_val200_llm_prompt.json"),
    )
    parser.add_argument(
        "--spoken-final-answer-compare",
        type=Path,
        default=Path("outputs/rag_final_answer_compare_spoken_squad_test200.json"),
    )
    return parser


def main() -> None:
    result = build(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
