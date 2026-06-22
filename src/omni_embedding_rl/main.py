"""Entrypoint: training-free RL on a frozen omni-embedding model for speech disentanglement.

The flagship proof is the CREMA-D two-factor (speaker x emotion) closed loop under Operator A
(``rl.algo == "embed_search"``): encode the same audio under several task conditionings, score each
with a verifiable probe reward, select the best conditioning per factor, and report the
conditioning x factor accuracy matrix vs a no-conditioning baseline — all on a FROZEN model. Other
``rl.algo`` values remain stubs for now.
"""
from __future__ import annotations

import hydra
from omegaconf import DictConfig, OmegaConf

from speechrl_common import get_logger, seed_everything
from speechrl_common.tracking.mlflow_logger import mlflow_run

log = get_logger("omni_embedding_rl")


def _run_embed_search(cfg: DictConfig) -> None:
    from pathlib import Path

    from omni_embedding_rl import eval_harness
    from speechrl_common.models.omni_embed import load_omni_embedder
    from speechrl_common.utils.checkpoint import run_dir

    cache_dir = run_dir(cfg.work_name, cfg.run_name)
    # Skip the (heavy) model load when reproducing a cached run from disk.
    cache_hit = cfg.get("mode", "train") == "eval" and (Path(cache_dir) / "embeddings.npz").exists()
    embedder = None
    if cache_hit:
        log.info("mode=eval + cache hit -> skipping model load, reusing %s/embeddings.npz", cache_dir)
    else:
        model_path = cfg.model.get("local_path") or cfg.model.hf_id
        log.info("Loading frozen omni-embedder: %s", model_path)
        embedder = load_omni_embedder(
            model_path,
            torch_dtype=cfg.model.dtype,
            attn_implementation=cfg.model.attn_implementation,
        )

    params = {
        "model": cfg.model.name, "operator": cfg.rl.operator, "probe": cfg.rl.probe,
        "knn_k": cfg.rl.knn_k, "seed": cfg.seed,
        "dev_size": cfg.dataset.dev_size, "test_size": cfg.dataset.test_size,
        "mode": cfg.get("mode", "train"),
    }
    with mlflow_run(cfg.tracking.experiment, cfg.run_name, params=params) as run:
        import mlflow  # lazy
        res = eval_harness.run(embedder, cfg, cache_dir=cache_dir)
        log.info("dev=%d test=%d  diagonal_dominant=%s",
                 res["n_dev"], res["n_test"], res["diagonal_dominant"])
        mlflow.log_metric("diagonal_dominant", float(res["diagonal_dominant"]))
        # conditioning x factor matrix
        for cname, row in res["matrix"].items():
            for factor, acc in row.items():
                mlflow.log_metric(f"acc__{cname}__{factor}", float(acc))
        # per-factor selected-vs-baseline delta + CIs
        for factor, info in res["per_factor"].items():
            mlflow.log_metric(f"delta__{factor}", float(info["delta"]))
            mlflow.log_metric(f"acc_selected__{factor}", float(info["test_acc_selected"]))
            mlflow.log_metric(f"acc_baseline__{factor}", float(info["test_acc_baseline"]))
            log.info("factor=%s selected=%s delta=%+.3f (sel CI=%s, base CI=%s)",
                     factor, info["selected_conditioning"], info["delta"],
                     info["ci_selected"], info["ci_baseline"])
        mlflow.log_dict(res, "results.json")
        log.info("MLflow run: %s", getattr(run, "info", None) and run.info.run_id)


@hydra.main(version_base=None, config_path="../../configs", config_name="config")
def main(cfg: DictConfig) -> None:
    seed_everything(cfg.seed)
    log.info("Resolved config:\n%s", OmegaConf.to_yaml(cfg))
    if cfg.rl.algo == "embed_search":
        _run_embed_search(cfg)
    else:
        log.info("TODO: implement the RL loop (%s) for %s", cfg.rl.algo, cfg.work_name)


if __name__ == "__main__":
    main()
