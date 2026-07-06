"""Build stress variants of omni memory-use manifests by corrupting text hints.

The output keeps audio, candidates, gold labels, and task metadata unchanged,
but rewrites ``asr_text`` / ``text_hint`` so that memory-use runners can test
whether query audio rescues a misleading or degraded textual hint.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9\u4e00-\u9fff]+", str(text).lower())


def token_edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, token_a in enumerate(a, start=1):
        cur = [i]
        for j, token_b in enumerate(b, start=1):
            cur.append(
                min(
                    prev[j] + 1,
                    cur[j - 1] + 1,
                    prev[j - 1] + (0 if token_a == token_b else 1),
                )
            )
        prev = cur
    return prev[-1]


def token_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalize_tokens(reference)
    hyp = normalize_tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return token_edit_distance(ref, hyp) / len(ref)


def first_negative_summary(row: dict[str, Any]) -> str:
    for candidate in row.get("candidate_memories", []):
        if not candidate.get("is_gold"):
            return str(candidate.get("summary") or candidate.get("label") or "")
    return ""


def drop_words(text: str) -> str:
    tokens = str(text).split()
    if len(tokens) <= 2:
        return str(text)
    return " ".join(token for index, token in enumerate(tokens) if index % 2 == 0)


def corrupt_row(row: dict[str, Any], mode: str) -> dict[str, Any]:
    out = dict(row)
    original = str(row.get("asr_text") or row.get("query_text") or "")
    if mode == "neighbor_text":
        replacement = first_negative_summary(row) or original
    elif mode == "drop_words":
        replacement = drop_words(original)
    elif mode == "blank_text":
        replacement = ""
    else:
        raise ValueError(f"unsupported corruption mode: {mode}")
    out["original_asr_text"] = original
    out["asr_text"] = replacement
    out["text_hint"] = replacement
    out["stress_mode"] = mode
    out["stress_text_error_rate"] = token_error_rate(str(row.get("query_text") or original), replacement)
    return out


def natural_drift_rows(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        rate = token_error_rate(str(row.get("query_text") or ""), str(row.get("asr_text") or ""))
        if rate >= threshold:
            out = dict(row)
            out["stress_mode"] = "natural_asr_drift"
            out["stress_text_error_rate"] = rate
            selected.append(out)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=["neighbor_text", "drop_words", "blank_text", "natural_asr_drift"],
        required=True,
    )
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    rows = read_jsonl(args.manifest)
    if args.mode == "natural_asr_drift":
        rows = natural_drift_rows(rows, args.threshold)
    else:
        rows = [corrupt_row(row, args.mode) for row in rows]
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    if args.max_samples and len(rows) > args.max_samples:
        rows = rows[: args.max_samples]
    write_jsonl(args.output, rows)

    report = {
        "source_manifest": str(args.manifest),
        "output": str(args.output),
        "mode": args.mode,
        "n": len(rows),
        "mean_stress_text_error_rate": (
            sum(float(row.get("stress_text_error_rate", 0.0)) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
