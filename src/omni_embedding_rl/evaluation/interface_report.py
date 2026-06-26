"""Layer-wise effect reports for the semantic interface controller.

The report consumes already generated selector/stability JSON outputs.  It does
not run models and does not train weights.  Its job is attribution: make clear
which layer produced a gain and whether the gain is accepted, diagnostic, or
rejected.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EffectReportConfig:
    entries: Path
    output: Path
    csv_output: Path | None = None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fmt_float(value: Any, digits: int = 4) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def summarize_stability(report: dict[str, Any]) -> dict[str, Any]:
    selected = report.get("selected")
    leaderboard = report.get("leaderboard", [])
    top = selected or (leaderboard[0] if leaderboard else {})
    return {
        "source_type": "stability",
        "decision": report.get("decision", ""),
        "selected_action": top.get("name", ""),
        "selection_rate": top.get("selection_rate", ""),
        "locked_pass_rate": top.get("locked_pass_rate", ""),
        "delta": top.get("mean_locked_delta", ""),
        "lcb": top.get("mean_locked_lcb", ""),
        "regression_rate": top.get("mean_locked_regression_rate", ""),
        "reject_reasons": ";".join(top.get("reject_reasons", [])),
    }


def summarize_selector(report: dict[str, Any]) -> dict[str, Any]:
    selected = report.get("selected_locked_test", {})
    diagnostic = report.get("diagnostic_candidate_by_selection") or {}
    action = selected.get("name", "")
    if action == report.get("config", {}).get("baseline") and diagnostic:
        action = diagnostic.get("name", action)
    return {
        "source_type": "selector",
        "decision": report.get("decision", ""),
        "selected_action": action,
        "selection_rate": "",
        "locked_pass_rate": 1.0 if report.get("locked_test_gate_passed") else 0.0,
        "delta": selected.get("hit_delta", ""),
        "lcb": selected.get("hit_lcb", ""),
        "regression_rate": selected.get("regression_rate", ""),
        "reject_reasons": ";".join(selected.get("reject_reasons", [])),
    }


def summarize_result(path: Path) -> dict[str, Any]:
    report = read_json(path)
    experiment = report.get("experiment", "")
    if experiment == "task_level_selector_stability":
        return summarize_stability(report)
    if experiment == "task_level_omni_policy_selector":
        return summarize_selector(report)
    return {
        "source_type": experiment or "unknown",
        "decision": report.get("decision", ""),
        "selected_action": "",
        "selection_rate": "",
        "locked_pass_rate": "",
        "delta": "",
        "lcb": "",
        "regression_rate": "",
        "reject_reasons": "",
    }


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    path_text = entry.get("path", "")
    if "manual" in entry:
        manual = entry["manual"]
        summary = {
            "source_type": "manual",
            "decision": manual.get("decision", ""),
            "selected_action": manual.get("selected_action", ""),
            "selection_rate": manual.get("selection_rate", ""),
            "locked_pass_rate": manual.get("locked_pass_rate", ""),
            "delta": manual.get("delta", ""),
            "lcb": manual.get("lcb", ""),
            "regression_rate": manual.get("regression_rate", ""),
            "reject_reasons": manual.get("reject_reasons", ""),
        }
    else:
        path = Path(path_text)
        summary = summarize_result(path)
    return {
        "task": entry.get("task", ""),
        "dataset": entry.get("dataset", ""),
        "model": entry.get("model", ""),
        "layer": entry.get("layer", ""),
        "policy_family": entry.get("policy_family", ""),
        "source": path_text,
        "claim_level": entry.get("claim_level", ""),
        **summary,
        "notes": entry.get("notes", ""),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = [
        "Task",
        "Dataset",
        "Model",
        "Layer",
        "Policy",
        "Decision",
        "Action",
        "Delta",
        "LCB",
        "Reg.",
        "Claim",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        values = [
            row["task"],
            row["dataset"],
            row["model"],
            row["layer"],
            row["policy_family"],
            row["decision"],
            row["selected_action"],
            fmt_float(row["delta"]),
            fmt_float(row["lcb"]),
            fmt_float(row["regression_rate"]),
            row["claim_level"],
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def render_markdown(rows: list[dict[str, Any]], config: EffectReportConfig) -> str:
    accepted = [
        row
        for row in rows
        if row["decision"] == "accepted" or row["claim_level"].startswith("accepted")
    ]
    rejected = [row for row in rows if "reject" in row["claim_level"] or row["decision"] == "no_stable_policy"]
    layers = sorted({row["layer"] for row in rows})
    layer_counts = [f"{layer}: {sum(1 for row in rows if row['layer'] == layer)}" for layer in layers]
    lines = [
        "# V3 Semantic Interface Effect Report",
        "",
        "This report attributes gains by controller layer.  It consumes already",
        "generated selector/stability outputs and does not run models.",
        "",
        "## Summary",
        "",
        f"- Entries: {len(rows)}",
        f"- Accepted / positive entries: {len(accepted)}",
        f"- Rejected / fallback entries: {len(rejected)}",
        f"- Layer counts: {', '.join(layer_counts)}",
        "",
        "## Layer-Wise Table",
        "",
        markdown_table(rows),
        "",
        "## Interpretation Rules",
        "",
        "- `omni-side` rows are evidence about how to use the frozen omni model.",
        "- `system-side` rows are useful controller gains, but not model-side gains.",
        "- `hybrid-route` and `downstream` rows are end-task reliability policies.",
        "- A diagnostic or underpowered row should not be reported as accepted.",
        "",
        "## Source",
        "",
        f"- Entry manifest: `{config.entries}`",
    ]
    return "\n".join(lines) + "\n"


def run(config: EffectReportConfig) -> dict[str, Any]:
    entries = read_json(config.entries)
    if not isinstance(entries, list):
        raise ValueError("Entries file must contain a JSON list.")
    rows = [normalize_entry(entry) for entry in entries]
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(render_markdown(rows, config), encoding="utf-8")
    csv_path = config.csv_output or config.output.with_suffix(".csv")
    write_csv(csv_path, rows)
    return {
        "experiment": "semantic_interface_effect_report",
        "config": asdict(config)
        | {
            "entries": str(config.entries),
            "output": str(config.output),
            "csv_output": str(csv_path),
        },
        "row_count": len(rows),
        "csv_output": str(csv_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--csv-output", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(run(EffectReportConfig(**vars(args))), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
