"""JSONL manifest utilities for speech omni-embedding experiments."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ManifestSummaryConfig:
    manifest: Path
    output: Path | None = None
    top_k: int = 20
    check_audio_exists: bool = True


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarize_manifest(config: ManifestSummaryConfig) -> dict[str, Any]:
    rows = read_jsonl(config.manifest)
    source_counts = Counter(row.get("source", "unknown") for row in rows)
    domain_counts = Counter(row.get("domain", "unknown") for row in rows)
    intent_counts = Counter(row.get("intent", "unknown") for row in rows)
    style_counts = Counter(row.get("query_style", row.get("tts_dialect", "unknown")) for row in rows)
    word_counts = [len(str(row.get("text", "")).split()) for row in rows]

    missing_audio: list[str] = []
    if config.check_audio_exists:
        for row in rows:
            audio_path = str(row.get("audio_path", ""))
            if audio_path and not Path(audio_path).exists():
                missing_audio.append(str(row.get("sample_id", "")))

    summary = {
        "experiment": "manifest_summary",
        "config": asdict(config) | {
            "manifest": str(config.manifest),
            "output": str(config.output) if config.output else "",
        },
        "manifest": str(config.manifest),
        "count": len(rows),
        "sources": source_counts.most_common(config.top_k),
        "domains": domain_counts.most_common(config.top_k),
        "intents": intent_counts.most_common(config.top_k),
        "styles": style_counts.most_common(config.top_k),
        "missing_audio_count": len(missing_audio),
        "missing_audio_examples": missing_audio[:10],
        "text_words": {
            "min": min(word_counts) if word_counts else 0,
            "max": max(word_counts) if word_counts else 0,
            "mean": sum(word_counts) / len(word_counts) if word_counts else 0,
        },
        "field_presence": {
            key: sum(1 for row in rows if row.get(key) not in (None, ""))
            for key in sorted({key for row in rows for key in row})
        },
        "examples": rows[:5],
    }
    if config.output:
        config.output.parent.mkdir(parents=True, exist_ok=True)
        config.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--no-check-audio-exists", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> ManifestSummaryConfig:
    return ManifestSummaryConfig(
        manifest=args.manifest,
        output=args.output,
        top_k=args.top_k,
        check_audio_exists=not args.no_check_audio_exists,
    )


def main() -> None:
    result = summarize_manifest(config_from_args(build_parser().parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
