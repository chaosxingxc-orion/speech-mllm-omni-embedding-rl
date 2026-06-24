"""Low-margin rerank for URO-Bench QA candidate retrieval.

The script consumes a row-level retrieval report, reranks only samples whose
top-1/top-2 score gap is below a threshold, and leaves high-confidence rows
unchanged.  The intended use is to test whether a frozen LLM reranker can repair
the ambiguous tail without adding regressions to stable omni-embedding hits.

API keys are read from an environment variable or an optional local key file and
are never written to the output report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _top_margin(row: dict[str, Any]) -> float:
    scores = row.get("scores", [])
    if len(scores) < 2:
        return float("inf")
    return float(scores[0].get("score", 0.0)) - float(scores[1].get("score", 0.0))


def _unique_text_count(row: dict[str, Any], top_k: int) -> int:
    return len({_normalize_text(candidate.get("text", "")) for candidate in row.get("scores", [])[:top_k]})


def _top_tie_count(row: dict[str, Any], top_k: int, eps: float = 1e-9) -> int:
    scores = row.get("scores", [])[:top_k]
    if not scores:
        return 0
    top_score = float(scores[0].get("score", 0.0))
    return sum(abs(float(candidate.get("score", 0.0)) - top_score) <= eps for candidate in scores)


def _hit_from_top(row: dict[str, Any], top_sample_id: str, top_text: str) -> bool:
    target_text = str(row.get("target_text", "")).strip()
    if target_text and top_text.strip() == target_text:
        return True
    return bool(top_sample_id and top_sample_id == str(row.get("sample_id", "")))


def _read_api_key(env_name: str, key_file: Path | None) -> str:
    key = os.environ.get(env_name, "").strip()
    if key:
        return key
    if key_file is not None:
        return key_file.read_text(encoding="utf-8").strip()
    raise RuntimeError(f"missing API key: set {env_name} or pass --api-key-file")


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in response: {text[:200]}")
    return json.loads(match.group(0))


def _candidate_label(index: int) -> str:
    return chr(ord("A") + index)


def _make_prompt(row: dict[str, Any], top_k: int, prompt_style: str) -> str:
    candidates = []
    for index, candidate in enumerate(row.get("scores", [])[:top_k]):
        candidates.append(
            {
                "choice": _candidate_label(index),
                "sample_id": candidate.get("sample_id", ""),
                "task": candidate.get("dataset_config", ""),
                "candidate_card": candidate.get("text", ""),
                "retrieval_score": candidate.get("score", 0.0),
            }
        )
    base_prompt = (
        "You are a rule-constrained reranker for spoken QA retrieval.\n"
        "Choose the candidate that directly answers the spoken question. "
        "Use only the question and candidate cards. Do not prefer a candidate "
        "just because its retrieval score is higher.\n"
    )
    if prompt_style == "conservative":
        base_prompt += (
            "\nCandidate A is the embedding model's current top-1. Keep A unless "
            "another candidate is unambiguously better. Override A only when the "
            "other candidate's answer is directly supported by the question text "
            "and A is clearly wrong or irrelevant. If two candidates are both "
            "plausible, choose A to avoid regression.\n"
        )
    return (
        base_prompt
        + "\n"
        + f"Spoken question transcript:\n{row.get('query_text', '')}\n\n"
        + f"Candidates:\n{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        + "Return strict JSON only with this schema:\n"
        + (
            "{\"choice\":\"A\", \"confidence\":0.0, "
            "\"accept_override\":false, \"reason_tags\":[\"...\"]}"
        )
    )


def _call_openai_compatible(
    api_key: str,
    api_base: str,
    model: str,
    prompt: str,
    timeout: int,
    max_retries: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You rerank retrieval candidates for QA. Return JSON only. "
                    "Do not include markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 256,
    }
    request = urllib.request.Request(
        api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return _extract_json(content)
        except (urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(sleep_seconds * (attempt + 1))
    raise RuntimeError(f"LLM rerank failed after retries: {last_error}")


def _choose_with_llm(
    row: dict[str, Any],
    api_key: str,
    api_base: str,
    model: str,
    top_k: int,
    prompt_style: str,
    timeout: int,
    max_retries: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    result = _call_openai_compatible(
        api_key=api_key,
        api_base=api_base,
        model=model,
        prompt=_make_prompt(row, top_k, prompt_style),
        timeout=timeout,
        max_retries=max_retries,
        sleep_seconds=sleep_seconds,
    )
    choice = str(result.get("choice", "")).strip().upper()
    choice_index = ord(choice[0]) - ord("A") if choice else -1
    scores = row.get("scores", [])[:top_k]
    if choice_index < 0 or choice_index >= len(scores):
        choice_index = 0
        result["invalid_choice_fallback"] = True
    return {
        "choice_index": choice_index,
        "choice": _candidate_label(choice_index),
        "llm_result": result,
    }


def _choose_with_oracle(row: dict[str, Any], top_k: int) -> dict[str, Any]:
    target_text = str(row.get("target_text", "")).strip()
    for index, candidate in enumerate(row.get("scores", [])[:top_k]):
        if (
            candidate.get("sample_id") == row.get("sample_id")
            or str(candidate.get("text", "")).strip() == target_text
        ):
            return {
                "choice_index": index,
                "choice": _candidate_label(index),
                "llm_result": {"oracle": True},
            }
    return {"choice_index": 0, "choice": "A", "llm_result": {"oracle": True, "miss": True}}


def _rank_to_metrics(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"accuracy": 0.0, "recall_at_3": 0.0, "recall_at_5": 0.0, "mrr": 0.0}
    return {
        "accuracy": sum(rank == 1 for rank in ranks) / len(ranks),
        "recall_at_3": sum(rank <= 3 for rank in ranks) / len(ranks),
        "recall_at_5": sum(rank <= 5 for rank in ranks) / len(ranks),
        "mrr": sum(1.0 / rank for rank in ranks) / len(ranks),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    report = _load_report(args.input)
    rows = report.get("rows", [])
    api_key = ""
    if args.rerank_mode == "llm":
        api_key = _read_api_key(args.api_key_env, args.api_key_file)

    output_rows: list[dict[str, Any]] = []
    ranks: list[int] = []
    routed = 0
    fixes = 0
    regressions = 0
    for row in rows:
        base_hit = bool(row.get("text_hit_at_1", row.get("sample_hit_at_1", False)))
        margin = _top_margin(row)
        unique_texts = _unique_text_count(row, args.top_k)
        top_tie_count = _top_tie_count(row, args.top_k)
        should_route = margin <= args.margin_threshold
        if args.min_unique_texts > 0 and unique_texts < args.min_unique_texts:
            should_route = False
        if args.max_top_tie_count > 0 and top_tie_count > args.max_top_tie_count:
            should_route = False
        if args.max_rerank > 0 and routed >= args.max_rerank:
            should_route = False

        selected_index = 0
        rerank_detail: dict[str, Any] = {}
        if should_route:
            routed += 1
            if args.rerank_mode == "oracle":
                rerank_detail = _choose_with_oracle(row, args.top_k)
            elif args.rerank_mode == "llm":
                rerank_detail = _choose_with_llm(
                    row=row,
                    api_key=api_key,
                    api_base=args.api_base,
                    model=args.model,
                    top_k=args.top_k,
                    prompt_style=args.prompt_style,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                    sleep_seconds=args.sleep_seconds,
                )
            else:
                rerank_detail = {"choice_index": 0, "choice": "A", "llm_result": {"none": True}}
            selected_index = int(rerank_detail["choice_index"])

        candidates = row.get("scores", [])
        selected = candidates[selected_index] if selected_index < len(candidates) else candidates[0]
        hit = _hit_from_top(row, str(selected.get("sample_id", "")), str(selected.get("text", "")))
        if hit and not base_hit:
            fixes += 1
        if base_hit and not hit:
            regressions += 1
        # The reranker chooses a new top-1 candidate only.  Once it overrides
        # the base order, the old gold rank no longer represents the deployed
        # decision, so non-hits must count as misses for all selected-candidate
        # metrics.  Keep richer top-k analysis in the source retrieval report.
        rank = 1 if hit else 10**9
        ranks.append(rank)
        output_rows.append(
            {
                **row,
                "base_margin": margin,
                "unique_text_count": unique_texts,
                "top_tie_count": top_tie_count,
                "rerouted": should_route,
                "selected_choice": _candidate_label(selected_index),
                "selected_sample_id": selected.get("sample_id", ""),
                "selected_dataset_config": selected.get("dataset_config", ""),
                "selected_text": selected.get("text", ""),
                "hit_at_1": hit,
                "rerank_hit_at_1": hit,
                "base_hit_at_1": base_hit,
                "rerank_detail": rerank_detail.get("llm_result", {}),
            }
        )

    result = {
        "experiment": "uro_qa_low_margin_rerank",
        "input": str(args.input),
        "rerank_mode": args.rerank_mode,
        "model": args.model if args.rerank_mode == "llm" else "",
        "prompt_style": args.prompt_style if args.rerank_mode == "llm" else "",
        "top_k": args.top_k,
        "margin_threshold": args.margin_threshold,
        "min_unique_texts": args.min_unique_texts,
        "max_top_tie_count": args.max_top_tie_count,
        "sample_count": len(output_rows),
        "route_count": routed,
        "route_rate": routed / len(output_rows) if output_rows else 0.0,
        "fix_count": fixes,
        "regression_count": regressions,
        "metrics": _rank_to_metrics(ranks),
        "rows": output_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rerank-mode", choices=("none", "oracle", "llm"), default="llm")
    parser.add_argument("--margin-threshold", type=float, default=0.01)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-unique-texts", type=int, default=0)
    parser.add_argument("--max-top-tie-count", type=int, default=0)
    parser.add_argument("--max-rerank", type=int, default=0)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--api-key-file", type=Path, default=None)
    parser.add_argument("--api-base", default="https://api.deepseek.com")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--prompt-style", choices=("standard", "conservative"), default="standard")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
