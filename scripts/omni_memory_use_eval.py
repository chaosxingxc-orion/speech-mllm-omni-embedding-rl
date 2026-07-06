"""Evaluate fixed-candidate omni memory-use policies.

The runner keeps output protocol / parser / backend flags as validity
prerequisites and compares memory-use policies over a canonical manifest.
It supports a local deterministic backend for smoke tests and llama.cpp-style
backends for frozen generative omni experiments.
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import re
import shlex
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

POLICY_DESCRIPTIONS = {
    "text_summary_only": (
        "Use only the text summaries of candidate memories. Select the memory "
        "that best answers or matches the spoken query."
    ),
    "translation_target_text": (
        "The query is speech in a source language. Use only the candidate text "
        "memories as possible target-language translations. Select the candidate "
        "whose translation best matches the spoken query meaning."
    ),
    "audio_clip_only": (
        "Use the query audio and the candidate memory audio clips. Select the "
        "memory whose spoken content best matches the query."
    ),
    "dual_summary_plus_audio": (
        "Use both candidate text summaries and candidate audio clips. Prefer "
        "the memory whose text and audio jointly support the best answer."
    ),
    "conflict_aware_asr_audio": (
        "The text may contain speech recognition or summary errors. Compare "
        "text evidence against audio evidence and prefer the memory supported "
        "by the audio semantics when they conflict."
    ),
    "task_card_plus_audio": (
        "Use the task card, candidate text summaries, and available audio to "
        "choose the executable or answer-supporting memory. Reject nearby "
        "candidates with different intent or decision boundaries."
    ),
    "two_stage_audio_verify_then_answer": (
        "First infer the meaning of the query and relevant candidate memory "
        "audio. Then select the candidate memory that best supports the final "
        "decision."
    ),
}

COMPACT_POLICY_DESCRIPTIONS = {
    "text_summary_only": "Listen to the query audio and choose the candidate memory whose text summary best matches it.",
    "translation_target_text": "Listen to the source-language query audio and choose the candidate English translation that best matches it.",
    "audio_clip_only": "Listen to the query audio and choose the candidate memory audio clip that best matches it.",
    "dual_summary_plus_audio": "Listen to the query audio and choose the candidate memory whose text and audio best match it.",
    "conflict_aware_asr_audio": "If text and audio conflict, prefer the candidate supported by audio semantics.",
    "task_card_plus_audio": "Choose the candidate memory that matches the requested task, intent, or decision boundary.",
    "two_stage_audio_verify_then_answer": "First compare the audio meanings, then choose the best supporting memory.",
}

POLICIES_WITH_MEMORY_AUDIO = {
    "audio_clip_only",
    "dual_summary_plus_audio",
    "conflict_aware_asr_audio",
    "task_card_plus_audio",
    "two_stage_audio_verify_then_answer",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(8):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.25 * (attempt + 1))


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9\u4e00-\u9fff]+", str(text).lower()))


def parse_prediction(text: str, candidates: list[dict[str, Any]]) -> tuple[str, str, float]:
    answer_region = text
    if "<|channel>final" in answer_region:
        answer_region = answer_region.rsplit("<|channel>final", 1)[-1]
    elif "<channel|>" in answer_region:
        answer_region = answer_region.rsplit("<channel|>", 1)[-1]
    elif "<|channel>thought" in answer_region:
        return "", "no_final_channel", 0.0

    explicit = re.search(r'"answer"\s*:\s*"([A-H])"', answer_region, re.IGNORECASE)
    if not explicit:
        explicit = re.search(r"\b(?:answer|option|choice)\s*[:?]\s*([A-H])\b", answer_region, re.IGNORECASE)
    if explicit:
        index = LABELS.find(explicit.group(1).upper())
        if 0 <= index < len(candidates):
            return str(candidates[index]["memory_id"]), "letter", 1.0
    labels = re.findall(r"\b([A-H])\b", answer_region.upper())
    for label in reversed(labels):
        index = LABELS.find(label)
        if 0 <= index < len(candidates):
            return str(candidates[index]["memory_id"]), "letter", 1.0

    match = re.search(r'"answer"\s*:\s*"([A-Z])"', answer_region, re.IGNORECASE)
    if not match:
        match = re.search(r"\b(?:answer|option|choice)\s*[:：]?\s*([A-Z])\b", answer_region, re.IGNORECASE)
    if not match:
        match = re.search(r"\b([A-Z])\b", answer_region.upper())
    if match:
        label = match.group(1).upper()
        index = LABELS.find(label)
        if 0 <= index < len(candidates):
            return str(candidates[index]["memory_id"]), "letter", 1.0

    normalized_output = normalize_text(answer_region)
    best_id = ""
    best_score = 0.0
    for candidate in candidates:
        candidate_text = normalize_text(
            f"{candidate.get('summary', '')} {candidate.get('label', '')}"
        )
        if not candidate_text:
            continue
        if candidate_text and candidate_text in normalized_output:
            return str(candidate["memory_id"]), "content_exact", 1.0
        candidate_tokens = set(candidate_text.split())
        output_tokens = set(normalized_output.split())
        if not candidate_tokens:
            continue
        score = len(candidate_tokens & output_tokens) / len(candidate_tokens)
        if score > best_score:
            best_id = str(candidate["memory_id"])
            best_score = score
    if best_score >= 0.75:
        return best_id, "content_overlap", best_score
    return "", "none", best_score


def render_candidates(
    candidates: list[dict[str, Any]],
    policy: str,
    include_audio_paths: bool,
    *,
    compact: bool,
) -> list[str]:
    rendered: list[str] = []
    for index, candidate in enumerate(candidates):
        label = LABELS[index]
        summary = str(candidate.get("summary") or "")
        task_label = str(candidate.get("label") or "")
        if compact:
            if policy == "audio_clip_only":
                text = task_label or summary or f"candidate memory {label}"
            else:
                text = summary or task_label or f"candidate memory {label}"
            rendered.append(f"{label}. {text}")
            continue
        parts = [f"{label}. Memory id: {candidate['memory_id']}"]
        if summary and policy != "audio_clip_only":
            parts.append(f"Summary: {summary}")
        if task_label and task_label != summary:
            parts.append(f"Label: {task_label}")
        if include_audio_paths and candidate.get("audio_path"):
            parts.append(f"Audio clip reference: {candidate['audio_path']}")
        rendered.append(". ".join(parts))
    return rendered


def memory_audio_items(
    row: dict[str, Any],
    policy: str,
    memory_audio_limit: int,
) -> list[tuple[int, dict[str, Any]]]:
    if policy not in POLICIES_WITH_MEMORY_AUDIO:
        return []
    items = [
        (index, candidate)
        for index, candidate in enumerate(row.get("candidate_memories", []))
        if candidate.get("audio_path")
    ]
    if memory_audio_limit >= 0:
        return items[:memory_audio_limit]
    return items


def build_prompt(
    row: dict[str, Any],
    policy: str,
    fixed_output_protocol: str,
    prompt_style: str,
    flatten_prompt: bool,
    query_text_hint: bool,
    memory_audio_limit: int,
) -> str:
    candidates = row["candidate_memories"]
    include_audio_paths = policy in POLICIES_WITH_MEMORY_AUDIO
    compact = prompt_style == "compact"
    candidate_lines = render_candidates(candidates, policy, include_audio_paths, compact=compact)
    protocol = {
        "letter": "Reply with exactly one capital option letter and nothing else.",
        "json": 'Reply with exactly this JSON shape: {"answer":"A"}.',
        "anti_answer": (
            "This is a multiple-choice memory-use benchmark. Do not answer the "
            "spoken question directly. Do not translate or explain. Select the "
            "candidate memory option that best supports the task. Reply with "
            "only one capital letter."
        ),
    }[fixed_output_protocol]
    if compact:
        lines = [
            COMPACT_POLICY_DESCRIPTIONS[policy],
            protocol,
        ]
        if query_text_hint:
            lines.append(f"Query text/ASR hint: {row.get('asr_text') or row.get('query_text') or ''}")
        if policy in POLICIES_WITH_MEMORY_AUDIO:
            memory_labels = ", ".join(
                LABELS[index] for index, _ in memory_audio_items(row, policy, memory_audio_limit)
            )
            if not memory_labels:
                memory_labels = "none"
            lines.append(
                "Audio attachments are ordered as: query audio first, "
                f"then candidate memory audio clips {memory_labels}."
            )
        lines.extend(["", *candidate_lines])
        prompt = "\n".join(lines)
        if flatten_prompt:
            return " ".join(line.strip() for line in prompt.splitlines() if line.strip())
        return prompt
    lines = [
        POLICY_DESCRIPTIONS[policy],
        "This is a fixed-candidate memory-use evaluation.",
        "Do not answer the user directly unless the candidate itself is the answer.",
        protocol,
        "",
        f"Task family: {row.get('task_family', '')}",
        f"Spoken query text or ASR hint: {row.get('asr_text') or row.get('query_text') or ''}",
        "",
        "Candidate memories:",
        *candidate_lines,
    ]
    prompt = "\n".join(lines)
    if flatten_prompt:
        return " ".join(line.strip() for line in prompt.splitlines() if line.strip())
    return prompt


def audio_cost_seconds(row: dict[str, Any], policy: str) -> float:
    query_cost = 1.0 if row.get("query_audio_path") and not row.get("_disable_query_audio") else 0.0
    if policy not in POLICIES_WITH_MEMORY_AUDIO:
        return query_cost
    memory_count = len(memory_audio_items(row, policy, int(row.get("_memory_audio_limit", -1))))
    return query_cost + float(memory_count)


def text_cost_tokens(prompt: str) -> int:
    return len(prompt.split())


def call_local(row: dict[str, Any], policy: str, mode: str) -> tuple[str, str, int, str]:
    candidates = list(row["candidate_memories"])
    if mode == "oracle":
        prediction_id = str(row["gold_memory_id"])
    elif mode == "first":
        prediction_id = str(candidates[0]["memory_id"]) if candidates else ""
    elif mode == "random":
        prediction_id = str(random.choice(candidates)["memory_id"]) if candidates else ""
    else:
        raise ValueError(f"Unsupported local mode: {mode}")
    index = next((i for i, item in enumerate(candidates) if str(item["memory_id"]) == prediction_id), -1)
    letter = LABELS[index] if index >= 0 else ""
    return prediction_id, "local_" + mode, 0, letter


def run_command(cmd: list[str], timeout_s: int, capture_backend: str) -> tuple[int, str]:
    if capture_backend == "subprocess":
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_s,
            check=False,
        )
        return proc.returncode, proc.stdout
    if capture_backend == "pty":
        import os
        import pty
        import select

        master_fd, slave_fd = pty.openpty()
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            text=False,
            close_fds=True,
        )
        os.close(slave_fd)
        chunks: list[bytes] = []
        deadline = time.monotonic() + timeout_s
        try:
            while True:
                if time.monotonic() > deadline:
                    proc.kill()
                    return 124, b"".join(chunks).decode("utf-8", errors="replace")
                ready, _, _ = select.select([master_fd], [], [], 0.2)
                if ready:
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        chunk = b""
                    if chunk:
                        chunks.append(chunk)
                if proc.poll() is not None:
                    while True:
                        ready, _, _ = select.select([master_fd], [], [], 0)
                        if not ready:
                            break
                        try:
                            chunk = os.read(master_fd, 4096)
                        except OSError:
                            break
                        if not chunk:
                            break
                        chunks.append(chunk)
                    break
        finally:
            os.close(master_fd)
        return proc.returncode or 0, b"".join(chunks).decode("utf-8", errors="replace")
    with tempfile.NamedTemporaryFile(prefix="omni_memory_use_", suffix=".txt", delete=False) as tmp:
        path = Path(tmp.name)
    shell_cmd = f"timeout {int(timeout_s)}s {shlex.join(cmd)} > {shlex.quote(str(path))} 2>&1"
    proc = subprocess.run(shell_cmd, shell=True, check=False)
    output = path.read_text(encoding="utf-8", errors="replace")
    path.unlink(missing_ok=True)
    return proc.returncode, output


def call_llama_cli(args: argparse.Namespace, row: dict[str, Any], prompt: str) -> tuple[str, str, int, str]:
    if not args.query_audio:
        raise ValueError("llama_cli backend requires query audio; use llama_server for --no-query-audio controls")
    cmd = [
        args.llama_cli,
        "-m",
        args.model,
        "--audio",
        str(row["query_audio_path"]),
        "-p",
        prompt,
        "-n",
        str(args.max_tokens),
        "--temp",
        "0",
        "--ctx-size",
        str(args.ctx_size),
        "--gpu-layers",
        args.gpu_layers,
    ]
    if args.mmproj:
        cmd[3:3] = ["--mmproj", args.mmproj]
    if args.jinja:
        cmd.append("--jinja")
    if args.no_warmup:
        cmd.append("--no-warmup")
    if args.log_disable:
        cmd.append("--log-disable")
    cmd.extend(args.extra_llama_arg)
    code, output = run_command(cmd, args.timeout_s, args.capture_backend)
    pred_id, method, _ = parse_prediction(output, row["candidate_memories"])
    return pred_id, method, code, output[-2000:]


def call_llama_chat_multi_audio(
    args: argparse.Namespace, row: dict[str, Any], policy: str, prompt: str
) -> tuple[str, str, int, str]:
    if not args.mmproj:
        raise ValueError("llama_chat_multi_audio requires --mmproj")
    lines = []
    if args.query_audio and row.get("query_audio_path"):
        lines.append(f"/audio {row['query_audio_path']}")
    for _, candidate in memory_audio_items(row, policy, args.memory_audio_limit):
        lines.append(f"/audio {candidate['audio_path']}")
    lines.extend([prompt, "/exit"])
    stdin_text = "\n".join(lines) + "\n"
    cmd = [
        args.llama_cli,
        "-m",
        args.model,
        "--mmproj",
        args.mmproj,
        "-n",
        str(args.max_tokens),
        "--temp",
        "0",
        "--ctx-size",
        str(args.ctx_size),
        "--gpu-layers",
        args.gpu_layers,
    ]
    if args.jinja:
        cmd.append("--jinja")
    if args.no_warmup:
        cmd.append("--no-warmup")
    if args.log_disable:
        cmd.append("--log-disable")
    cmd.extend(args.extra_llama_arg)
    start = time.monotonic()
    proc = subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=args.timeout_s,
        check=False,
    )
    _ = start  # keep timing in caller for a single source of truth
    pred_id, method, _ = parse_prediction(proc.stdout, row["candidate_memories"])
    return pred_id, method, proc.returncode, proc.stdout[-2000:]


def audio_format(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in {"mp3", "wav"}:
        return suffix
    return "wav"


def audio_part(path: str) -> dict[str, Any]:
    data = Path(path).read_bytes()
    return {
        "type": "input_audio",
        "input_audio": {
            "data": base64.b64encode(data).decode("ascii"),
            "format": audio_format(path),
        },
    }


def call_llama_server(
    args: argparse.Namespace,
    row: dict[str, Any],
    policy: str,
    prompt: str,
) -> tuple[str, str, int, str]:
    content: list[dict[str, Any]] = []
    query_audio_path = str(row.get("query_audio_path") or "")
    if args.query_audio and query_audio_path:
        content.append(audio_part(query_audio_path))
    for _, candidate in memory_audio_items(row, policy, args.memory_audio_limit):
        memory_audio_path = str(candidate.get("audio_path") or "")
        if memory_audio_path:
            content.append(audio_part(memory_audio_path))
    content.append({"type": "text", "text": prompt})
    payload = {
        "model": args.model_name,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    request = urllib.request.Request(
        args.server_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    attempts = max(1, int(args.server_retries) + 1)
    last_status = 0
    last_body = ""
    for attempt in range(attempts):
        try:
            with opener.open(request, timeout=args.timeout_s) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = response.status
            data = json.loads(body)
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            output = str(message.get("content") or "")
            if message.get("reasoning_content"):
                output = str(message.get("reasoning_content")) + "\n" + output
            pred_id, method, _ = parse_prediction(output, row["candidate_memories"])
            return pred_id, method, status, output[-2000:]
        except urllib.error.HTTPError as exc:
            last_status = exc.code
            last_body = exc.read().decode("utf-8", errors="replace")
            if exc.code < 500 or attempt + 1 >= attempts:
                break
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_status = 0
            last_body = str(exc)
            if attempt + 1 >= attempts:
                break
        time.sleep(min(2.0, 0.5 * (attempt + 1)))
    return "", "http_error", last_status, last_body[-2000:]


def load_baseline(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"baseline output not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(row.get("query_id")): row for row in data.get("rows", [])}


def evaluate_row(
    args: argparse.Namespace,
    row: dict[str, Any],
    baseline_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = dict(row)
    if args.candidate_shuffle_seed is not None:
        row["candidate_memories"] = list(row.get("candidate_memories", []))
        row_id = str(row.get("query_id") or row.get("sample_id"))
        random.Random(f"{args.candidate_shuffle_seed}:{row_id}").shuffle(row["candidate_memories"])
    row["_disable_query_audio"] = not args.query_audio
    row["_memory_audio_limit"] = args.memory_audio_limit
    prompt = build_prompt(
        row,
        args.policy,
        args.fixed_output_protocol,
        args.prompt_style,
        args.flatten_prompt,
        args.query_text_hint,
        args.memory_audio_limit,
    )
    start = time.monotonic()
    error = ""
    model_output = ""
    returncode = 0
    try:
        if args.backend == "local_oracle":
            pred_id, parse_method, returncode, model_output = call_local(row, args.policy, "oracle")
        elif args.backend == "local_first":
            pred_id, parse_method, returncode, model_output = call_local(row, args.policy, "first")
        elif args.backend == "local_random":
            pred_id, parse_method, returncode, model_output = call_local(row, args.policy, "random")
        elif args.backend == "llama_cli":
            pred_id, parse_method, returncode, model_output = call_llama_cli(args, row, prompt)
        elif args.backend == "llama_chat_multi_audio":
            pred_id, parse_method, returncode, model_output = call_llama_chat_multi_audio(
                args, row, args.policy, prompt
            )
        elif args.backend == "llama_server":
            pred_id, parse_method, returncode, model_output = call_llama_server(
                args, row, args.policy, prompt
            )
        else:
            raise ValueError(f"Unsupported backend: {args.backend}")
    except subprocess.TimeoutExpired as exc:
        pred_id = ""
        parse_method = "timeout"
        returncode = 124
        model_output = str(exc.stdout or "")[-2000:]
        error = "timeout"
    except Exception as exc:  # pragma: no cover - row-level resilience
        pred_id = ""
        parse_method = "exception"
        returncode = -1
        model_output = ""
        error = f"{type(exc).__name__}:{str(exc)[:180]}"

    latency_ms = int((time.monotonic() - start) * 1000)
    gold_id = str(row["gold_memory_id"])
    invalid = not pred_id
    task_success = pred_id == gold_id
    selected_memory = next(
        (item for item in row.get("candidate_memories", []) if str(item.get("memory_id")) == pred_id),
        None,
    )
    grounded = bool(selected_memory and selected_memory.get("is_gold"))
    wrong_memory = bool(pred_id and pred_id != gold_id)
    query_id = str(row.get("query_id") or row.get("sample_id"))
    baseline_row = baseline_rows.get(query_id, {})
    regression = bool(baseline_row.get("task_success") and not task_success)
    return {
        "query_id": query_id,
        "policy_id": args.policy,
        "backend": args.backend,
        "task_family": row.get("task_family", ""),
        "prediction": pred_id,
        "gold_memory_id": gold_id,
        "gold_answer": row.get("gold_answer", ""),
        "task_success": task_success,
        "grounded_memory_use": grounded,
        "wrong_memory": wrong_memory,
        "invalid_output": invalid,
        "parse_method": parse_method,
        "returncode": returncode,
        "error": error,
        "text_cost": text_cost_tokens(prompt),
        "audio_cost": audio_cost_seconds(row, args.policy),
        "latency_ms": latency_ms,
        "regression_vs_text_only": regression,
        "candidate_memory_ids": [item.get("memory_id") for item in row.get("candidate_memories", [])],
        "prompt": prompt if args.include_prompts else "",
        "model_output": model_output,
    }


def aggregate(args: argparse.Namespace, rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if not n:
        return {
            "experiment": "omni_memory_use_eval",
            "policy": args.policy,
            "backend": args.backend,
            "n": 0,
        }
    return {
        "experiment": "omni_memory_use_eval",
        "policy": args.policy,
        "backend": args.backend,
        "split": args.split,
        "query_audio": args.query_audio,
        "query_text_hint": args.query_text_hint,
        "candidate_shuffle_seed": args.candidate_shuffle_seed,
        "memory_audio_limit": args.memory_audio_limit,
        "n": n,
        "task_success": sum(row["task_success"] for row in rows) / n,
        "grounded_memory_use": sum(row["grounded_memory_use"] for row in rows) / n,
        "wrong_memory": sum(row["wrong_memory"] for row in rows) / n,
        "invalid_output": sum(row["invalid_output"] for row in rows) / n,
        "mean_text_cost": sum(row["text_cost"] for row in rows) / n,
        "mean_audio_cost": sum(row["audio_cost"] for row in rows) / n,
        "mean_latency_ms": sum(row["latency_ms"] for row in rows) / n,
        "regression_vs_text_only": sum(row["regression_vs_text_only"] for row in rows) / n,
        "regression_count": sum(row["regression_vs_text_only"] for row in rows),
        "rows": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-output", type=Path)
    parser.add_argument("--policy", choices=sorted(POLICY_DESCRIPTIONS), required=True)
    parser.add_argument(
        "--backend",
        choices=[
            "local_oracle",
            "local_first",
            "local_random",
            "llama_cli",
            "llama_chat_multi_audio",
            "llama_server",
        ],
        default="local_oracle",
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--model-name", default="local-model")
    parser.add_argument("--server-url", default="http://127.0.0.1:8080")
    parser.add_argument("--mmproj", default="")
    parser.add_argument("--llama-cli", default="llama-cli")
    parser.add_argument("--split", default="")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--fixed-output-protocol", choices=["letter", "json", "anti_answer"], default="letter")
    parser.add_argument("--prompt-style", choices=["verbose", "compact"], default="verbose")
    parser.add_argument("--flatten-prompt", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--query-audio", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--query-text-hint", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--candidate-shuffle-seed", type=int)
    parser.add_argument("--memory-audio-limit", type=int, default=-1)
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--server-retries", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--ctx-size", type=int, default=1024)
    parser.add_argument("--gpu-layers", default="auto")
    parser.add_argument("--capture-backend", choices=["subprocess", "shell_file", "pty"], default="shell_file")
    parser.add_argument("--jinja", action=argparse.BooleanOptionalAction, default=False)
    warmup_group = parser.add_mutually_exclusive_group()
    warmup_group.add_argument("--no-warmup", dest="no_warmup", action="store_true")
    warmup_group.add_argument("--warmup", dest="no_warmup", action="store_false")
    parser.set_defaults(no_warmup=True)
    parser.add_argument("--log-disable", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--extra-llama-arg", action="append", default=[])
    parser.add_argument("--include-prompts", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source_rows = read_jsonl(args.manifest)
    baseline_rows = load_baseline(args.baseline_output)
    if args.start_index < 0:
        raise ValueError("--start-index must be non-negative")
    selected = source_rows[args.start_index :]
    if args.max_samples and args.max_samples > 0:
        selected = selected[: args.max_samples]

    output_rows: list[dict[str, Any]] = []
    completed: set[str] = set()
    if args.resume and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        output_rows = list(existing.get("rows", []))
        completed = {str(row.get("query_id")) for row in output_rows}

    for row in selected:
        row_id = str(row.get("query_id") or row.get("sample_id"))
        if row_id in completed:
            continue
        output_rows.append(evaluate_row(args, row, baseline_rows))
        write_json(args.output, aggregate(args, output_rows))
    write_json(args.output, aggregate(args, output_rows))


if __name__ == "__main__":
    main()
