"""Execute or audit cache taxonomy plans.

The planner records task/arm/step metadata.  This runner turns those steps into
concrete command lines and, when explicitly requested, executes them.  The
default remains dry-run so a taxonomy sweep can be inspected before loading
large embedding models.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SUPPORTED_STEPS = {
    "cache_text",
    "cache_omni_audio",
    "evaluate_hybrid_from_cache",
    "evaluate_tool_omni_audio",
    "evaluate_asr_like_omni_selection",
    "evaluate_translation_omni_selection",
}


@dataclass(frozen=True)
class CacheTaxonomyRunnerConfig:
    plan: Path
    output: Path
    mode: str = "dry_run"
    backend: str = "legacy"
    python: str = "python"
    legacy_experiments_dir: Path = Path("omni_embedding/experiments")
    max_steps: int = 0
    skip_existing: bool = True
    require_manifest: bool = True
    continue_on_error: bool = False
    env: tuple[str, ...] = ()


def _add_arg(command: list[str], name: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        if value:
            command.append(name)
        return
    if isinstance(value, (int, float)) and value == 0 and name not in {
        "--max-samples",
        "--seed",
    }:
        return
    if value == "":
        return
    command.extend([name, str(value)])


def _legacy_path(script: str) -> str:
    return f"mainline/{script}"


def _repo_relative_from_legacy(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    item = Path(value)
    if item.is_absolute():
        return value
    return str(Path("../..") / item)


def command_for_step(step: dict[str, Any], config: CacheTaxonomyRunnerConfig) -> list[str]:
    """Build an argv command for one taxonomy step.

    The legacy backend intentionally wraps the old ignored experiment scripts.
    This preserves current model behavior while the new Hydra-native encoders
    are still being migrated.
    """

    step_name = step.get("step")
    if step_name not in SUPPORTED_STEPS:
        raise ValueError(f"Unsupported taxonomy step: {step_name}")
    if config.backend != "legacy":
        raise ValueError(f"Unsupported cache taxonomy backend: {config.backend}")

    command = [config.python]
    if step_name == "cache_text":
        command.append(_legacy_path("cache_audio_memory_embeddings.py"))
        _add_arg(command, "--cache-kind", "text")
        _add_arg(command, "--manifest", step.get("manifest"))
        _add_arg(command, "--output", step.get("output"))
        _add_arg(command, "--text-model", step.get("text_model"))
        _add_arg(command, "--query-text-source", step.get("query_text_source"))
        _add_arg(command, "--memory-text-style", step.get("memory_text_style"))
        _add_arg(command, "--max-samples", step.get("max_samples"))
        _add_arg(command, "--test-size", step.get("test_size"))
        _add_arg(command, "--seed", step.get("seed"))
    elif step_name == "cache_omni_audio":
        command.append(_legacy_path("cache_audio_memory_embeddings.py"))
        _add_arg(command, "--cache-kind", "omni")
        _add_arg(command, "--manifest", step.get("manifest"))
        _add_arg(command, "--output", step.get("output"))
        _add_arg(command, "--omni-model", step.get("omni_model"))
        _add_arg(command, "--audio-encode-method", step.get("audio_encode_method"))
        _add_arg(command, "--text-encode-method", step.get("text_encode_method"))
        _add_arg(command, "--audio-query-instruction", step.get("audio_instruction"))
        _add_arg(command, "--max-samples", step.get("max_samples"))
        _add_arg(command, "--test-size", step.get("test_size"))
        _add_arg(command, "--seed", step.get("seed"))
    elif step_name == "evaluate_hybrid_from_cache":
        command.append(_legacy_path("audio_memory_hybrid_from_cache.py"))
        _add_arg(command, "--manifest", step.get("manifest"))
        _add_arg(command, "--text-cache", step.get("text_cache"))
        _add_arg(command, "--omni-cache", step.get("omni_cache"))
        _add_arg(command, "--output", step.get("output"))
        _add_arg(command, "--memory-text-style", step.get("memory_text_style"))
        _add_arg(command, "--score-count", step.get("score_count"))
        _add_arg(command, "--test-size", step.get("test_size"))
        _add_arg(command, "--seed", step.get("seed"))
    elif step_name == "evaluate_tool_omni_audio":
        command.append(_legacy_path("audio_nlp_label_classification.py"))
        _add_arg(command, "--manifest", step.get("manifest"))
        _add_arg(command, "--output", step.get("output"))
        _add_arg(command, "--task", step.get("task"))
        _add_arg(command, "--routes", "omni_audio")
        _add_arg(command, "--omni-model", step.get("omni_model"))
        _add_arg(command, "--omni-query-cache", step.get("omni_query_cache"))
        _add_arg(command, "--audio-encode-method", step.get("audio_encode_method"))
        _add_arg(command, "--text-encode-method", step.get("text_encode_method"))
        _add_arg(command, "--audio-query-instruction", step.get("audio_instruction"))
        _add_arg(command, "--label-description-style", step.get("label_description_style"))
        _add_arg(command, "--label-example-count", step.get("label_example_count"))
        _add_arg(command, "--label-boundary-count", step.get("label_boundary_count"))
        _add_arg(command, "--max-samples", step.get("max_samples"))
        _add_arg(command, "--score-count", step.get("score_count"))
        _add_arg(command, "--seed", step.get("seed"))
    elif step_name == "evaluate_asr_like_omni_selection":
        command.append(_legacy_path("omni_embed_selection.py"))
        _add_arg(command, "--manifest", step.get("manifest"))
        _add_arg(command, "--output", step.get("output"))
        _add_arg(command, "--omni-model", step.get("omni_model"))
        _add_arg(command, "--audio-encode-method", step.get("audio_encode_method"))
        _add_arg(command, "--text-encode-method", step.get("text_encode_method"))
        _add_arg(command, "--audio-query-instruction", step.get("audio_instruction"))
        _add_arg(command, "--candidate-count", step.get("candidate_count"))
        _add_arg(command, "--same-intent-negatives", step.get("same_intent_negatives"))
        _add_arg(command, "--same-domain-negatives", step.get("same_domain_negatives"))
        _add_arg(command, "--max-samples", step.get("max_samples"))
        _add_arg(command, "--score-count", step.get("score_count"))
        _add_arg(command, "--seed", step.get("seed"))
        _add_arg(command, "--include-rows", True)
    elif step_name == "evaluate_translation_omni_selection":
        command = [config.python, "../../scripts/transcript_candidate_retrieval.py"]
        _add_arg(command, "--manifest", _repo_relative_from_legacy(step.get("manifest")))
        _add_arg(command, "--output", _repo_relative_from_legacy(step.get("output")))
        _add_arg(command, "--model", _repo_relative_from_legacy(step.get("omni_model")))
        _add_arg(command, "--route", "direct_omni")
        _add_arg(command, "--instruction-arm", step.get("instruction_arm"))
        _add_arg(command, "--audio-encode-method", step.get("audio_encode_method"))
        _add_arg(command, "--text-encode-method", step.get("text_encode_method"))
        _add_arg(command, "--query-field", "source_text")
        _add_arg(command, "--candidate-field", step.get("candidate_field"))
        _add_arg(command, "--candidate-count", step.get("candidate_count"))
        _add_arg(command, "--max-samples", step.get("max_samples"))
        _add_arg(command, "--score-count", step.get("score_count"))
        _add_arg(command, "--seed", step.get("seed"))
    return command


def load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_steps(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row_index, row in enumerate(plan.get("rows", []), start=1):
        for step_index, step in enumerate(row.get("steps", []), start=1):
            rows.append(
                {
                    "row_index": row_index,
                    "step_index": step_index,
                    "arm": row.get("arm", ""),
                    "audio_instruction": row.get("audio_instruction", ""),
                    "step": step,
                }
            )
    return rows


def _path_exists(path: str | None, base_dir: Path) -> bool:
    if not path:
        return False
    item = Path(path)
    if item.is_absolute():
        return item.exists()
    return (base_dir / item).exists()


def _validate_step(step: dict[str, Any], config: CacheTaxonomyRunnerConfig, cwd: Path) -> list[str]:
    warnings = []
    step_name = step.get("step")
    if step_name not in SUPPORTED_STEPS:
        warnings.append(f"unsupported step {step_name}")
    if config.require_manifest and step.get("manifest") and not _path_exists(step.get("manifest"), cwd):
        warnings.append(f"manifest not found: {step.get('manifest')}")
    if step_name == "evaluate_hybrid_from_cache":
        for key in ("text_cache", "omni_cache"):
            if not _path_exists(step.get(key), cwd):
                warnings.append(f"{key} not found before eval: {step.get(key)}")
    return warnings


def _should_skip(step: dict[str, Any], config: CacheTaxonomyRunnerConfig, cwd: Path) -> bool:
    return bool(config.skip_existing and step.get("output") and _path_exists(step.get("output"), cwd))


def run(config: CacheTaxonomyRunnerConfig) -> dict[str, Any]:
    if config.mode not in {"dry_run", "execute"}:
        raise ValueError(f"Unsupported runner mode: {config.mode}")
    plan = load_plan(config.plan)
    cwd = config.legacy_experiments_dir if config.backend == "legacy" else Path.cwd()
    flat_steps = iter_steps(plan)
    if config.max_steps:
        flat_steps = flat_steps[: config.max_steps]

    started = time.time()
    step_reports = []
    for item in flat_steps:
        step = item["step"]
        command = command_for_step(step, config)
        warnings = _validate_step(step, config, cwd)
        status = "planned"
        returncode = None
        elapsed_sec = 0.0
        skipped = _should_skip(step, config, cwd)
        if skipped:
            status = "skipped_existing"
        elif config.mode == "execute":
            if warnings and config.require_manifest:
                status = "blocked"
            else:
                step_started = time.time()
                completed = subprocess.run(command, cwd=cwd, check=False)
                elapsed_sec = time.time() - step_started
                returncode = completed.returncode
                status = "ok" if completed.returncode == 0 else "failed"
                if completed.returncode != 0 and not config.continue_on_error:
                    step_reports.append(
                        {
                            **item,
                            "command": command,
                            "cwd": str(cwd),
                            "status": status,
                            "returncode": returncode,
                            "elapsed_sec": elapsed_sec,
                            "warnings": warnings,
                        }
                    )
                    break
        step_reports.append(
            {
                **item,
                "command": command,
                "cwd": str(cwd),
                "status": status,
                "returncode": returncode,
                "elapsed_sec": elapsed_sec,
                "warnings": warnings,
            }
        )

    counts: dict[str, int] = {}
    for row in step_reports:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    report = {
        "experiment": "cache_taxonomy_runner",
        "config": asdict(config)
        | {
            "plan": str(config.plan),
            "output": str(config.output),
            "legacy_experiments_dir": str(config.legacy_experiments_dir),
            "env": list(config.env),
        },
        "plan_experiment": plan.get("experiment"),
        "step_count": len(step_reports),
        "status_counts": counts,
        "elapsed_sec": time.time() - started,
        "steps": step_reports,
        "notes": [
            "dry_run builds argv commands and validation warnings without loading models.",
            "execute runs the legacy backend from legacy_experiments_dir; migrate Hydra-native encoders before removing this bridge.",
        ],
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=["dry_run", "execute"], default="dry_run")
    parser.add_argument("--backend", choices=["legacy"], default="legacy")
    parser.add_argument("--python", default="python")
    parser.add_argument("--legacy-experiments-dir", type=Path, default=Path("omni_embedding/experiments"))
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--no-require-manifest", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> CacheTaxonomyRunnerConfig:
    return CacheTaxonomyRunnerConfig(
        plan=args.plan,
        output=args.output,
        mode=args.mode,
        backend=args.backend,
        python=args.python,
        legacy_experiments_dir=args.legacy_experiments_dir,
        max_steps=args.max_steps,
        skip_existing=not args.no_skip_existing,
        require_manifest=not args.no_require_manifest,
        continue_on_error=args.continue_on_error,
    )


def main() -> None:
    print(json.dumps(run(config_from_args(build_parser().parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
