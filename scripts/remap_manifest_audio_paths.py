"""Rewrite audio paths in a JSONL manifest.

This is useful when archived manifests were created before a repository move.
The script only rewrites JSONL rows; it does not copy audio or model files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def remap_manifest(input_path: Path, output_path: Path, old_prefix: str, new_prefix: str) -> dict[str, object]:
    rows = []
    changed = 0
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            audio_path = str(row.get("audio_path", ""))
            if old_prefix and audio_path.startswith(old_prefix):
                row["audio_path"] = new_prefix + audio_path[len(old_prefix) :]
                changed += 1
            rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "input": str(input_path),
        "output": str(output_path),
        "row_count": len(rows),
        "changed_count": changed,
        "old_prefix": old_prefix,
        "new_prefix": new_prefix,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--old-prefix", required=True)
    parser.add_argument("--new-prefix", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(
        json.dumps(
            remap_manifest(args.input, args.output, args.old_prefix, args.new_prefix),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
