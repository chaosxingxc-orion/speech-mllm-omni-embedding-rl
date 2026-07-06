#!/usr/bin/env python
"""Export paper-facing bad-case and regression taxonomy.

This script is intentionally offline.  It reads existing row-level result JSONs
and writes a compact JSON plus Markdown appendix that explains where accepted
policies still fail or regress.
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


def row_key(row: dict[str, Any]) -> str:
    return str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")


def index_rows(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row_key(row): row for row in data.get("rows", [])}


def short(value: Any, limit: int = 220) -> str:
    text = " ".join(str("" if value is None else value).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def candidate_text(row: dict[str, Any], memory_id: str) -> str:
    ids = [str(item) for item in row.get("candidate_memory_ids", [])]
    try:
        index = ids.index(str(memory_id))
    except ValueError:
        return ""
    # The memory-use result rows keep only ids, but the original manifest rows
    # are not needed for the taxonomy.  A candidate position is still useful.
    return f"candidate_{index + 1}"


def classify_heysquad_packed(base: dict[str, Any], cand: dict[str, Any]) -> str:
    if cand.get("invalid_output"):
        return "packed_invalid_output"
    if not cand.get("task_success") and cand.get("wrong_memory"):
        return "packed_wrong_memory"
    if base.get("task_success") and not cand.get("task_success"):
        return "packing_regression"
    return "packed_other_failure"


def heysquad_packed_cases(
    original_path: Path,
    packed_path: Path,
    max_cases: int,
) -> dict[str, Any]:
    original = read_json(original_path)
    packed = read_json(packed_path)
    base_rows = index_rows(original)
    packed_rows = index_rows(packed)
    cases = []
    fixes = 0
    regressions = 0
    remaining_failures = 0
    for key, base in base_rows.items():
        cand = packed_rows.get(key)
        if not cand:
            continue
        base_ok = bool(base.get("task_success"))
        cand_ok = bool(cand.get("task_success"))
        fixes += int(cand_ok and not base_ok)
        regressions += int(base_ok and not cand_ok)
        remaining_failures += int(not cand_ok)
        if len(cases) < max_cases and (base_ok and not cand_ok or not cand_ok):
            cases.append(
                {
                    "case_type": classify_heysquad_packed(base, cand),
                    "query_id": key,
                    "gold_answer": cand.get("gold_answer"),
                    "gold_memory_id": cand.get("gold_memory_id"),
                    "original_prediction": base.get("prediction"),
                    "packed_prediction": cand.get("prediction"),
                    "packed_prediction_position": candidate_text(cand, str(cand.get("prediction") or "")),
                    "packed_model_output": short(cand.get("model_output"), 160),
                    "original_success": base_ok,
                    "packed_success": cand_ok,
                    "packed_invalid": cand.get("invalid_output"),
                    "packed_text_cost": cand.get("text_cost"),
                }
            )
    return {
        "name": "heysquad_packed_retrieval_use",
        "source_original": str(original_path),
        "source_candidate": str(packed_path),
        "summary": {
            "n": len(base_rows),
            "original_success": original.get("task_success"),
            "packed_success": packed.get("task_success"),
            "fixes": fixes,
            "regressions": regressions,
            "remaining_failures": remaining_failures,
            "invalid_after_packing": packed.get("invalid_output"),
        },
        "taxonomy": {
            "main_regression_mode": "packing may sharpen/shorten evidence enough that the model chooses a nearby wrong memory",
            "main_remaining_failure_mode": "gold memory absent from retrieved top-k or wrong packed memory selected",
            "accepted_mitigation": "keep packing, then add rerank/verifier for remaining low-confidence top-k rows",
        },
        "examples": cases,
    }


def classify_gate_case(row: dict[str, Any]) -> str:
    reason = str(row.get("gate_reason") or "")
    if row.get("gate_regression"):
        return "audio_gate_regression"
    if "text_equals_noquery" in reason:
        return "text_hint_uninformative"
    if "overlap" in reason:
        return "text_candidate_overlap_trigger"
    if "first_candidate" in reason:
        return "position_sensitive_trigger"
    return "gate_case"


def gate_selector_cases(selector_path: Path, gate_report_paths: list[Path], max_cases: int) -> dict[str, Any]:
    selector = read_json(selector_path)
    selected = {item["dataset"]: item["selected_gate"] for item in selector.get("selections", [])}
    reports = [read_json(path) for path in gate_report_paths]
    cases = []
    per_dataset: dict[str, dict[str, Any]] = {}
    for report in reports:
        dataset_label = str(report.get("dataset") or "")
        # Map raw report labels to selector labels.
        if dataset_label.startswith("covost2"):
            dataset = "CoVoST2 ar"
        elif dataset_label.startswith("minds"):
            dataset = "MInDS"
        elif dataset_label.startswith("heysquad"):
            dataset = "HeySQuAD"
        else:
            continue
        gate = selected.get(dataset)
        if not gate:
            continue
        summaries = {item["gate"]: item for item in report.get("summaries", [])}
        paired = {item["gate"]: item for item in report.get("paired_vs_text", [])}
        if gate in summaries:
            per_dataset.setdefault(dataset, {"gate": gate, "conditions": []})["conditions"].append(
                {
                    "report_dataset": dataset_label,
                    "success": summaries[gate].get("success"),
                    "gate_rate": summaries[gate].get("gate_rate"),
                    "audio_cost": summaries[gate].get("mean_decision_audio_cost"),
                    "delta": paired.get(gate, {}).get("delta"),
                    "ci95": paired.get(gate, {}).get("ci95"),
                    "fixes": paired.get(gate, {}).get("fixes"),
                    "regressions": paired.get(gate, {}).get("regressions"),
                }
            )
        for row in report.get("gate_results", {}).get(gate, {}).get("rows", []):
            if len(cases) >= max_cases:
                break
            if row.get("gate_regression") or row.get("gate_rescue"):
                cases.append(
                    {
                        "dataset": dataset,
                        "report_dataset": dataset_label,
                        "selected_gate": gate,
                        "case_type": classify_gate_case(row),
                        "query_id": row_key(row),
                        "gold_memory_id": row.get("gold_memory_id"),
                        "text_prediction": row.get("text_prediction"),
                        "audio_prediction": row.get("audio_prediction"),
                        "chosen_prediction": row.get("prediction"),
                        "text_success": row.get("text_success"),
                        "audio_success": row.get("audio_success"),
                        "gate_rescue": row.get("gate_rescue"),
                        "gate_regression": row.get("gate_regression"),
                        "gate_reason": row.get("gate_reason"),
                        "hint_prediction_overlap": row.get("hint_prediction_overlap"),
                    }
                )
    return {
        "name": "budgeted_query_audio_gate_selector",
        "source_selector": str(selector_path),
        "summary": selector.get("selections", []),
        "per_condition": per_dataset,
        "taxonomy": {
            "accepted_pattern": "different semantic tasks need different cheap audio triggers",
            "remaining_risk": "QA gate can regress when audio branch selects a plausible but wrong memory",
            "accepted_mitigation": "budgeted accept gate plus regression audit; keep task-level rather than universal gate",
        },
        "examples": cases,
    }


def classify_covost_regression(row: dict[str, Any]) -> str:
    base = str(row.get("top_text") or "")
    target = str(row.get("target_text") or "")
    selected = str(row.get("low_margin_verifier", {}).get("selected_candidate") or "")
    if selected and target and selected.lower() != target.lower():
        if any(token in selected.lower() for token in ("matter", "problem", "homework", "finished")):
            return "semantic_neighbor_translation"
        return "translation_style_or_boundary_conflict"
    if base and target and base.lower() != target.lower():
        return "base_wrong_verifier_failed_to_rescue"
    return "verifier_regression"


def covost_verifier_cases(path: Path, max_cases: int) -> dict[str, Any]:
    data = read_json(path)
    regressions = []
    fixes = []
    for row in data.get("rows", []):
        verifier = row.get("low_margin_verifier", {})
        base_hit = bool(verifier.get("base_hit_at_1", row.get("sample_hit_at_1")))
        hit = bool(row.get("hit_at_1"))
        if base_hit and not hit and len(regressions) < max_cases:
            regressions.append(
                {
                    "case_type": classify_covost_regression(row),
                    "sample_id": row.get("sample_id"),
                    "query_text": short(row.get("query_text"), 120),
                    "target_text": row.get("target_text"),
                    "base_prediction": verifier.get("base_prediction") or row.get("top_text"),
                    "selected_candidate": verifier.get("selected_candidate"),
                    "selected_choice": verifier.get("selected_choice"),
                    "reason": short(verifier.get("detail", {}).get("reason"), 220),
                    "margin": verifier.get("margin"),
                }
            )
        if (not base_hit) and hit and len(fixes) < max_cases:
            fixes.append(
                {
                    "case_type": "low_margin_fix",
                    "sample_id": row.get("sample_id"),
                    "target_text": row.get("target_text"),
                    "base_prediction": verifier.get("base_prediction") or row.get("top_text"),
                    "selected_candidate": verifier.get("selected_candidate"),
                    "reason": short(verifier.get("detail", {}).get("reason"), 220),
                    "margin": verifier.get("margin"),
                }
            )
    return {
        "name": "covost2_ar_low_margin_verifier",
        "source": str(path),
        "summary": {
            "n": data.get("sample_count"),
            "raw_acc": data.get("base_metrics", {}).get("accuracy_at_1"),
            "policy_acc": data.get("metrics", {}).get("accuracy_at_1"),
            "delta": data.get("delta", {}).get("accuracy_at_1"),
            "ci95": data.get("delta", {}).get("ci95"),
            "route_rate": data.get("route_rate"),
            "fixes": data.get("fix_count"),
            "regressions": data.get("regression_count"),
        },
        "taxonomy": {
            "main_fix_mode": "low-margin top-3 contains the exact target and the verifier resolves near-translation ambiguity",
            "main_regression_mode": "verifier sometimes prefers a semantically plausible or more idiomatic translation over the dataset target",
            "accepted_mitigation": "report regression count; use conservative prompts and keep paired regression gate",
        },
        "regression_examples": regressions,
        "fix_examples": fixes,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Issue 011: Regression And Bad-Case Taxonomy For Accepted Controllers",
        "",
        "This appendix summarizes remaining failures for accepted training-free",
        "controllers.  It is generated from row-level result artifacts and is meant",
        "to support paper writing, not to introduce new model runs.",
        "",
    ]
    for section in payload["sections"]:
        lines.extend(["## " + section["name"], ""])
        summary = section.get("summary", {})
        if isinstance(summary, dict):
            for key, value in summary.items():
                lines.append(f"- `{key}`: {value}")
        elif isinstance(summary, list):
            for item in summary:
                if isinstance(item, dict):
                    label = item.get("dataset") or item.get("name") or "item"
                    details = ", ".join(f"{key}={value}" for key, value in item.items() if key != "dataset")
                    lines.append(f"- `{label}`: {details}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(f"- {summary}")
        lines.append("")
        taxonomy = section.get("taxonomy", {})
        if taxonomy:
            lines.append("Taxonomy:")
            for key, value in taxonomy.items():
                lines.append(f"- `{key}`: {value}")
            lines.append("")
        examples = section.get("examples") or section.get("regression_examples") or []
        if examples:
            lines.append("Representative cases:")
            for item in examples[:8]:
                label = item.get("query_id") or item.get("sample_id")
                lines.append(f"- `{label}`: `{item.get('case_type')}`")
                for key, value in item.items():
                    if key in {"query_id", "sample_id", "case_type"}:
                        continue
                    lines.append(f"  - `{key}`: {short(value, 180)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    sections = [
        heysquad_packed_cases(args.heysquad_original, args.heysquad_packed, args.max_cases),
        gate_selector_cases(args.gate_selector, args.gate_reports, args.max_cases),
        covost_verifier_cases(args.covost_verifier, args.max_cases),
    ]
    payload = {
        "experiment": "failure_taxonomy_export",
        "sections": sections,
    }
    write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--heysquad-original",
        type=Path,
        default=Path("outputs/omni_memory_v0/heysquad_retrieval_raw_top5_use_gemma4e4b_server_200.json"),
    )
    parser.add_argument(
        "--heysquad-packed",
        type=Path,
        default=Path("outputs/omni_memory_v0/heysquad_retrieval_raw_top5_packed_use_gemma4e4b_server_200.json"),
    )
    parser.add_argument(
        "--gate-selector",
        type=Path,
        default=Path("outputs/query_audio_gate_selector_summary.json"),
    )
    parser.add_argument(
        "--gate-report",
        dest="gate_reports",
        action="append",
        type=Path,
        default=[
            Path("outputs/omni_memory_v0/query_audio_gate_covost2_clean_manifest_200.json"),
            Path("outputs/omni_memory_v0/query_audio_gate_covost2_neighbor_text_manifest_60.json"),
            Path("outputs/omni_memory_v0/query_audio_gate_minds14_clean_manifest_180.json"),
            Path("outputs/omni_memory_v0/query_audio_gate_minds14_neighbor_text_manifest_60.json"),
            Path("outputs/omni_memory_v0/query_audio_gate_heysquad_clean_manifest_200.json"),
            Path("outputs/omni_memory_v0/query_audio_gate_heysquad_natural_drift_manifest_60.json"),
        ],
    )
    parser.add_argument(
        "--covost-verifier",
        type=Path,
        default=Path("outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json"),
    )
    parser.add_argument("--output-json", type=Path, default=Path("outputs/failure_taxonomy_summary.json"))
    parser.add_argument("--output-md", type=Path, default=Path("docs/bugs/issue-011-regression-taxonomy.md"))
    parser.add_argument("--max-cases", type=int, default=8)
    return parser


def main() -> None:
    payload = run(build_parser().parse_args())
    print(json.dumps({"sections": [section["name"] for section in payload["sections"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
