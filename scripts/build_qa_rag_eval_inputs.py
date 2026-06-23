"""Build RAG final-answer eval inputs from candidate-retrieval outputs.

This converts the narrow transcript/answer/passage candidate retrieval JSON
into the row shape expected by `scripts/rag_answer_eval.py`.

It also writes simple answer keys from manifest answer fields. The key format
uses exact answer aliases as required terms; it is intentionally conservative
and reproducible.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _normalize_answer(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _answer_aliases(row: dict[str, Any]) -> list[str]:
    aliases = []
    answer = _normalize_answer(row.get("answer", ""))
    if answer:
        aliases.append(answer)
    raw = row.get("raw_answers")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                value = _normalize_answer(item.get("text", ""))
            else:
                value = _normalize_answer(str(item))
            if value and value not in aliases:
                aliases.append(value)
    return aliases or [answer]


def _candidate_list(row: dict[str, Any], source: str) -> list[dict[str, Any]]:
    candidates = []
    for item in row.get("scores", []):
        candidates.append(
            {
                "rank": item.get("rank", len(candidates) + 1),
                "sample_id": item["sample_id"],
                "score": item.get("score", 0.0),
                "document": item.get("text", ""),
                "source": source,
            }
        )
    return candidates


def _rows_by_sample(result_path: Path, source: str) -> dict[str, list[dict[str, Any]]]:
    if not result_path:
        return {}
    data = _read_json(result_path)
    return {row["sample_id"]: _candidate_list(row, source) for row in data.get("rows", [])}


def build_inputs(args: argparse.Namespace) -> dict[str, Any]:
    manifest_rows = _read_jsonl(args.manifest)
    asr_rows = _rows_by_sample(args.asr_result, "asr") if args.asr_result else {}
    omni_rows = _rows_by_sample(args.omni_result, "omni") if args.omni_result else {}

    retrieval_rows = []
    for row in manifest_rows:
        sample_id = row["sample_id"]
        retrieval_rows.append(
            {
                "sample_id": sample_id,
                "query_text": row.get("question") or row.get("text") or "",
                "asr_text": row.get("transcript", ""),
                "target": row.get("question") or row.get("text") or "",
                "asr_top_k": asr_rows.get(sample_id, []),
                "omni_top_k": omni_rows.get(sample_id, []),
            }
        )

    retrieval_report = {
        "experiment": "qa_rag_eval_input_adapter",
        "source_manifest": str(args.manifest),
        "asr_result": str(args.asr_result) if args.asr_result else "",
        "omni_result": str(args.omni_result) if args.omni_result else "",
        "metrics": {
            args.split: {
                "rows": retrieval_rows,
            }
        },
    }
    args.output_retrieval.parent.mkdir(parents=True, exist_ok=True)
    args.output_retrieval.write_text(
        json.dumps(retrieval_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    keys = {}
    for row in manifest_rows:
        aliases = _answer_aliases(row)
        keys[row["sample_id"]] = {
            "gold_answer": row.get("answer", aliases[0]),
            "key_decision": row.get("answer", aliases[0]),
            "required_terms": [aliases],
            "forbidden_terms": [],
        }
    answer_report = {
        "source_manifest": str(args.manifest),
        "key_policy": "exact answer aliases from manifest answer/raw_answers",
        "keys": keys,
    }
    args.output_answer_keys.parent.mkdir(parents=True, exist_ok=True)
    args.output_answer_keys.write_text(
        json.dumps(answer_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = {
        "retrieval_rows": len(retrieval_rows),
        "answer_keys": len(keys),
        "output_retrieval": str(args.output_retrieval),
        "output_answer_keys": str(args.output_answer_keys),
        "examples": retrieval_rows[:3],
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-retrieval", required=True, type=Path)
    parser.add_argument("--output-answer-keys", required=True, type=Path)
    parser.add_argument("--split", default="test")
    parser.add_argument("--asr-result", type=Path)
    parser.add_argument("--omni-result", type=Path)
    return parser


def main() -> None:
    print(json.dumps(build_inputs(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
