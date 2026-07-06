"""Build a compact cost and failure-mode summary from aggregate reports."""

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


def find_policy(report: dict[str, Any], prefix: str) -> dict[str, Any]:
    for item in report.get("summaries", []):
        if str(item.get("policy", "")).startswith(prefix):
            return item
    raise ValueError(f"policy not found: {prefix}")


def find_label(report: dict[str, Any], label: str) -> dict[str, Any]:
    for item in report.get("summaries", []):
        if str(item.get("label")) == label:
            return item
    raise ValueError(f"label not found: {label}")


def low_margin_row(name: str, path: Path, llm_prefix: str) -> dict[str, Any]:
    report = read_json(path)
    raw = find_policy(report, "raw")
    always = find_policy(report, "oracle_always")
    llm = find_policy(report, llm_prefix)
    return {
        "task": name,
        "policy_type": "low_margin_verifier",
        "raw_acc": raw["metrics"]["accuracy_at_1"],
        "policy_acc": llm["metrics"]["accuracy_at_1"],
        "delta": llm["delta"]["accuracy_at_1"],
        "ci95": llm["delta"].get("ci95"),
        "route_rate": llm.get("route_rate"),
        "api_call_rate_proxy": llm.get("route_rate"),
        "fixes": llm.get("fix_count"),
        "regressions": llm.get("regression_count"),
        "oracle_always_topk_acc": always["metrics"]["accuracy_at_1"],
        "topk_headroom": always["delta"]["accuracy_at_1"],
        "failure_mode_after_policy": "remaining errors are top-k misses or verifier misses",
    }


def rag_row(report: dict[str, Any], label: str) -> dict[str, Any]:
    item = find_label(report, label)
    dec = item["decomposition"]
    return {
        "task": f"HeySQuAD {label}",
        "policy_type": "retrieval_to_answer",
        "answer_pass": dec.get("answer_pass"),
        "context_gold_rate": dec.get("context_gold_rate"),
        "retrieval_miss_rate": dec.get("retrieval_miss_rate"),
        "generation_miss_rate": dec.get("generation_miss_rate"),
        "answer_given_gold_context": dec.get("answer_given_gold_context"),
        "api_error_count": dec.get("api_error_count"),
        "failure_mode_after_policy": "generation miss remains after context is available",
    }


def stress_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for task in report.get("tasks", []):
        dataset = task["dataset"]
        conditions = {item["condition"]: item for item in task.get("conditions", [])}
        for condition in ("text_only", "audio_only", "audio_text"):
            item = conditions.get(condition)
            if not item:
                continue
            rows.append(
                {
                    "task": f"{dataset} {condition}",
                    "policy_type": "query_audio_rescue",
                    "task_success": item.get("task_success"),
                    "wrong_memory": item.get("wrong_memory"),
                    "invalid_output": item.get("invalid_output"),
                    "mean_audio_cost": item.get("mean_audio_cost"),
                    "mean_latency_ms": item.get("mean_latency_ms"),
                    "failure_mode_after_policy": (
                        "corrupted text dominates if fused blindly"
                        if condition == "audio_text"
                        else "wrong memory"
                    ),
                }
            )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    low_margin = [
        low_margin_row(
            "MInDS intent",
            args.minds_ablation,
            "llm:minds_llm_top3_tau0p02",
        ),
        low_margin_row(
            "CoVoST2 ar->en",
            args.covost_ar_ablation,
            "llm:covost_ar_llm_top3_tau0p02",
        ),
        low_margin_row(
            "CoVoST2 zh-CN->en",
            args.covost_zh_ablation,
            "llm:covost_zh_llm_top3_tau0p0206",
        ),
    ]
    rag = read_json(args.rag_compare)
    rag_rows = [
        rag_row(rag, "asr_top3_prompt"),
        rag_row(rag, "omni_top3_prompt"),
        rag_row(rag, "rrf_top5_prompt"),
    ]
    stress = stress_rows(read_json(args.stress_summary))
    result = {
        "experiment": "cost_failure_summary",
        "low_margin": low_margin,
        "rag_final_answer": rag_rows,
        "query_audio_stress": stress,
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minds-ablation", type=Path, required=True)
    parser.add_argument("--covost-ar-ablation", type=Path, required=True)
    parser.add_argument("--covost-zh-ablation", type=Path, required=True)
    parser.add_argument("--rag-compare", type=Path, required=True)
    parser.add_argument("--stress-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
