"""Low-margin top-k verifier for frozen omni retrieval outputs.

This script consumes existing row-level retrieval JSON.  It does not reload an
embedding model and does not change model weights.  For rows whose raw top-1 /
top-2 score margin is below a fixed threshold, it asks a verifier to choose
among the raw top-k candidates; high-margin rows keep the raw top-1.

Supported verifier modes:

* oracle: choose the gold candidate when it appears in top-k; upper bound only.
* llm: use an OpenAI-compatible chat API as a frozen verifier.

API keys are read from an environment variable or an optional local key file and
are never written to the output report.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_id(row: dict[str, Any]) -> str:
    value = row.get("sample_id", row.get("id"))
    if value is None:
        raise ValueError(f"row has no sample_id/id: {row}")
    return str(value)


def row_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = row.get("scores")
    if isinstance(candidates, list):
        return candidates
    candidates = row.get("top_labels")
    if isinstance(candidates, list):
        return candidates
    raise ValueError(f"row has no scores/top_labels: {sample_id(row)}")


def candidate_text(candidate: dict[str, Any]) -> str:
    return str(candidate.get("text", candidate.get("label", "")))


def candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("sample_id", candidate.get("label", candidate_text(candidate))))


def target_text(row: dict[str, Any]) -> str:
    return str(row.get("target_text", row.get("target", "")))


def query_text(row: dict[str, Any]) -> str:
    return str(row.get("query_text", row.get("text", row.get("transcript", ""))))


def base_prediction(row: dict[str, Any]) -> str:
    return str(row.get("top_text", row.get("prediction", "")))


def base_rank(row: dict[str, Any], hit_mode: str) -> int:
    if hit_mode == "text" and "text_rank" in row:
        return int(row["text_rank"])
    if hit_mode == "sample" and "sample_rank" in row:
        return int(row["sample_rank"])
    if "rank" in row:
        return int(row["rank"])
    if "text_rank" in row:
        return int(row["text_rank"])
    if "sample_rank" in row:
        return int(row["sample_rank"])
    return 1 if base_hit(row, hit_mode) else 10**9


def base_hit(row: dict[str, Any], hit_mode: str) -> bool:
    if hit_mode == "text" and "text_hit_at_1" in row:
        return bool(row["text_hit_at_1"])
    if hit_mode == "sample" and "sample_hit_at_1" in row:
        return bool(row["sample_hit_at_1"])
    if "hit_at_1" in row:
        return bool(row["hit_at_1"])
    if "text_hit_at_1" in row:
        return bool(row["text_hit_at_1"])
    if "sample_hit_at_1" in row:
        return bool(row["sample_hit_at_1"])
    return base_rank(row, hit_mode) == 1


def selected_hit(row: dict[str, Any], candidate: dict[str, Any], hit_mode: str) -> bool:
    target = target_text(row).strip()
    if hit_mode in {"auto", "text"} and target:
        if candidate_text(candidate).strip() == target:
            return True
    if hit_mode in {"auto", "sample"}:
        if candidate_id(candidate) == sample_id(row):
            return True
    return False


def gold_rank_in_candidates(row: dict[str, Any], hit_mode: str) -> int:
    for index, candidate in enumerate(row_candidates(row)):
        if selected_hit(row, candidate, hit_mode):
            return index + 1
    return 10**9


def score_margin(row: dict[str, Any]) -> float:
    candidates = row_candidates(row)
    if len(candidates) < 2:
        return float("inf")
    return float(candidates[0].get("score", 0.0)) - float(candidates[1].get("score", 0.0))


def label_family(label: str) -> str:
    return label.split("_", 1)[0] if "_" in label else label


def candidate_label(index: int) -> str:
    return chr(ord("A") + index)


def label_index(choice: str) -> int:
    choice = str(choice or "").strip().upper()
    if not choice:
        return -1
    return ord(choice[0]) - ord("A")


def read_api_key(env_name: str, key_file: Path | None) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    if key_file:
        return key_file.read_text(encoding="utf-8").strip()
    raise RuntimeError(f"missing API key: set {env_name} or pass --api-key-file")


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    # Some chat models occasionally return a nearly-JSON object with an
    # unescaped quote in the reason field.  The choice is the only field needed
    # for deterministic reranking, so fall back to a narrow parser instead of
    # failing the whole experiment.
    choice_match = re.search(r'"?choice"?\s*[:=]\s*"?([A-Z])"?', text, flags=re.IGNORECASE)
    if choice_match:
        confidence_match = re.search(
            r'"?confidence"?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)',
            text,
            flags=re.IGNORECASE,
        )
        payload: dict[str, Any] = {
            "choice": choice_match.group(1).upper(),
            "parse_fallback": True,
        }
        if confidence_match:
            payload["confidence"] = float(confidence_match.group(1))
        return payload
    bare_choice = re.search(r"\b([A-Z])\b", text)
    if bare_choice:
        return {"choice": bare_choice.group(1).upper(), "parse_fallback": True}
    raise ValueError(f"no choice found in response: {text[:200]}")


def build_prompt(row: dict[str, Any], top_k: int, task: str, prompt_style: str) -> str:
    candidates = []
    for index, candidate in enumerate(row_candidates(row)[:top_k]):
        candidates.append(
            {
                "choice": candidate_label(index),
                "candidate": candidate_text(candidate),
                "retrieval_score": candidate.get("score"),
            }
        )
    if task == "tool_intent":
        task_text = (
            "You are verifying a spoken command intent.  Choose the tool intent "
            "label that best matches the user's utterance.  Prefer exact user "
            "goal and action boundary over broad topical similarity."
        )
        input_label = "Spoken command transcript"
    elif task == "translation":
        task_text = (
            "You are verifying speech translation retrieval.  Choose the English "
            "candidate that best translates the source-language utterance. "
            "Prefer meaning equivalence over topical association."
        )
        input_label = "Source utterance transcript"
    else:
        task_text = "Choose the candidate that best matches the query."
        input_label = "Query"
    if prompt_style == "conservative":
        task_text += (
            " Candidate A is the embedding model's current top-1. Keep A unless "
            "another candidate is clearly and directly better. If uncertain, choose A."
        )
    return (
        f"{task_text}\n\n"
        f"{input_label}:\n{query_text(row)}\n\n"
        f"Candidates:\n{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        "Return strict JSON only with this schema:\n"
        "{\"choice\":\"A\", \"confidence\":0.0, \"reason\":\"short reason\"}"
    )


def call_openai_compatible(
    *,
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
                "content": "You are a deterministic reranker. Return JSON only.",
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
            return extract_json(content)
        except (urllib.error.URLError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(sleep_seconds * (attempt + 1))
    raise RuntimeError(f"verifier call failed after retries: {last_error}")


def choose_oracle(row: dict[str, Any], top_k: int, hit_mode: str) -> dict[str, Any]:
    for index, candidate in enumerate(row_candidates(row)[:top_k]):
        if selected_hit(row, candidate, hit_mode):
            return {"choice_index": index, "detail": {"oracle": True}}
    return {"choice_index": 0, "detail": {"oracle": True, "miss": True}}


def choose_llm(
    row: dict[str, Any],
    *,
    top_k: int,
    task: str,
    prompt_style: str,
    api_key: str,
    api_base: str,
    model: str,
    timeout: int,
    max_retries: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    detail = call_openai_compatible(
        api_key=api_key,
        api_base=api_base,
        model=model,
        prompt=build_prompt(row, top_k, task, prompt_style),
        timeout=timeout,
        max_retries=max_retries,
        sleep_seconds=sleep_seconds,
    )
    index = label_index(str(detail.get("choice", "")))
    if index < 0 or index >= min(top_k, len(row_candidates(row))):
        index = 0
        detail["invalid_choice_fallback"] = True
    return {"choice_index": index, "detail": detail}


def ranks_to_metrics(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"accuracy_at_1": 0.0, "recall_at_3": 0.0, "recall_at_5": 0.0, "mrr": 0.0}
    return {
        "accuracy_at_1": sum(rank == 1 for rank in ranks) / len(ranks),
        "recall_at_3": sum(rank <= 3 for rank in ranks) / len(ranks),
        "recall_at_5": sum(rank <= 5 for rank in ranks) / len(ranks),
        "mrr": sum(1.0 / rank for rank in ranks) / len(ranks),
    }


def bootstrap_ci(diffs: list[int], rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(rounds)
    ]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def make_output_row(
    row: dict[str, Any],
    *,
    args: argparse.Namespace,
    should_route: bool,
    selected_index: int,
    detail: dict[str, Any],
) -> dict[str, Any]:
    candidates = row_candidates(row)
    selected = candidates[selected_index] if selected_index < len(candidates) else candidates[0]
    hit = selected_hit(row, selected, args.hit_mode)
    raw_rank = gold_rank_in_candidates(row, args.hit_mode)
    raw_hit = raw_rank == 1
    deployed_rank = 1 if hit else 10**9
    return {
        **row,
        "low_margin_verifier": {
            "margin": score_margin(row),
            "threshold": args.margin_threshold,
            "routed": should_route,
            "verifier_mode": args.verifier_mode,
            "top_k": args.top_k,
            "selected_choice": candidate_label(selected_index),
            "selected_candidate": candidate_text(selected),
            "base_prediction": base_prediction(row),
            "base_rank": raw_rank,
            "base_hit_at_1": raw_hit,
            "hit_at_1": hit,
            "detail": detail,
        },
        "prediction": candidate_text(selected) if args.task == "tool_intent" else row.get("prediction"),
        "top_text": candidate_text(selected) if args.task == "translation" else row.get("top_text"),
        "hit_at_1": hit,
        "text_hit_at_1": hit if "text_hit_at_1" in row else row.get("text_hit_at_1"),
        "sample_hit_at_1": hit if "sample_hit_at_1" in row else row.get("sample_hit_at_1"),
        "rank": deployed_rank if "rank" in row else row.get("rank"),
        "text_rank": deployed_rank if "text_rank" in row else row.get("text_rank"),
        "sample_rank": deployed_rank if "sample_rank" in row else row.get("sample_rank"),
    }


def completed_row_compatible(row: dict[str, Any], args: argparse.Namespace) -> bool:
    verifier = row.get("low_margin_verifier")
    if not isinstance(verifier, dict):
        return False
    return (
        verifier.get("verifier_mode") == args.verifier_mode
        and int(verifier.get("top_k", -1)) == args.top_k
        and abs(float(verifier.get("threshold", float("nan"))) - args.margin_threshold) < 1e-12
    )


def load_completed_rows(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    if not args.resume or not args.output.exists():
        return {}
    existing = read_json(args.output)
    rows = existing.get("rows")
    if not isinstance(rows, list):
        return {}
    completed: dict[str, dict[str, Any]] = {}
    for row in rows:
        try:
            row_id = sample_id(row)
        except ValueError:
            continue
        if completed_row_compatible(row, args):
            completed[row_id] = row
    return completed


def build_result(
    *,
    args: argparse.Namespace,
    output_rows: list[dict[str, Any]],
    requested_count: int,
    complete: bool,
    reused_count: int,
    new_count: int,
) -> dict[str, Any]:
    deployed_ranks: list[int] = []
    base_ranks: list[int] = []
    diffs: list[int] = []
    route_count = 0
    fixes = 0
    regressions = 0
    unsafe_wrong_tool = 0
    boundary_error = 0

    for row in output_rows:
        verifier = row.get("low_margin_verifier", {})
        routed = bool(verifier.get("routed"))
        route_count += int(routed)
        raw_rank = int(verifier.get("base_rank", gold_rank_in_candidates(row, args.hit_mode)))
        raw_hit = raw_rank == 1
        hit = bool(verifier.get("hit_at_1", row.get("hit_at_1")))
        deployed_rank = 1 if hit else 10**9
        deployed_ranks.append(deployed_rank)
        base_ranks.append(raw_rank)
        diff = int(hit) - int(raw_hit)
        diffs.append(diff)
        fixes += diff > 0
        regressions += diff < 0

        if args.task == "tool_intent" and not hit:
            gold_family = label_family(target_text(row))
            selected_family = label_family(str(verifier.get("selected_candidate", "")))
            if gold_family != selected_family:
                unsafe_wrong_tool += 1
            else:
                boundary_error += 1

    metrics = ranks_to_metrics(deployed_ranks)
    base_metrics = ranks_to_metrics(base_ranks)
    result = {
        "experiment": "low_margin_topk_verifier",
        "input": str(args.input),
        "task": args.task,
        "verifier_mode": args.verifier_mode,
        "model": args.model if args.verifier_mode == "llm" else "",
        "prompt_style": args.prompt_style if args.verifier_mode == "llm" else "",
        "hit_mode": args.hit_mode,
        "top_k": args.top_k,
        "margin_threshold": args.margin_threshold,
        "requested_count": requested_count,
        "sample_count": len(output_rows),
        "complete": complete,
        "resume_enabled": bool(args.resume),
        "reused_row_count": reused_count,
        "new_row_count": new_count,
        "route_count": route_count,
        "route_rate": route_count / len(output_rows) if output_rows else 0.0,
        "fix_count": fixes,
        "regression_count": regressions,
        "regression_rate": regressions / len(output_rows) if output_rows else 0.0,
        "base_metrics": base_metrics,
        "metrics": metrics,
        "delta": {
            "accuracy_at_1": metrics["accuracy_at_1"] - base_metrics["accuracy_at_1"],
            "ci95": bootstrap_ci(diffs, args.bootstrap_rounds, args.bootstrap_seed),
        },
        "tool_utility": {
            "tool_call_success": metrics["accuracy_at_1"],
            "unsafe_wrong_tool_rate": unsafe_wrong_tool / len(output_rows)
            if args.task == "tool_intent" and output_rows
            else 0.0,
            "boundary_error_rate": boundary_error / len(output_rows)
            if args.task == "tool_intent" and output_rows
            else 0.0,
        },
        "rows": output_rows,
    }
    return result


def write_checkpoint(
    args: argparse.Namespace,
    output_rows: list[dict[str, Any]],
    requested_count: int,
    reused_count: int,
    new_count: int,
    complete: bool,
) -> None:
    result = build_result(
        args=args,
        output_rows=output_rows,
        requested_count=requested_count,
        complete=complete,
        reused_count=reused_count,
        new_count=new_count,
    )
    write_json(args.output, result)


def run(args: argparse.Namespace) -> dict[str, Any]:
    report = read_json(args.input)
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("input report has no rows")
    if args.max_samples > 0:
        rows = rows[: args.max_samples]

    api_key = ""
    if args.verifier_mode == "llm":
        api_key = read_api_key(args.api_key_env, args.api_key_file)

    completed_rows = load_completed_rows(args)
    output_rows: list[dict[str, Any]] = []
    route_count = 0
    reused_count = 0
    new_count = 0
    stopped_early = False

    for row in rows:
        row_id = sample_id(row)
        completed = completed_rows.get(row_id)
        if completed is not None:
            output_rows.append(completed)
            route_count += int(bool(completed.get("low_margin_verifier", {}).get("routed")))
            reused_count += 1
            continue

        margin = score_margin(row)
        should_route = margin <= args.margin_threshold
        if args.max_rerank > 0 and route_count >= args.max_rerank:
            should_route = False
        selected_index = 0
        detail: dict[str, Any] = {}
        if should_route:
            route_count += 1
            if args.verifier_mode == "oracle":
                decision = choose_oracle(row, args.top_k, args.hit_mode)
            elif args.verifier_mode == "llm":
                decision = choose_llm(
                    row,
                    top_k=args.top_k,
                    task=args.task,
                    prompt_style=args.prompt_style,
                    api_key=api_key,
                    api_base=args.api_base,
                    model=args.model,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                    sleep_seconds=args.sleep_seconds,
                )
            else:
                decision = {"choice_index": 0, "detail": {"none": True}}
            selected_index = int(decision["choice_index"])
            detail = decision["detail"]

        output_rows.append(
            make_output_row(
                row,
                args=args,
                should_route=should_route,
                selected_index=selected_index,
                detail=detail,
            )
        )
        new_count += 1

        if args.checkpoint_every > 0 and new_count % args.checkpoint_every == 0:
            write_checkpoint(
                args,
                output_rows,
                requested_count=len(rows),
                reused_count=reused_count,
                new_count=new_count,
                complete=False,
            )
        if args.stop_after_new_rows > 0 and new_count >= args.stop_after_new_rows:
            stopped_early = True
            break

    result = build_result(
        args=args,
        output_rows=output_rows,
        requested_count=len(rows),
        complete=not stopped_early and len(output_rows) == len(rows),
        reused_count=reused_count,
        new_count=new_count,
    )
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--task", choices=["tool_intent", "translation"], required=True)
    parser.add_argument("--hit-mode", choices=["auto", "sample", "text"], default="auto")
    parser.add_argument("--verifier-mode", choices=["none", "oracle", "llm"], default="oracle")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--margin-threshold", type=float, default=0.01)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--max-rerank", type=int, default=0)
    parser.add_argument("--prompt-style", choices=["plain", "conservative"], default="conservative")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--api-key-file", type=Path, default=None)
    parser.add_argument("--api-base", default="https://api.deepseek.com")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse compatible completed rows from --output and continue unfinished rows.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
        help="Write a partial output after this many newly processed rows; 0 disables checkpoints.",
    )
    parser.add_argument(
        "--stop-after-new-rows",
        type=int,
        default=0,
        help="Process only this many new rows, useful for chunked long API runs.",
    )
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=13)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "experiment": result["experiment"],
                "task": result["task"],
                "verifier_mode": result["verifier_mode"],
                "requested_count": result["requested_count"],
                "sample_count": result["sample_count"],
                "complete": result["complete"],
                "resume_enabled": result["resume_enabled"],
                "reused_row_count": result["reused_row_count"],
                "new_row_count": result["new_row_count"],
                "route_rate": result["route_rate"],
                "base_metrics": result["base_metrics"],
                "metrics": result["metrics"],
                "delta": result["delta"],
                "fix_count": result["fix_count"],
                "regression_count": result["regression_count"],
                "tool_utility": result["tool_utility"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
