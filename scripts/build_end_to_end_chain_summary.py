"""Build paper-facing retrieval -> use -> final-answer chain summaries.

This script is fully offline.  It reads existing row-level/result JSON files and
creates a compact artifact that aligns three evidence layers:

1. retrieval hit at k,
2. frozen main-model memory-use success,
3. final-answer pass under the accepted evidence protocol.

The goal is to keep the manuscript claim honest: retrieved evidence, selected
memory, and final answers are related but distinct bottlenecks.
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


def gold_in_memory_context(row: dict[str, Any]) -> bool:
    gold = str(row.get("gold_memory_id") or "")
    candidates = [str(item) for item in row.get("candidate_memory_ids", [])]
    return bool(gold) and gold in candidates


def summarize_memory_use(path: Path, *, label: str, stage: str) -> dict[str, Any]:
    data = read_json(path)
    rows = data.get("rows", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path} has no row list")
    n = len(rows)
    hits = [gold_in_memory_context(row) for row in rows]
    success = [bool(row.get("task_success")) for row in rows]
    invalid = [bool(row.get("invalid_output")) for row in rows]
    hit_but_use_fail = [hits[i] and not success[i] for i in range(n)]
    retrieval_miss = [not hits[i] for i in range(n)]
    miss_but_success = [not hits[i] and success[i] for i in range(n)]
    return {
        "label": label,
        "stage": stage,
        "source": str(path),
        "n": n,
        "retrieval_hit_at_k": sum(hits) / n,
        "memory_use_success": sum(success) / n,
        "hit_but_use_fail": sum(hit_but_use_fail) / n,
        "retrieval_miss": sum(retrieval_miss) / n,
        "miss_but_success": sum(miss_but_success) / n,
        "invalid_output": sum(invalid) / n,
        "mean_text_cost": data.get("mean_text_cost"),
        "mean_audio_cost": data.get("mean_audio_cost"),
        "mean_latency_ms": data.get("mean_latency_ms"),
    }


def summary_by_label(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("label")): item for item in data.get("summaries", [])}


def find_summary(data: dict[str, Any], contains: list[str]) -> dict[str, Any]:
    for item in data.get("summaries", []):
        label = str(item.get("label") or "")
        if all(token in label for token in contains):
            return item
    raise KeyError(f"no summary label contains all tokens: {contains}")


def summarize_final_answer(
    compare_path: Path,
    *,
    label: str,
    stage: str,
    contains: list[str],
) -> dict[str, Any]:
    data = read_json(compare_path)
    item = find_summary(data, contains)
    return {
        "label": label,
        "stage": stage,
        "source": str(compare_path),
        "report": item.get("path"),
        "n": nested(item, "metrics", "n"),
        "context_gold_rate": nested(item, "decomposition", "context_gold_rate"),
        "grounded_exact_rate": nested(item, "decomposition", "grounded_exact_rate"),
        "answer_pass": nested(item, "metrics", "answer_pass"),
        "answer_given_gold_context": nested(item, "decomposition", "answer_given_gold_context"),
        "retrieval_miss_rate": nested(item, "decomposition", "retrieval_miss_rate"),
        "generation_miss_rate": nested(item, "decomposition", "generation_miss_rate"),
        "api_error_count": nested(item, "decomposition", "api_error_count"),
        "error_type_counts": nested(item, "decomposition", "error_type_counts"),
    }


def summarize_answer_shuffle(path: Path, *, label: str) -> dict[str, Any]:
    data = read_json(path)
    summaries = data.get("summaries", [])
    if len(summaries) < 2:
        raise ValueError(f"{path} does not contain shuffle summaries")
    base = summaries[0]
    shuffles = summaries[1:]
    scores = [nested(item, "metrics", "answer_pass") for item in shuffles]
    comparisons = data.get("comparisons", [])
    deltas = [nested(item, "answer_pass", "delta") for item in comparisons]
    ci_lowers = [nested(item, "answer_pass", "ci95", default=[0.0, 0.0])[0] for item in comparisons]
    fixes = [nested(item, "answer_pass", "fixes") for item in comparisons]
    regressions = [nested(item, "answer_pass", "regressions") for item in comparisons]
    return {
        "label": label,
        "stage": "final_answer_order_control",
        "source": str(path),
        "n": nested(base, "metrics", "n"),
        "base_answer_pass": nested(base, "metrics", "answer_pass"),
        "shuffle_count": len(shuffles),
        "shuffle_answer_pass_mean": sum(scores) / len(scores),
        "shuffle_answer_pass_min": min(scores),
        "shuffle_answer_pass_max": max(scores),
        "max_abs_delta": max(abs(float(delta)) for delta in deltas),
        "worst_ci_lower": min(ci_lowers),
        "total_fixes": sum(fixes),
        "total_regressions": sum(regressions),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    heysquad_memory_raw = summarize_memory_use(
        args.heysquad_memory_raw,
        label="heysquad_top5_original_memory_use",
        stage="retrieval_to_use",
    )
    heysquad_memory_packed = summarize_memory_use(
        args.heysquad_memory_packed,
        label="heysquad_top5_packed_memory_use",
        stage="retrieval_to_packed_use",
    )
    heysquad_answer_top3 = summarize_final_answer(
        args.heysquad_answer_compare,
        label="heysquad_top3_evidence_final_answer",
        stage="retrieval_to_final_answer",
        contains=["raw_retrieval", "top3", "evidence_then_answer"],
    )
    heysquad_answer_top5 = summarize_final_answer(
        args.heysquad_answer_compare,
        label="heysquad_top5_evidence_final_answer",
        stage="retrieval_to_final_answer",
        contains=["raw_retrieval", "top5", "evidence_then_answer"],
    )
    spoken_answer_default = summarize_final_answer(
        args.spoken_answer_compare,
        label="spoken_squad_top3_default_final_answer",
        stage="transfer_final_answer",
        contains=["omni_top3_llm_default"],
    )
    spoken_answer_evidence = summarize_final_answer(
        args.spoken_answer_compare,
        label="spoken_squad_top3_evidence_final_answer",
        stage="transfer_final_answer",
        contains=["omni_top3_llm_evidence_then_answer"],
    )

    output = {
        "experiment": "end_to_end_chain_summary",
        "note": (
            "Offline alignment of retrieval hit, memory-use, and final-answer "
            "evidence. It does not call models or APIs."
        ),
        "rows": [
            heysquad_memory_raw,
            heysquad_memory_packed,
            heysquad_answer_top3,
            heysquad_answer_top5,
            spoken_answer_default,
            spoken_answer_evidence,
        ],
        "controls": [
            summarize_answer_shuffle(args.heysquad_answer_shuffle, label="heysquad_top3_evidence_order_shuffle"),
            summarize_answer_shuffle(args.spoken_answer_shuffle, label="spoken_squad_top3_evidence_order_shuffle"),
        ],
        "headline": {
            "heysquad_retrieval_hit_at_5": heysquad_memory_raw["retrieval_hit_at_k"],
            "heysquad_original_memory_use_success": heysquad_memory_raw["memory_use_success"],
            "heysquad_packed_memory_use_success": heysquad_memory_packed["memory_use_success"],
            "heysquad_top3_evidence_answer_pass": heysquad_answer_top3["answer_pass"],
            "heysquad_top5_evidence_answer_pass": heysquad_answer_top5["answer_pass"],
            "spoken_squad_default_answer_pass": spoken_answer_default["answer_pass"],
            "spoken_squad_evidence_answer_pass": spoken_answer_evidence["answer_pass"],
        },
    }
    write_json(args.output, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/end_to_end_chain_summary.json"))
    parser.add_argument(
        "--heysquad-memory-raw",
        type=Path,
        default=Path("outputs/omni_memory_v0/heysquad_retrieval_raw_top5_use_gemma4e4b_server_200.json"),
    )
    parser.add_argument(
        "--heysquad-memory-packed",
        type=Path,
        default=Path("outputs/omni_memory_v0/heysquad_retrieval_raw_top5_packed_use_gemma4e4b_server_200.json"),
    )
    parser.add_argument(
        "--heysquad-answer-compare",
        type=Path,
        default=Path("outputs/rag_final_answer_compare_heysquad_val200_evidence_policy_context.json"),
    )
    parser.add_argument(
        "--heysquad-answer-shuffle",
        type=Path,
        default=Path("outputs/rag_final_answer_order_shuffle_heysquad_val200_evidence.json"),
    )
    parser.add_argument(
        "--spoken-answer-compare",
        type=Path,
        default=Path("outputs/rag_final_answer_compare_spoken_squad_test200.json"),
    )
    parser.add_argument(
        "--spoken-answer-shuffle",
        type=Path,
        default=Path("outputs/rag_final_answer_order_shuffle_spoken_squad_test200_evidence.json"),
    )
    return parser


def main() -> None:
    result = build(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
