"""Build a cross-model/backend readiness summary from existing outputs.

This script is offline. It reads ignored JSON artifacts and creates a compact
paper-facing summary that separates:

- embedding-backend transfer checks;
- system-side candidate formatting checks;
- generative main-model backend readiness.

The summary is intentionally conservative: a backend can be "usable" for a
paper row only when it has task-level metrics, not just a smoke/probe result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


JINA_SELECTOR_PATHS = {
    "Jina SLURP intent": Path("outputs/omni_memory_v0/retrieval/selector_jina_slurp_intent.json"),
    "Jina CoVoST2 ar->en": Path(
        "outputs/omni_memory_v0/retrieval/selector_jina_covost2_ar_en_translation.json"
    ),
    "Jina CoVoST2 zh-CN->en": Path(
        "outputs/omni_memory_v0/retrieval/selector_jina_covost2_zh_cn_en_translation.json"
    ),
}

JINA_STABILITY_PATHS = {
    "Jina URO QA/reasoning": Path("outputs/v3_power_jina_uro_summary.json"),
    "Jina CoVoST2 zh-CN->en repeated selector": Path("outputs/v3_power_jina_covost2_zh_summary.json"),
}

JINA_SYSTEM_SIDE_PATHS = {
    "Jina SLURP boundary tool card": Path("outputs/jina_slurp_tool_500_boundary_compare.json"),
    "Jina MInDS boundary tool card": Path("outputs/jina_minds_tool_180_boundary_compare.json"),
}

E4B_FORMAL_LOCKED = Path("outputs/generative_v3_gemma4_e4b_formal/summary_locked30.json")
E4B_CLI_PROBE = Path("outputs/omni_memory_v0/gpu_probe_gemma4e4b_1.json")
E4B_SERVER_PROBE = Path("outputs/omni_memory_v0/covost2_server_probe_text_1.json")
GEMMA12B_PARTIAL = Path("outputs/omni_memory_v0/summary_gemma12b_partial_covost2_vs_e4b.json")
QWEN3_GGUF_SMOKE = Path("outputs/generative_omni_qwen3_covost2_ar2_translation_boundary.json")
QWEN3_CHAT_SMOKE = Path("outputs/generative_omni_qwen3_chat_covost2_ar2_translation_boundary.json")
VOXTRAL_CLI_HANG_SMOKE = Path("outputs/generative_omni_voxtral_cli_hang_smoke.json")
VOXTRAL_CHAT_SMOKE_CANDIDATES = [
    Path("outputs/generative_omni_voxtral_chat45_covost2_ar60_translation_boundary_v3.json"),
    Path("outputs/generative_omni_voxtral_chat45_covost2_ar12_translation_boundary_v2.json"),
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_first_complete_json(paths: list[Path], min_n: int) -> tuple[Path, dict[str, Any]]:
    fallback: tuple[Path, dict[str, Any]] | None = None
    for path in paths:
        if not path.exists():
            continue
        data = read_json(path)
        fallback = (path, data)
        if int(data.get("n", 0) or 0) >= min_n:
            return path, data
    if fallback is not None:
        return fallback
    raise FileNotFoundError(f"None of the expected result files exists: {paths}")


def normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def selector_locked_rows(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("name")): row
        for row in data.get("leaderboards", {}).get("locked_test", [])
    }


def selector_embedding_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task, path in JINA_SELECTOR_PATHS.items():
        data = read_json(path)
        locked = selector_locked_rows(data)
        raw = locked.get("raw") or data.get("selected_locked_test", {})
        alternatives = [row for name, row in locked.items() if name != "raw"]
        max_delta = max((float(row.get("hit_delta", 0.0)) for row in alternatives), default=0.0)
        regressions = sum(int(row.get("regression_count", 0)) for row in alternatives)
        rows.append(
            {
                "model": "jina-embeddings-v5-omni-small",
                "task": task,
                "source": normalize_path(path),
                "n": raw.get("n"),
                "raw_acc_at_1": raw.get("acc_at_1"),
                "raw_recall_at_3": raw.get("recall_at_3"),
                "raw_mrr": raw.get("mrr"),
                "decision": data.get("decision") or data.get("selection_decision"),
                "max_instruction_delta": max_delta,
                "alternative_count": len(alternatives),
                "alternative_regressions": regressions,
                "readiness": "safe_raw_fallback",
                "paper_role": "cross-model safety/fallback, not positive instruction transfer",
            }
        )
    return rows


def selector_stability_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task, path in JINA_STABILITY_PATHS.items():
        data = read_json(path)
        leaderboard = data.get("leaderboard", [])
        best = leaderboard[0] if leaderboard else {}
        rows.append(
            {
                "model": "jina-embeddings-v5-omni-small",
                "task": task,
                "source": normalize_path(path),
                "run_count": data.get("run_count"),
                "decision": data.get("decision"),
                "selected": data.get("selected"),
                "best_name": best.get("name"),
                "best_selection_rate": best.get("selection_rate"),
                "mean_locked_delta": best.get("mean_locked_delta"),
                "mean_locked_lcb": best.get("mean_locked_lcb"),
                "mean_locked_regression_rate": best.get("mean_locked_regression_rate"),
                "readiness": "no_stable_positive_policy",
                "paper_role": "evidence that robust selector falls back to raw on strong Jina baseline",
            }
        )
    return rows


def system_side_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task, path in JINA_SYSTEM_SIDE_PATHS.items():
        data = read_json(path)
        hit = data.get("hit_at_1", {})
        rows.append(
            {
                "model": "jina-embeddings-v5-omni-small",
                "task": task,
                "source": normalize_path(path),
                "n": data.get("n"),
                "baseline_acc_at_1": hit.get("baseline"),
                "candidate_acc_at_1": hit.get("candidate"),
                "delta": hit.get("delta"),
                "ci95": hit.get("bootstrap_ci95"),
                "fixes": data.get("fix_count"),
                "regressions": data.get("regression_count"),
                "readiness": "system_side_positive",
                "paper_role": "candidate/schema formatting baseline; not omni-side optimization",
            }
        )
    return rows


def e4b_formal_row() -> dict[str, Any]:
    data = read_json(E4B_FORMAL_LOCKED)
    runs = data.get("runs", [])
    raw = next(row for row in runs if row.get("policy") == "raw" and row.get("prompt_mode") == "anti_answer")
    best = max(runs, key=lambda row: float(row.get("accuracy", 0.0)))
    return {
        "model": "Gemma 4 E4B GGUF",
        "task": "CoVoST2 ar->en candidate selection",
        "source": normalize_path(E4B_FORMAL_LOCKED),
        "n": best.get("n"),
        "raw_acc_at_1": raw.get("accuracy"),
        "best_policy": f"{best.get('policy')} / {best.get('prompt_mode')}",
        "best_acc_at_1": best.get("accuracy"),
        "delta_vs_raw": float(best.get("accuracy", 0.0)) - float(raw.get("accuracy", 0.0)),
        "readiness": "main_backend_small_formal_positive",
        "paper_role": "small formal generative-omni policy-surface evidence; E4B remains main backend",
    }


def e4b_probe_rows() -> list[dict[str, Any]]:
    rows = []
    for label, path, role in [
        ("Gemma 4 E4B CLI probe", E4B_CLI_PROBE, "CLI backend sanity"),
        ("Gemma 4 E4B server probe", E4B_SERVER_PROBE, "service backend sanity"),
    ]:
        data = read_json(path)
        rows.append(
            {
                "model": "Gemma 4 E4B GGUF",
                "task": label,
                "source": normalize_path(path),
                "n": data.get("n"),
                "success": data.get("task_success"),
                "invalid_output": data.get("invalid_output"),
                "mean_latency_ms": data.get("mean_latency_ms"),
                "readiness": "backend_probe_passed",
                "paper_role": role,
            }
        )
    return rows


def gemma12b_partial_row() -> dict[str, Any]:
    data = read_json(GEMMA12B_PARTIAL)
    summaries = {row["label"]: row for row in data.get("summaries", [])}
    base = summaries["e4b"]
    partial = summaries["gemma12b_partial"]
    paired = data["paired"][0]
    return {
        "model": "Gemma 4 12B GGUF",
        "task": "CoVoST2 ar->en partial backend reference",
        "source": normalize_path(GEMMA12B_PARTIAL),
        "baseline_model": "Gemma 4 E4B GGUF",
        "baseline_n": base.get("n"),
        "partial_n": partial.get("n"),
        "baseline_success": base.get("success"),
        "partial_success": partial.get("success"),
        "delta_vs_e4b": paired.get("delta"),
        "ci95": paired.get("ci95"),
        "fixes": paired.get("fixes"),
        "regressions": paired.get("regressions"),
        "regression_rate": paired.get("regression_rate"),
        "latency_ratio": partial.get("mean_latency_ms") / base.get("mean_latency_ms"),
        "readiness": "rejected_backend_reference",
        "paper_role": "backend blocker / negative diagnostic, not cross-model confirmation",
    }


def qwen3_smoke_row() -> dict[str, Any]:
    data = read_json(QWEN3_GGUF_SMOKE)
    return {
        "model": "Qwen3-Omni GGUF",
        "task": "CoVoST2 ar->en tiny candidate-selection smoke",
        "source": normalize_path(QWEN3_GGUF_SMOKE),
        "n": data.get("n"),
        "accuracy": data.get("accuracy"),
        "policy": data.get("policy"),
        "readiness": "backend_smoke_only",
        "paper_role": "backend readiness signal only; no formal task evidence",
    }


def qwen3_chat_timeout_row() -> dict[str, Any]:
    data = read_json(QWEN3_CHAT_SMOKE)
    timeout_count = sum(1 for row in data.get("rows", []) if row.get("error") == "timeout")
    return {
        "model": "Qwen3-Omni GGUF",
        "task": "CoVoST2 ar->en chat-mode candidate-selection smoke",
        "source": normalize_path(QWEN3_CHAT_SMOKE),
        "n": data.get("n"),
        "valid_rate": data.get("valid_rate"),
        "parse_rate": data.get("parse_rate"),
        "accuracy": data.get("accuracy"),
        "timeout_count": timeout_count,
        "mean_latency_ms": data.get("mean_latency_ms"),
        "policy": f"{data.get('policy')} / {data.get('prompt_mode')}",
        "readiness": "chat_backend_timeout_blocker",
        "paper_role": "backend blocker after using the more appropriate chat-mode audio interface",
    }


def voxtral_cli_hang_row() -> dict[str, Any]:
    data = read_json(VOXTRAL_CLI_HANG_SMOKE)
    return {
        "model": "Voxtral Mini 3B 2507 GGUF",
        "task": data.get("task"),
        "source": normalize_path(VOXTRAL_CLI_HANG_SMOKE),
        "attempted_rows": data.get("attempted_rows"),
        "completed_rows": data.get("completed_rows"),
        "valid_rate": data.get("valid_rate"),
        "parse_rate": data.get("parse_rate"),
        "accuracy": data.get("accuracy"),
        "timeout_count": data.get("timeout_count"),
        "timeout_s": data.get("timeout_s"),
        "minimal_log_timeout_s": data.get("minimal_log_timeout_s"),
        "minimal_log_bytes": data.get("minimal_log_bytes"),
        "ctx_size": data.get("ctx_size"),
        "readiness": data.get("readiness"),
        "paper_role": "downloaded smaller audio backend candidate, but llama.cpp CLI audio smoke hangs before producing output",
    }


def voxtral_chat_smoke_row() -> dict[str, Any]:
    path, data = read_first_complete_json(VOXTRAL_CHAT_SMOKE_CANDIDATES, min_n=60)
    n = int(data.get("n", 0) or 0)
    readiness = "extended_chat_runnable_underpowered" if n >= 60 else "small_chat_smoke_positive"
    paper_role = (
        "runnable backend check, but quality/latency are not enough for second main-backend validation"
        if n >= 60
        else "small backend-readiness positive; not enough to replace the audited Gemma 4 E4B main backend"
    )
    return {
        "model": "Voxtral Mini 3B 2507 GGUF",
        "task": "CoVoST2 ar->en chat-mode candidate-selection smoke",
        "source": normalize_path(path),
        "n": data.get("n"),
        "valid_rate": data.get("valid_rate"),
        "parse_rate": data.get("parse_rate"),
        "accuracy": data.get("accuracy"),
        "mean_latency_ms": data.get("mean_latency_ms"),
        "policy": f"{data.get('policy')} / {data.get('prompt_mode')}",
        "readiness": readiness,
        "paper_role": paper_role,
    }


def build_summary() -> dict[str, Any]:
    embedding_rows = selector_embedding_rows()
    stability_rows = selector_stability_rows()
    system_rows = system_side_rows()
    voxtral_chat = voxtral_chat_smoke_row()
    generative_rows = [
        e4b_formal_row(),
        *e4b_probe_rows(),
        gemma12b_partial_row(),
        qwen3_smoke_row(),
        qwen3_chat_timeout_row(),
        voxtral_cli_hang_row(),
        voxtral_chat,
    ]
    return {
        "experiment": "cross_model_backend_readiness_summary",
        "note": "Offline synthesis from existing cross-model/backend outputs; no model/API calls.",
        "embedding_backend_rows": embedding_rows,
        "embedding_stability_rows": stability_rows,
        "system_side_rows": system_rows,
        "generative_backend_rows": generative_rows,
        "summary": {
            "embedding_backend_count": len(embedding_rows),
            "embedding_raw_fallback_count": sum(row["readiness"] == "safe_raw_fallback" for row in embedding_rows),
            "embedding_stability_no_positive_count": sum(
                row["readiness"] == "no_stable_positive_policy" for row in stability_rows
            ),
            "system_side_positive_count": len(system_rows),
            "generative_backend_count": len(generative_rows),
            "main_backend_ready": True,
            "stable_second_generative_backend_ready": False,
            "second_backend_smoke_positive": True,
        },
        "takeaways": [
            "Jina validates backend normalization and raw fallback, not positive instruction transfer.",
            "Jina system-side boundary cards can improve QA/tool retrieval, but this is candidate/schema formatting.",
            "Gemma 4 E4B is the audited main generative backend; a small formal CoVoST2 candidate-selection run is positive.",
            f"Gemma 4 12B and Qwen3-Omni remain blockers; Voxtral Mini chat mode now has an N={voxtral_chat.get('n')} runnable check but is still slow and not yet a stable main backend.",
            "Qwen3-Omni chat-mode audio is a clearer interface attempt than the old --audio/-p smoke, but it timed out on 2/2 rows.",
            f"Voxtral Mini 3B no longer looks like an audio-interface blocker when driven through chat mode: the current N={voxtral_chat.get('n')} CoVoST2 check is valid/parseable but underpowered.",
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
        "# Cross-Model Backend Readiness",
        "",
        "Last updated: 2026-07-03",
        "",
        "This document summarizes what the current artifacts prove about",
        "cross-model transfer and backend readiness.  It is generated offline by:",
        "",
        "```text",
        "python scripts/build_cross_model_backend_readiness_summary.py",
        "```",
        "",
        "The important distinction is:",
        "",
        "- embedding-backend transfer checks whether the frozen omni-embedding",
        "  controller remains safe on another embedding model;",
        "- system-side rows are useful deployment baselines but do not count as",
        "  omni-side instruction optimization;",
        "- generative backend rows decide whether a second main model is ready for",
        "  paper-facing memory-use validation.",
        "",
        "## Embedding Backend Transfer",
        "",
        "| Model | Task | N | Raw Acc@1 | R@3 | MRR | Decision | Paper Role |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in summary["embedding_backend_rows"]:
        lines.append(
            "| {model} | {task} | {n} | {acc} | {r3} | {mrr} | {decision} | {role} |".format(
                model=row["model"],
                task=row["task"],
                n=fmt(row.get("n")),
                acc=fmt(row.get("raw_acc_at_1")),
                r3=fmt(row.get("raw_recall_at_3")),
                mrr=fmt(row.get("raw_mrr")),
                decision=row["readiness"],
                role=row["paper_role"],
            )
        )

    lines.extend(
        [
            "",
            "Repeated selector diagnostics give the same conservative conclusion:",
            "",
            "| Model | Task | Runs | Decision | Best Arm | Mean Delta | Mean LCB | Role |",
            "|---|---|---:|---|---|---:|---:|---|",
        ]
    )
    for row in summary["embedding_stability_rows"]:
        lines.append(
            "| {model} | {task} | {runs} | {decision} | {best} | {delta} | {lcb} | {role} |".format(
                model=row["model"],
                task=row["task"],
                runs=fmt(row.get("run_count")),
                decision=row["decision"],
                best=row.get("best_name"),
                delta=fmt(row.get("mean_locked_delta")),
                lcb=fmt(row.get("mean_locked_lcb")),
                role=row["paper_role"],
            )
        )

    lines.extend(
        [
            "",
            "## System-Side Cross-Backend Controls",
            "",
            "These rows are useful engineering baselines, but they should not be",
            "described as omni-side model optimization.",
            "",
            "| Model | Task | N | Baseline | Candidate | Delta | CI95 | Decision |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary["system_side_rows"]:
        lines.append(
            "| {model} | {task} | {n} | {base} | {cand} | {delta} | {ci} | {decision} |".format(
                model=row["model"],
                task=row["task"],
                n=fmt(row.get("n")),
                base=fmt(row.get("baseline_acc_at_1")),
                cand=fmt(row.get("candidate_acc_at_1")),
                delta=fmt(row.get("delta")),
                ci=fmt(row.get("ci95")),
                decision=row["readiness"],
            )
        )

    lines.extend(
        [
            "",
            "## Generative Main-Model Backend Readiness",
            "",
            "| Model | Task | Evidence | Result | Decision | Paper Role |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in summary["generative_backend_rows"]:
        if row["model"] == "Gemma 4 E4B GGUF" and row.get("best_acc_at_1") is not None:
            evidence = f"N={fmt(row.get('n'))}; raw={fmt(row.get('raw_acc_at_1'))}; best={row.get('best_policy')}"
            result = f"best={fmt(row.get('best_acc_at_1'))}; delta={fmt(row.get('delta_vs_raw'))}"
        elif row["model"] == "Gemma 4 E4B GGUF":
            evidence = f"N={fmt(row.get('n'))}; probe"
            result = f"success={fmt(row.get('success'))}; latency={fmt(row.get('mean_latency_ms'))} ms"
        elif row["model"] == "Gemma 4 12B GGUF":
            evidence = f"partial N={fmt(row.get('partial_n'))}; matched against E4B"
            result = f"delta={fmt(row.get('delta_vs_e4b'))}; CI95={fmt(row.get('ci95'))}; latency ratio={fmt(row.get('latency_ratio'))}"
        elif row.get("readiness") == "chat_backend_timeout_blocker":
            evidence = f"N={fmt(row.get('n'))}; {row.get('policy')}"
            result = (
                f"valid={fmt(row.get('valid_rate'))}; parse={fmt(row.get('parse_rate'))}; "
                f"timeouts={fmt(row.get('timeout_count'))}; mean latency={fmt(row.get('mean_latency_ms'))} ms"
            )
        elif row.get("readiness") == "cli_audio_hang_blocker":
            evidence = (
                f"attempted={fmt(row.get('attempted_rows'))}; completed={fmt(row.get('completed_rows'))}; "
                f"ctx={fmt(row.get('ctx_size'))}"
            )
            result = (
                f"valid={fmt(row.get('valid_rate'))}; parse={fmt(row.get('parse_rate'))}; "
                f"timeouts={fmt(row.get('timeout_count'))}; timeout={fmt(row.get('timeout_s'))} s; "
                f"minimal log bytes={fmt(row.get('minimal_log_bytes'))}"
            )
        else:
            evidence = f"N={fmt(row.get('n'))}; {row.get('policy')}"
            result = f"accuracy={fmt(row.get('accuracy'))}"
        lines.append(
            f"| {row['model']} | {row['task']} | {evidence} | {result} | {row['readiness']} | {row['paper_role']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The current cross-model evidence supports a **safe fallback** story for",
            "  Jina: once its correct raw media-path interface is used, Nemotron-style",
            "  instructions do not reliably improve it, and the selector correctly",
            "  falls back to raw.",
            "- Jina boundary-card improvements are strong on tool tasks, but they are",
            "  candidate/schema-side system design, not omni-side instruction gains.",
            "- Gemma 4 E4B remains the only audited main generative backend for the",
            "  memory-use story.  The small formal V3 candidate-selection run is useful",
            "  backend evidence but should not replace the larger E4B memory-use tables.",
            "- Gemma 4 12B and Qwen3-Omni remain backend blockers: the 12B run",
            "  is partial and worse, while Qwen3 chat-mode audio times out.",
            "- Voxtral Mini 3B is no longer an audio-interface blocker in chat mode:",
            "  the current CoVoST2 chat-mode check is valid and parseable, but",
            "  accuracy and latency are not enough to replace Gemma 4 E4B as the",
            "  audited main backend.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/cross_model_backend_readiness_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/cross_model_backend_readiness.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_summary()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown, summary)
    print(json.dumps({"output": normalize_path(args.output), "markdown": normalize_path(args.markdown), **summary["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
