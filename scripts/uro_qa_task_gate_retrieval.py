"""Evaluate predicted task-gated retrieval on URO QA/reasoning rows."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from omni_embedding_rl.data.manifest import read_jsonl
from omni_embedding_rl.evaluation.transcript_candidates import (
    TranscriptRetrievalConfig,
    _encode_candidates,
    _encode_queries,
    _encode_with_method,
    _load_model,
    _normalize_text,
    _ranks_to_metrics,
    _resolve_device,
    _row_text,
    _require_sentence_transformer,
)
from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS


TASK_DESCRIPTIONS = {
    "GaokaoEval": "English listening-comprehension multiple-choice exam",
    "Gsm8kEval": "grade-school math reasoning question",
    "HSK5-zh": "Chinese language proficiency multiple-choice question",
    "MuChoEval-en": "music audio understanding multiple-choice question",
    "OpenbookQA-zh": "open-book science multiple-choice question",
    "SQuAD-zh": "Chinese reading-comprehension span question",
    "StoralEval": "story or fable moral understanding question",
    "TruthfulEval": "truthfulness-oriented question answering",
}


def _task_card(name: str) -> str:
    desc = TASK_DESCRIPTIONS.get(name, name)
    return f"Task: {name}\nTask type: {desc}\nSelect this task for spoken questions of this type."


def _metrics_from_rows(result_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sample_ranks = [int(row["sample_rank"]) for row in result_rows]
    text_ranks = [int(row["text_rank"]) for row in result_rows]
    return {
        "sample": _ranks_to_metrics(sample_ranks),
        "text": _ranks_to_metrics(text_ranks),
    }


def _rank_with_predicted_gate(
    rows: list[dict[str, Any]],
    query_vectors: np.ndarray,
    candidate_vectors: np.ndarray,
    gate_vectors: np.ndarray,
    gate_names: list[str],
    gate_top_k: int,
    candidate_field: str,
    query_field: str,
    score_count: int,
    normalize_cjk_spaces: bool,
) -> dict[str, Any]:
    by_task: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        by_task.setdefault(str(row.get("dataset_config", "")), []).append(index)
    normalized_texts = [
        _normalize_text(_row_text(row, candidate_field), normalize_cjk_spaces) for row in rows
    ]

    result_rows = []
    gate_correct = 0
    for index, row in enumerate(rows):
        gate_scores = gate_vectors @ query_vectors[index]
        gate_order = np.argsort(-gate_scores).tolist()
        predicted_task = gate_names[gate_order[0]]
        predicted_tasks = [gate_names[pos] for pos in gate_order[:gate_top_k]]
        gold_task = str(row.get("dataset_config", ""))
        gate_correct += int(gold_task in predicted_tasks)
        candidate_ids = [
            row_id
            for task in predicted_tasks
            for row_id in by_task.get(task, [])
        ]

        if not candidate_ids:
            sample_rank = len(rows) + 1
            text_rank = len(rows) + 1
            scores_payload = []
            top_row = {}
        else:
            scores = candidate_vectors[candidate_ids] @ query_vectors[index]
            order = np.argsort(-scores).tolist()
            top_row = rows[candidate_ids[order[0]]]
            if index in candidate_ids:
                positive_position = candidate_ids.index(index)
                sample_rank = order.index(positive_position) + 1
                target_text = normalized_texts[index]
                positive_text_positions = {
                    pos
                    for pos, row_id in enumerate(candidate_ids)
                    if normalized_texts[row_id] == target_text
                }
                text_rank = next(
                    rank
                    for rank, candidate_pos in enumerate(order, start=1)
                    if candidate_pos in positive_text_positions
                )
            else:
                sample_rank = len(candidate_ids) + 1
                text_rank = len(candidate_ids) + 1
            scores_payload = [
                {
                    "rank": rank,
                    "sample_id": rows[candidate_ids[candidate_pos]].get("sample_id", ""),
                    "dataset_config": rows[candidate_ids[candidate_pos]].get("dataset_config", ""),
                    "text": _row_text(rows[candidate_ids[candidate_pos]], candidate_field),
                    "score": float(scores[candidate_pos]),
                }
                for rank, candidate_pos in enumerate(order[:score_count], start=1)
            ]

        result_rows.append(
            {
                "sample_id": row.get("sample_id", str(index)),
                "dataset_config": gold_task,
                "predicted_task": predicted_task,
                "predicted_tasks": predicted_tasks,
                "gate_hit_at_k": gold_task in predicted_tasks,
                "query_text": _row_text(row, query_field),
                "target_text": _row_text(row, candidate_field),
                "top_sample_id": top_row.get("sample_id", ""),
                "top_dataset_config": top_row.get("dataset_config", ""),
                "top_text": _row_text(top_row, candidate_field) if top_row else "",
                "sample_rank": sample_rank,
                "text_rank": text_rank,
                "sample_hit_at_1": sample_rank == 1,
                "text_hit_at_1": text_rank == 1,
                "scores": scores_payload,
                "gate_scores": [
                    {
                        "rank": rank,
                        "task": gate_names[pos],
                        "score": float(gate_scores[pos]),
                    }
                    for rank, pos in enumerate(gate_order[:score_count], start=1)
                ],
            }
        )

    metrics = _metrics_from_rows(result_rows)
    metrics["gate"] = {
        "accuracy_at_k": gate_correct / len(rows) if rows else 0.0,
        "top_k": gate_top_k,
    }
    metrics["rows"] = result_rows
    metrics["examples"] = result_rows[:5]
    metrics["bad_cases"] = [row for row in result_rows if not row["text_hit_at_1"]][:10]
    return metrics


def run(args: argparse.Namespace) -> dict[str, Any]:
    torch, _, _ = _require_sentence_transformer()
    device = _resolve_device(torch, args.device)
    config = TranscriptRetrievalConfig(
        manifest=args.manifest,
        output=args.output_dir / "placeholder.json",
        model=args.model,
        route="direct_omni",
        instruction_arm="raw",
        device=args.device,
        trust_remote_code=not args.no_trust_remote_code,
        torch_dtype=args.torch_dtype,
        attn_implementation=args.attn_implementation,
        audio_encode_method=args.audio_encode_method,
        text_encode_method=args.text_encode_method,
        query_field=args.query_field,
        candidate_field=args.candidate_field,
        batch_size=args.batch_size,
        audio_max_length=args.audio_max_length,
        score_count=args.score_count,
        normalize_cjk_spaces=args.normalize_cjk_spaces,
    )
    rows = [row for row in read_jsonl(args.manifest) if row.get("audio_path")]
    if args.max_samples > 0:
        rows = rows[: args.max_samples]
    model = _load_model(config, device)
    task_names = sorted({str(row.get("dataset_config", "")) for row in rows})
    gate_vectors = _encode_with_method(
        model, [_task_card(name) for name in task_names], args.text_encode_method, args.batch_size
    )
    candidate_vectors = _encode_candidates(model, rows, config)

    reports = []
    leaderboard = []
    for arm in args.arm:
        if arm not in INSTRUCTION_ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        arm_config = config.__class__(**(asdict(config) | {"instruction_arm": arm}))
        query_vectors = _encode_queries(model, rows, arm_config, INSTRUCTION_ARMS[arm])
        metrics = _rank_with_predicted_gate(
            rows,
            query_vectors,
            candidate_vectors,
            gate_vectors,
            task_names,
            args.gate_top_k,
            args.candidate_field,
            args.query_field,
            args.score_count,
            args.normalize_cjk_spaces,
        )
        report = {
            "experiment": "uro_qa_task_gate_retrieval",
            "instruction_arm": arm,
            "sample_count": len(rows),
            "candidate_field": args.candidate_field,
            "task_count": len(task_names),
            "config": asdict(arm_config)
            | {
                "manifest": str(args.manifest),
                "output": str(arm_config.output),
                "output_dir": str(args.output_dir),
            },
            **metrics,
        }
        output = args.output_dir / f"predicted_gate__{args.candidate_field}__{arm}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        reports.append(report)
        leaderboard.append(
            {
                "instruction_arm": arm,
                "candidate_field": args.candidate_field,
                "sample_count": len(rows),
                "gate_top_k": report["gate"]["top_k"],
                "gate_acc": report["gate"]["accuracy_at_k"],
                "sample_acc": report["sample"]["accuracy"],
                "sample_r3": report["sample"]["recall_at_3"],
                "sample_mrr": report["sample"]["mrr"],
                "text_acc": report["text"]["accuracy"],
                "text_r3": report["text"]["recall_at_3"],
                "text_mrr": report["text"]["mrr"],
            }
        )
        print(json.dumps(leaderboard[-1], ensure_ascii=False), flush=True)

    summary = {
        "experiment": "uro_qa_task_gate_retrieval_summary",
        "device": device,
        "leaderboard": leaderboard,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (args.output_dir / "leaderboard.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(leaderboard[0]) if leaderboard else [])
        if leaderboard:
            writer.writeheader()
            writer.writerows(leaderboard)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--arm", action="append", default=["raw", "policy_grounding"])
    parser.add_argument("--candidate-field", default="target_boundary_card")
    parser.add_argument("--gate-top-k", type=int, default=1)
    parser.add_argument("--query-field", default="source_text")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--no-trust-remote-code", action="store_true")
    parser.add_argument("--torch-dtype", default="bfloat16")
    parser.add_argument("--attn-implementation", default="")
    parser.add_argument("--audio-encode-method", choices=["query", "document", "encode"], default="query")
    parser.add_argument("--text-encode-method", choices=["query", "document", "encode"], default="document")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--audio-max-length", type=int, default=2048000)
    parser.add_argument("--score-count", type=int, default=5)
    parser.add_argument("--normalize-cjk-spaces", action="store_true")
    return parser


def main() -> None:
    print(json.dumps(run(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
