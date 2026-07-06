"""Build a runtime latency/cost summary from existing memory-use outputs.

This script is offline: it reads existing JSON results and does not call any
model or API.  It focuses on practical runtime evidence for the paper:

- candidate audio memory can increase latency/cost while hurting success;
- evidence packing can improve success while reducing text budget and latency;
- the partial larger-backend reference is currently too slow and inaccurate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


OMNI_DIR = Path("outputs/omni_memory_v0")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_metrics(path: Path) -> dict[str, Any]:
    data = read_json(path)
    return {
        "path": str(path).replace("\\", "/"),
        "n": data.get("n"),
        "success": data.get("task_success"),
        "wrong_memory": data.get("wrong_memory"),
        "invalid_output": data.get("invalid_output"),
        "mean_text_cost": data.get("mean_text_cost"),
        "mean_audio_cost": data.get("mean_audio_cost"),
        "mean_latency_ms": data.get("mean_latency_ms"),
        "regressions": data.get("regression_count"),
    }


def compare(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    def delta(key: str) -> float | None:
        cand = candidate.get(key)
        base = baseline.get(key)
        if cand is None or base is None:
            return None
        return float(cand) - float(base)

    latency = candidate.get("mean_latency_ms")
    base_latency = baseline.get("mean_latency_ms")
    latency_ratio = None
    if isinstance(latency, (int, float)) and isinstance(base_latency, (int, float)) and base_latency:
        latency_ratio = float(latency) / float(base_latency)

    return {
        "success_delta": delta("success"),
        "text_cost_delta": delta("mean_text_cost"),
        "audio_cost_delta": delta("mean_audio_cost"),
        "latency_delta_ms": delta("mean_latency_ms"),
        "latency_ratio": latency_ratio,
    }


def candidate_audio_rows(dataset: str, baseline_file: str, candidate_files: list[tuple[str, str]]) -> list[dict[str, Any]]:
    baseline = run_metrics(OMNI_DIR / baseline_file)
    rows = []
    for policy, file_name in candidate_files:
        candidate = run_metrics(OMNI_DIR / file_name)
        rows.append(
            {
                "component": "candidate_audio_memory",
                "dataset": dataset,
                "baseline_policy": "text memory + query audio",
                "policy": policy,
                "baseline": baseline,
                "candidate": candidate,
                "delta": compare(candidate, baseline),
                "decision": "rejected_costly_regression",
            }
        )
    return rows


def heysquad_packing_rows() -> list[dict[str, Any]]:
    original = run_metrics(OMNI_DIR / "heysquad_retrieval_raw_top5_use_gemma4e4b_server_200.json")
    packed = run_metrics(OMNI_DIR / "heysquad_retrieval_raw_top5_packed_use_gemma4e4b_server_200.json")
    pg_original = run_metrics(OMNI_DIR / "heysquad_retrieval_policy_grounding_top5_use_gemma4e4b_server_200.json")
    pg_packed = run_metrics(OMNI_DIR / "heysquad_retrieval_policy_grounding_top5_packed_use_gemma4e4b_server_200.json")
    return [
        {
            "component": "memory_packing_runtime",
            "dataset": "HeySQuAD retrieval-to-use",
            "baseline_policy": "raw top-5 memory cards",
            "policy": "answer/evidence packed cards",
            "baseline": original,
            "candidate": packed,
            "delta": compare(packed, original),
            "decision": "accepted_win_win_quality_and_cost",
        },
        {
            "component": "memory_packing_runtime",
            "dataset": "HeySQuAD retrieval-to-use",
            "baseline_policy": "policy_grounding top-5 memory cards",
            "policy": "policy_grounding packed cards",
            "baseline": pg_original,
            "candidate": pg_packed,
            "delta": compare(pg_packed, pg_original),
            "decision": "accepted_cost_reduction_but_no_policy_gain",
        },
    ]


def backend_reference_row() -> dict[str, Any]:
    data = read_json(OMNI_DIR / "summary_gemma12b_partial_covost2_vs_e4b.json")
    summaries = {item["label"]: item for item in data["summaries"]}
    e4b = summaries["e4b"]
    large = summaries["gemma12b_partial"]
    paired = data["paired"][0]
    latency_ratio = large["mean_latency_ms"] / e4b["mean_latency_ms"]
    return {
        "component": "cross_model_backend_runtime",
        "dataset": "CoVoST2 ar->en partial backend check",
        "baseline_policy": "Gemma 4 E4B",
        "policy": "Gemma 4 12B partial",
        "baseline": {
            "n": e4b["n"],
            "success": e4b["success"],
            "mean_text_cost": e4b["mean_text_cost"],
            "mean_audio_cost": e4b["mean_audio_cost"],
            "mean_latency_ms": e4b["mean_latency_ms"],
        },
        "candidate": {
            "n": large["n"],
            "success": large["success"],
            "mean_text_cost": large["mean_text_cost"],
            "mean_audio_cost": large["mean_audio_cost"],
            "mean_latency_ms": large["mean_latency_ms"],
        },
        "delta": {
            "success_delta": paired["delta"],
            "ci95": paired["ci95"],
            "regressions": paired["regressions"],
            "latency_ratio": latency_ratio,
            "latency_delta_ms": large["mean_latency_ms"] - e4b["mean_latency_ms"],
        },
        "decision": "rejected_backend_reference",
    }


def build_summary() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        candidate_audio_rows(
            "CoVoST2 ar->en fixed-candidate memory use",
            "covost2_ar_en_text_summary_query_hint_gemma4e4b_server_200.json",
            [
                ("candidate audio limit=1", "covost2_dual_audio_limit1_query_hint_gemma4e4b_server_200.json"),
                ("candidate audio limit=2", "covost2_dual_audio_limit2_query_hint_gemma4e4b_server_200.json"),
                ("full candidate audio", "covost2_dual_audio_full_query_hint_gemma4e4b_server_200.json"),
            ],
        )
    )
    rows.extend(
        candidate_audio_rows(
            "MInDS fixed-candidate tool memory use",
            "minds14_text_summary_query_hint_gemma4e4b_server_180.json",
            [
                ("candidate audio limit=1", "minds14_dual_audio_limit1_query_hint_gemma4e4b_server_180.json"),
                ("candidate audio limit=2", "minds14_dual_audio_limit2_query_hint_gemma4e4b_server_180.json"),
                ("full candidate audio", "minds14_dual_audio_full_query_hint_gemma4e4b_server_180.json"),
            ],
        )
    )
    rows.extend(heysquad_packing_rows())
    rows.append(backend_reference_row())

    return {
        "experiment": "runtime_latency_summary",
        "note": "Offline runtime/cost synthesis from existing memory-use outputs; no model/API calls.",
        "row_count": len(rows),
        "rows": rows,
        "takeaways": [
            "Candidate audio memory is a costly negative baseline for semantic memory use.",
            "HeySQuAD evidence packing is a win-win: higher success with lower text budget and lower latency.",
            "The partial larger-backend reference is slower and less accurate, so it remains a diagnostic blocker.",
        ],
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Runtime Latency And Cost Summary",
        "",
        "Last updated: 2026-07-03",
        "",
        "This offline summary consolidates runtime-like fields already present in",
        "memory-use row-level outputs.  It does not call models or APIs.",
        "",
        "Generated by:",
        "",
        "```text",
        "python scripts/build_runtime_latency_summary.py",
        "```",
        "",
        "## Summary Table",
        "",
        "| Component | Dataset | Policy | Success delta | Text cost delta | Audio cost delta | Latency ratio | Decision |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in summary["rows"]:
        delta = row["delta"]
        lines.append(
            "| {component} | {dataset} | {policy} | {success_delta} | {text_delta} | {audio_delta} | {latency_ratio} | {decision} |".format(
                component=row["component"],
                dataset=row["dataset"],
                policy=row["policy"],
                success_delta=format_number(delta.get("success_delta")),
                text_delta=format_number(delta.get("text_cost_delta")),
                audio_delta=format_number(delta.get("audio_cost_delta")),
                latency_ratio=format_number(delta.get("latency_ratio")),
                decision=row["decision"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Candidate audio memory is not a free semantic signal.  On CoVoST2 and",
            "  MInDS, adding more candidate audio increases latency/audio cost while",
            "  reducing memory-use success.",
            "- HeySQuAD packing is the cleanest runtime-positive intervention: it",
            "  improves memory-use success and reduces prompt text budget and mean",
            "  latency.",
            "- The partial larger-backend reference should stay out of main claims: it",
            "  is slower and less accurate on the completed subset.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def format_number(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/runtime_latency_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/runtime_latency_summary.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_summary()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown, summary)
    print(json.dumps({"row_count": summary["row_count"], "output": str(args.output), "markdown": str(args.markdown)}, indent=2))


if __name__ == "__main__":
    main()
