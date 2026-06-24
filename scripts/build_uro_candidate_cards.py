"""Add candidate-card fields to URO-Bench manifests.

The derived fields are training-free candidate-side wrappers.  They do not
change audio, labels, or model weights.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


OPTION_RE = re.compile(
    r"(?P<label>[A-D])[\.\uff0e\u3002;\uff1b:：]\s*(?P<text>.*?)(?=(?:\s+[A-D][\.\uff0e\u3002;\uff1b:：])|$)",
    re.DOTALL,
)


TASK_DESCRIPTIONS = {
    "GaokaoEval": "English listening-comprehension multiple-choice exam",
    "Gsm8kEval": "grade-school math reasoning question",
    "HSK5-zh": "Chinese language proficiency multiple-choice question",
    "MuChoEval-en": "music audio understanding multiple-choice question",
    "OpenbookQA-zh": "open-book science multiple-choice question",
    "SQuAD-zh": "Chinese reading-comprehension span question",
    "StoralEval": "story or fable moral understanding question",
    "TruthfulEval": "truthfulness-oriented question answering",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_options(source_text: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for match in OPTION_RE.finditer(source_text):
        label = match.group("label")
        text = _clean(match.group("text"))
        if text:
            options[label] = text
    return options


def expanded_answer(row: dict[str, Any]) -> str:
    target = _clean(row.get("target_text") or row.get("answer"))
    source = _clean(row.get("source_text") or row.get("text"))
    options = parse_options(source)
    letter_match = re.match(r"^([A-D])(?:[\.\uff0e\u3002;\uff1b:：]\s*)?(.*)$", target)
    if letter_match:
        label = letter_match.group(1)
        remainder = _clean(letter_match.group(2))
        option = options.get(label, "")
        if option and (not remainder or remainder == option):
            return f"{label}. {option}"
    return target


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    dataset_config = _clean(out.get("dataset_config"))
    task_desc = TASK_DESCRIPTIONS.get(dataset_config, dataset_config or "speech QA/reasoning task")
    answer = expanded_answer(out)
    out["target_option_expanded"] = answer
    out["target_answer_card"] = f"Answer: {answer}"
    out["target_task_card"] = f"Task: {dataset_config}\nTask type: {task_desc}\nAnswer: {answer}"
    out["target_boundary_card"] = (
        f"Task: {dataset_config}\n"
        f"Task type: {task_desc}\n"
        f"Candidate answer: {answer}\n"
        "Use this candidate only when the spoken query asks for this exact answer, "
        "option, span, or reasoning result."
    )
    return out


def convert(input_path: Path, output_path: Path) -> dict[str, Any]:
    rows = []
    changed = 0
    with input_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            enriched = enrich_row(row)
            changed += int(enriched.get("target_option_expanded") != row.get("target_text"))
            rows.append(enriched)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "experiment": "build_uro_candidate_cards",
        "input": str(input_path),
        "output": str(output_path),
        "row_count": len(rows),
        "option_expanded_count": changed,
        "fields": [
            "target_option_expanded",
            "target_answer_card",
            "target_task_card",
            "target_boundary_card",
        ],
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
