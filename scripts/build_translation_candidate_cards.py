"""Add candidate-card fields to speech translation manifests.

The derived fields are training-free text-side wrappers.  They do not alter
audio, labels, or model weights.  The cards intentionally avoid using the
source transcript inside the candidate text, so the task remains:

    source speech audio -> target-language translation candidate
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    target_language = _clean(out.get("target_language") or "target")
    target_text = _clean(out.get("target_text") or out.get("translation") or out.get("text"))
    out["target_translation_card"] = (
        f"Target language: {target_language}\n"
        f"Translation candidate: {target_text}"
    )
    out["target_boundary_card"] = (
        f"Task: speech translation candidate retrieval\n"
        f"Target language: {target_language}\n"
        f"Candidate translation: {target_text}\n"
        "Use this candidate only when it preserves the spoken source meaning, "
        "including named entities, numbers, negation, and predicate-argument structure."
    )
    return out


def convert(input_path: Path, output_path: Path) -> dict[str, Any]:
    rows = []
    with input_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(enrich_row(json.loads(line)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "experiment": "build_translation_candidate_cards",
        "input": str(input_path),
        "output": str(output_path),
        "row_count": len(rows),
        "fields": ["target_translation_card", "target_boundary_card"],
        "examples": rows[:3],
    }
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(convert(args.input, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
