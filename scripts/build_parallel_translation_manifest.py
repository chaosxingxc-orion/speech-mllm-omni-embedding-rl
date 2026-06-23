"""Build a compact speech-translation retrieval manifest from parallel manifests.

The source manifest supplies the spoken audio and source transcript.  The target
manifest supplies the target-language text.  Rows are paired by `dataset_index`
by default, which matches parallel corpora such as FLEURS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from omni_embedding_rl.data.manifest import read_jsonl


def _key(row: dict[str, Any], key_field: str) -> str:
    value = row.get(key_field)
    if value in (None, ""):
        raise ValueError(f"row is missing pair key {key_field!r}: {row}")
    return str(value)


def build_parallel_manifest(
    source_manifest: Path,
    target_manifest: Path,
    output: Path,
    key_field: str,
    max_samples: int,
    source_language: str,
    target_language: str,
) -> dict[str, Any]:
    source_rows = read_jsonl(source_manifest)
    target_rows = {_key(row, key_field): row for row in read_jsonl(target_manifest)}

    rows = []
    missing = []
    for source_index, source in enumerate(source_rows):
        if max_samples and len(rows) >= max_samples:
            break
        key = _key(source, key_field)
        target = target_rows.get(key)
        if not target:
            missing.append(key)
            continue
        source_text = str(source.get("text") or source.get("transcript") or "")
        target_text = str(target.get("text") or target.get("transcript") or "")
        rows.append(
            {
                "sample_id": f"translation_{source_language}_{target_language}_{len(rows):06d}",
                "source": "parallel_manifest",
                "task": "speech_translation",
                "split": source.get("split", ""),
                "language": source_language,
                "target_language": target_language,
                "audio_path": source.get("audio_path", ""),
                "text": source_text,
                "transcript": source_text,
                "source_text": source_text,
                "target_text": target_text,
                "translation": target_text,
                "dataset": source.get("dataset", ""),
                "dataset_config": source.get("dataset_config", ""),
                "target_dataset_config": target.get("dataset_config", ""),
                "dataset_index": source.get("dataset_index", source_index),
                "pair_key": key,
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "experiment": "build_parallel_translation_manifest",
        "source_manifest": str(source_manifest),
        "target_manifest": str(target_manifest),
        "output": str(output),
        "key_field": key_field,
        "row_count": len(rows),
        "missing_count": len(missing),
        "missing_examples": missing[:10],
        "source_language": source_language,
        "target_language": target_language,
        "examples": rows[:3],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--target-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--key-field", default="dataset_index")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--source-language", default="")
    parser.add_argument("--target-language", default="")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(
        json.dumps(
            build_parallel_manifest(
                args.source_manifest,
                args.target_manifest,
                args.output,
                args.key_field,
                args.max_samples,
                args.source_language,
                args.target_language,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
