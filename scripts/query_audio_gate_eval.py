"""Evaluate deployable query-audio gates from existing memory-use runs.

The stress experiments already contain several row-level runs over the same
queries:

* no query signal
* corrupted or drifted text hint only
* query audio only
* query audio plus text hint

This script does not call a model.  It composes deterministic gates over those
existing predictions and reports paired deltas against the text-hint baseline.
The gates do not inspect labels:

* ``audio_on_invalid``: use audio if the text-only interface is invalid.
* ``audio_on_text_audio_disagreement``: run text and audio interfaces; use
  audio when their predictions disagree.
* ``audio_on_text_equals_noquery``: use audio when the text-only prediction is
  identical to the no-query prediction, suggesting the text hint did not add
  useful signal.
* ``audio_on_disagreement_or_text_equals_noquery``: union of the previous two
  deployable triggers.

For comparison, the report also includes text-only, audio-only, and audio+text
baselines.  Cost fields are decision costs: a disagreement gate pays for every
branch it must evaluate, even if the final prediction comes from the text row.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


GATES = (
    "text_only",
    "audio_only",
    "audio_text",
    "audio_on_invalid",
    "audio_on_text_audio_disagreement",
    "audio_on_text_equals_noquery",
    "audio_on_disagreement_or_text_equals_noquery",
    "audio_on_text_first_candidate",
    "audio_on_hint_pred_overlap_ge_0_80",
    "audio_on_hint_pred_overlap_ge_0_95",
)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "rows" not in data:
        raise ValueError(f"missing rows in {path}")
    return data


def key(row: dict[str, Any]) -> str:
    return str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")


def index_rows(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {key(row): row for row in data.get("rows", [])}


def load_manifest(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")] = row
    return out


def prediction(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("prediction") or row.get("model_output") or "")


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def selected_memory(manifest_row: dict[str, Any] | None, pred: str) -> dict[str, Any] | None:
    if not manifest_row:
        return None
    for item in manifest_row.get("candidate_memories", []):
        if str(item.get("memory_id")) == pred:
            return item
    return None


def selected_index(manifest_row: dict[str, Any] | None, pred: str) -> int | None:
    if not manifest_row:
        return None
    for idx, item in enumerate(manifest_row.get("candidate_memories", [])):
        if str(item.get("memory_id")) == pred:
            return idx
    return None


def hint_text(manifest_row: dict[str, Any] | None) -> str:
    if not manifest_row:
        return ""
    for field in ("text_hint", "asr_text", "transcript", "query_text", "text", "question"):
        value = str(manifest_row.get(field) or "")
        if value:
            return value
    return ""


def hint_prediction_overlap(manifest_row: dict[str, Any] | None, pred: str) -> float:
    memory = selected_memory(manifest_row, pred)
    if not memory:
        return 0.0
    hint = tokens(hint_text(manifest_row))
    summary = tokens(str(memory.get("summary") or memory.get("label") or memory.get("context") or ""))
    if not hint or not summary:
        return 0.0
    return len(hint & summary) / max(1, min(len(hint), len(summary)))


def is_success(row: dict[str, Any] | None, field: str) -> bool:
    return bool(row and row.get(field))


def branch_cost(*rows: dict[str, Any] | None) -> dict[str, float]:
    present = [row for row in rows if row is not None]
    return {
        "decision_text_cost": sum(float(row.get("text_cost", 0.0)) for row in present),
        "decision_audio_cost": sum(float(row.get("audio_cost", 0.0)) for row in present),
        "decision_latency_ms": sum(float(row.get("latency_ms", 0.0)) for row in present),
    }


def choose_row(
    gate: str,
    *,
    text_row: dict[str, Any],
    audio_row: dict[str, Any],
    audio_text_row: dict[str, Any] | None,
    noquery_row: dict[str, Any] | None,
    manifest_row: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool, str, dict[str, float]]:
    text_pred = prediction(text_row)
    audio_pred = prediction(audio_row)
    noquery_pred = prediction(noquery_row)
    text_invalid = bool(text_row.get("invalid_output"))

    if gate == "text_only":
        return text_row, False, "baseline_text", branch_cost(text_row)
    if gate == "audio_only":
        return audio_row, True, "baseline_audio", branch_cost(audio_row)
    if gate == "audio_text":
        row = audio_text_row or text_row
        return row, bool(audio_text_row), "baseline_audio_text", branch_cost(row)

    if gate == "audio_on_invalid":
        triggered = text_invalid
        reason = "text_invalid" if triggered else "text_valid"
        costs = branch_cost(text_row, audio_row) if triggered else branch_cost(text_row)
        return (audio_row if triggered else text_row), triggered, reason, costs

    if gate == "audio_on_text_audio_disagreement":
        triggered = text_invalid or (text_pred != audio_pred)
        reason = "invalid_or_text_audio_disagreement" if triggered else "text_audio_agree"
        return (audio_row if triggered else text_row), triggered, reason, branch_cost(text_row, audio_row)

    if gate == "audio_on_text_equals_noquery":
        triggered = text_invalid or (bool(noquery_pred) and text_pred == noquery_pred)
        reason = "invalid_or_text_equals_noquery" if triggered else "text_differs_from_noquery"
        costs = branch_cost(text_row, noquery_row, audio_row) if triggered else branch_cost(text_row, noquery_row)
        return (audio_row if triggered else text_row), triggered, reason, costs

    if gate == "audio_on_disagreement_or_text_equals_noquery":
        disagreement = text_pred != audio_pred
        equals_noquery = bool(noquery_pred) and text_pred == noquery_pred
        triggered = text_invalid or disagreement or equals_noquery
        reason = "invalid_or_disagreement_or_text_equals_noquery" if triggered else "no_trigger"
        return (audio_row if triggered else text_row), triggered, reason, branch_cost(text_row, noquery_row, audio_row)

    if gate == "audio_on_text_first_candidate":
        triggered = text_invalid or selected_index(manifest_row, text_pred) == 0
        reason = "invalid_or_text_selected_first_candidate" if triggered else "text_not_first_candidate"
        costs = branch_cost(text_row, audio_row) if triggered else branch_cost(text_row)
        return (audio_row if triggered else text_row), triggered, reason, costs

    if gate in {"audio_on_hint_pred_overlap_ge_0_80", "audio_on_hint_pred_overlap_ge_0_95"}:
        threshold = 0.80 if gate.endswith("0_80") else 0.95
        overlap = hint_prediction_overlap(manifest_row, text_pred)
        triggered = text_invalid or overlap >= threshold
        reason = f"invalid_or_hint_pred_overlap_ge_{threshold:.2f}" if triggered else "hint_pred_overlap_below_threshold"
        costs = branch_cost(text_row, audio_row) if triggered else branch_cost(text_row)
        return (audio_row if triggered else text_row), triggered, reason, costs

    raise ValueError(f"unknown gate {gate}")


def compose_gate(
    gate: str,
    *,
    text: dict[str, Any],
    audio: dict[str, Any],
    audio_text: dict[str, Any] | None,
    noquery: dict[str, Any] | None,
    manifest: dict[str, dict[str, Any]],
    success_field: str,
) -> dict[str, Any]:
    text_rows = index_rows(text)
    audio_rows = index_rows(audio)
    audio_text_rows = index_rows(audio_text) if audio_text else {}
    noquery_rows = index_rows(noquery) if noquery else {}

    rows: list[dict[str, Any]] = []
    for row_id, text_row in text_rows.items():
        audio_row = audio_rows.get(row_id)
        if audio_row is None:
            continue
        audio_text_row = audio_text_rows.get(row_id)
        noquery_row = noquery_rows.get(row_id)
        manifest_row = manifest.get(row_id)
        chosen, triggered, reason, costs = choose_row(
            gate,
            text_row=text_row,
            audio_row=audio_row,
            audio_text_row=audio_text_row,
            noquery_row=noquery_row,
            manifest_row=manifest_row,
        )
        out = deepcopy(chosen)
        text_ok = is_success(text_row, success_field)
        audio_ok = is_success(audio_row, success_field)
        chosen_ok = is_success(chosen, success_field)
        out.update(
            {
                "gate_name": gate,
                "gate_triggered": triggered,
                "gate_reason": reason,
                "text_prediction": prediction(text_row),
                "audio_prediction": prediction(audio_row),
                "audio_text_prediction": prediction(audio_text_row),
                "noquery_prediction": prediction(noquery_row),
                "text_selected_index": selected_index(manifest_row, prediction(text_row)),
                "hint_prediction_overlap": hint_prediction_overlap(manifest_row, prediction(text_row)),
                "text_success": text_ok,
                "audio_success": audio_ok,
                "gate_rescue": bool(chosen_ok and not text_ok),
                "gate_regression": bool(text_ok and not chosen_ok),
                **costs,
            }
        )
        rows.append(out)
    return {
        "experiment": "query_audio_gate_eval",
        "gate": gate,
        "success_field": success_field,
        "rows": rows,
    }


def summarize(data: dict[str, Any], success_field: str) -> dict[str, Any]:
    rows = data.get("rows", [])
    n = len(rows)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "success": sum(bool(row.get(success_field)) for row in rows) / n,
        "wrong_memory": sum(bool(row.get("wrong_memory")) for row in rows) / n,
        "invalid_output": sum(bool(row.get("invalid_output")) for row in rows) / n,
        "gate_rate": sum(bool(row.get("gate_triggered")) for row in rows) / n,
        "rescues": sum(bool(row.get("gate_rescue")) for row in rows),
        "regressions": sum(bool(row.get("gate_regression")) for row in rows),
        "mean_decision_text_cost": sum(float(row.get("decision_text_cost", 0.0)) for row in rows) / n,
        "mean_decision_audio_cost": sum(float(row.get("decision_audio_cost", 0.0)) for row in rows) / n,
        "mean_decision_latency_ms": sum(float(row.get("decision_latency_ms", 0.0)) for row in rows) / n,
    }


def paired_delta(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    *,
    success_field: str,
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    baseline_rows = {key(row): row for row in baseline.get("rows", [])}
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    for row in candidate.get("rows", []):
        base = baseline_rows.get(key(row))
        if not base:
            continue
        cand_ok = bool(row.get(success_field))
        base_ok = bool(base.get(success_field))
        diffs.append(int(cand_ok) - int(base_ok))
        fixes += int(cand_ok and not base_ok)
        regressions += int(base_ok and not cand_ok)
    if not diffs:
        return {"paired_n": 0}
    rng = random.Random(seed)
    n = len(diffs)
    boot = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    boot.sort()
    return {
        "paired_n": n,
        "delta": sum(diffs) / n,
        "ci95": [boot[int(0.025 * rounds)], boot[max(0, int(0.975 * rounds) - 1)]],
        "fixes": fixes,
        "regressions": regressions,
        "regression_rate": regressions / n,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    text = load_json(args.text)
    audio = load_json(args.audio)
    audio_text = load_json(args.audio_text) if args.audio_text else None
    noquery = load_json(args.noquery) if args.noquery else None
    manifest = load_manifest(args.manifest)

    gate_results = {
        gate: compose_gate(
            gate,
            text=text,
            audio=audio,
            audio_text=audio_text,
            noquery=noquery,
            manifest=manifest,
            success_field=args.success_field,
        )
        for gate in GATES
        if gate != "audio_text" or audio_text is not None
    }
    baseline = gate_results["text_only"]
    report: dict[str, Any] = {
        "experiment": "query_audio_gate_eval",
        "dataset": args.dataset,
        "success_field": args.success_field,
        "inputs": {
            "text": str(args.text),
            "audio": str(args.audio),
            "audio_text": str(args.audio_text) if args.audio_text else "",
            "noquery": str(args.noquery) if args.noquery else "",
            "manifest": str(args.manifest) if args.manifest else "",
        },
        "summaries": [
            {"gate": gate, **summarize(result, args.success_field)}
            for gate, result in gate_results.items()
        ],
        "paired_vs_text": [
            {
                "gate": gate,
                **paired_delta(
                    result,
                    baseline,
                    success_field=args.success_field,
                    rounds=args.bootstrap_rounds,
                    seed=args.seed,
                ),
            }
            for gate, result in gate_results.items()
            if gate != "text_only"
        ],
    }
    if args.include_rows:
        report["gate_results"] = gate_results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--audio-text", type=Path)
    parser.add_argument("--noquery", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--success-field", default="task_success")
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-rows", action="store_true")
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    compact = {k: v for k, v in result.items() if k != "gate_results"}
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
