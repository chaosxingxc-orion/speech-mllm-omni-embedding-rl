"""Build a paper-facing experiment coverage summary.

The project now has many audited result artifacts.  This script reads the
offline evidence verifier output and converts it into a compact coverage map:

- which evidence blocks are ready for a manuscript;
- which blocks are partial or blocker evidence;
- which directions are intentionally out of scope for the current frozen,
  semantic, training-free round.

It does not call any model or API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BLOCKS = [
    {
        "block": "omni_instruction",
        "status": "ready",
        "role": "main_method_component",
        "required_checks": [
            "uro_policy_grounding_full200",
            "uro_exact_condition_full200",
        ],
        "summary": "Task instructions help as validated arms, especially on URO, but are not universal.",
        "next_action": "Use as one controller action class; do not headline as universal prompt optimization.",
    },
    {
        "block": "low_margin_verifier",
        "status": "ready",
        "role": "main_method_component",
        "required_checks": [
            "slurp_low_margin_llm_top3_tau0p02",
            "minds_low_margin_llm_180",
            "covost_ar_low_margin_llm_test_full",
        ],
        "summary": "Low-margin top-k verification is the strongest general controller across tool and translation tasks.",
        "next_action": "Report route rate, fixes/regressions, and cost curve next to accuracy.",
    },
    {
        "block": "tool_final_utility",
        "status": "ready",
        "role": "final_task_evidence",
        "required_checks": [
            "slurp_tool_call_utility_multiseed",
            "minds_tool_call_raw_fallback_multiseed",
            "minds_retrieval_top5_tool_memory_use",
            "slurp_retrieval_top5_tool_memory_use",
        ],
        "summary": "Tool/intent retrieval improvements transfer to deterministic tool-call utility, with MInDS falling back to raw.",
        "next_action": "Use as final-task evidence for semantic tool use; slot filling remains future work.",
    },
    {
        "block": "qa_rag_final_answer",
        "status": "ready",
        "role": "final_task_evidence",
        "required_checks": [
            "heysquad_evidence_then_answer_top3",
            "spoken_squad_200_evidence_then_answer_transfer",
            "heysquad_spoken_squad_end_to_end_chain_summary",
        ],
        "summary": "Evidence-bound memory-use improves final-answer quality on HeySQuAD and Spoken-SQuAD.",
        "next_action": "Use HeySQuAD/Spoken-SQuAD as public QA/RAG evidence; larger splits are optional strengthening.",
    },
    {
        "block": "uro_multi_family_stress",
        "status": "ready",
        "role": "robustness_evidence",
        "required_checks": [
            "uro_final_task_low_margin_llm_boundary",
            "uro_final_task_family_breakdown",
        ],
        "summary": "URO verifier gains are not a single-family artifact: 7/8 families improve and none regress.",
        "next_action": "Use as multi-family semantic stress support under the URO final-task row.",
    },
    {
        "block": "query_audio_gate",
        "status": "ready_with_caveat",
        "role": "memory_interface_component",
        "required_checks": [
            "query_audio_gate_selector_covost_budgeted",
            "query_audio_gate_selector_minds_budgeted",
            "query_audio_gate_selector_heysquad_budgeted",
            "aishell_wu_dialect_route_summary",
        ],
        "summary": "Query audio helps under text drift and dialect ASR collapse; candidate audio should not be used by default.",
        "next_action": "Present as selective query-audio gating, not all-audio memory stuffing.",
    },
    {
        "block": "memory_packing_and_cost",
        "status": "ready",
        "role": "memory_use_component",
        "required_checks": [
            "heysquad_raw_top5_packed_memory_use_gain",
            "heysquad_raw_top5_answer_evidence_packing_budget",
            "controller_cost_budget_summary",
            "runtime_latency_summary",
        ],
        "summary": "Memory packing improves HeySQuAD use quality while reducing prompt budget and latency.",
        "next_action": "Use in the memory-use and cost tables.",
    },
    {
        "block": "translation_memory_use_order",
        "status": "ready",
        "role": "limitation_and_repair",
        "required_checks": [
            "covost2_ar_translation_target_text_memory_use_gain",
            "covost2_zh_translation_target_text_memory_use_gain",
            "covost2_ar_translation_policy_shuffle_control",
            "covost2_zh_translation_policy_shuffle_control",
            "translation_order_gate_repair_summary",
            "translation_multivote_gate_repair_summary",
        ],
        "summary": "Translation memory-use can improve; a cheap rank/deviation gate gives weak repair and a four-order multivote/rank gate gives strict no-regression repair.",
        "next_action": "Report the cheap gate as the lower-cost option and the multivote gate as the strict but expensive stability repair.",
    },
    {
        "block": "cross_model_backend",
        "status": "blocker_documented",
        "role": "negative_control",
        "required_checks": [
            "cross_model_backend_readiness_summary",
        ],
        "summary": "Jina supports safe raw fallback, but no positive instruction transfer; Qwen3/Gemma12B remain blockers, and Voxtral is runnable but not yet paper-ready as a second backend.",
        "next_action": "Keep Gemma 4 E4B as the only audited main backend until a stronger second backend is available.",
    },
    {
        "block": "nonsemantic_speaker_emotion",
        "status": "out_of_scope",
        "role": "scope_boundary",
        "required_checks": [],
        "summary": "Speaker and emotion are outside the current semantic speech scope.",
        "next_action": "Exclude from the manuscript claim rather than treating as missing experiments.",
    },
    {
        "block": "weight_training_lora_rl",
        "status": "deferred",
        "role": "future_upper_bound",
        "required_checks": [],
        "summary": "The current paper round is frozen/training-free; LoRA/RL weight updates are future upper-bound work.",
        "next_action": "Mention only as future adaptation, not as evidence for the current claim.",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    verifier = read_json(args.verifier)
    all_verifier_rows = list(verifier.get("rows", []))
    verifier_rows = [
        row for row in all_verifier_rows
        if row.get("name") != "experiment_coverage_summary"
    ]
    rows = {row["name"]: row for row in verifier_rows}
    block_rows: list[dict[str, Any]] = []
    for block in BLOCKS:
        required = list(block["required_checks"])
        missing = [name for name in required if name not in rows]
        failing = [name for name in required if name in rows and rows[name].get("status") != "pass"]
        if not required:
            coverage = "not_applicable"
        elif missing:
            coverage = "missing"
        elif failing:
            coverage = "failing"
        else:
            coverage = "verified"
        block_rows.append(
            {
                **block,
                "required_count": len(required),
                "verified_count": len(required) - len(missing) - len(failing),
                "missing_checks": missing,
                "failing_checks": failing,
                "coverage": coverage,
            }
        )

    ready_statuses = {"ready", "ready_with_caveat"}
    summary = {
        "block_count": len(block_rows),
        "verified_block_count": sum(row["coverage"] == "verified" for row in block_rows),
        "ready_block_count": sum(row["status"] in ready_statuses for row in block_rows),
        "partial_block_count": sum(row["status"] == "partial" for row in block_rows),
        "blocker_count": sum(row["status"] == "blocker_documented" for row in block_rows),
        "out_of_scope_count": sum(row["status"] == "out_of_scope" for row in block_rows),
        "deferred_count": sum(row["status"] == "deferred" for row in block_rows),
        "paper_verifier_check_count": len(all_verifier_rows),
        "paper_verifier_pass_count": sum(row.get("status") == "pass" for row in all_verifier_rows),
        "paper_verifier_mismatch_count": sum(row.get("status") == "mismatch" for row in all_verifier_rows),
        "paper_verifier_missing_source_count": sum(row.get("status") == "missing_source" for row in all_verifier_rows),
        "coverage_guardrail_check_count": len(verifier_rows),
        "coverage_guardrail_pass_count": sum(row.get("status") == "pass" for row in verifier_rows),
        "coverage_guardrail_mismatch_count": sum(row.get("status") == "mismatch" for row in verifier_rows),
        "coverage_guardrail_missing_source_count": sum(row.get("status") == "missing_source" for row in verifier_rows),
        # Backward-compatible aliases used by the verifier.  They intentionally
        # exclude the coverage self-check to avoid recursive accounting.
        "verifier_check_count": len(verifier_rows),
        "verifier_pass_count": sum(row.get("status") == "pass" for row in verifier_rows),
        "verifier_mismatch_count": sum(row.get("status") == "mismatch" for row in verifier_rows),
        "verifier_missing_source_count": sum(row.get("status") == "missing_source" for row in verifier_rows),
    }
    return {
        "experiment": "experiment_coverage_summary",
        "verifier": str(args.verifier),
        "summary": summary,
        "blocks": block_rows,
        "paper_decision": (
            "core_evidence_ready"
            if summary["paper_verifier_check_count"] == summary["paper_verifier_pass_count"]
            and summary["paper_verifier_missing_source_count"] == 0
            and summary["paper_verifier_mismatch_count"] == 0
            else "evidence_audit_not_clean"
        ),
        "next_priority": [
            "Draft the manuscript from the ready evidence blocks.",
            "If adding new experiments, prioritize a stable second generative backend.",
            "Report translation stability as a cost tradeoff: cheap weak repair and four-order strict repair.",
        ],
    }


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Experiment Coverage Summary",
        "",
        "Last updated: 2026-07-03",
        "",
        "This document summarizes which experiment blocks are ready for the",
        "current frozen/training-free semantic omni-agentic-memory paper and",
        "which blocks are partial, blocked, out of scope, or deferred.",
        "",
        "Generated by:",
        "",
        "```text",
        "python scripts/build_experiment_coverage_summary.py",
        "```",
        "",
        "## Audit Summary",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Paper evidence verifier checks | {summary['summary']['paper_verifier_pass_count']} / {summary['summary']['paper_verifier_check_count']} |",
        f"| Coverage guardrail checks | {summary['summary']['coverage_guardrail_pass_count']} / {summary['summary']['coverage_guardrail_check_count']} |",
        f"| Verified experiment blocks | {summary['summary']['verified_block_count']} / {summary['summary']['block_count']} |",
        f"| Ready blocks | {summary['summary']['ready_block_count']} |",
        f"| Partial blocks | {summary['summary']['partial_block_count']} |",
        f"| Backend blockers | {summary['summary']['blocker_count']} |",
        f"| Out-of-scope blocks | {summary['summary']['out_of_scope_count']} |",
        f"| Deferred blocks | {summary['summary']['deferred_count']} |",
        f"| Paper decision | {summary['paper_decision']} |",
        "",
        "## Coverage Table",
        "",
        "| Block | Status | Role | Coverage | Required Checks | Summary | Next Action |",
        "|---|---|---|---|---:|---|---|",
    ]
    for row in summary["blocks"]:
        lines.append(
            "| {block} | {status} | {role} | {coverage} | {count} | {summary} | {next_action} |".format(
                block=row["block"],
                status=row["status"],
                role=row["role"],
                coverage=row["coverage"],
                count=row["required_count"],
                summary=row["summary"],
                next_action=row["next_action"],
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The main experiment blocks are ready enough for manuscript drafting.",
            "- The incomplete items are not hidden missing main experiments: they are",
            "  either documented blockers, explicit limitations, out-of-scope",
            "  non-semantic tasks, or deferred weight-training upper bounds.",
            "- New experiments should now be targeted strengthening runs rather than",
            "  broad evidence collection.",
            "",
            "## Next Priority",
            "",
        ]
    )
    for item in summary["next_priority"]:
        lines.append(f"- {item}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", type=Path, default=Path("outputs/paper_evidence_verification.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/experiment_coverage_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/experiment_coverage_summary.md"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = build_summary(args)
    write_json(args.output, summary)
    write_markdown(args.markdown, summary)
    print(json.dumps({"output": str(args.output), "markdown": str(args.markdown), **summary["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
