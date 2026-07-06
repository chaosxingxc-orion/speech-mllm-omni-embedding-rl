"""Summarize memory evidence-packing prompt-budget diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_REPORTS = {
    "heysquad_raw_top5": Path(
        "outputs/omni_memory_v0/heysquad_retrieval_raw_top5_packed_answer_evidence_200.report.json"
    ),
    "heysquad_policy_grounding_top5": Path(
        "outputs/omni_memory_v0/heysquad_retrieval_policy_grounding_top5_packed_answer_evidence_200.report.json"
    ),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(label: str, path: Path) -> dict[str, Any]:
    data = read_json(path)
    original = data["original_prompt_stats"]
    packed = data["packed_prompt_stats"]
    return {
        "label": label,
        "source": str(path),
        "n": data.get("row_count"),
        "style": data.get("style"),
        "original_mean_prompt_tokens": original.get("mean_prompt_tokens"),
        "packed_mean_prompt_tokens": packed.get("mean_prompt_tokens"),
        "mean_token_reduction": data.get("token_reduction"),
        "original_max_prompt_tokens": original.get("max_prompt_tokens"),
        "packed_max_prompt_tokens": packed.get("max_prompt_tokens"),
        "original_overflow_rate": original.get("overflow_rate"),
        "packed_overflow_rate": packed.get("overflow_rate"),
        "overflow_rate_delta": packed.get("overflow_rate", 0.0) - original.get("overflow_rate", 0.0),
        "original_p95_prompt_tokens": original.get("p95_prompt_tokens"),
        "packed_p95_prompt_tokens": packed.get("p95_prompt_tokens"),
        "context_token_budget": packed.get("context_token_budget"),
    }


def run(output: Path) -> dict[str, Any]:
    rows = [summarize(label, path) for label, path in DEFAULT_REPORTS.items()]
    result = {
        "experiment": "memory_packing_summary",
        "note": "Offline prompt-budget diagnostic for evidence-packed retrieved memories.",
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/memory_packing_summary.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
