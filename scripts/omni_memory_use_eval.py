"""Evaluate fixed-candidate omni memory-use policies.

The runner keeps output protocol / parser / backend flags as validity
prerequisites and compares memory-use policies over a canonical manifest.
It supports a local deterministic backend for smoke tests and llama.cpp-style
backends for frozen generative omni experiments.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

POLICY_DESCRIPTIONS = {
    "text_summary_only": (
        "Use only the text summaries of candidate memories. Select the memory "
        "that best answers or matches the spoken query."
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
    tmp.replace(path)


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


def render_candidates(candidates: list[dict[str, Any]], policy: str, include_audio_paths: bool) -> list[str]:
    rendered: list[str] = []
    for index, candidate in enumerate(candidates):
        label = LABELS[index]
        summary = str(candidate.get("summary") or "")
        task_label = str(candidate.get("label") or "")
        parts = [f"{label}. Memory id: {candidate['memory_id']}"]
        if summary and policy != "audio_clip_only":
            parts.append(f"Summary: {summary}")
        if task_label and task_label != summary:
            parts.append(f"Label: {task_label}")
        if include_audio_paths and candidate.get("audio_path"):
            parts.append(f"Audio clip reference: {candidate['audio_path']}")
        rendered.append(". ".join(parts))
    return rendered


def build_prompt(row: dict[str, Any], policy: str, fixed_output_protocol: str) -> str:
    candidates = row["candidate_memories"]
    include_audio_paths = policy in POLICIES_WITH_MEMORY_AUDIO
    candidate_lines = render_candidates(candidates, policy, include_audio_paths)
    protocol = {
        "letter": "Reply with exactly one capital option letter and nothing else.",
        "json": 'Reply with exactly this JSON shape: {"answer":"A"}.',
    }[fixed_output_protocol]
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
    return "\n".join(lines)


def audio_cost_seconds(row: dict[str, Any], policy: str) -> float:
    query_cost = 1.0 if row.get("query_audio_path") else 0.0
    if policy not in POLICIES_WITH_MEMORY_AUDIO:
        return query_cost
    memory_count = sum(1 for item in row.get("candidate_memories", []) if item.get("audio_path"))
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
    with tempfile.NamedTemporaryFile(prefix="omni_memory_use_", suffix=".txt", delete=False) as tmp:
        path = Path(tmp.name)
    shell_cmd = f"timeout {int(timeout_s)}s {shlex.join(cmd)} > {shlex.quote(str(path))} 2>&1"
    proc = subprocess.run(shell_cmd, shell=True, check=False)
    output = path.read_text(encoding="utf-8", errors="replace")
    path.unlink(missing_ok=True)
    return proc.returncode, output


def call_llama_cli(args: argparse.Namespace, row: dict[str, Any], prompt: str) -> tuple[str, str, int, str]:
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
    if row.get("query_audio_path"):
        lines.append(f"/audio {row['query_audio_path']}")
    if policy in POLICIES_WITH_MEMORY_AUDIO:
        for candidate in row.get("candidate_memories", []):
            if candidate.get("audio_path"):
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
    prompt = build_prompt(row, args.policy, args.fixed_output_protocol)
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
        choices=["local_oracle", "local_first", "local_random", "llama_cli", "llama_chat_multi_audio"],
        default="local_oracle",
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--mmproj", default="")
    parser.add_argument("--llama-cli", default="llama-cli")
    parser.add_argument("--split", default="")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--fixed-output-protocol", choices=["letter", "json"], default="letter")
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--ctx-size", type=int, default=1024)
    parser.add_argument("--gpu-layers", default="auto")
    parser.add_argument("--capture-backend", choices=["subprocess", "shell_file"], default="shell_file")
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
