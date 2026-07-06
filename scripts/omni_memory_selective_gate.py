"""Compose selective audio-memory gate results from existing row-level runs.

This script is deliberately offline. It does not call a model. Instead, it
combines a baseline memory-use result with an audio-inclusive candidate result
under a deterministic diagnostic gate. The first gates are oracle-style probes:
they answer whether audio memory *could* help under clear failure conditions,
not whether the gate is deployable yet.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


GATES = {
    "text_hint_wrong_gate",
    "invalid_gate",
    "shuffle_disagreement_gate",
}


def load_result(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "rows" not in data:
        raise ValueError(f"result has no rows: {path}")
    return data


def row_key(row: dict[str, Any]) -> str:
    return str(row.get("query_id"))


def index_rows(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row_key(row): row for row in data.get("rows", [])}


def predict(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("prediction") or "")


def gate_triggers(
    gate: str,
    baseline_row: dict[str, Any],
    shuffle_rows: list[dict[str, Any] | None],
) -> tuple[bool, str]:
    if gate == "text_hint_wrong_gate":
        return (not bool(baseline_row.get("task_success"))), "baseline_wrong"
    if gate == "invalid_gate":
        return bool(baseline_row.get("invalid_output")), "baseline_invalid"
    if gate == "shuffle_disagreement_gate":
        predictions = {predict(baseline_row)}
        predictions.update(predict(row) for row in shuffle_rows if row is not None)
        predictions.discard("")
        return len(predictions) > 1, "shuffle_disagreement"
    raise ValueError(f"unknown gate: {gate}")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if not n:
        return {"n": 0}
    gate_rate = sum(bool(row.get("gate_triggered")) for row in rows) / n
    return {
        "n": n,
        "task_success": sum(bool(row.get("task_success")) for row in rows) / n,
        "grounded_memory_use": sum(bool(row.get("grounded_memory_use")) for row in rows) / n,
        "wrong_memory": sum(bool(row.get("wrong_memory")) for row in rows) / n,
        "invalid_output": sum(bool(row.get("invalid_output")) for row in rows) / n,
        "mean_text_cost": sum(float(row.get("text_cost", 0.0)) for row in rows) / n,
        "mean_audio_cost": sum(float(row.get("audio_cost", 0.0)) for row in rows) / n,
        "mean_latency_ms": sum(float(row.get("latency_ms", 0.0)) for row in rows) / n,
        "gate_rate": gate_rate,
        "gate_trigger_count": sum(bool(row.get("gate_triggered")) for row in rows),
        "rescue_count": sum(bool(row.get("gate_rescue")) for row in rows),
        "gate_regression_count": sum(bool(row.get("gate_regression")) for row in rows),
        "regression_count": sum(bool(row.get("regression_vs_baseline")) for row in rows),
        "regression_rate": sum(bool(row.get("regression_vs_baseline")) for row in rows) / n,
    }


def compose(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    gate: str,
    shuffles: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_rows = index_rows(baseline)
    candidate_rows = index_rows(candidate)
    shuffle_indices = [index_rows(item) for item in shuffles]

    rows: list[dict[str, Any]] = []
    missing_candidate = 0
    for key, baseline_row in baseline_rows.items():
        candidate_row = candidate_rows.get(key)
        if candidate_row is None:
            missing_candidate += 1
            chosen = deepcopy(baseline_row)
            triggered = False
            reason = "missing_candidate"
            candidate_success = None
            candidate_prediction = ""
        else:
            shuffle_rows = [index.get(key) for index in shuffle_indices]
            triggered, reason = gate_triggers(gate, baseline_row, shuffle_rows)
            chosen = deepcopy(candidate_row if triggered else baseline_row)
            candidate_success = bool(candidate_row.get("task_success"))
            candidate_prediction = predict(candidate_row)

        baseline_success = bool(baseline_row.get("task_success"))
        chosen_success = bool(chosen.get("task_success"))
        chosen.update(
            {
                "gate_name": gate,
                "gate_triggered": triggered,
                "gate_reason": reason,
                "baseline_prediction": predict(baseline_row),
                "candidate_prediction": candidate_prediction,
                "baseline_task_success": baseline_success,
                "candidate_task_success": candidate_success,
                "gate_rescue": bool(triggered and chosen_success and not baseline_success),
                "gate_regression": bool(triggered and baseline_success and not chosen_success),
                "regression_vs_baseline": bool(baseline_success and not chosen_success),
            }
        )
        rows.append(chosen)

    result: dict[str, Any] = {
        "experiment": "omni_memory_selective_gate",
        "gate": gate,
        "baseline_policy": baseline.get("policy"),
        "candidate_policy": candidate.get("policy"),
        "backend": baseline.get("backend"),
        "missing_candidate": missing_candidate,
        "shuffle_count": len(shuffles),
        "rows": rows,
    }
    result.update(summarize(rows))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--shuffle", type=Path, action="append", default=[])
    parser.add_argument("--gate", choices=sorted(GATES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = compose(
        load_result(args.baseline),
        load_result(args.candidate),
        gate=args.gate,
        shuffles=[load_result(path) for path in args.shuffle],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in result if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
