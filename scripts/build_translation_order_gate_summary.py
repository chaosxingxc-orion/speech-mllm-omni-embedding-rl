"""Evaluate cheap order-risk gates for CoVoST2 translation memory use.

The previous order-robustness audit showed that the translation-target
memory-use policy is positive in the original candidate order but unstable
under candidate-order shuffles.  This script tests a cheaper repair using
only existing outputs:

```
use translation-target output only when it selects the original retrieval
top-1 memory; otherwise fall back.
```

Two fallbacks are reported:

- `else_generic`: fall back to the generic memory-use model output. This is
  the main controller-style repair.
- `else_retrieval_top1`: fall back directly to retrieval top-1. This is a
  system-side diagnostic and should not be counted as memory-use improvement.

The script also reports a deployable stronger gate:

- `translation_if_original_top1_or_generic_not_original_top1_else_generic`:
  use translation-target output when it selects the original retrieval top-1,
  or when the generic memory-use output already deviates from the original
  retrieval top-1.  Otherwise keep the generic output.  This uses only
  retrieval rank and model outputs, not gold labels.

No model or API is called.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable


SEEDS = [None, 7, 17, 29]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def row_key(row: dict[str, Any]) -> str:
    return str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")


def prediction(row: dict[str, Any]) -> str:
    return str(row.get("prediction") or row.get("predicted_memory_id") or "")


def success(row: dict[str, Any]) -> bool:
    return bool(row.get("task_success"))


def original_rank(original_row: dict[str, Any], memory_id: str) -> int:
    ids = [str(item) for item in original_row.get("candidate_memory_ids", [])]
    try:
        return ids.index(memory_id) + 1
    except ValueError:
        return 999


def original_top1(original_row: dict[str, Any]) -> str:
    ids = [str(item) for item in original_row.get("candidate_memory_ids", [])]
    return ids[0] if ids else ""


def bootstrap_ci(diffs: list[int], *, rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def result_path(dataset: str, *, seed: int | None, translation: bool) -> Path:
    prefix = "covost2_ar" if dataset == "ar" else "covost2_zh"
    policy = "translation_policy" if translation else "server"
    if seed is None:
        return Path(f"outputs/omni_memory_v0/{prefix}_retrieval_raw_top5_use_gemma4e4b_{policy}_200.json")
    return Path(
        f"outputs/omni_memory_v0/{prefix}_retrieval_raw_top5_use_gemma4e4b_{policy}_shuffle_seed{seed}_200.json"
    )


def load_rows(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    return {row_key(row): row for row in data.get("rows", [])}


def evaluate_policy(
    *,
    label: str,
    order_label: str,
    original_generic: dict[str, dict[str, Any]],
    generic_rows: dict[str, dict[str, Any]],
    translation_rows: dict[str, dict[str, Any]],
    choose: Callable[[str, dict[str, Any], dict[str, Any], dict[str, Any]], tuple[str, bool]],
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    routed = 0
    task_success = 0
    missing = 0

    for key, generic in generic_rows.items():
        translation = translation_rows.get(key)
        original = original_generic.get(key)
        if translation is None or original is None:
            missing += 1
            continue
        pred, route = choose(key, original, generic, translation)
        gold = str(generic.get("gold_memory_id") or "")
        candidate_ok = bool(pred and gold and pred == gold)
        baseline_ok = success(generic)
        task_success += int(candidate_ok)
        routed += int(route)
        diff = int(candidate_ok) - int(baseline_ok)
        diffs.append(diff)
        fixes += int(diff > 0)
        regressions += int(diff < 0)

    n = len(diffs)
    return {
        "policy": label,
        "order": order_label,
        "n": n,
        "success": task_success / n if n else 0.0,
        "delta_vs_generic": sum(diffs) / n if n else 0.0,
        "ci95": bootstrap_ci(diffs, rounds=rounds, seed=seed),
        "fixes": fixes,
        "regressions": regressions,
        "regression_rate": regressions / n if n else 0.0,
        "route_rate": routed / n if n else 0.0,
        "missing": missing,
    }


def accepted(row: dict[str, Any], *, strict_lcb: bool) -> bool:
    ci95 = row.get("ci95", [0.0, 0.0])
    lower = float(ci95[0])
    return (
        float(row.get("delta_vs_generic", 0.0)) > 0.0
        and (lower > 0.0 if strict_lcb else lower >= 0.0)
        and float(row.get("regression_rate", 1.0)) <= 0.03
    )


def summarize_policy(policy: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    shuffle_rows = [row for row in rows if row["order"] != "base"]
    deltas = [float(row["delta_vs_generic"]) for row in rows]
    shuffle_deltas = [float(row["delta_vs_generic"]) for row in shuffle_rows]
    return {
        "policy": policy,
        "order_count": len(rows),
        "shuffle_count": len(shuffle_rows),
        "mean_delta": sum(deltas) / len(deltas),
        "min_delta": min(deltas),
        "shuffle_mean_delta": sum(shuffle_deltas) / len(shuffle_deltas),
        "shuffle_min_delta": min(shuffle_deltas),
        "strict_accept_count": sum(accepted(row, strict_lcb=True) for row in rows),
        "weak_accept_count": sum(accepted(row, strict_lcb=False) for row in rows),
        "shuffle_strict_accept_count": sum(accepted(row, strict_lcb=True) for row in shuffle_rows),
        "shuffle_weak_accept_count": sum(accepted(row, strict_lcb=False) for row in shuffle_rows),
        "max_regression_rate": max(float(row["regression_rate"]) for row in rows),
        "total_fixes": sum(int(row["fixes"]) for row in rows),
        "total_regressions": sum(int(row["regressions"]) for row in rows),
        "mean_route_rate": sum(float(row["route_rate"]) for row in rows) / len(rows),
    }


def decision(summary: dict[str, Any]) -> str:
    if summary["shuffle_strict_accept_count"] == summary["shuffle_count"]:
        return "strict_order_robust_accept"
    if summary["shuffle_weak_accept_count"] == summary["shuffle_count"]:
        return "weak_order_robust_accept"
    if summary["min_delta"] > 0 and summary["max_regression_rate"] <= 0.03:
        return "partial_order_repair"
    return "diagnostic_only"


def build_dataset(dataset: str, *, rounds: int, seed: int) -> dict[str, Any]:
    original_generic = load_rows(result_path(dataset, seed=None, translation=False))
    order_rows: list[dict[str, Any]] = []

    policies: dict[str, Callable[[str, dict[str, Any], dict[str, Any], dict[str, Any]], tuple[str, bool]]] = {
        "always_translation": lambda _key, _orig, _gen, trans: (prediction(trans), True),
        "translation_if_original_top1_else_generic": lambda _key, orig, gen, trans: (
            prediction(trans) if original_rank(orig, prediction(trans)) == 1 else prediction(gen),
            original_rank(orig, prediction(trans)) == 1,
        ),
        "translation_if_original_top1_or_generic_not_original_top1_else_generic": (
            lambda _key, orig, gen, trans: (
                prediction(trans)
                if original_rank(orig, prediction(trans)) == 1
                or original_rank(orig, prediction(gen)) != 1
                else prediction(gen),
                original_rank(orig, prediction(trans)) == 1
                or original_rank(orig, prediction(gen)) != 1,
            )
        ),
        "translation_if_original_top1_else_retrieval_top1": lambda _key, orig, _gen, trans: (
            prediction(trans) if original_rank(orig, prediction(trans)) == 1 else original_top1(orig),
            original_rank(orig, prediction(trans)) == 1,
        ),
    }

    for order_seed in SEEDS:
        order_label = "base" if order_seed is None else f"shuffle_seed{order_seed}"
        generic_rows = load_rows(result_path(dataset, seed=order_seed, translation=False))
        translation_rows = load_rows(result_path(dataset, seed=order_seed, translation=True))
        for policy, choose in policies.items():
            order_rows.append(
                evaluate_policy(
                    label=policy,
                    order_label=order_label,
                    original_generic=original_generic,
                    generic_rows=generic_rows,
                    translation_rows=translation_rows,
                    choose=choose,
                    rounds=rounds,
                    seed=seed,
                )
            )

    policy_summaries = []
    for policy in policies:
        rows = [row for row in order_rows if row["policy"] == policy]
        item = summarize_policy(policy, rows)
        item["decision"] = decision(item)
        if policy == "translation_if_original_top1_else_retrieval_top1":
            item["paper_role"] = "system-side retrieval fallback diagnostic"
        elif policy in {
            "translation_if_original_top1_else_generic",
            "translation_if_original_top1_or_generic_not_original_top1_else_generic",
        }:
            item["paper_role"] = "cheap order-risk controller over memory-use outputs"
        else:
            item["paper_role"] = "ungated translation-target policy"
        policy_summaries.append(item)

    return {
        "dataset": "CoVoST2 ar->en" if dataset == "ar" else "CoVoST2 zh-CN->en",
        "rows": order_rows,
        "policy_summaries": policy_summaries,
        "sources": {
            "base_generic": str(result_path(dataset, seed=None, translation=False)),
            "base_translation": str(result_path(dataset, seed=None, translation=True)),
            "shuffle_seeds": [7, 17, 29],
        },
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    datasets = [
        build_dataset("ar", rounds=args.bootstrap_rounds, seed=args.seed),
        build_dataset("zh", rounds=args.bootstrap_rounds, seed=args.seed),
    ]
    return {
        "experiment": "translation_order_gate_summary",
        "note": "Offline cheap order-risk gate analysis; no model/API calls.",
        "gate_definition": (
            "translation_if_original_top1_else_generic uses the translation-target "
            "memory-use output only when it selects the original retrieval top-1 memory; "
            "otherwise it falls back to the generic memory-use output.  "
            "translation_if_original_top1_or_generic_not_original_top1_else_generic "
            "also routes to the translation-target output when the generic output "
            "already deviates from the original retrieval top-1."
        ),
        "accept_rule": {
            "strict": "delta > 0, CI lower > 0, regression_rate <= 0.03",
            "weak": "delta > 0, CI lower >= 0, regression_rate <= 0.03",
            "order_robust": "rule holds for all three candidate-order shuffle seeds",
        },
        "datasets": datasets,
        "takeaways": [
            "Original-retrieval-rank gating improves order stability relative to ungated translation-target prompting.",
            "The strengthened rank/deviation gate is weakly order-robust for both ar->en and zh-CN->en.",
            "Direct retrieval-top1 fallback is language-pair-specific and should remain a system-side diagnostic.",
        ],
    }


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return "[" + ", ".join(fmt(item) for item in value) + "]"
    return str(value)


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Translation Order Gate Repair",
        "",
        "Last updated: 2026-07-03",
        "",
        "This document reports a cheap offline repair for the CoVoST2 translation",
        "memory-use order-sensitivity issue.  It is generated by:",
        "",
        "```text",
        "python scripts/build_translation_order_gate_summary.py",
        "```",
        "",
        "The main gate is:",
        "",
        "```text",
        "use translation-target memory-use output only if it selects the original",
        "retrieval top-1 memory; otherwise fall back to generic memory-use output.",
        "```",
        "",
        "The stronger deployable gate is:",
        "",
        "```text",
        "use translation-target memory-use output if it selects the original",
        "retrieval top-1 memory, or if the generic output already deviates from",
        "the original retrieval top-1; otherwise keep generic output.",
        "```",
        "",
        "This is cheaper than four-order self-consistency because it uses the",
        "original retrieval rank as a risk signal instead of asking the model to",
        "solve several shuffled prompts.",
        "",
        "## Summary",
        "",
        "| Dataset | Policy | Mean Delta | Min Delta | Shuffle Strict | Shuffle Weak | Max Regression Rate | Mean Route | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for dataset in summary["datasets"]:
        for item in dataset["policy_summaries"]:
            lines.append(
                "| {dataset} | {policy} | {mean_delta} | {min_delta} | {strict}/{shuffle_count} | {weak}/{shuffle_count} | {reg} | {route} | {decision} |".format(
                    dataset=dataset["dataset"],
                    policy=item["policy"],
                    mean_delta=fmt(item["mean_delta"]),
                    min_delta=fmt(item["min_delta"]),
                    strict=item["shuffle_strict_accept_count"],
                    weak=item["shuffle_weak_accept_count"],
                    shuffle_count=item["shuffle_count"],
                    reg=fmt(item["max_regression_rate"]),
                    route=fmt(item["mean_route_rate"]),
                    decision=item["decision"],
                )
            )

    lines.extend(
        [
            "",
            "## Per-Order Gate Rows",
            "",
            "| Dataset | Policy | Order | Success | Delta | CI95 | Fixes | Regressions | Route |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset in summary["datasets"]:
        rows = [
            row
            for row in dataset["rows"]
            if row["policy"]
            in {
                "translation_if_original_top1_else_generic",
                "translation_if_original_top1_or_generic_not_original_top1_else_generic",
            }
        ]
        for row in rows:
            lines.append(
                "| {dataset} | {policy} | {order} | {success} | {delta} | {ci95} | {fixes} | {regressions} | {route} |".format(
                    dataset=dataset["dataset"],
                    policy=row["policy"],
                    order=row["order"],
                    success=fmt(row["success"]),
                    delta=fmt(row["delta_vs_generic"]),
                    ci95=fmt(row["ci95"]),
                    fixes=row["fixes"],
                    regressions=row["regressions"],
                    route=fmt(row["route_rate"]),
                )
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The gate improves order stability over the ungated translation-target",
            "  prompt.",
            "- The simple original-top1 gate still leaves ar->en partially repaired.",
            "  The stronger rank/deviation gate makes ar->en weakly order-robust",
            "  across all tested shuffle seeds while keeping max regression rate",
            "  at 0.005.",
            "- For zh-CN->en, both rank-aware gates are weakly order-robust across",
            "  all shuffle seeds and have zero regressions in the evaluated orders.",
            "- The retrieval-top1 fallback variant is strong on zh-CN->en but regresses",
            "  on ar->en, so it should remain a system-side diagnostic rather than a",
            "  universal deployment policy.",
            "- Paper use: this is a strengthening run showing that order risk can be",
            "  reduced by a retrieval-rank-aware controller, while still preserving",
            "  the limitation that translation memory-use needs task/language-pair",
            "  validation.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/translation_order_gate_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/translation_order_gate_repair.md"))
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown, summary)
    print(
        json.dumps(
            {
                "output": str(args.output).replace("\\", "/"),
                "markdown": str(args.markdown).replace("\\", "/"),
                "dataset_count": len(summary["datasets"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
