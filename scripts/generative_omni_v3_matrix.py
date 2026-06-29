"""Run a resumable V3 policy matrix for generative omni candidate-choice tasks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_MATRIX = [
    ("raw", "anti_answer"),
    ("translation_boundary", "anti_answer"),
    ("translation_boundary", "explicit_final"),
    ("translation_boundary", "json"),
    ("semantic_boundary", "anti_answer"),
]


def safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in text)


def run_one(args: argparse.Namespace, policy: str, prompt_mode: str) -> dict:
    stem = f"{args.output_prefix}_{safe_name(policy)}_{safe_name(prompt_mode)}"
    output = Path(f"{stem}.json")
    backend_log = Path(f"{stem}.backend.log")
    backend_log.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(Path(__file__).with_name("generative_omni_policy_smoke.py")),
        "--manifest",
        args.manifest,
        "--output",
        str(output),
        "--llama-cli",
        args.llama_cli,
        "--model",
        args.model,
        "--policy",
        policy,
        "--prompt-mode",
        prompt_mode,
        "--audio-field",
        args.audio_field,
        "--label-field",
        args.label_field,
        "--text-field",
        args.text_field,
        "--max-samples",
        str(args.max_samples),
        "--start-index",
        str(args.start_index),
        "--candidate-count",
        str(args.candidate_count),
        "--timeout-s",
        str(args.timeout_s),
        "--max-tokens",
        str(args.max_tokens),
        "--ctx-size",
        str(args.ctx_size),
        "--gpu-layers",
        args.gpu_layers,
        "--capture-backend",
        args.capture_backend,
        "--resume",
        "--extra-llama-arg=--log-file",
        "--extra-llama-arg",
        str(backend_log),
    ]
    if args.mmproj:
        cmd.extend(["--mmproj", args.mmproj])
    if args.jinja:
        cmd.append("--jinja")
    if args.no_warmup:
        cmd.append("--no-warmup")
    if args.log_disable:
        cmd.append("--log-disable")
    else:
        cmd.append("--no-log-disable")
    if not args.flatten_prompt:
        cmd.append("--no-flatten-prompt")

    proc = subprocess.run(cmd, check=False)
    result = {
        "policy": policy,
        "prompt_mode": prompt_mode,
        "output": str(output),
        "backend_log": str(backend_log),
        "returncode": proc.returncode,
    }
    if output.exists():
        data = json.loads(output.read_text(encoding="utf-8"))
        result.update(
            {
                "n": data.get("n", 0),
                "accuracy": data.get("accuracy", 0.0),
                "correct": sum(1 for row in data.get("rows", []) if row.get("correct")),
            }
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--llama-cli", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--mmproj")
    parser.add_argument("--audio-field", default="audio_path")
    parser.add_argument("--label-field", default="target_text")
    parser.add_argument("--text-field", default="source_text")
    parser.add_argument("--max-samples", type=int, default=24)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=4)
    parser.add_argument("--timeout-s", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--ctx-size", type=int, default=1024)
    parser.add_argument("--gpu-layers", default="auto")
    parser.add_argument("--capture-backend", choices=["pty", "shell_file", "subprocess"], default="shell_file")
    parser.add_argument("--jinja", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--no-warmup", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--log-disable", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--flatten-prompt", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--matrix",
        action="append",
        default=[],
        help="Optional policy:prompt_mode pair. Repeat to override the default matrix.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    matrix = []
    if args.matrix:
        for item in args.matrix:
            policy, prompt_mode = item.split(":", 1)
            matrix.append((policy, prompt_mode))
    else:
        matrix = DEFAULT_MATRIX

    results = []
    for policy, prompt_mode in matrix:
        print(f"Running {policy}:{prompt_mode}", flush=True)
        results.append(run_one(args, policy, prompt_mode))
        Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_output).write_text(
            json.dumps({"runs": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
