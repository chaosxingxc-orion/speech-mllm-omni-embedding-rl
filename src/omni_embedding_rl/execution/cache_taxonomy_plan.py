"""Build cache-first taxonomy execution plans.

The legacy cache taxonomy script executed old modules directly.  This migrated
version deliberately produces a structured plan first.  The plan records what
would be cached/evaluated for every task and instruction arm, without depending
on ignored legacy paths or loading large models.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omni_embedding_rl.policies.instructions import arm_items, slugify


@dataclass(frozen=True)
class CacheTaxonomyPlanConfig:
    task: str
    manifest: str
    output: Path
    dataset_name: str = ""
    arms: tuple[str, ...] = ()
    max_samples: int = 0
    seed: int = 42
    test_size: float = 0.35
    results_dir: str = "outputs"
    text_model: str = "Qwen/Qwen3-Embedding-4B"
    omni_model: str = "experiments/models/omni-embed-nemotron-3b"
    score_count: int = 8
    memory_text_style: str = "document_memory"
    tool_task: str = "intent"
    label_description_style: str = "contrastive_boundary_tool"
    label_example_count: int = 3
    label_boundary_count: int = 3
    candidate_count: int = 8
    same_intent_negatives: int = 2
    same_domain_negatives: int = 2
    translation_target_field: str = "target_text"


def result_name(config: CacheTaxonomyPlanConfig, arm: str) -> str:
    return f"agentic_cache_taxonomy_{config.task}_{slugify(config.dataset_name or config.task)}_{slugify(arm)}.json"


def cache_name(config: CacheTaxonomyPlanConfig, arm: str, kind: str) -> str:
    return f"cache_agentic_taxonomy_{config.task}_{slugify(config.dataset_name or config.task)}_{slugify(arm)}_{kind}.pt"


def text_cache_name(config: CacheTaxonomyPlanConfig) -> str:
    return f"cache_agentic_taxonomy_{config.task}_{slugify(config.dataset_name or config.task)}_qwen3_text.pt"


def result_path(config: CacheTaxonomyPlanConfig, name: str) -> str:
    return str(Path(config.results_dir) / name)


def rag_steps(config: CacheTaxonomyPlanConfig, arm: str, instruction: str) -> list[dict[str, Any]]:
    text_cache = text_cache_name(config)
    omni_cache = cache_name(config, arm, "omni")
    result = result_name(config, arm)
    return [
        {
            "step": "cache_text",
            "cache_kind": "text",
            "output": result_path(config, text_cache),
            "manifest": config.manifest,
            "text_model": config.text_model,
            "query_text_source": "asr",
            "memory_text_style": config.memory_text_style,
            "max_samples": config.max_samples,
            "test_size": config.test_size,
            "seed": config.seed,
        },
        {
            "step": "cache_omni_audio",
            "cache_kind": "omni",
            "output": result_path(config, omni_cache),
            "manifest": config.manifest,
            "omni_model": config.omni_model,
            "audio_encode_method": "query",
            "text_encode_method": "document",
            "audio_instruction": instruction,
            "max_samples": config.max_samples,
            "test_size": config.test_size,
            "seed": config.seed,
        },
        {
            "step": "evaluate_hybrid_from_cache",
            "output": result_path(config, result),
            "manifest": config.manifest,
            "text_cache": result_path(config, text_cache),
            "omni_cache": result_path(config, omni_cache),
            "memory_text_style": config.memory_text_style,
            "score_count": config.score_count,
            "test_size": config.test_size,
            "seed": config.seed,
        },
    ]


def tool_steps(config: CacheTaxonomyPlanConfig, arm: str, instruction: str) -> list[dict[str, Any]]:
    query_cache = cache_name(config, arm, "tool_query")
    result = result_name(config, arm)
    return [
        {
            "step": "evaluate_tool_omni_audio",
            "output": result_path(config, result),
            "manifest": config.manifest,
            "task": config.tool_task,
            "omni_model": config.omni_model,
            "omni_query_cache": result_path(config, query_cache),
            "audio_encode_method": "query",
            "text_encode_method": "document",
            "audio_instruction": instruction,
            "label_description_style": config.label_description_style,
            "label_example_count": config.label_example_count,
            "label_boundary_count": config.label_boundary_count,
            "max_samples": config.max_samples,
            "score_count": config.score_count,
            "seed": config.seed,
        }
    ]


def asr_like_steps(config: CacheTaxonomyPlanConfig, arm: str, instruction: str) -> list[dict[str, Any]]:
    result = result_name(config, arm)
    return [
        {
            "step": "evaluate_asr_like_omni_selection",
            "output": result_path(config, result),
            "manifest": config.manifest,
            "omni_model": config.omni_model,
            "audio_encode_method": "query",
            "text_encode_method": "document",
            "audio_instruction": instruction,
            "candidate_count": config.candidate_count,
            "same_intent_negatives": config.same_intent_negatives,
            "same_domain_negatives": config.same_domain_negatives,
            "max_samples": config.max_samples,
            "score_count": config.score_count,
            "seed": config.seed,
        }
    ]


def translation_steps(
    config: CacheTaxonomyPlanConfig, arm: str, instruction: str
) -> list[dict[str, Any]]:
    result = result_name(config, arm)
    return [
        {
            "step": "evaluate_translation_omni_selection",
            "output": result_path(config, result),
            "manifest": config.manifest,
            "omni_model": config.omni_model,
            "instruction_arm": arm,
            "audio_encode_method": "query",
            "text_encode_method": "document",
            "audio_instruction": instruction,
            "candidate_field": config.translation_target_field,
            "candidate_count": config.candidate_count,
            "max_samples": config.max_samples,
            "score_count": config.score_count,
            "seed": config.seed,
        }
    ]


def build_plan(config: CacheTaxonomyPlanConfig) -> dict[str, Any]:
    arms = arm_items(config.task, config.arms or None)
    rows = []
    for arm, instruction in arms:
        if config.task == "rag":
            steps = rag_steps(config, arm, instruction)
        elif config.task == "tool":
            steps = tool_steps(config, arm, instruction)
        elif config.task == "asr_like":
            steps = asr_like_steps(config, arm, instruction)
        elif config.task == "translation":
            steps = translation_steps(config, arm, instruction)
        else:
            raise ValueError(f"Unsupported cache taxonomy task: {config.task}")
        rows.append(
            {
                "arm": arm,
                "audio_instruction": instruction or "none",
                "result_path": result_path(config, result_name(config, arm)),
                "steps": steps,
            }
        )
    return {
        "experiment": "cache_taxonomy_plan",
        "config": asdict(config) | {"output": str(config.output), "arms": list(config.arms)},
        "rows": rows,
        "notes": [
            "This is a dry execution plan, not a model runner.",
            "Use it to review cache/eval actions before wiring model-heavy Hydra execution.",
        ],
    }


def run(config: CacheTaxonomyPlanConfig) -> dict[str, Any]:
    report = build_plan(config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["rag", "tool", "asr_like", "translation"], required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset-name", default="")
    parser.add_argument("--arm", action="append")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.35)
    parser.add_argument("--results-dir", default="outputs")
    parser.add_argument("--translation-target-field", default="target_text")
    return parser


def config_from_args(args: argparse.Namespace) -> CacheTaxonomyPlanConfig:
    return CacheTaxonomyPlanConfig(
        task=args.task,
        manifest=args.manifest,
        output=args.output,
        dataset_name=args.dataset_name,
        arms=tuple(args.arm or ()),
        max_samples=args.max_samples,
        seed=args.seed,
        test_size=args.test_size,
        results_dir=args.results_dir,
        translation_target_field=args.translation_target_field,
    )


def main() -> None:
    print(json.dumps(run(config_from_args(build_parser().parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
