"""Smoke runner for training-free policies on generative omni models.

This script is intentionally small and model-agnostic. It builds multiple-choice
audio prompts from a manifest and calls a llama.cpp-compatible CLI with an audio
file. The goal is to test whether the same policy/interface ideas used for
omni-embedding retrieval transfer to generative omni models without training.
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


POLICIES = {
    "raw": "Listen to the audio and choose the best answer.",
    "semantic_boundary": (
        "Listen for the user's semantic intent. Ignore wording variations and "
        "choose the candidate whose meaning best matches the audio."
    ),
    "tool_boundary": (
        "Listen to the command and choose the executable tool intent. Prefer "
        "the candidate that captures the requested action and reject nearby "
        "tools with different side effects."
    ),
    "translation_boundary": (
        "Listen to the source-language speech and choose the English candidate "
        "that preserves the argument structure and named entities."
    ),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def normalize_answer(text: str) -> str:
    match = re.search(r'"answer"\s*:\s*"([A-H])"', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"\b(?:answer|option|choice)\s*[:：]\s*([A-H])\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"\b([A-H])\b", text.upper())
    return match.group(1) if match else ""


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def option_content_match(text: str, options: list[str]) -> tuple[str, str, float]:
    """Best-effort parser for models that answer with option content."""

    labels = "ABCDEFGH"
    normalized_output = normalize_text(text)
    if not normalized_output:
        return "", "none", 0.0

    best_label = ""
    best_score = 0.0
    for i, option in enumerate(options):
        normalized_option = normalize_text(option)
        if not normalized_option:
            continue
        if normalized_option in normalized_output:
            return labels[i], "content_exact", 1.0
        option_tokens = set(normalized_option.split())
        output_tokens = set(normalized_output.split())
        if not option_tokens:
            continue
        score = len(option_tokens & output_tokens) / len(option_tokens)
        if score > best_score:
            best_label = labels[i]
            best_score = score

    if best_score >= 0.75:
        return best_label, "content_overlap", best_score
    return "", "none", best_score


def parse_prediction(text: str, options: list[str]) -> tuple[str, str, float]:
    if "<|channel>final" in text:
        text = text.rsplit("<|channel>final", 1)[-1]
    elif "<channel|>" in text:
        text = text.rsplit("<channel|>", 1)[-1]
    elif "<|channel>thought" in text:
        return "", "no_final_channel", 0.0

    letter = normalize_answer(text)
    if letter:
        return letter, "letter", 1.0
    return option_content_match(text, options)


def build_options(
    gold: str,
    universe: list[str],
    candidate_count: int,
    rng: random.Random,
) -> tuple[list[str], str]:
    negatives = [x for x in universe if x != gold]
    rng.shuffle(negatives)
    options = [gold] + negatives[: max(0, candidate_count - 1)]
    rng.shuffle(options)
    labels = "ABCDEFGH"
    gold_letter = labels[options.index(gold)]
    rendered = [f"{labels[i]}. {option}" for i, option in enumerate(options)]
    return rendered, gold_letter


def run_llama(
    llama_cli: str,
    model: str,
    mmproj: str | None,
    audio_path: str,
    prompt: str,
    timeout_s: int,
    max_tokens: int,
    ctx_size: int,
    gpu_layers: str,
    no_warmup: bool,
    log_disable: bool,
    jinja: bool,
    extra_llama_args: list[str],
    capture_backend: str,
) -> tuple[int, str, list[str]]:
    cmd = [
        llama_cli,
        "-m",
        model,
        "--audio",
        audio_path,
        "-p",
        prompt,
        "-n",
        str(max_tokens),
        "--temp",
        "0",
        "--ctx-size",
        str(ctx_size),
        "--gpu-layers",
        gpu_layers,
    ]
    if mmproj:
        cmd[3:3] = ["--mmproj", mmproj]
    if no_warmup:
        cmd.append("--no-warmup")
    if log_disable:
        cmd.append("--log-disable")
    if jinja:
        cmd.append("--jinja")
    cmd.extend(extra_llama_args)
    if capture_backend == "subprocess":
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_s,
            check=False,
        )
        return proc.returncode, proc.stdout, cmd

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
                    return 124, b"".join(chunks).decode("utf-8", errors="replace"), cmd
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
        return proc.returncode or 0, b"".join(chunks).decode("utf-8", errors="replace"), cmd

    with tempfile.NamedTemporaryFile(prefix="generative_omni_", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    shell_cmd = f"timeout {int(timeout_s)}s {shlex.join(cmd)} > {shlex.quote(str(tmp_path))} 2>&1"
    proc = subprocess.run(shell_cmd, shell=True, check=False)
    output = tmp_path.read_text(encoding="utf-8", errors="replace")
    tmp_path.unlink(missing_ok=True)
    return proc.returncode, output, cmd


def build_prompt(policy: str, options: list[str], prompt_mode: str, flatten: bool) -> str:
    strict = {
        "letter": "Choose exactly one option. Answer with only the option letter.",
        "json": 'Choose exactly one option. Output exactly this JSON shape: {"answer":"A"}.',
        "explicit_final": (
            "You may reason if needed. At the very end, output exactly one "
            "capital option letter on its own final line."
        ),
        "anti_answer": (
            "This is a multiple-choice benchmark. Do not answer the spoken question. "
            "Do not translate or explain. Select the option that best matches the audio. "
            "Reply with only one capital letter."
        ),
    }[prompt_mode]
    prompt = "\n".join([POLICIES[policy], strict, "", *options])
    if flatten:
        return " ".join(line.strip() for line in prompt.splitlines() if line.strip())
    return prompt


def make_result(args: argparse.Namespace, out_rows: list[dict[str, Any]]) -> dict[str, Any]:
    accuracy = (
        sum(1 for r in out_rows if r["correct"]) / len(out_rows) if out_rows else 0.0
    )
    return {
        "experiment": "generative_omni_policy_smoke",
        "policy": args.policy,
        "prompt_mode": args.prompt_mode,
        "start_index": args.start_index,
        "n": len(out_rows),
        "accuracy": accuracy,
        "rows": out_rows,
    }


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--llama-cli", default="llama-cli")
    parser.add_argument("--model", required=True)
    parser.add_argument("--mmproj")
    parser.add_argument("--policy", choices=sorted(POLICIES), default="raw")
    parser.add_argument("--audio-field", default="audio_path")
    parser.add_argument("--label-field", default="intent")
    parser.add_argument("--text-field", default="text")
    parser.add_argument("--max-samples", type=int, default=8)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=4)
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--ctx-size", type=int, default=1024)
    parser.add_argument("--gpu-layers", default="auto")
    parser.add_argument(
        "--prompt-mode",
        choices=["letter", "json", "anti_answer", "explicit_final"],
        default="anti_answer",
    )
    parser.add_argument("--flatten-prompt", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--capture-backend", choices=["pty", "shell_file", "subprocess"], default="pty")
    parser.add_argument("--no-warmup", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--log-disable", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--jinja", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--extra-llama-arg", action="append", default=[])
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.manifest))
    rows = [r for r in rows if r.get(args.audio_field) and r.get(args.label_field)]
    universe = sorted({str(r[args.label_field]) for r in rows})
    rng = random.Random(args.seed)
    if args.start_index < 0:
        raise ValueError("--start-index must be non-negative")
    selected = rows[args.start_index : args.start_index + args.max_samples]

    output_path = Path(args.output)
    out_rows = []
    completed: set[str] = set()
    if args.resume and output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        out_rows = list(existing.get("rows", []))
        completed = {str(r.get("sample_id")) for r in out_rows if r.get("sample_id")}

    labels = "ABCDEFGH"
    for row in selected:
        sample_id = str(row.get("sample_id"))
        if sample_id in completed:
            continue
        gold = str(row[args.label_field])
        options, gold_letter = build_options(
            gold=gold,
            universe=universe,
            candidate_count=min(args.candidate_count, len(labels)),
            rng=rng,
        )
        prompt = build_prompt(args.policy, options, args.prompt_mode, args.flatten_prompt)
        try:
            code, output, command = run_llama(
                llama_cli=args.llama_cli,
                model=args.model,
                mmproj=args.mmproj,
                audio_path=str(row[args.audio_field]),
                prompt=prompt,
                timeout_s=args.timeout_s,
                max_tokens=args.max_tokens,
                ctx_size=args.ctx_size,
                gpu_layers=args.gpu_layers,
                no_warmup=args.no_warmup,
                log_disable=args.log_disable,
                jinja=args.jinja,
                extra_llama_args=args.extra_llama_arg,
                capture_backend=args.capture_backend,
            )
            option_texts = [o.split(". ", 1)[1] for o in options]
            pred, parse_method, parse_score = parse_prediction(output, option_texts)
            error = ""
        except subprocess.TimeoutExpired as exc:
            code = 124
            output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            command = []
            pred = ""
            parse_method = "none"
            parse_score = 0.0
            error = "timeout"

        out_rows.append(
            {
                "sample_id": sample_id,
                "policy": args.policy,
                "gold": gold,
                "gold_letter": gold_letter,
                "prediction_letter": pred,
                "parse_method": parse_method,
                "parse_score": parse_score,
                "correct": pred == gold_letter,
                "returncode": code,
                "error": error,
                "prompt": prompt,
                "model_output": output[-2000:],
                "command_head": command[:8],
                "audio_path": row.get(args.audio_field),
                "source_text": row.get(args.text_field),
            }
        )
        write_result(output_path, make_result(args, out_rows))

    write_result(output_path, make_result(args, out_rows))


if __name__ == "__main__":
    main()
