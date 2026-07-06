"""Chat-mode smoke runner for llama.cpp generative omni models.

Some multimodal llama.cpp builds handle audio more reliably through chat-mode
commands such as ``/audio <path>`` than through ``--audio ... -p ...``.  This
runner keeps the same multiple-choice policy surface as
``generative_omni_policy_smoke.py`` but feeds scripted stdin:

```
/audio <audio>
<multiple-choice prompt>
/exit
```

It is intended for backend-readiness and small cross-model checks.  It is
resumable and writes row-level JSON after each sample.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from generative_omni_policy_smoke import POLICIES, build_options, build_prompt, parse_prediction, read_jsonl


def parse_chat_prediction(text: str, options: list[str]) -> tuple[str, str, float]:
    """Parse a llama.cpp chat-mode response.

    The chat CLI echoes prompts and backend status lines.  The generic parser
    can therefore latch onto an option letter from the echoed prompt.  For
    chat-mode smoke tests, prefer the last standalone A-H token near the end of
    the transcript; fall back to the generic content parser if no letter is
    present.
    """

    matches = re.findall(r"(?<![A-Z0-9])([A-H])(?![A-Z0-9])", text.upper())
    if matches:
        return matches[-1], "chat_last_letter", 1.0
    return parse_prediction(text, options)


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def make_result(args: argparse.Namespace, rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row.get("returncode") == 0 and not row.get("error")]
    parsed = [row for row in rows if row.get("prediction_letter")]
    return {
        "experiment": "generative_omni_chat_cli_smoke",
        "model_label": args.model_label,
        "policy": args.policy,
        "prompt_mode": args.prompt_mode,
        "start_index": args.start_index,
        "n": len(rows),
        "valid_rate": len(valid) / len(rows) if rows else 0.0,
        "parse_rate": len(parsed) / len(rows) if rows else 0.0,
        "accuracy": sum(1 for row in rows if row.get("correct")) / len(rows) if rows else 0.0,
        "mean_latency_ms": sum(float(row.get("latency_ms", 0.0)) for row in rows) / len(rows) if rows else 0.0,
        "rows": rows,
    }


def row_rng(seed: int, sample_id: str, gold: str) -> random.Random:
    """Create deterministic per-row RNG so resumable runs keep stable options."""

    material = f"{seed}\n{sample_id}\n{gold}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return random.Random(int(digest[:16], 16))


def run_chat(args: argparse.Namespace, audio_path: str, prompt: str) -> tuple[int, str, float, list[str], str]:
    cmd = [
        args.llama_cli,
        "-m",
        args.model,
    ]
    if args.mmproj:
        cmd.extend(["--mmproj", args.mmproj])
    cmd.extend(
        [
            "-n",
            str(args.max_tokens),
            "--temp",
            "0",
            "--ctx-size",
            str(args.ctx_size),
            "--gpu-layers",
            args.gpu_layers,
        ]
    )
    if args.no_warmup:
        cmd.append("--no-warmup")
    if args.log_disable:
        cmd.append("--log-disable")
    if args.jinja:
        cmd.append("--jinja")
    cmd.extend(args.extra_llama_arg)

    stdin = f"/audio {audio_path}\n{prompt}\n/exit\n"
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        input=stdin,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=args.timeout_s,
        check=False,
    )
    latency_ms = (time.monotonic() - started) * 1000
    return proc.returncode, proc.stdout, latency_ms, cmd, stdin


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--llama-cli", default="llama-mtmd-cli")
    parser.add_argument("--model", required=True)
    parser.add_argument("--mmproj")
    parser.add_argument("--model-label", default="generative_omni")
    parser.add_argument("--policy", choices=sorted(POLICIES), default="raw")
    parser.add_argument("--prompt-mode", choices=["letter", "json", "anti_answer", "explicit_final"], default="anti_answer")
    parser.add_argument("--audio-field", default="query_audio_path")
    parser.add_argument("--label-field", default="gold_label")
    parser.add_argument("--text-field", default="query_text")
    parser.add_argument("--max-samples", type=int, default=4)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=4)
    parser.add_argument("--timeout-s", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--ctx-size", type=int, default=1024)
    parser.add_argument("--gpu-layers", default="auto")
    parser.add_argument("--no-warmup", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--log-disable", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--jinja", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--flatten-prompt", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--extra-llama-arg", action="append", default=[])
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.manifest))
    rows = [row for row in rows if row.get(args.audio_field) and row.get(args.label_field)]
    universe = sorted({str(row[args.label_field]) for row in rows})
    selected = rows[args.start_index : args.start_index + args.max_samples]

    output_path = Path(args.output)
    out_rows: list[dict[str, Any]] = []
    completed: set[str] = set()
    if args.resume and output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        out_rows = list(existing.get("rows", []))
        completed = {str(row.get("sample_id")) for row in out_rows if row.get("sample_id")}

    for row in selected:
        sample_id = str(row.get("sample_id"))
        if sample_id in completed:
            continue
        gold = str(row[args.label_field])
        rng = row_rng(args.seed, sample_id, gold)
        options, gold_letter = build_options(
            gold=gold,
            universe=universe,
            candidate_count=args.candidate_count,
            rng=rng,
        )
        prompt = build_prompt(args.policy, options, args.prompt_mode, args.flatten_prompt)
        try:
            returncode, output, latency_ms, command, stdin = run_chat(args, str(row[args.audio_field]), prompt)
            option_texts = [option.split(". ", 1)[1] for option in options]
            prediction, parse_method, parse_score = parse_chat_prediction(output, option_texts)
            error = ""
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            latency_ms = float(args.timeout_s) * 1000
            command = []
            stdin = ""
            prediction = ""
            parse_method = "timeout"
            parse_score = 0.0
            error = "timeout"

        out_rows.append(
            {
                "sample_id": sample_id,
                "policy": args.policy,
                "gold": gold,
                "gold_letter": gold_letter,
                "prediction_letter": prediction,
                "parse_method": parse_method,
                "parse_score": parse_score,
                "correct": prediction == gold_letter,
                "returncode": returncode,
                "error": error,
                "latency_ms": latency_ms,
                "prompt": prompt,
                "model_output": output[-2000:],
                "command_head": command[:8],
                "stdin_head": stdin[:200],
                "audio_path": row.get(args.audio_field),
                "source_text": row.get(args.text_field),
            }
        )
        write_result(output_path, make_result(args, out_rows))

    write_result(output_path, make_result(args, out_rows))
    print(json.dumps({k: v for k, v in make_result(args, out_rows).items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
