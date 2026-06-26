"""Parse raw generative omni CLI outputs from a generated shell plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from generative_omni_policy_smoke import parse_prediction


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def option_texts(options: list[str]) -> list[str]:
    texts: list[str] = []
    for option in options:
        texts.append(option.split(". ", 1)[1] if ". " in option else option)
    return texts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tail-chars", type=int, default=2000)
    args = parser.parse_args()

    cases = read_jsonl(Path(args.cases))
    rows: list[dict[str, Any]] = []
    for case in cases:
        raw_path = Path(case["raw_output_path"])
        raw = raw_path.read_text(encoding="utf-8", errors="replace") if raw_path.exists() else ""
        pred, method, score = parse_prediction(raw, option_texts(case["options"]))
        correct = pred == case["gold_letter"]
        rows.append(
            {
                "case_id": case["case_id"],
                "sample_id": case.get("sample_id"),
                "policy": case.get("policy"),
                "gold": case["gold"],
                "gold_letter": case["gold_letter"],
                "prediction_letter": pred,
                "parse_method": method,
                "parse_score": score,
                "correct": correct,
                "options": case["options"],
                "prompt": case["prompt"],
                "raw_output_path": case["raw_output_path"],
                "model_output": raw[-args.tail_chars :],
                "audio_path": case.get("audio_path"),
                "source_text": case.get("source_text"),
            }
        )

    n = len(rows)
    accuracy = sum(1 for row in rows if row["correct"]) / n if n else 0.0
    parse_counts: dict[str, int] = {}
    for row in rows:
        parse_counts[row["parse_method"]] = parse_counts.get(row["parse_method"], 0) + 1
    result = {
        "experiment": "generative_omni_parse_outputs",
        "n": n,
        "accuracy": accuracy,
        "parse_counts": parse_counts,
        "rows": rows,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
