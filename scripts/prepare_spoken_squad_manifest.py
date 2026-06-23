"""Prepare a small Spoken-SQuAD/HeySQuAD-style speech QA manifest from Hugging Face.

The first supported source is `AudioLLMs/spoken_squad_test`, which exposes a
spoken context/passage audio column named `context`, the text question in
`instruction`, and a short gold answer in `answer`.

It also supports HeySQuAD-style datasets that expose spoken question audio,
question text, passage context, and SQuAD-like answers.

This script does not decode audio or train any model.
"""

from __future__ import annotations

import argparse
import json
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
    audio_bytes = audio.get("bytes")
    if isinstance(audio_bytes, bytes):
        if audio_bytes[:4] == b"RIFF":
            return ".wav"
        if audio_bytes[:3] == b"ID3":
            return ".mp3"
    source_path = str(audio.get("path") or "")
    suffix = Path(source_path).suffix
    return suffix if suffix else ".audio"


def _write_audio(audio: dict[str, Any], output: Path) -> None:
    audio_bytes = audio.get("bytes")
    if audio_bytes is None:
        raise ValueError("expected audio bytes from decode=False dataset column")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio_bytes)


def _extract_answer(example: dict[str, Any], answer_field: str) -> tuple[str, Any]:
    value = example.get(answer_field)
    if isinstance(value, str):
        return value.strip(), value
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict) and first.get("text") not in (None, ""):
            return str(first["text"]).strip(), value
        if isinstance(first, str):
            return first.strip(), value
    if isinstance(value, dict):
        texts = value.get("text")
        if isinstance(texts, list) and texts:
            return str(texts[0]).strip(), value
        if isinstance(texts, str):
            return texts.strip(), value
    return "", value


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    Audio, load_dataset = _require_datasets()
    dataset = load_dataset(
        args.dataset,
        split=args.split,
        cache_dir=args.cache_dir,
        streaming=args.streaming,
    )
    dataset = dataset.cast_column(args.audio_column, Audio(decode=False))
    if args.streaming:
        dataset = dataset.take(args.max_samples)
    elif args.max_samples:
        dataset = dataset.select(range(min(args.max_samples, len(dataset))))

    output_dir = args.output_dir
    audio_dir = output_dir / "audio"
    manifest_path = output_dir / "manifest.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with manifest_path.open("w", encoding="utf-8") as handle:
        for index, example in enumerate(dataset):
            sample_id = f"{args.sample_prefix}_{index:06d}"
            question = str(example.get(args.question_field, "")).strip()
            transcription = str(example.get(args.transcription_field, question)).strip()
            context = str(example.get(args.context_field, "")).strip()
            answer, raw_answers = _extract_answer(example, args.answer_field)
            audio = example[args.audio_column]
            audio_path = audio_dir / f"{sample_id}{_audio_suffix(audio)}"
            _write_audio(audio, audio_path)
            row = {
                "sample_id": sample_id,
                "source": args.source,
                "task": "speech_qa",
                "split": args.split,
                "language": args.language,
                "audio_path": str(audio_path),
                "question": question,
                "text": question,
                "transcript": transcription or question,
                "context": context,
                "answer": answer,
                "raw_answers": raw_answers,
                "audio_role": args.audio_role,
                "dataset": args.dataset,
                "dataset_config": "",
                "dataset_index": index,
                "construction_note": (
                    args.construction_note
                    or "HF speech-QA manifest with audio, question, context if available, and answer."
                ),
            }
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "dataset": args.dataset,
        "split": args.split,
        "count": len(rows),
        "manifest": str(manifest_path),
        "audio_dir": str(audio_dir),
        "examples": rows[:3],
    }
    (output_dir / "manifest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="AudioLLMs/spoken_squad_test")
    parser.add_argument("--split", default="test")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-samples", type=int, default=12)
    parser.add_argument("--audio-column", default="context")
    parser.add_argument("--question-field", default="instruction")
    parser.add_argument("--transcription-field", default="transcription")
    parser.add_argument("--context-field", default="context")
    parser.add_argument("--answer-field", default="answer")
    parser.add_argument("--sample-prefix", default="spoken_squad")
    parser.add_argument("--source", default="spoken_squad_hf")
    parser.add_argument("--language", default="en")
    parser.add_argument("--audio-role", default="spoken_context")
    parser.add_argument("--construction-note", default="")
    parser.add_argument("--streaming", action="store_true")
    return parser


def main() -> None:
    report = build_manifest(build_parser().parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
