"""Build a deployability audit for query-audio gates.

This script is offline: it reads existing clean+stress mixture summaries and
the task-level gate selector output, then writes a compact paper-facing JSON
and Markdown note.

The audit answers a narrower question than the raw gate summary:

* What does the selected deployable gate do on clean rows?
* What does it do on stress/drift rows?
* How much audio cost does it spend compared with full audio?
* Which datasets accept a budgeted gate, and which fall back?
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


def fmt_float(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_delta(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    return f"{number:+.{digits}f}"


def fmt_ci(ci95: Any) -> str:
    if not isinstance(ci95, list) or len(ci95) != 2:
        return "n/a"
    return f"[{fmt_float(ci95[0])}, {fmt_float(ci95[1])}]"


def by_dataset_gate(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("dataset")), str(row.get("gate"))): row
        for row in rows
    }


def build_rows(selector: dict[str, Any], mixture: dict[str, Any]) -> list[dict[str, Any]]:
    mixture_rows = by_dataset_gate(mixture.get("rows", []))
    rows: list[dict[str, Any]] = []
    for selection in selector.get("selections", []):
        dataset = str(selection.get("dataset"))
        selected_gate = str(selection.get("selected_gate"))
        selected = mixture_rows.get((dataset, selected_gate))
        text_baseline = mixture_rows.get((dataset, "audio_on_invalid"))
        full_audio = mixture_rows.get((dataset, "audio_only"))
        if selected is None or text_baseline is None or full_audio is None:
            rows.append(
                {
                    "dataset": dataset,
                    "selected_gate": selected_gate,
                    "decision": "missing_source",
                    "missing_selected": selected is None,
                    "missing_text_baseline": text_baseline is None,
                    "missing_full_audio": full_audio is None,
                }
            )
            continue

        clean_delta = float(selected.get("clean_success", 0.0)) - float(text_baseline.get("clean_success", 0.0))
        stress_delta = float(selected.get("stress_success", 0.0)) - float(text_baseline.get("stress_success", 0.0))
        full_audio_delta = float(full_audio.get("mixed_success", 0.0)) - float(text_baseline.get("mixed_success", 0.0))
        selected_delta = float(selected.get("mixed_success", 0.0)) - float(text_baseline.get("mixed_success", 0.0))
        full_audio_cost = float(full_audio.get("mixed_audio_cost", 1.0))
        selected_audio_cost = float(selected.get("mixed_audio_cost", 0.0))
        cost_reduction = full_audio_cost - selected_audio_cost
        retained_full_audio_gain = selected_delta / full_audio_delta if full_audio_delta > 0 else None

        rows.append(
            {
                "dataset": dataset,
                "decision": selection.get("decision"),
                "selected_gate": selected_gate,
                "text_baseline_success": text_baseline.get("mixed_success"),
                "full_audio_success": full_audio.get("mixed_success"),
                "selected_success": selected.get("mixed_success"),
                "selected_delta_vs_text": selected_delta,
                "selected_ci95": selected.get("ci95"),
                "selected_fixes": selected.get("fixes"),
                "selected_regressions": selected.get("regressions"),
                "selected_regression_rate": selected.get("regression_rate"),
                "clean_text_success": text_baseline.get("clean_success"),
                "clean_selected_success": selected.get("clean_success"),
                "clean_delta_vs_text": clean_delta,
                "stress_text_success": text_baseline.get("stress_success"),
                "stress_selected_success": selected.get("stress_success"),
                "stress_delta_vs_text": stress_delta,
                "full_audio_delta_vs_text": full_audio_delta,
                "retained_full_audio_gain": retained_full_audio_gain,
                "full_audio_cost": full_audio_cost,
                "selected_audio_cost": selected_audio_cost,
                "audio_cost_reduction_vs_full": cost_reduction,
                "audio_cost_reduction_rate": cost_reduction / full_audio_cost if full_audio_cost else None,
                "accepted_candidate_count": selection.get("accepted_count"),
                "candidate_count": selection.get("candidate_count"),
            }
        )
    return rows


def decision_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in rows if row.get("decision") == "accepted"]
    return {
        "dataset_count": len(rows),
        "accepted_count": len(accepted),
        "fallback_count": len(rows) - len(accepted),
        "mean_selected_delta": sum(float(row.get("selected_delta_vs_text", 0.0)) for row in rows) / len(rows)
        if rows
        else 0.0,
        "mean_selected_audio_cost": sum(float(row.get("selected_audio_cost", 0.0)) for row in rows) / len(rows)
        if rows
        else 0.0,
        "mean_audio_cost_reduction_rate": sum(float(row.get("audio_cost_reduction_rate", 0.0)) for row in rows)
        / len(rows)
        if rows
        else 0.0,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Query-Audio Gate Deployability Audit",
        "",
        "Last updated: 2026-07-03",
        "",
        "This note audits the deployability of the selected query-audio gates.",
        "It is generated from existing clean+stress result artifacts and does",
        "not call a model or API.",
        "",
        "Generated by:",
        "",
        "```text",
        "python scripts/build_query_audio_gate_deployability_summary.py",
        "```",
        "",
        "## Summary",
        "",
    ]
    summary = payload["summary"]
    lines.extend(
        [
            f"- Accepted datasets: {summary['accepted_count']} / {summary['dataset_count']}.",
            f"- Mean selected delta vs text-only: {fmt_delta(summary['mean_selected_delta'])}.",
            f"- Mean selected audio cost: {fmt_float(summary['mean_selected_audio_cost'])}.",
            f"- Mean audio-cost reduction vs full audio: {fmt_float(summary['mean_audio_cost_reduction_rate'])}.",
            "",
            "## Deployability Table",
            "",
            "| Dataset | Text Baseline | Full Audio | Selected Gate | Selected | Delta | CI95 | Clean Delta | Stress Delta | Audio Cost | Cost Reduction | Fix / Regression | Decision |",
            "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in payload["rows"]:
        lines.append(
            "| {dataset} | {text} | {full_audio} | `{gate}` | {selected} | {delta} | {ci} | {clean_delta} | {stress_delta} | {cost} | {cost_reduction} | {fixes} / {regs} | {decision} |".format(
                dataset=row.get("dataset"),
                text=fmt_float(row.get("text_baseline_success")),
                full_audio=fmt_float(row.get("full_audio_success")),
                gate=row.get("selected_gate"),
                selected=fmt_float(row.get("selected_success")),
                delta=fmt_delta(row.get("selected_delta_vs_text")),
                ci=fmt_ci(row.get("selected_ci95")),
                clean_delta=fmt_delta(row.get("clean_delta_vs_text")),
                stress_delta=fmt_delta(row.get("stress_delta_vs_text")),
                cost=fmt_float(row.get("selected_audio_cost")),
                cost_reduction=fmt_float(row.get("audio_cost_reduction_rate")),
                fixes=row.get("selected_fixes"),
                regs=row.get("selected_regressions"),
                decision=row.get("decision"),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The accepted gates are deployable in the narrow sense used here: they use",
            "  only interface-level signals such as text/audio disagreement, selected",
            "  candidate overlap, or no-query equivalence. They do not inspect gold",
            "  labels at decision time.",
            "- Full audio remains a useful upper-bound baseline, but the selected gates",
            "  recover much of its stress benefit with substantially lower audio cost.",
            "- Clean rows are not the target of this component. The paper should frame",
            "  query audio as a selective rescue channel for text drift or ASR collapse,",
            "  not as a default memory format.",
            "",
            "## Paper Use",
            "",
            "Use this table when defending the claim that the controller decides when",
            "audio is worth paying for. It should be cited with:",
            "",
            "```text",
            "docs/controller_cost_budget.md",
            "docs/cost_failure_table.md",
            "docs/dialect_route_table.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build(args: argparse.Namespace) -> dict[str, Any]:
    selector = read_json(args.selector)
    mixture = read_json(args.mixture)
    rows = build_rows(selector, mixture)
    payload = {
        "experiment": "query_audio_gate_deployability_summary",
        "selector": str(args.selector),
        "mixture": str(args.mixture),
        "summary": decision_summary(rows),
        "rows": rows,
    }
    write_json(args.output, payload)
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector", type=Path, default=Path("outputs/query_audio_gate_selector_summary.json"))
    parser.add_argument("--mixture", type=Path, default=Path("outputs/query_audio_gate_mixture_extended_summary.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/query_audio_gate_deployability_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/query_audio_gate_deployability.md"))
    return parser


def main() -> None:
    print(json.dumps(build(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
