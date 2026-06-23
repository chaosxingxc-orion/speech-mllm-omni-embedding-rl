"""Hydra entrypoint for unified speech omni-embedding experiments."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

import hydra
from omegaconf import DictConfig, OmegaConf

try:  # Keep offline migrated tools runnable before speechrl-common is restored.
    from speechrl_common import get_logger, seed_everything
except ImportError:  # pragma: no cover - exercised only in lightweight local setups.
    logging.basicConfig(level=logging.INFO)

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

    def seed_everything(seed: int) -> None:
        random.seed(seed)

from omni_embedding_rl.evaluation.routing import RouteEvalConfig
from omni_embedding_rl.evaluation.routing import run as run_route_policy_eval
from omni_embedding_rl.evaluation.taxonomy import TaxonomySummaryConfig
from omni_embedding_rl.evaluation.taxonomy import run as run_taxonomy_summary
from omni_embedding_rl.data.manifest import ManifestSummaryConfig
from omni_embedding_rl.data.manifest import summarize_manifest
from omni_embedding_rl.execution.cache_taxonomy_plan import CacheTaxonomyPlanConfig
from omni_embedding_rl.execution.cache_taxonomy_plan import run as run_cache_taxonomy_plan
from omni_embedding_rl.execution.cache_taxonomy_runner import CacheTaxonomyRunnerConfig
from omni_embedding_rl.execution.cache_taxonomy_runner import run as run_cache_taxonomy_runner
from omni_embedding_rl.tasks.rag_answer import RAGAnswerEvalConfig
from omni_embedding_rl.tasks.rag_answer import run as run_rag_answer_eval
from omni_embedding_rl.policies.accept_gate import AcceptGateConfig
from omni_embedding_rl.policies.accept_gate import run as run_accept_gate
from omni_embedding_rl.policies.strict_selection import StrictSelectionConfig
from omni_embedding_rl.policies.strict_selection import run as run_strict_selection
from omni_embedding_rl.training.offline_policy import OfflinePolicyConfig
from omni_embedding_rl.training.offline_policy import run as run_offline_policy

log = get_logger("omni_embedding_rl")


def _list_cfg(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if OmegaConf.is_config(value):
        return tuple(OmegaConf.to_container(value, resolve=True))
    return tuple(value)


def _path(value: str | Path) -> Path:
    return Path(str(value))


def route_policy_config(cfg: DictConfig) -> RouteEvalConfig:
    section = cfg.route_policy
    return RouteEvalConfig(
        hybrid_result=_path(section.hybrid_result),
        output=_path(section.output),
        split=section.get("split", "test"),
        policies=_list_cfg(section.get("policies", ())),
        max_rows=section.get("max_rows", 0),
        confidence_below=section.get("confidence_below", 0.6),
        asr_wer_above=section.get("asr_wer_above", 0.6),
        unrouted_policy=section.get("unrouted_policy", "asr"),
        disagreement_fallback=section.get("disagreement_fallback", "rrf"),
        bootstrap_rounds=section.get("bootstrap_rounds", 10_000),
        seed=cfg.seed,
    )


def manifest_summary_config(cfg: DictConfig) -> ManifestSummaryConfig:
    section = cfg.manifest_summary
    output = section.get("output")
    return ManifestSummaryConfig(
        manifest=_path(section.manifest),
        output=_path(output) if output else None,
        top_k=section.get("top_k", 20),
        check_audio_exists=section.get("check_audio_exists", True),
    )


def cache_taxonomy_plan_config(cfg: DictConfig) -> CacheTaxonomyPlanConfig:
    section = cfg.cache_taxonomy_plan
    return CacheTaxonomyPlanConfig(
        task=section.task,
        manifest=section.manifest,
        output=_path(section.output),
        dataset_name=section.get("dataset_name", ""),
        arms=_list_cfg(section.get("arms", ())),
        max_samples=section.get("max_samples", 0),
        seed=cfg.seed,
        test_size=section.get("test_size", 0.35),
        results_dir=section.get("results_dir", "outputs"),
        text_model=section.get("text_model", "Qwen/Qwen3-Embedding-4B"),
        omni_model=section.get("omni_model", "experiments/models/omni-embed-nemotron-3b"),
        score_count=section.get("score_count", 8),
        memory_text_style=section.get("memory_text_style", "document_memory"),
        tool_task=section.get("tool_task", "intent"),
        label_description_style=section.get("label_description_style", "contrastive_boundary_tool"),
        label_example_count=section.get("label_example_count", 3),
        label_boundary_count=section.get("label_boundary_count", 3),
        candidate_count=section.get("candidate_count", 8),
        same_intent_negatives=section.get("same_intent_negatives", 2),
        same_domain_negatives=section.get("same_domain_negatives", 2),
    )


def cache_taxonomy_runner_config(cfg: DictConfig) -> CacheTaxonomyRunnerConfig:
    section = cfg.cache_taxonomy_runner
    return CacheTaxonomyRunnerConfig(
        plan=_path(section.plan),
        output=_path(section.output),
        mode=section.get("mode", "dry_run"),
        backend=section.get("backend", "legacy"),
        python=section.get("python", "python"),
        legacy_experiments_dir=_path(section.get("legacy_experiments_dir", "omni_embedding/experiments")),
        max_steps=section.get("max_steps", 0),
        skip_existing=section.get("skip_existing", True),
        require_manifest=section.get("require_manifest", True),
        continue_on_error=section.get("continue_on_error", False),
    )


def rag_answer_eval_config(cfg: DictConfig) -> RAGAnswerEvalConfig:
    section = cfg.rag_answer_eval
    return RAGAnswerEvalConfig(
        retrieval_result=_path(section.retrieval_result),
        manifest=_path(section.manifest),
        answer_keys=_path(section.answer_keys),
        output=_path(section.output),
        split=section.get("split", "test"),
        candidate_order=section.get("candidate_order", "asr"),
        candidate_count=section.get("candidate_count", 5),
        answer_context_count=section.get("answer_context_count", 3),
        rrf_k=section.get("rrf_k", 60),
        generator_mode=section.get("generator_mode", "llm"),
        judge_mode=section.get("judge_mode", "local_rule"),
        model=section.get("model", "deepseek-chat"),
        base_url=section.get("base_url", "https://api.deepseek.com"),
        api_key_env=section.get("api_key_env", "DEEPSEEK_API_KEY"),
        api_key_file=section.get("api_key_file", ""),
        temperature=section.get("temperature", 0.0),
        answer_max_tokens=section.get("answer_max_tokens", 256),
        judge_max_tokens=section.get("judge_max_tokens", 256),
        timeout=section.get("timeout", 60.0),
        api_retries=section.get("api_retries", 2),
        api_retry_sleep=section.get("api_retry_sleep", 2.0),
        sleep_sec=section.get("sleep_sec", 0.0),
        max_rows=section.get("max_rows", 0),
        include_rows=section.get("include_rows", True),
        example_count=section.get("example_count", 5),
        bad_case_count=section.get("bad_case_count", 20),
        grounding_target=section.get("grounding_target", "document_id"),
    )


def taxonomy_summary_config(cfg: DictConfig) -> TaxonomySummaryConfig:
    section = cfg.taxonomy_summary
    return TaxonomySummaryConfig(
        task=section.task,
        output=_path(section.output),
        results=_list_cfg(section.get("results", ())),
        arms=_list_cfg(section.get("arms", ())),
        dataset_name=section.get("dataset_name", ""),
    )


def accept_gate_config(cfg: DictConfig) -> AcceptGateConfig:
    section = cfg.accept_gate
    return AcceptGateConfig(
        family=section.family,
        baseline=_path(section.baseline),
        candidates=_list_cfg(section.get("candidates", ())),
        output=_path(section.output),
        min_primary_delta=section.get("min_primary_delta", 0.0),
        min_utility_delta=section.get("min_utility_delta", 0.0),
        max_recall_regression=section.get("max_recall_regression", 0.0),
        recall_weight=section.get("recall_weight", 0.05),
        mrr_weight=section.get("mrr_weight", 0.10),
        max_primary_regression=section.get("max_primary_regression", 0.0),
        max_unsafe_increase=section.get("max_unsafe_increase", 0.0),
        max_regression_rate=section.get("max_regression_rate", 0.03),
        bootstrap_rounds=section.get("bootstrap_rounds", 5_000),
        seed=cfg.seed,
    )


def strict_selection_config(cfg: DictConfig) -> StrictSelectionConfig:
    section = cfg.strict_selection
    return StrictSelectionConfig(
        task=section.task,
        candidates=_list_cfg(section.get("candidates", ())),
        output=_path(section.output),
        proposal_ratio=section.get("proposal_ratio", 0.3),
        selection_ratio=section.get("selection_ratio", 0.3),
        split_seed=section.get("split_seed", cfg.seed),
        reward_r3_weight=section.get("reward_r3_weight", 0.1),
        reward_mrr_weight=section.get("reward_mrr_weight", 0.1),
        bootstrap_rounds=section.get("bootstrap_rounds", 10_000),
        seed=cfg.seed,
    )


def offline_policy_config(cfg: DictConfig) -> OfflinePolicyConfig:
    section = cfg.offline_policy
    return OfflinePolicyConfig(
        hybrid_result=_path(section.hybrid_result),
        output=_path(section.output),
        split=section.get("split", "test"),
        baseline_action=section.get("baseline_action", "asr"),
        max_rows=section.get("max_rows", 0),
        train_ratio=section.get("train_ratio", 0.4),
        val_ratio=section.get("val_ratio", 0.3),
        mrr_weight=section.get("mrr_weight", 0.1),
        api_cost=section.get("api_cost", 0.0),
        regression_penalty=section.get("regression_penalty", 0.2),
        confidence_thresholds=_list_cfg(section.get("confidence_thresholds", (0.2, 0.4, 0.6, 0.8))),
        asr_margin_thresholds=_list_cfg(section.get("asr_margin_thresholds", (0.02, 0.05, 0.1, 0.2))),
        omni_margin_thresholds=_list_cfg(section.get("omni_margin_thresholds", (0.02, 0.05, 0.1))),
        bootstrap_rounds=section.get("bootstrap_rounds", 2_000),
        seed=cfg.seed,
    )


@hydra.main(version_base=None, config_path="../../configs", config_name="config")
def main(cfg: DictConfig) -> None:
    seed_everything(cfg.seed)
    log.info("Resolved config:\n%s", OmegaConf.to_yaml(cfg))
    mode = cfg.get("mode", "stub")
    if mode == "stub":
        log.info("Stub mode: no experiment executed for %s", cfg.work_name)
        return
    if mode == "route_policy_eval":
        report = run_route_policy_eval(route_policy_config(cfg))
    elif mode == "manifest_summary":
        report = summarize_manifest(manifest_summary_config(cfg))
    elif mode == "cache_taxonomy_plan":
        report = run_cache_taxonomy_plan(cache_taxonomy_plan_config(cfg))
    elif mode == "cache_taxonomy_runner":
        report = run_cache_taxonomy_runner(cache_taxonomy_runner_config(cfg))
    elif mode == "rag_answer_eval":
        report = run_rag_answer_eval(rag_answer_eval_config(cfg))
    elif mode == "taxonomy_summary":
        report = run_taxonomy_summary(taxonomy_summary_config(cfg))
    elif mode == "accept_gate":
        report = run_accept_gate(accept_gate_config(cfg))
    elif mode == "strict_selection":
        report = run_strict_selection(strict_selection_config(cfg))
    elif mode == "offline_policy":
        report = run_offline_policy(offline_policy_config(cfg))
    else:
        raise ValueError(f"Unsupported Hydra mode: {mode}")
    log.info("Completed %s -> %s", mode, report.get("experiment", "unknown"))


if __name__ == "__main__":
    main()
