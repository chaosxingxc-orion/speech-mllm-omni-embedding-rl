"""Prepare a bounded manifest from the parquet-backed fixie-ai CoVoST2 mirror.

The original `facebook/covost2` dataset relies on a loading script that recent
`datasets` versions no longer execute.  The `fixie-ai/covost2` mirror stores
audio directly in dataset rows, so we can prepare small frozen-evaluation
manifests without decoding audio or training any model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _require_datasets():
    try:
        from datasets import Audio
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover - depends on local env
        raise SystemExit("This script requires the `datasets` package.") from exc
    return Audio, load_dataset


def _audio_suffix(audio: dict[str, Any]) -> str:
    source_path = str(audio.get("path") or "")
    suffix = Path(source_path).suffix
    return suffix if suffix else ".audio"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    Audio, load_dataset = _require_datasets()
    dataset = load_dataset(
        args.dataset,
        args.config,
        split=args.split,
        streaming=True,
        cache_dir=args.cache_dir,
    )
    dataset = dataset.cast_column(args.audio_column, Audio(decode=False))
    rows = []
    audio_dir = args.output_dir / "audio"
    manifest_path = args.output_dir / "manifest.jsonl"
    audio_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("w", encoding="utf-8") as handle:
        for index, example in enumerate(dataset):
            if args.max_samples and index >= args.max_samples:
                break
            sample_id = f"{args.sample_prefix}_{index:06d}"
            audio = example[args.audio_column]
            audio_path = audio_dir / f"{sample_id}{_audio_suffix(audio)}"
            audio_bytes = audio.get("bytes")
            if audio_bytes is None:
                raise ValueError(f"audio bytes missing at row {index}")
            audio_path.write_bytes(audio_bytes)

            sentence = _clean(example.get("sentence"))
            translation = _clean(example.get("translation"))
            row = {
                "sample_id": sample_id,
                "source": args.dataset,
                "task": "speech_translation",
                "split": args.split,
                "language": args.source_language,
                "target_language": args.target_language,
                "audio_path": str(audio_path),
                "text": sentence,
                "transcript": sentence,
                "source_text": sentence,
                "target_text": translation,
                "translation": translation,
                "dataset": args.dataset,
                "dataset_config": args.config,
                "dataset_index": index,
            }
            for source_key, target_key in (
                ("id", "source_id"),
                ("client_id", "client_id"),
                ("file", "source_audio_file"),
            ):
                value = example.get(source_key)
                if value not in (None, ""):
                    row[target_key] = value
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "experiment": "prepare_covost2_manifest",
        "dataset": args.dataset,
        "config": args.config,
        "split": args.split,
        "row_count": len(rows),
        "manifest": str(manifest_path),
        "audio_dir": str(audio_dir),
        "examples": rows[:3],
    }
    (args.output_dir / "manifest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="fixie-ai/covost2")
    parser.add_argument("--config", required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-samples", type=int, default=100)
    parser.add_argument("--audio-column", default="audio")
    parser.add_argument("--sample-prefix", default="covost2")
    parser.add_argument("--source-language", default="")
    parser.add_argument("--target-language", default="")
    return parser


def main() -> None:
    print(json.dumps(prepare(build_parser().parse_args()), ensure_ascii=False, indent=2))
    sys.stdout.flush()
    # Some `datasets` streaming audio iterators abort during Python finalization
    # after all rows have been written.  Exit immediately after flushing the
    # report so automation sees the actual preparation status.
    os._exit(0)


if __name__ == "__main__":
    main()
