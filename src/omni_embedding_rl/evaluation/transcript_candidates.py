"""Frozen transcript-candidate retrieval for semantic speech manifests.

The task is intentionally narrow:

    spoken query or oracle transcript -> candidate transcript texts

The positive candidate is the row's own transcript. Negatives are sampled from
the same manifest. This gives a compact ASR-semantic diagnostic for datasets
such as FLEURS without training or modifying model weights.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from omni_embedding_rl.data.manifest import read_jsonl
from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS


@dataclass(frozen=True)
class TranscriptRetrievalConfig:
    manifest: Path
    output: Path
    model: str
    route: str = "direct_omni"
    instruction_arm: str = "raw"
    candidate_count: int = 8
    max_samples: int = 0
    seed: int = 42
    device: str = "auto"
    trust_remote_code: bool = True
    torch_dtype: str = "bfloat16"
    attn_implementation: str = ""
    audio_encode_method: str = "query"
    text_encode_method: str = "document"
    text_as_document_dict: bool = False
    query_field: str = "transcript"
    candidate_field: str = "transcript"
    include_query_text_with_audio: bool = False
    batch_size: int = 16
    audio_max_length: int = 2048000
    score_count: int = 5
    bad_case_count: int = 10
    normalize_cjk_spaces: bool = False


def _normalize_text(text: str, normalize_cjk_spaces: bool) -> str:
    text = str(text or "").strip().lower()
    if normalize_cjk_spaces:
        text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _row_text(row: dict[str, Any], preferred: str = "transcript") -> str:
    for key in (preferred, "transcript", "text", "question", "answer", "sentence", "raw_transcription"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _limit_rows(rows: list[dict[str, Any]], max_samples: int) -> list[dict[str, Any]]:
    if max_samples and max_samples > 0:
        return rows[:max_samples]
    return rows


def _candidate_indices(index: int, total: int, candidate_count: int, rng: random.Random) -> list[int]:
    if total <= 0:
        return []
    negatives = [i for i in range(total) if i != index]
    rng.shuffle(negatives)
    selected = [index] + negatives[: max(0, candidate_count - 1)]
    rng.shuffle(selected)
    return selected


def _ranks_to_metrics(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"accuracy": 0.0, "recall_at_3": 0.0, "mrr": 0.0, "mean_rank": 0.0}
    count = len(ranks)
    return {
        "accuracy": sum(1 for rank in ranks if rank == 1) / count,
        "recall_at_3": sum(1 for rank in ranks if rank <= 3) / count,
        "mrr": sum(1 / rank for rank in ranks) / count,
        "mean_rank": sum(ranks) / count,
    }


def _require_sentence_transformer():
    try:
        import torch
        import torch.nn.functional as F
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - depends on experiment env
        raise SystemExit(
            "This evaluator requires torch and sentence-transformers in the "
            "experiment environment."
        ) from exc
    return torch, F, SentenceTransformer


def _resolve_device(torch: Any, requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return requested


def _load_model(config: TranscriptRetrievalConfig, device: str):
    torch, _, SentenceTransformer = _require_sentence_transformer()
    model_kwargs: dict[str, Any] = {}
    if config.attn_implementation:
        model_kwargs["attn_implementation"] = config.attn_implementation
    if config.torch_dtype:
        model_kwargs["torch_dtype"] = getattr(torch, config.torch_dtype)
    model = SentenceTransformer(
        config.model,
        device=device,
        trust_remote_code=config.trust_remote_code,
        model_kwargs=model_kwargs or None,
    )
    if hasattr(model[0], "processing_kwargs"):
        model[0].processing_kwargs.update({"audio": {"max_length": config.audio_max_length}})
    return model


def _to_normalized_numpy(embeddings: Any) -> np.ndarray:
    array = np.asarray(embeddings, dtype=np.float32)
    if array.ndim == 1:
        array = array[None, :]
    norm = np.linalg.norm(array, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return array / norm


def _encode_with_method(model: Any, items: list[Any], method: str, batch_size: int) -> np.ndarray:
    if method == "query":
        embeddings = model.encode_query(items, batch_size=batch_size, show_progress_bar=False)
    elif method == "document":
        embeddings = model.encode_document(items, batch_size=batch_size, show_progress_bar=False)
    else:
        embeddings = model.encode(items, batch_size=batch_size, show_progress_bar=False)
    return _to_normalized_numpy(embeddings)


def _instruction(config: TranscriptRetrievalConfig) -> str:
    if config.instruction_arm not in INSTRUCTION_ARMS:
        raise ValueError(
            f"unknown instruction arm {config.instruction_arm!r}; "
            f"known={sorted(INSTRUCTION_ARMS)}"
        )
    return INSTRUCTION_ARMS[config.instruction_arm]


def _audio_payload(
    row: dict[str, Any],
    instruction: str,
    query_field: str,
    include_query_text: bool,
) -> dict[str, str]:
    payload = {"audio": str(row["audio_path"])}
    text_parts = []
    if instruction:
        text_parts.append(instruction)
    if include_query_text:
        query_text = _row_text(row, query_field)
        if query_text:
            text_parts.append(f"Question or query: {query_text}")
    if text_parts:
        payload["text"] = "\n".join(text_parts)
    return payload


def _text_payload(text: str, instruction: str) -> str:
    if instruction:
        return f"{instruction}\n{text}"
    return text


def _encode_queries(
    model: Any,
    rows: list[dict[str, Any]],
    config: TranscriptRetrievalConfig,
    instruction: str,
) -> np.ndarray:
    if config.route == "direct_omni":
        vectors = []
        for row in rows:
            payload = [
                _audio_payload(
                    row,
                    instruction,
                    config.query_field,
                    config.include_query_text_with_audio,
                )
            ]
            vectors.append(
                _encode_with_method(model, payload, config.audio_encode_method, batch_size=1)[0]
            )
        return np.stack(vectors)
    if config.route == "oracle_text":
        texts = [_text_payload(_row_text(row, config.query_field), instruction) for row in rows]
        return _encode_with_method(model, texts, "query", config.batch_size)
    raise ValueError("route must be one of: direct_omni, oracle_text")


def _encode_candidates(
    model: Any,
    rows: list[dict[str, Any]],
    config: TranscriptRetrievalConfig,
) -> np.ndarray:
    texts: list[Any]
    if config.text_as_document_dict:
        texts = [{"text": _row_text(row, config.candidate_field)} for row in rows]
    else:
        texts = [_row_text(row, config.candidate_field) for row in rows]
    return _encode_with_method(model, texts, config.text_encode_method, config.batch_size)


def run_transcript_retrieval(config: TranscriptRetrievalConfig) -> dict[str, Any]:
    torch, _, _ = _require_sentence_transformer()
    device = _resolve_device(torch, config.device)
    rng = random.Random(config.seed)
    rows = _limit_rows(read_jsonl(config.manifest), config.max_samples)
    if not rows:
        raise ValueError(f"manifest has no rows: {config.manifest}")
    if config.candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")

    instruction = _instruction(config)
    model = _load_model(config, device)
    query_vectors = _encode_queries(model, rows, config, instruction)
    candidate_vectors = _encode_candidates(model, rows, config)

    sample_ranks: list[int] = []
    text_ranks: list[int] = []
    candidate_sizes: list[int] = []
    bad_cases: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    normalized_texts = [
        _normalize_text(_row_text(row, config.candidate_field), config.normalize_cjk_spaces)
        for row in rows
    ]

    for index, row in enumerate(rows):
        candidate_ids = _candidate_indices(index, len(rows), config.candidate_count, rng)
        candidate_sizes.append(len(candidate_ids))
        candidate_matrix = candidate_vectors[candidate_ids]
        scores = candidate_matrix @ query_vectors[index]
        order = np.argsort(-scores).tolist()
        positive_position = candidate_ids.index(index)
        sample_rank = order.index(positive_position) + 1
        target_text = normalized_texts[index]
        positive_text_positions = {
            pos for pos, row_id in enumerate(candidate_ids) if normalized_texts[row_id] == target_text
        }
        text_rank = next(
            rank for rank, candidate_pos in enumerate(order, start=1)
            if candidate_pos in positive_text_positions
        )
        sample_ranks.append(sample_rank)
        text_ranks.append(text_rank)
        top_row = rows[candidate_ids[order[0]]]
        output_row = {
            "sample_id": row.get("sample_id", str(index)),
            "query_text": _row_text(row, config.query_field),
            "target_text": _row_text(row, config.candidate_field),
            "top_sample_id": top_row.get("sample_id", ""),
            "top_text": _row_text(top_row, config.candidate_field),
            "sample_rank": sample_rank,
            "text_rank": text_rank,
            "sample_hit_at_1": sample_rank == 1,
            "text_hit_at_1": text_rank == 1,
            "scores": [
                {
                    "rank": rank,
                    "sample_id": rows[candidate_ids[candidate_pos]].get("sample_id", ""),
                    "text": _row_text(rows[candidate_ids[candidate_pos]], config.candidate_field),
                    "score": float(scores[candidate_pos]),
                }
                for rank, candidate_pos in enumerate(order[: config.score_count], start=1)
            ],
        }
        result_rows.append(output_row)
        if len(examples) < 5:
            examples.append(output_row)
        if text_rank > 1 and len(bad_cases) < config.bad_case_count:
            bad_cases.append(output_row)

    report = {
        "experiment": "transcript_candidate_retrieval",
        "config": asdict(config) | {
            "manifest": str(config.manifest),
            "output": str(config.output),
        },
        "device": device,
        "sample_count": len(rows),
        "candidate_count_mean": sum(candidate_sizes) / len(candidate_sizes),
        "sample": _ranks_to_metrics(sample_ranks),
        "text": _ranks_to_metrics(text_ranks),
        "examples": examples,
        "bad_cases": bad_cases,
        "rows": result_rows,
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--route", choices=["direct_omni", "oracle_text"], default="direct_omni")
    parser.add_argument("--instruction-arm", default="raw")
    parser.add_argument("--candidate-count", type=int, default=8)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--no-trust-remote-code", action="store_true")
    parser.add_argument("--torch-dtype", default="bfloat16")
    parser.add_argument("--attn-implementation", default="")
    parser.add_argument("--audio-encode-method", choices=["query", "document", "encode"], default="query")
    parser.add_argument("--text-encode-method", choices=["query", "document", "encode"], default="document")
    parser.add_argument("--text-as-document-dict", action="store_true")
    parser.add_argument("--query-field", default="transcript")
    parser.add_argument("--candidate-field", default="transcript")
    parser.add_argument("--include-query-text-with-audio", action="store_true")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--audio-max-length", type=int, default=2048000)
    parser.add_argument("--score-count", type=int, default=5)
    parser.add_argument("--bad-case-count", type=int, default=10)
    parser.add_argument("--normalize-cjk-spaces", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> TranscriptRetrievalConfig:
    return TranscriptRetrievalConfig(
        manifest=args.manifest,
        output=args.output,
        model=args.model,
        route=args.route,
        instruction_arm=args.instruction_arm,
        candidate_count=args.candidate_count,
        max_samples=args.max_samples,
        seed=args.seed,
        device=args.device,
        trust_remote_code=not args.no_trust_remote_code,
        torch_dtype=args.torch_dtype,
        attn_implementation=args.attn_implementation,
        audio_encode_method=args.audio_encode_method,
        text_encode_method=args.text_encode_method,
        text_as_document_dict=args.text_as_document_dict,
        query_field=args.query_field,
        candidate_field=args.candidate_field,
        include_query_text_with_audio=args.include_query_text_with_audio,
        batch_size=args.batch_size,
        audio_max_length=args.audio_max_length,
        score_count=args.score_count,
        bad_case_count=args.bad_case_count,
        normalize_cjk_spaces=args.normalize_cjk_spaces,
    )


def main() -> None:
    report = run_transcript_retrieval(config_from_args(build_parser().parse_args()))
    print(json.dumps({k: report[k] for k in ("experiment", "sample_count", "sample", "text")}, indent=2))


if __name__ == "__main__":
    main()
