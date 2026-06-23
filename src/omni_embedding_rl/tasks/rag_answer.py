"""Final-answer evaluation for speech-RAG pipelines.

The evaluator upgrades retrieval-only experiments into task-level RAG utility:

1. choose top-k knowledge documents from ASR/omni/RRF candidates;
2. generate a grounded answer, normally through an OpenAI-compatible LLM API;
3. evaluate the answer with explicit rule keys;
4. optionally ask an LLM judge to apply the same rule keys and return JSON.

The LLM is never used as an unconstrained judge.  The judge prompt receives
required term groups, forbidden terms, the key decision, and the selected
document, then must return a fixed schema.  A deterministic local rule audit is
always computed and preserved.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class RAGAnswerEvalConfig:
    retrieval_result: Path
    manifest: Path
    answer_keys: Path
    output: Path
    split: str = "test"
    candidate_order: str = "asr"
    candidate_count: int = 5
    answer_context_count: int = 3
    rrf_k: int = 60
    generator_mode: str = "llm"
    judge_mode: str = "local_rule"
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "DEEPSEEK_API_KEY"
    api_key_file: str = ""
    temperature: float = 0.0
    answer_max_tokens: int = 256
    judge_max_tokens: int = 256
    timeout: float = 60.0
    api_retries: int = 2
    api_retry_sleep: float = 2.0
    sleep_sec: float = 0.0
    max_rows: int = 0
    include_rows: bool = True
    example_count: int = 5
    bad_case_count: int = 20
    grounding_target: str = "document_id"


def safe_error(exc: BaseException, limit: int = 180) -> str:
    text = str(exc).replace("\n", " ")
    text = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer <redacted>", text)
    return f"{type(exc).__name__}:{text[:limit]}"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_manifest(path: Path) -> dict[str, dict[str, Any]]:
    samples = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                item = json.loads(line)
                samples[item["sample_id"]] = item
    return samples


def load_api_key(config: RAGAnswerEvalConfig) -> str:
    api_key = os.environ.get(config.api_key_env, "")
    if api_key:
        return api_key.strip()
    if config.api_key_file:
        path = Path(config.api_key_file)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return ""


def call_openai_compatible(config: RAGAnswerEvalConfig, prompt: str, max_tokens: int) -> str:
    api_key = load_api_key(config)
    if not api_key:
        raise RuntimeError(f"Missing API key env var or file: {config.api_key_env}")
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "You are a careful, concise RAG assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.temperature,
        "max_tokens": max_tokens,
    }
    url = config.base_url.rstrip("/") + "/chat/completions"
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error: Exception | None = None
    for attempt in range(config.api_retries + 1):
        request = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=config.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except (
            http.client.RemoteDisconnected,
            TimeoutError,
            urllib.error.URLError,
            urllib.error.HTTPError,
        ) as exc:
            last_error = exc
            if attempt >= config.api_retries:
                break
            time.sleep(config.api_retry_sleep * (attempt + 1))
    raise RuntimeError(f"OpenAI-compatible API call failed after retries: {last_error}")


def rrf_candidates(row: dict[str, Any], limit: int, k: int) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    candidates: dict[str, dict[str, Any]] = {}
    for source in ("asr_top_k", "omni_top_k"):
        for rank, candidate in enumerate(row.get(source, []), start=1):
            sample_id = candidate["sample_id"]
            scores[sample_id] = scores.get(sample_id, 0.0) + 1.0 / (k + rank)
            candidates.setdefault(sample_id, dict(candidate))
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    output = []
    for rank, (sample_id, score) in enumerate(ordered[:limit], start=1):
        item = dict(candidates[sample_id])
        item.update({"rank": rank, "score": score, "source": "rrf"})
        output.append(item)
    return output


def merge_candidates(
    primary: list[dict[str, Any]], secondary: list[dict[str, Any]], limit: int, source: str
) -> list[dict[str, Any]]:
    output = []
    seen = set()
    for candidate in [*primary, *secondary]:
        sample_id = candidate["sample_id"]
        if sample_id in seen:
            continue
        seen.add(sample_id)
        item = dict(candidate)
        item["source"] = source
        output.append(item)
        if len(output) >= limit:
            break
    return output


def base_candidates(row: dict[str, Any], config: RAGAnswerEvalConfig) -> list[dict[str, Any]]:
    limit = min(config.candidate_count, len(LABELS))
    asr_candidates = row.get("asr_top_k", [])
    omni_candidates = row.get("omni_top_k", [])
    if config.candidate_order in {"asr", "asr_first"}:
        return merge_candidates(asr_candidates, omni_candidates, limit, "asr")
    if config.candidate_order in {"omni", "omni_first"}:
        return merge_candidates(omni_candidates, asr_candidates, limit, "omni")
    if config.candidate_order == "rrf":
        return rrf_candidates(row, limit, config.rrf_k)
    raise ValueError(f"Unsupported candidate_order: {config.candidate_order}")


def candidate_doc(candidate: dict[str, Any], samples: dict[str, dict[str, Any]]) -> str:
    sample = samples.get(candidate["sample_id"], {})
    return str(candidate.get("document") or sample.get("document_text") or sample.get("text") or "")


def answer_prompt(
    row: dict[str, Any],
    candidates: list[dict[str, Any]],
    samples: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "You answer a user question using only the provided knowledge documents.",
        "The user question came from speech ASR and may contain recognition errors.",
        "Prefer the document that directly matches the user's business rule, condition, exception, amount, time, or tool intent.",
        "Do not merge conflicting rules from neighboring documents.",
        "If the documents do not contain enough information, say that the knowledge base does not provide enough information.",
        "",
        f"ASR/user question: {row.get('asr_text') or row.get('query_text') or row.get('target')}",
        "",
        "Knowledge documents:",
    ]
    for index, candidate in enumerate(candidates, start=1):
        lines.append(f"{index}. {candidate_doc(candidate, samples)}")
    lines.append("")
    lines.append("Final answer:")
    return "\n".join(lines)


def local_generated_answer(
    mode: str,
    target_id: str,
    candidates: list[dict[str, Any]],
    samples: dict[str, dict[str, Any]],
    key: dict[str, Any],
) -> str:
    if mode == "gold":
        return str(key.get("gold_answer") or key.get("key_decision") or "")
    if mode == "first_document":
        return candidate_doc(candidates[0], samples) if candidates else ""
    raise ValueError(f"Unsupported non-LLM generator_mode: {mode} for target {target_id}")


def generate_answer(
    config: RAGAnswerEvalConfig,
    row: dict[str, Any],
    candidates: list[dict[str, Any]],
    samples: dict[str, dict[str, Any]],
    key: dict[str, Any],
) -> str:
    if config.generator_mode == "llm":
        return call_openai_compatible(config, answer_prompt(row, candidates, samples), config.answer_max_tokens)
    return local_generated_answer(config.generator_mode, row["sample_id"], candidates, samples, key)


def group_matches(answer: str, group: list[str]) -> bool:
    return any(term and term in answer for term in group)


def score_answer_local(answer: str, key: dict[str, Any]) -> dict[str, Any]:
    required_groups = key.get("required_terms", [])
    group_hits = [group_matches(answer, group) for group in required_groups]
    forbidden_hits = [term for term in key.get("forbidden_terms", []) if term and term in answer]
    required_recall = sum(group_hits) / len(group_hits) if group_hits else 1.0
    return {
        "required_terms_recall": required_recall,
        "required_group_hits": group_hits,
        "forbidden_hits": forbidden_hits,
        "forbidden_violation": bool(forbidden_hits),
        "answer_pass": required_recall == 1.0 and not forbidden_hits,
    }


def judge_prompt(
    row: dict[str, Any], key: dict[str, Any], answer_text: str, selected_document: str
) -> str:
    return "\n".join(
        [
            "You are a strict but rule-bound RAG evaluator.",
            "Judge the system answer only by the provided rule key and selected document.",
            "Do not use outside knowledge. Do not reward fluent but unsupported answers.",
            "Return compact JSON only; no markdown.",
            "",
            "Rules:",
            "1. pass=true only if the answer covers the key_decision.",
            "2. required_terms are OR groups. For each group, a paraphrase is acceptable if it clearly expresses the same condition.",
            "3. If the answer states any forbidden_terms or their clear meaning, forbidden_violation=true and pass=false.",
            "4. If the selected document is the wrong neighboring rule and changes the answer, grounding_error=true and pass=false.",
            "5. If the answer refuses despite enough evidence in the selected document, pass=false.",
            "",
            f"User question: {row.get('target') or row.get('query_text') or ''}",
            f"ASR text: {row.get('asr_text', '')}",
            f"Gold answer: {key.get('gold_answer', '')}",
            f"Key decision: {key.get('key_decision', '')}",
            f"Required term groups: {json.dumps(key.get('required_terms', []), ensure_ascii=False)}",
            f"Forbidden terms: {json.dumps(key.get('forbidden_terms', []), ensure_ascii=False)}",
            f"Selected document: {selected_document}",
            f"System answer: {answer_text}",
            "",
            'Schema: {"pass": true, "required_coverage": 1.0, "forbidden_violation": false, "grounding_error": false, "reason": "short reason"}',
        ]
    )


def parse_judge_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        stripped = match.group(0)
    data = json.loads(stripped)
    return {
        "pass": bool(data.get("pass", False)),
        "required_coverage": float(data.get("required_coverage", 0.0)),
        "forbidden_violation": bool(data.get("forbidden_violation", False)),
        "grounding_error": bool(data.get("grounding_error", False)),
        "reason": str(data.get("reason", "")),
    }


def judge_answer(
    config: RAGAnswerEvalConfig,
    row: dict[str, Any],
    key: dict[str, Any],
    answer_text: str,
    selected_document: str,
    local_score: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if config.judge_mode == "local_rule":
        return (
            {
                "pass": local_score["answer_pass"],
                "required_coverage": local_score["required_terms_recall"],
                "forbidden_violation": local_score["forbidden_violation"],
                "grounding_error": False,
                "reason": "local_rule",
            },
            "",
        )
    if config.judge_mode == "llm_rule":
        response = call_openai_compatible(config, judge_prompt(row, key, answer_text, selected_document), config.judge_max_tokens)
        return parse_judge_json(response), response
    raise ValueError(f"Unsupported judge_mode: {config.judge_mode}")


def domain_intent_match(sample_id: str, target_id: str, samples: dict[str, dict[str, Any]]) -> bool:
    sample = samples.get(sample_id, {})
    target = samples.get(target_id, {})
    return sample.get("domain") == target.get("domain") and sample.get("intent") == target.get("intent")


def grounding_id(sample_id: str, samples: dict[str, dict[str, Any]], grounding_target: str) -> str:
    sample = samples.get(sample_id, {})
    if grounding_target == "document_id":
        return str(sample.get("document_id") or sample.get("base_sample_id") or sample_id)
    return sample_id


def grounding_match(
    sample_id: str, target_id: str, samples: dict[str, dict[str, Any]], grounding_target: str
) -> bool:
    return grounding_id(sample_id, samples, grounding_target) == grounding_id(target_id, samples, grounding_target)


def error_type(
    row: dict[str, Any],
    selected_id: str,
    used_ids: list[str],
    answer_pass: bool,
    baseline_id: str,
    samples: dict[str, dict[str, Any]],
    grounding_target: str,
) -> str:
    target_id = row["sample_id"]
    if answer_pass:
        return "none"
    if not any(grounding_match(used_id, target_id, samples, grounding_target) for used_id in used_ids):
        return "retrieval_miss"
    if grounding_match(baseline_id, target_id, samples, grounding_target) and not grounding_match(selected_id, target_id, samples, grounding_target):
        return "over_override"
    if not grounding_match(selected_id, target_id, samples, grounding_target) and domain_intent_match(selected_id, target_id, samples):
        return "same_cluster_neighbor"
    asr_top = row.get("asr_top_k", [{}])[0].get("sample_id")
    if asr_top and not domain_intent_match(asr_top, target_id, samples):
        return "asr_semantic_drift"
    return "generation_miss"


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if not n:
        return {}
    return {
        "n": n,
        "answer_pass": sum(row["answer_pass"] for row in rows) / n,
        "required_terms_recall": sum(row["required_terms_recall"] for row in rows) / n,
        "local_rule_answer_pass": sum(row["local_rule_answer_pass"] for row in rows) / n,
        "judge_required_coverage": sum(row["judge_required_coverage"] for row in rows) / n,
        "forbidden_terms_violation_rate": sum(row["forbidden_violation"] for row in rows) / n,
        "judge_grounding_error_rate": sum(row["judge_grounding_error"] for row in rows) / n,
        "grounded_target_acc": sum(row["grounded_target_pass"] for row in rows) / n,
        "grounded_sample_acc": sum(row["grounded_sample_pass"] for row in rows) / n,
        "grounded_domain_intent_acc": sum(row["grounded_domain_intent_pass"] for row in rows) / n,
        "api_error_count": sum(bool(row["api_error"]) for row in rows),
        "generation_error_rate": sum(row["error_type"] == "generation_miss" for row in rows) / n,
        "error_type_counts": {
            error: sum(row["error_type"] == error for row in rows)
            for error in sorted({row["error_type"] for row in rows})
        },
    }


def grouped_metrics(rows: list[dict[str, Any]], group_key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        group = row.get(group_key) or "unknown"
        groups.setdefault(group, []).append(row)
    return {group: aggregate_metrics(group_rows) for group, group_rows in sorted(groups.items())}


def retrieval_rows(retrieval: dict[str, Any], split: str) -> list[dict[str, Any]]:
    metrics = retrieval["metrics"]
    if split in metrics and "rows" in metrics[split]:
        return metrics[split]["rows"]
    raise KeyError(f"Cannot find rows for split={split}")


def run(config: RAGAnswerEvalConfig) -> dict[str, Any]:
    retrieval = read_json(config.retrieval_result)
    answer_keys = read_json(config.answer_keys)["keys"]
    samples = read_manifest(config.manifest)
    rows = retrieval_rows(retrieval, config.split)
    if config.max_rows:
        rows = rows[: config.max_rows]

    out_rows = []
    for row in rows:
        target_id = row["sample_id"]
        candidates = base_candidates(row, config)
        answer_candidates = candidates[: config.answer_context_count]
        baseline_id = candidates[0]["sample_id"] if candidates else ""
        selected_id = baseline_id
        used_ids = [candidate["sample_id"] for candidate in answer_candidates]
        key = answer_keys[target_id]
        api_error = ""
        try:
            answer_text = generate_answer(config, row, answer_candidates, samples, key)
        except (RuntimeError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
            answer_text = ""
            api_error = f"answer:{safe_error(exc)}"
        if config.sleep_sec:
            time.sleep(config.sleep_sec)

        local_score = score_answer_local(answer_text, key)
        selected_document = candidate_doc(answer_candidates[0], samples) if answer_candidates else ""
        try:
            judge_score, judge_response = judge_answer(config, row, key, answer_text, selected_document, local_score)
        except (RuntimeError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
            judge_score = {
                "pass": local_score["answer_pass"],
                "required_coverage": local_score["required_terms_recall"],
                "forbidden_violation": local_score["forbidden_violation"],
                "grounding_error": False,
                "reason": "judge_failed_fallback_to_local_rule",
            }
            judge_response = ""
            api_error = f"{api_error};judge:{safe_error(exc)}".strip(";")

        grounded_sample_pass = selected_id == target_id
        grounded_target_pass = bool(selected_id) and grounding_match(selected_id, target_id, samples, config.grounding_target)
        grounded_domain_intent_pass = bool(selected_id) and domain_intent_match(selected_id, target_id, samples)
        err = error_type(
            row,
            selected_id,
            used_ids,
            judge_score["pass"],
            baseline_id,
            samples,
            config.grounding_target,
        )
        out_rows.append(
            {
                "sample_id": target_id,
                "document_id": grounding_id(target_id, samples, "document_id"),
                "query_style": samples.get(target_id, {}).get("query_style", ""),
                "tts_dialect": samples.get(target_id, {}).get("tts_dialect", ""),
                "target_query": samples.get(target_id, {}).get("text", row.get("target", "")),
                "asr_text": row.get("asr_text", ""),
                "gold_answer": key.get("gold_answer", ""),
                "key_decision": key.get("key_decision", ""),
                "candidate_order": config.candidate_order,
                "baseline_choice_id": baseline_id,
                "selected_candidate_id": selected_id,
                "used_candidate_ids": used_ids,
                "grounding_target": config.grounding_target,
                "grounded_target_pass": grounded_target_pass,
                "grounded_sample_pass": grounded_sample_pass,
                "grounded_domain_intent_pass": grounded_domain_intent_pass,
                "answer_text": answer_text,
                "answer_pass": judge_score["pass"],
                "local_rule_answer_pass": local_score["answer_pass"],
                "required_terms_recall": local_score["required_terms_recall"],
                "required_group_hits": local_score["required_group_hits"],
                "forbidden_violation": judge_score["forbidden_violation"],
                "forbidden_hits": local_score["forbidden_hits"],
                "judge_mode": config.judge_mode,
                "judge_required_coverage": judge_score["required_coverage"],
                "judge_grounding_error": judge_score["grounding_error"],
                "judge_reason": judge_score["reason"],
                "judge_response": judge_response,
                "error_type": err,
                "api_error": api_error,
            }
        )

    report = {
        "experiment": "rag_final_answer_eval",
        "config": asdict(config) | {
            "retrieval_result": str(config.retrieval_result),
            "manifest": str(config.manifest),
            "answer_keys": str(config.answer_keys),
            "output": str(config.output),
        },
        "metrics": aggregate_metrics(out_rows),
        "by_query_style": grouped_metrics(out_rows, "query_style"),
        "by_tts_dialect": grouped_metrics(out_rows, "tts_dialect"),
        "rows": out_rows if config.include_rows else out_rows[: config.example_count],
        "bad_cases": [row for row in out_rows if not row["answer_pass"]][: config.bad_case_count],
        "notes": [
            "generator_mode=llm is the intended experiment mode.",
            "local_rule_answer_pass is always reported as deterministic audit.",
            "judge_mode=llm_rule constrains the LLM judge with required/forbidden rule keys.",
        ],
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieval-result", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--answer-keys", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split", default="test")
    parser.add_argument("--candidate-order", choices=["asr", "asr_first", "omni", "omni_first", "rrf"], default="asr")
    parser.add_argument("--candidate-count", type=int, default=5)
    parser.add_argument("--answer-context-count", type=int, default=3)
    parser.add_argument("--generator-mode", choices=["llm", "gold", "first_document"], default="llm")
    parser.add_argument("--judge-mode", choices=["local_rule", "llm_rule"], default="local_rule")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--api-key-file", default="")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--include-rows", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> RAGAnswerEvalConfig:
    return RAGAnswerEvalConfig(
        retrieval_result=args.retrieval_result,
        manifest=args.manifest,
        answer_keys=args.answer_keys,
        output=args.output,
        split=args.split,
        candidate_order=args.candidate_order,
        candidate_count=args.candidate_count,
        answer_context_count=args.answer_context_count,
        generator_mode=args.generator_mode,
        judge_mode=args.judge_mode,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        api_key_file=args.api_key_file,
        max_rows=args.max_rows,
        include_rows=args.include_rows,
    )


def main() -> None:
    print(json.dumps(run(config_from_args(build_parser().parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
