"""Run cache-first URO-Bench semantic-family instruction retrieval.

This is a thin experiment runner for URO-Bench mini/full manifests.  It keeps
the frozen omni model loaded once, caches text candidate embeddings per task
family, then evaluates multiple audio-side instruction arms.
"""

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
    _load_model,
    _normalize_text,
    _ranks_to_metrics,
    _resolve_device,
    _row_text,
    _require_sentence_transformer,
)
from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS


DEFAULT_ARMS_BY_FAMILY: dict[str, list[str]] = {
    "speech_qa_reasoning": [
        "raw",
        "semantic_qa",
        "policy_grounding",
        "exact_condition_matching",
        "negation_exception_sensitive",
        "dialect_robust_semantic",
    ],
    "speech_translation": [
        "raw",
        "translation_semantic",
        "semantic_qa",
        "transcript_like",
        "dialect_robust_semantic",
    ],
    "tool_or_label_semantics": [
        "raw",
        "tool_specific_intent",
        "exact_condition_matching",
        "negation_exception_sensitive",
        "semantic_qa",
    ],
    "asr_semantics": [
        "raw",
        "transcript_like",
        "semantic_qa",
        "exact_condition_matching",
        "dialect_robust_semantic",
    ],
    "speech_summarization": [
        "raw",
        "semantic_qa",
        "policy_grounding",
        "transcript_like",
        "exact_condition_matching",
    ],
}


def _limit_rows(rows: list[dict[str, Any]], max_samples: int) -> list[dict[str, Any]]:
    if max_samples > 0:
        return rows[:max_samples]
    return rows


def _family_name(path: Path) -> str:
    if path.stem == "manifest" and path.parent.name:
        return path.parent.name
    return path.stem


def _rank_rows(
    rows: list[dict[str, Any]],
    query_vectors: np.ndarray,
    candidate_vectors: np.ndarray,
    query_field: str,
    candidate_field: str,
    score_count: int,
    normalize_cjk_spaces: bool,
) -> dict[str, Any]:
    normalized_texts = [
        _normalize_text(_row_text(row, candidate_field), normalize_cjk_spaces) for row in rows
    ]
    sample_ranks: list[int] = []
    text_ranks: list[int] = []
    result_rows: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    bad_cases: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        scores = candidate_vectors @ query_vectors[index]
        order = np.argsort(-scores).tolist()
        sample_rank = order.index(index) + 1
        target_text = normalized_texts[index]
        positive_text_positions = {
            pos for pos, text in enumerate(normalized_texts) if text == target_text
        }
        text_rank = next(
            rank for rank, candidate_pos in enumerate(order, start=1)
            if candidate_pos in positive_text_positions
        )
        sample_ranks.append(sample_rank)
        text_ranks.append(text_rank)
        top_row = rows[order[0]]
        output_row = {
            "sample_id": row.get("sample_id", str(index)),
            "dataset_config": row.get("dataset_config", ""),
            "query_text": _row_text(row, query_field),
            "target_text": _row_text(row, candidate_field),
            "top_sample_id": top_row.get("sample_id", ""),
            "top_dataset_config": top_row.get("dataset_config", ""),
            "top_text": _row_text(top_row, candidate_field),
            "sample_rank": sample_rank,
            "text_rank": text_rank,
            "sample_hit_at_1": sample_rank == 1,
            "text_hit_at_1": text_rank == 1,
            "scores": [
                {
                    "rank": rank,
                    "sample_id": rows[candidate_pos].get("sample_id", ""),
                    "dataset_config": rows[candidate_pos].get("dataset_config", ""),
                    "text": _row_text(rows[candidate_pos], candidate_field),
                    "score": float(scores[candidate_pos]),
                }
                for rank, candidate_pos in enumerate(order[:score_count], start=1)
            ],
        }
        result_rows.append(output_row)
        if len(examples) < 5:
            examples.append(output_row)
        if text_rank > 1 and len(bad_cases) < 10:
            bad_cases.append(output_row)

    return {
        "sample": _ranks_to_metrics(sample_ranks),
        "text": _ranks_to_metrics(text_ranks),
        "examples": examples,
        "bad_cases": bad_cases,
        "rows": result_rows,
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _csv_row(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": report["family"],
        "instruction_arm": report["instruction_arm"],
        "sample_count": report["sample_count"],
        "candidate_count": report["candidate_count"],
        "sample_acc": report["sample"]["accuracy"],
        "sample_r3": report["sample"]["recall_at_3"],
        "sample_mrr": report["sample"]["mrr"],
        "text_acc": report["text"]["accuracy"],
        "text_r3": report["text"]["recall_at_3"],
        "text_mrr": report["text"]["mrr"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    torch, _, _ = _require_sentence_transformer()
    device = _resolve_device(torch, args.device)
    base_config = TranscriptRetrievalConfig(
        manifest=Path(""),
        output=Path(""),
        model=args.model,
        route=args.route,
        instruction_arm="raw",
        candidate_count=2,
        max_samples=args.max_samples,
        seed=args.seed,
        device=args.device,
        trust_remote_code=not args.no_trust_remote_code,
        torch_dtype=args.torch_dtype,
        attn_implementation=args.attn_implementation,
        model_modality=args.model_modality,
        audio_encode_method=args.audio_encode_method,
        text_encode_method=args.text_encode_method,
        query_field=args.query_field,
        candidate_field=args.candidate_field,
        audio_payload_mode=args.audio_payload_mode,
        batch_size=args.batch_size,
        audio_max_length=args.audio_max_length,
        score_count=args.score_count,
        normalize_cjk_spaces=args.normalize_cjk_spaces,
    )
    model = _load_model(base_config, device)

    reports: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    for family_manifest in args.manifest:
        family = _family_name(family_manifest)
        rows = [
            row
            for row in _limit_rows(read_jsonl(family_manifest), args.max_samples)
            if row.get(args.candidate_field) and row.get("audio_path")
        ]
        if not rows:
            continue
        family_config = base_config.__class__(
            **(
                asdict(base_config)
                | {
                    "manifest": family_manifest,
                    "output": args.output_dir / f"{family}__raw.json",
                    "candidate_count": len(rows),
                    "max_samples": args.max_samples,
                }
            )
        )
        candidate_vectors = _encode_candidates(model, rows, family_config)
        arms = args.arm or DEFAULT_ARMS_BY_FAMILY.get(family, ["raw"])
        for arm in arms:
            if arm not in INSTRUCTION_ARMS:
                raise ValueError(f"unknown arm {arm!r}")
            arm_config = family_config.__class__(
                **(
                    asdict(family_config)
                    | {
                        "instruction_arm": arm,
                        "output": args.output_dir / f"{family}__{arm}.json",
                    }
                )
            )
            query_vectors = _encode_queries(model, rows, arm_config, INSTRUCTION_ARMS[arm])
            metrics = _rank_rows(
                rows,
                query_vectors,
                candidate_vectors,
                args.query_field,
                args.candidate_field,
                args.score_count,
                args.normalize_cjk_spaces,
            )
            report = {
                "experiment": "uro_bench_taxonomy_retrieval",
                "family": family,
                "instruction_arm": arm,
                "sample_count": len(rows),
                "candidate_count": len(rows),
                "config": asdict(arm_config)
                | {
                    "manifest": str(family_manifest),
                    "output": str(arm_config.output),
                },
                **metrics,
            }
            _write_json(arm_config.output, report)
            reports.append(report)
            csv_rows.append(_csv_row(report))
            print(
                json.dumps(
                    {
                        "family": family,
                        "arm": arm,
                        "sample_count": len(rows),
                        "text": report["text"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    summary = {
        "experiment": "uro_bench_taxonomy_retrieval_summary",
        "device": device,
        "model": args.model,
        "result_count": len(reports),
        "leaderboard": csv_rows,
    }
    _write_json(args.output_dir / "summary.json", summary)
    with (args.output_dir / "leaderboard.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]) if csv_rows else [])
        if csv_rows:
            writer.writeheader()
            writer.writerows(csv_rows)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", nargs="+", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--route", choices=["direct_omni", "oracle_text"], default="direct_omni")
    parser.add_argument("--arm", action="append")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--no-trust-remote-code", action="store_true")
    parser.add_argument("--torch-dtype", default="bfloat16")
    parser.add_argument("--attn-implementation", default="")
    parser.add_argument("--model-modality", default="")
    parser.add_argument("--audio-encode-method", choices=["query", "document", "encode"], default="query")
    parser.add_argument("--text-encode-method", choices=["query", "document", "encode"], default="document")
    parser.add_argument("--query-field", default="source_text")
    parser.add_argument("--candidate-field", default="target_text")
    parser.add_argument("--audio-payload-mode", choices=["dict", "path", "tuple"], default="dict")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--audio-max-length", type=int, default=2048000)
    parser.add_argument("--score-count", type=int, default=5)
    parser.add_argument("--normalize-cjk-spaces", action="store_true")
    return parser


def main() -> None:
    print(json.dumps(run(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
