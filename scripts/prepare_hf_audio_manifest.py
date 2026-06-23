"""Prepare a small JSONL manifest from a Hugging Face audio dataset.

This script is intentionally generic and cache-friendly. It is meant for
semantic speech datasets such as FLEURS, MInDS-14, or small speech-QA
derivatives when they are exposed through the `datasets` Audio feature.

It does not train or modify any model weights.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def _require_datasets():
    try:
        from datasets import Audio
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover - depends on local env
        raise SystemExit(
            "This script requires the `datasets` package. Install the project "
            "runtime dependencies in your experiment environment first."
        ) from exc
    return Audio, load_dataset


def _find_audio_column(example: dict[str, Any], preferred: str) -> str:
    if preferred in example:
        return preferred
    for key, value in example.items():
        if isinstance(value, dict) and ("array" in value or "path" in value):
            return key
    raise KeyError(f"could not find audio column; preferred={preferred!r}")


def _text_value(example: dict[str, Any], field: str) -> str:
    for candidate in [field, "transcription", "transcript", "text", "sentence", "raw_transcription"]:
        value = example.get(candidate)
        if value not in (None, ""):
            return str(value)
    return ""


def _sample_id(example: dict[str, Any], field: str, index: int, prefix: str) -> str:
    if field and example.get(field) not in (None, ""):
        return f"{prefix}_{example[field]}"
    return f"{prefix}_{index:06d}"


def _write_audio(audio: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    source_path = audio.get("path")
    audio_bytes = audio.get("bytes")
    array = audio.get("array")
    sampling_rate = audio.get("sampling_rate")

    if audio_bytes is not None:
        output.write_bytes(audio_bytes)
        return

    if array is not None and sampling_rate:
        try:
            import soundfile as sf
        except Exception as exc:  # pragma: no cover - depends on local env
            if source_path and Path(source_path).exists():
                shutil.copyfile(source_path, output)
                return
            raise SystemExit(
                "Audio arrays require `soundfile` to materialize wav files."
            ) from exc
        sf.write(output, array, int(sampling_rate))
        return

    if source_path and Path(source_path).exists():
        shutil.copyfile(source_path, output)
        return

    raise ValueError("audio example has neither array/sampling_rate nor an existing path")


def _audio_suffix(audio: dict[str, Any], decode_audio: bool) -> str:
    if decode_audio:
        return ".wav"
    source_path = str(audio.get("path") or "")
    suffix = Path(source_path).suffix
    return suffix if suffix else ".audio"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    Audio, load_dataset = _require_datasets()
    dataset = load_dataset(
        args.dataset,
        args.config,
        split=args.split,
        cache_dir=args.cache_dir,
        trust_remote_code=args.trust_remote_code,
        streaming=args.streaming,
    )
    if args.audio_column and getattr(dataset, "features", None) and args.audio_column in dataset.features:
        dataset = dataset.cast_column(
            args.audio_column,
            Audio(sampling_rate=args.sampling_rate if args.decode_audio else None, decode=args.decode_audio),
        )
    if args.streaming:
        if not args.max_samples:
            raise SystemExit("--streaming requires --max-samples for bounded preparation")
        dataset = dataset.take(args.max_samples)
    elif args.max_samples:
        dataset = dataset.select(range(min(args.max_samples, len(dataset))))

    iterator = iter(dataset)
    try:
        first = next(iterator)
    except StopIteration:
        raise SystemExit("dataset split is empty")
    audio_column = _find_audio_column(first, args.audio_column)
    if (
        not (getattr(dataset, "features", None) and audio_column in dataset.features)
        or audio_column != args.audio_column
    ):
        dataset = dataset.cast_column(
            audio_column,
            Audio(sampling_rate=args.sampling_rate if args.decode_audio else None, decode=args.decode_audio),
        )

    audio_dir = args.output_dir / "audio"
    manifest_path = args.output_dir / "manifest.jsonl"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    with manifest_path.open("w", encoding="utf-8") as handle:
        examples = [first] + list(iterator) if args.streaming else dataset
        for index, example in enumerate(examples):
            sample_id = _sample_id(example, args.id_field, index, args.sample_prefix)
            audio_path: Path | None = None
            if not args.skip_audio:
                audio = example[audio_column]
                audio_path = audio_dir / f"{sample_id}{_audio_suffix(audio, args.decode_audio)}"
                _write_audio(audio, audio_path)

            text = _text_value(example, args.text_field)
            row = {
                "sample_id": sample_id,
                "source": args.source or args.dataset,
                "task": args.task,
                "split": args.split,
                "language": args.language,
                "audio_path": str(audio_path) if audio_path else "",
                "text": text,
                "transcript": text,
                "dataset": args.dataset,
                "dataset_config": args.config,
                "dataset_index": index,
            }
            for source_key, target_key in (
                ("id", "source_id"),
                ("raw_transcription", "raw_transcription"),
                ("path", "source_audio_path"),
                ("num_samples", "num_samples"),
                ("gender", "gender"),
                ("language", "dataset_language"),
            ):
                if example.get(source_key) not in (None, ""):
                    row[target_key] = example[source_key]
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "dataset": args.dataset,
        "config": args.config,
        "split": args.split,
        "task": args.task,
        "language": args.language,
        "count": len(rows),
        "manifest": str(manifest_path),
        "audio_dir": "" if args.skip_audio else str(audio_dir),
        "examples": rows[:3],
    }
    (args.output_dir / "manifest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="HF dataset id, e.g. google/fleurs")
    parser.add_argument("--config", default=None, help="HF dataset config, e.g. en_us")
    parser.add_argument("--split", default="validation")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--audio-column", default="audio")
    parser.add_argument("--text-field", default="transcription")
    parser.add_argument("--id-field", default="")
    parser.add_argument("--sample-prefix", default="hf_audio")
    parser.add_argument("--source", default="")
    parser.add_argument("--task", default="asr_semantics")
    parser.add_argument("--language", default="")
    parser.add_argument("--sampling-rate", type=int, default=16000)
    parser.add_argument("--decode-audio", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--streaming", action="store_true")
    return parser


def main() -> None:
    report = build_manifest(build_parser().parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
