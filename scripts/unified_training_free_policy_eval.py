"""Aggregate current frozen semantic speech policies into one controller report.

This script does not run models and does not train weights.  It reads saved
row-level JSON results and evaluates whether a task-specific policy is safe to
include in a unified training-free policy surface.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    family: str
    baseline: Path
    selected: Path
    metric_kind: str
    baseline_name: str
    selected_name: str
    protected: bool = True
    min_delta: float = 0.0
    max_regression_rate: float = 0.03
    max_unsafe_delta: float = 0.0


@dataclass(frozen=True)
class UnifiedPolicyConfig:
    output: Path
    bootstrap_rounds: int = 5000
    seed: int = 42


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested_get(obj: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def extract_rows(obj: dict[str, Any], metric_kind: str) -> list[dict[str, Any]]:
    if metric_kind == "tool":
        return list(obj.get("rows") or nested_get(obj, ("metrics", "omni_audio", "rows"), []))
    return list(obj.get("rows", []))


def success(row: dict[str, Any], metric_kind: str) -> float:
    if metric_kind == "tool":
        return 1.0 if row.get("hit_at_1") else 0.0
    if metric_kind == "rag_answer":
        return 1.0 if row.get("answer_pass") else 0.0
    if metric_kind == "translation_text":
        return 1.0 if row.get("text_hit_at_1") else 0.0
    if metric_kind == "transcript_text":
        return 1.0 if row.get("text_hit_at_1") else 0.0
    raise ValueError(f"unknown metric_kind: {metric_kind}")


def rank_mrr(row: dict[str, Any], metric_kind: str) -> float:
    if metric_kind == "tool":
        rank = int(row.get("rank", 10**9))
    elif metric_kind in {"translation_text", "transcript_text"}:
        rank = int(row.get("text_rank", 10**9))
    elif metric_kind == "rag_answer":
        return float(row.get("required_terms_recall", 0.0))
    else:
        rank = 10**9
    return 1.0 / rank if rank > 0 else 0.0


def unsafe(row: dict[str, Any], metric_kind: str) -> float:
    if metric_kind == "rag_answer":
        return 1.0 if row.get("forbidden_violation") or row.get("api_error") else 0.0
    if metric_kind == "tool":
        pred = str(row.get("prediction", ""))
        target = str(row.get("target", ""))
        pred_domain = pred.split("_", 1)[0] if pred else ""
        target_domain = target.split("_", 1)[0] if target else ""
        return 1.0 if pred and target and pred != target and pred_domain != target_domain else 0.0
    return 0.0


def metric_summary(obj: dict[str, Any], metric_kind: str) -> dict[str, float]:
    if metric_kind == "tool":
        metrics = obj.get("metrics", {})
        if "accuracy_at_1" not in metrics:
            metrics = nested_get(obj, ("metrics", "omni_audio", "metrics"), {})
        return {
            "primary": float(metrics.get("accuracy_at_1", 0.0)),
            "auxiliary": float(metrics.get("mrr", 0.0)),
            "unsafe": unsafe_rate(extract_rows(obj, metric_kind), metric_kind),
        }
    if metric_kind == "rag_answer":
        metrics = obj.get("metrics", {})
        return {
            "primary": float(metrics.get("answer_pass", 0.0)),
            "auxiliary": float(metrics.get("required_terms_recall", 0.0)),
            "unsafe": float(metrics.get("forbidden_terms_violation_rate", 0.0)),
        }
    if metric_kind in {"translation_text", "transcript_text"}:
        text = obj.get("text", {})
        return {
            "primary": float(text.get("accuracy", 0.0)),
            "auxiliary": float(text.get("mrr", 0.0)),
            "unsafe": 0.0,
        }
    raise ValueError(f"unknown metric_kind: {metric_kind}")


def unsafe_rate(rows: list[dict[str, Any]], metric_kind: str) -> float:
    return sum(unsafe(row, metric_kind) for row in rows) / len(rows) if rows else 0.0


def paired_delta(
    baseline_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    metric_kind: str,
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    base = {str(row.get("sample_id", "")): row for row in baseline_rows if row.get("sample_id")}
    cand = {str(row.get("sample_id", "")): row for row in selected_rows if row.get("sample_id")}
    ids = sorted(set(base) & set(cand))
    if not ids:
        return {
            "n": 0,
            "delta": 0.0,
            "ci95": [0.0, 0.0],
            "fixes": 0,
            "regressions": 0,
            "regression_rate": 0.0,
        }
    diffs = [success(cand[sid], metric_kind) - success(base[sid], metric_kind) for sid in ids]
    rng = random.Random(seed)
    boots = []
    for _ in range(rounds):
        boots.append(sum(diffs[rng.randrange(len(diffs))] for _ in diffs) / len(diffs))
    boots.sort()
    regressions = sum(1 for value in diffs if value < 0)
    return {
        "n": len(ids),
        "delta": sum(diffs) / len(diffs),
        "ci95": [
            boots[int(0.025 * (rounds - 1))],
            boots[int(0.975 * (rounds - 1))],
        ],
        "fixes": sum(1 for value in diffs if value > 0),
        "regressions": regressions,
        "regression_rate": regressions / len(ids),
    }


def utility(summary: dict[str, float]) -> float:
    return summary["primary"] + 0.1 * summary["auxiliary"] - 0.2 * summary["unsafe"]


def default_specs() -> list[TaskSpec]:
    out = Path("outputs")
    return [
        TaskSpec(
            task_id="asr_semantics_fleurs_en",
            family="asr_semantics",
            baseline=out / "fleurs_en_us_direct_omni_60_raw.json",
            selected=out / "fleurs_en_us_direct_omni_60_transcript_like.json",
            metric_kind="transcript_text",
            baseline_name="direct_omni_raw",
            selected_name="direct_omni_transcript_like",
        ),
        TaskSpec(
            task_id="speech_rag_heysquad",
            family="speech_rag",
            baseline=out / "heysquad_human_train60_rag_answer_asr_llm_top3_60.json",
            selected=out / "heysquad_human_train60_rag_answer_omni_llm_top3_robust_60.json",
            metric_kind="rag_answer",
            baseline_name="asr_top3_default",
            selected_name="omni_top3_asr_robust",
            max_regression_rate=0.25,
        ),
        TaskSpec(
            task_id="tool_slurp500",
            family="tool_intent",
            baseline=out / "tool_intent_slurp500_omni_raw_tool_schema.json",
            selected=out / "tool_intent_slurp500_omni_tool_specific_contrastive_boundary.json",
            metric_kind="tool",
            baseline_name="raw_tool_schema",
            selected_name="tool_instruction_boundary_schema",
            max_regression_rate=0.03,
        ),
        TaskSpec(
            task_id="tool_minds180",
            family="tool_intent",
            baseline=out / "tool_intent_minds180_omni_raw_tool_schema.json",
            selected=out / "tool_intent_minds180_omni_tool_specific_contrastive_boundary.json",
            metric_kind="tool",
            baseline_name="raw_tool_schema",
            selected_name="tool_instruction_boundary_schema",
            max_regression_rate=0.03,
        ),
        TaskSpec(
            task_id="translation_fleurs_en_fr",
            family="speech_translation",
            baseline=out / "fleurs_en_fr_translation_direct_omni_raw_all57.json",
            selected=out / "fleurs_en_fr_translation_direct_omni_translation_semantic_all57.json",
            metric_kind="translation_text",
            baseline_name="direct_omni_raw",
            selected_name="direct_omni_translation_semantic",
        ),
        TaskSpec(
            task_id="translation_text_route_guard",
            family="speech_translation_guard",
            baseline=out / "fleurs_en_fr_translation_oracle_text_raw_all57.json",
            selected=out / "fleurs_en_fr_translation_oracle_text_translation_semantic_all57.json",
            metric_kind="translation_text",
            baseline_name="oracle_text_raw",
            selected_name="oracle_text_translation_semantic",
            protected=True,
            min_delta=-0.001,
            max_regression_rate=0.03,
        ),
    ]


def evaluate_spec(spec: TaskSpec, config: UnifiedPolicyConfig) -> dict[str, Any]:
    baseline = read_json(spec.baseline)
    selected = read_json(spec.selected)
    base_summary = metric_summary(baseline, spec.metric_kind)
    selected_summary = metric_summary(selected, spec.metric_kind)
    paired = paired_delta(
        extract_rows(baseline, spec.metric_kind),
        extract_rows(selected, spec.metric_kind),
        spec.metric_kind,
        config.bootstrap_rounds,
        config.seed,
    )
    utility_delta = utility(selected_summary) - utility(base_summary)
    unsafe_delta = selected_summary["unsafe"] - base_summary["unsafe"]
    accepted = (
        paired["delta"] >= spec.min_delta
        and paired["ci95"][0] >= spec.min_delta
        and paired["regression_rate"] <= spec.max_regression_rate
        and unsafe_delta <= spec.max_unsafe_delta
    )
    reasons = []
    if paired["delta"] < spec.min_delta:
        reasons.append("mean_delta_below_threshold")
    if paired["ci95"][0] < spec.min_delta:
        reasons.append("ci_lower_bound_below_threshold")
    if paired["regression_rate"] > spec.max_regression_rate:
        reasons.append("regression_rate_too_high")
    if unsafe_delta > spec.max_unsafe_delta:
        reasons.append("unsafe_delta_too_high")
    return {
        "task_id": spec.task_id,
        "family": spec.family,
        "baseline_name": spec.baseline_name,
        "selected_name": spec.selected_name,
        "metric_kind": spec.metric_kind,
        "protected": spec.protected,
        "baseline": base_summary,
        "selected": selected_summary,
        "primary_delta": selected_summary["primary"] - base_summary["primary"],
        "utility_delta": utility_delta,
        "unsafe_delta": unsafe_delta,
        "paired": paired,
        "accepted": accepted,
        "reject_reasons": reasons,
        "baseline_path": str(spec.baseline),
        "selected_path": str(spec.selected),
    }


def run(config: UnifiedPolicyConfig) -> dict[str, Any]:
    rows = []
    missing = []
    for spec in default_specs():
        if not spec.baseline.exists() or not spec.selected.exists():
            missing.append(asdict(spec) | {"baseline": str(spec.baseline), "selected": str(spec.selected)})
            continue
        rows.append(evaluate_spec(spec, config))
    protected = [row for row in rows if row["protected"]]
    accepted = [row for row in rows if row["accepted"]]
    report = {
        "experiment": "unified_training_free_policy_surface",
        "config": asdict(config) | {"output": str(config.output)},
        "summary": {
            "evaluated_tasks": len(rows),
            "missing_tasks": len(missing),
            "accepted_tasks": len(accepted),
            "protected_regression_failures": [
                row["task_id"] for row in protected if row["paired"]["ci95"][0] < 0
            ],
            "mean_primary_delta": sum(row["primary_delta"] for row in rows) / len(rows) if rows else 0.0,
            "mean_utility_delta": sum(row["utility_delta"] for row in rows) / len(rows) if rows else 0.0,
        },
        "rows": rows,
        "missing": missing,
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/unified_training_free_policy_surface.json"))
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    report = run(UnifiedPolicyConfig(**vars(build_parser().parse_args())))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for row in report["rows"]:
        print(
            row["task_id"],
            "accepted=" + str(row["accepted"]),
            "delta=" + f"{row['primary_delta']:.3f}",
            "ci=" + str([round(v, 3) for v in row["paired"]["ci95"]]),
            "reg=" + f"{row['paired']['regression_rate']:.3f}",
        )


if __name__ == "__main__":
    main()
