"""Build paper-ready low-margin verifier cost-curve summaries.

The script is offline: it consumes existing ablation and deployed verifier
JSON files, then writes a compact Markdown table and a machine-readable JSON
summary.  It is meant to support the claim that margin routing is a useful
cost/utility signal, not merely a hand-picked threshold.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    ablation: Path
    llm: Path | None = None
    llms: tuple[Path, ...] = ()


DEFAULT_DATASETS = [
    DatasetSpec(
        name="MInDS intent 180",
        ablation=Path("outputs/low_margin_verifier/ablation_minds14_top3.json"),
        llm=Path("outputs/low_margin_verifier/minds_llm_top3_tau0p02.json"),
    ),
    DatasetSpec(
        name="CoVoST2 ar->en 200",
        ablation=Path("outputs/low_margin_verifier/ablation_covost2_ar_top3.json"),
        llm=Path("outputs/low_margin_verifier/covost_ar_llm_top3_tau0p02.json"),
    ),
    DatasetSpec(
        name="CoVoST2 zh-CN->en 200",
        ablation=Path("outputs/low_margin_verifier/ablation_covost2_zh_top3.json"),
        llm=Path("outputs/low_margin_verifier/covost_zh_llm_top3_tau0p0206.json"),
    ),
    DatasetSpec(
        name="SLURP intent 500",
        ablation=Path("outputs/low_margin_verifier/ablation_slurp_top3_with_llm_cost_curve.json"),
        llms=(
            Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p01.json"),
            Path("outputs/low_margin_verifier/slurp_llm_top3_tau0p02.json"),
        ),
    ),
    DatasetSpec(
        name="CoVoST2 ar->en validation full",
        ablation=Path("outputs/low_margin_verifier/ablation_covost2_ar_validation_full_sample_top3.json"),
        llm=Path("outputs/low_margin_verifier/covost_ar_validation_full_llm_top3_tau0p02_resumable.json"),
    ),
    DatasetSpec(
        name="CoVoST2 ar->en locked test full",
        ablation=Path("outputs/low_margin_verifier/ablation_covost2_ar_test_full_sample_top3.json"),
        llm=Path("outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json"),
    ),
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = row
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def fmt_delta(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):+.3f}"


def fmt_ci(value: Any) -> str:
    if not isinstance(value, list) or len(value) != 2:
        return "n/a"
    return f"[{float(value[0]):.3f}, {float(value[1]):.3f}]"


def threshold_from_policy(policy: str) -> str:
    match = re.search(r"tau=([0-9.]+)", policy)
    return match.group(1) if match else "n/a"


def find_policy(summaries: list[dict[str, Any]], policy: str) -> dict[str, Any] | None:
    for row in summaries:
        if row.get("policy") == policy:
            return row
    return None


def low_margin_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    summaries = report.get("summaries", [])
    random_by_tau = {
        threshold_from_policy(row.get("policy", "")): row
        for row in summaries
        if str(row.get("policy", "")).startswith("oracle_random_same_rate")
    }
    for row in summaries:
        policy = str(row.get("policy", ""))
        if not policy.startswith("oracle_low_margin"):
            continue
        tau = threshold_from_policy(policy)
        random_row = random_by_tau.get(tau)
        rows.append(
            {
                "threshold": tau,
                "route_rate": row.get("route_rate"),
                "oracle_acc": metric(row, "metrics", "accuracy_at_1"),
                "oracle_delta": metric(row, "delta", "accuracy_at_1"),
                "oracle_ci95": metric(row, "delta", "ci95"),
                "oracle_fixes": row.get("fix_count"),
                "random_acc": metric(random_row or {}, "metrics", "accuracy_at_1"),
                "random_delta": metric(random_row or {}, "delta", "accuracy_at_1"),
            }
        )
    return rows


def deployed_row(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    report = read_json(path)
    return {
        "source": str(path),
        "n": report.get("sample_count"),
        "raw_acc": metric(report, "base_metrics", "accuracy_at_1"),
        "policy_acc": metric(report, "metrics", "accuracy_at_1"),
        "delta": metric(report, "delta", "accuracy_at_1"),
        "ci95": metric(report, "delta", "ci95"),
        "route_rate": report.get("route_rate"),
        "fixes": report.get("fix_count"),
        "regressions": report.get("regression_count"),
    }


def summarize_dataset(spec: DatasetSpec) -> dict[str, Any]:
    report = read_json(spec.ablation)
    summaries = report.get("summaries", [])
    raw = find_policy(summaries, "raw") or {}
    always = find_policy(summaries, f"oracle_always_top{report.get('top_k', 3)}") or {}
    llm_paths = list(spec.llms)
    if spec.llm is not None:
        llm_paths.append(spec.llm)
    return {
        "dataset": spec.name,
        "source": str(spec.ablation),
        "n": report.get("sample_count") or metric(raw, "sample_count"),
        "raw_acc": metric(raw, "metrics", "accuracy_at_1"),
        "raw_r3": metric(raw, "base_metrics", "recall_at_3"),
        "always_topk_acc": metric(always, "metrics", "accuracy_at_1"),
        "always_topk_delta": metric(always, "delta", "accuracy_at_1"),
        "thresholds": low_margin_rows(report),
        "deployed_llms": [row for path in llm_paths if (row := deployed_row(path))],
    }


def markdown_table(summary: dict[str, Any]) -> str:
    lines = []
    for dataset in summary["datasets"]:
        lines.append(f"## {dataset['dataset']}")
        lines.append("")
        lines.append(
            f"Raw Acc@1: `{fmt(dataset['raw_acc'])}`; "
            f"raw R@3: `{fmt(dataset['raw_r3'])}`; "
            f"always-top-k oracle Acc@1: `{fmt(dataset['always_topk_acc'])}` "
            f"({fmt_delta(dataset['always_topk_delta'])})."
        )
        lines.append("")
        lines.append(
            "| Tau | Route | Oracle Acc@1 | Oracle Delta | Oracle CI95 | "
            "Oracle Fixes | Random Same-Rate Acc@1 | Random Delta |"
        )
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in dataset["thresholds"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["threshold"],
                        fmt(row["route_rate"]),
                        fmt(row["oracle_acc"]),
                        fmt_delta(row["oracle_delta"]),
                        fmt_ci(row["oracle_ci95"]),
                        fmt(row["oracle_fixes"], 0),
                        fmt(row["random_acc"]),
                        fmt_delta(row["random_delta"]),
                    ]
                )
                + " |"
            )
        deployed_rows = dataset.get("deployed_llms") or []
        if deployed_rows:
            lines.append("")
            lines.append(
                "| Deployed verifier | N | Route | Acc@1 | Delta | CI95 | Fixes | Regressions |"
            )
            lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
            for deployed in deployed_rows:
                label = Path(str(deployed["source"])).stem
                lines.append(
                    f"| LLM low-margin top-k ({label}) | "
                    + " | ".join(
                        [
                            fmt(deployed["n"], 0),
                            fmt(deployed["route_rate"]),
                            fmt(deployed["policy_acc"]),
                            fmt_delta(deployed["delta"]),
                            fmt_ci(deployed["ci95"]),
                            fmt(deployed["fixes"], 0),
                            fmt(deployed["regressions"], 0),
                        ]
                    )
                    + " |"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/low_margin_cost_curve_summary.json"))
    parser.add_argument("--output-md", type=Path, default=Path("docs/low_margin_cost_curve.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = {
        "experiment": "low_margin_cost_curve_summary",
        "datasets": [summarize_dataset(spec) for spec in DEFAULT_DATASETS if spec.ablation.exists()],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        "# Low-Margin Verifier Cost Curve\n\n"
        "Last updated: 2026-07-03\n\n"
        "This page is generated from existing ablation and verifier outputs.  It "
        "shows the cost/utility trade-off for low-margin top-k verification and "
        "the random same-rate controls used to justify margin as a routing "
        "signal.\n\n"
        "Generated by:\n\n"
        "```text\n"
        "python scripts/build_low_margin_cost_curve.py\n"
        "```\n\n"
        + markdown_table(payload),
        encoding="utf-8",
    )
    print(json.dumps({"datasets": len(payload["datasets"]), "output_md": str(args.output_md)}, indent=2))


if __name__ == "__main__":
    main()
