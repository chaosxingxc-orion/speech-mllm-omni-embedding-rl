"""Frozen speech-to-tool/intent retrieval evaluation.

The evaluator ranks label/tool descriptions for each spoken command without
training a classifier or changing any model weights.  It supports direct omni
audio queries and text-query baselines over the same label descriptions.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from omni_embedding_rl.data.manifest import read_jsonl
from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS
from omni_embedding_rl.tasks.tool_schema import rank_metrics, tool_label_description


@dataclass(frozen=True)
class ToolIntentRetrievalConfig:
    manifest: Path
    output: Path
    model: str
    route: str = "direct_omni"
    task: str = "intent"
    instruction_arm: str = "tool_specific_intent"
    label_description_style: str = "tool_schema_card"
    label_example_count: int = 3
    label_boundary_count: int = 3
    max_samples: int = 0
    seed: int = 42
    device: str = "auto"
    trust_remote_code: bool = True
    torch_dtype: str = "bfloat16"
    attn_implementation: str = ""
    audio_encode_method: str = "query"
    text_encode_method: str = "document"
    query_encode_method: str = "query"
    query_field: str = "text"
    asr_field: str = "asr_text"
    include_query_text_with_audio: bool = False
    audio_payload_mode: str = "dict"
    batch_size: int = 16
    audio_max_length: int = 2048000
    score_count: int = 8
    bad_case_count: int = 20


def _require_sentence_transformer():
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - depends on experiment env
        raise SystemExit(
            "This evaluator requires torch and sentence-transformers in the "
            "experiment environment."
        ) from exc
    return torch, SentenceTransformer


def _resolve_device(torch: Any, requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return requested


def _load_model(config: ToolIntentRetrievalConfig, device: str):
    torch, SentenceTransformer = _require_sentence_transformer()
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


def _encode(model: Any, items: list[Any], method: str, batch_size: int) -> np.ndarray:
    if method == "query":
        embeddings = model.encode_query(items, batch_size=batch_size, show_progress_bar=False)
    elif method == "document":
        embeddings = model.encode_document(items, batch_size=batch_size, show_progress_bar=False)
    else:
        embeddings = model.encode(items, batch_size=batch_size, show_progress_bar=False)
    return _to_normalized_numpy(embeddings)


def _limit_rows(rows: list[dict[str, Any]], max_samples: int) -> list[dict[str, Any]]:
    if max_samples and max_samples > 0:
        return rows[:max_samples]
    return rows


def _task_label(row: dict[str, Any], task: str) -> str:
    value = row.get(task)
    if value in (None, ""):
        raise ValueError(f"row is missing required label field {task!r}: {row.get('sample_id', '')}")
    return str(value)


def _query_text(row: dict[str, Any], config: ToolIntentRetrievalConfig) -> str:
    if config.route == "asr_text":
        value = row.get(config.asr_field) or row.get("transcript") or row.get("text")
    else:
        value = row.get(config.query_field) or row.get("transcript") or row.get("text")
    return str(value or "")


def _instruction(config: ToolIntentRetrievalConfig) -> str:
    if config.instruction_arm not in INSTRUCTION_ARMS:
        raise ValueError(
            f"unknown instruction arm {config.instruction_arm!r}; known={sorted(INSTRUCTION_ARMS)}"
        )
    return INSTRUCTION_ARMS[config.instruction_arm]


def _audio_payload(
    row: dict[str, Any],
    instruction: str,
    query_text: str,
    include_text: bool,
    payload_mode: str,
) -> Any:
    audio_path = str(row["audio_path"])
    if payload_mode == "path":
        return audio_path
    if payload_mode != "dict":
        raise ValueError("audio_payload_mode must be one of: dict, path")
    payload = {"audio": audio_path}
    text_parts = []
    if instruction:
        text_parts.append(instruction)
    if include_text and query_text:
        text_parts.append(f"Spoken command transcript hint: {query_text}")
    if text_parts:
        payload["text"] = "\n".join(text_parts)
    return payload


def _text_payload(text: str, instruction: str) -> str:
    if instruction:
        return f"{instruction}\n{text}"
    return text


def _label_descriptions(
    rows: list[dict[str, Any]],
    labels: list[str],
    config: ToolIntentRetrievalConfig,
) -> dict[str, str]:
    label_domains: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        label = _task_label(row, config.task)
        if config.task == "intent" and row.get("domain"):
            label_domains[label][str(row["domain"])] += 1
        if len(examples[label]) < config.label_example_count:
            examples[label].append(str(row.get("text") or row.get("transcript") or ""))

    descriptions = {}
    for label in labels:
        label_domain = None
        if config.task == "intent" and label_domains[label]:
            label_domain = label_domains[label].most_common(1)[0][0]
        if config.task == "domain":
            boundary_labels = [other for other in labels if other != label][: config.label_boundary_count]
        elif label_domain:
            boundary_labels = [
                other
                for other in labels
                if other != label
                and label_domains[other]
                and label_domains[other].most_common(1)[0][0] == label_domain
            ][: config.label_boundary_count]
        else:
            boundary_labels = [other for other in labels if other != label][: config.label_boundary_count]
        descriptions[label] = tool_label_description(
            label=label,
            task=config.task,
            style=config.label_description_style,
            label_domain=label_domain,
            examples=examples[label],
            boundary_labels=boundary_labels,
        )
    return descriptions


def _encode_queries(
    model: Any,
    rows: list[dict[str, Any]],
    config: ToolIntentRetrievalConfig,
    instruction: str,
) -> np.ndarray:
    if config.route == "direct_omni":
        vectors = []
        for row in rows:
            payload = [
                _audio_payload(
                    row,
                    instruction,
                    _query_text(row, config),
                    config.include_query_text_with_audio,
                    config.audio_payload_mode,
                )
            ]
            vectors.append(_encode(model, payload, config.audio_encode_method, batch_size=1)[0])
        return np.stack(vectors)
    if config.route in {"oracle_text", "asr_text"}:
        texts = [_text_payload(_query_text(row, config), instruction) for row in rows]
        return _encode(model, texts, config.query_encode_method, config.batch_size)
    raise ValueError("route must be one of: direct_omni, oracle_text, asr_text")


def run_tool_intent_retrieval(config: ToolIntentRetrievalConfig) -> dict[str, Any]:
    torch, _ = _require_sentence_transformer()
    device = _resolve_device(torch, config.device)
    rows = _limit_rows(read_jsonl(config.manifest), config.max_samples)
    if not rows:
        raise ValueError(f"manifest has no rows: {config.manifest}")

    labels = sorted({_task_label(row, config.task) for row in rows})
    descriptions = _label_descriptions(rows, labels, config)
    instruction = _instruction(config)
    model = _load_model(config, device)

    query_vectors = _encode_queries(model, rows, config, instruction)
    label_texts = [descriptions[label] for label in labels]
    label_vectors = _encode(model, label_texts, config.text_encode_method, config.batch_size)
    scores = query_vectors @ label_vectors.T

    ranks: list[int] = []
    result_rows = []
    examples = []
    bad_cases = []
    confusion: Counter[tuple[str, str]] = Counter()
    for index, row in enumerate(rows):
        target = _task_label(row, config.task)
        target_index = labels.index(target)
        order = np.argsort(-scores[index]).tolist()
        rank = order.index(target_index) + 1
        prediction = labels[order[0]]
        ranks.append(rank)
        confusion[(target, prediction)] += 1
        output_row = {
            "sample_id": row.get("sample_id", str(index)),
            "text": row.get("text", ""),
            "target": target,
            "prediction": prediction,
            "rank": rank,
            "hit_at_1": rank == 1,
            "top_labels": [
                {
                    "rank": label_rank,
                    "label": labels[label_index],
                    "score": float(scores[index, label_index]),
                }
                for label_rank, label_index in enumerate(order[: config.score_count], start=1)
            ],
        }
        result_rows.append(output_row)
        if len(examples) < 10:
            examples.append(output_row)
        if rank > 1 and len(bad_cases) < config.bad_case_count:
            bad_cases.append(output_row)

    common_confusions = [
        {"target": target, "prediction": prediction, "count": count}
        for (target, prediction), count in confusion.most_common(20)
        if target != prediction
    ]
    report = {
        "experiment": "tool_intent_retrieval",
        "config": asdict(config) | {
            "manifest": str(config.manifest),
            "output": str(config.output),
        },
        "device": device,
        "sample_count": len(rows),
        "label_count": len(labels),
        "labels": [{"label": label, "description": descriptions[label]} for label in labels],
        "metrics": rank_metrics(ranks),
        "bad_case_count": sum(rank > 1 for rank in ranks),
        "common_confusions": common_confusions,
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
    parser.add_argument("--route", choices=["direct_omni", "oracle_text", "asr_text"], default="direct_omni")
    parser.add_argument("--task", choices=["domain", "intent"], default="intent")
    parser.add_argument("--instruction-arm", default="tool_specific_intent")
    parser.add_argument(
        "--label-description-style",
        choices=[
            "basic",
            "examples",
            "tool_schema_card",
            "example_augmented_tool",
            "contrastive_boundary_tool",
        ],
        default="tool_schema_card",
    )
    parser.add_argument("--label-example-count", type=int, default=3)
    parser.add_argument("--label-boundary-count", type=int, default=3)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--no-trust-remote-code", action="store_true")
    parser.add_argument("--torch-dtype", default="bfloat16")
    parser.add_argument("--attn-implementation", default="")
    parser.add_argument("--audio-encode-method", choices=["query", "document", "encode"], default="query")
    parser.add_argument("--text-encode-method", choices=["query", "document", "encode"], default="document")
    parser.add_argument("--query-encode-method", choices=["query", "document", "encode"], default="query")
    parser.add_argument("--query-field", default="text")
    parser.add_argument("--asr-field", default="asr_text")
    parser.add_argument("--include-query-text-with-audio", action="store_true")
    parser.add_argument("--audio-payload-mode", choices=["dict", "path"], default="dict")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--audio-max-length", type=int, default=2048000)
    parser.add_argument("--score-count", type=int, default=8)
    parser.add_argument("--bad-case-count", type=int, default=20)
    return parser


def config_from_args(args: argparse.Namespace) -> ToolIntentRetrievalConfig:
    return ToolIntentRetrievalConfig(
        manifest=args.manifest,
        output=args.output,
        model=args.model,
        route=args.route,
        task=args.task,
        instruction_arm=args.instruction_arm,
        label_description_style=args.label_description_style,
        label_example_count=args.label_example_count,
        label_boundary_count=args.label_boundary_count,
        max_samples=args.max_samples,
        seed=args.seed,
        device=args.device,
        trust_remote_code=not args.no_trust_remote_code,
        torch_dtype=args.torch_dtype,
        attn_implementation=args.attn_implementation,
        audio_encode_method=args.audio_encode_method,
        text_encode_method=args.text_encode_method,
        query_encode_method=args.query_encode_method,
        query_field=args.query_field,
        asr_field=args.asr_field,
        include_query_text_with_audio=args.include_query_text_with_audio,
        audio_payload_mode=args.audio_payload_mode,
        batch_size=args.batch_size,
        audio_max_length=args.audio_max_length,
        score_count=args.score_count,
        bad_case_count=args.bad_case_count,
    )


def main() -> None:
    report = run_tool_intent_retrieval(config_from_args(build_parser().parse_args()))
    print(
        json.dumps(
            {
                "experiment": report["experiment"],
                "sample_count": report["sample_count"],
                "label_count": report["label_count"],
                "metrics": report["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
