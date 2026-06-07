"""Entrypoint for: RL-Based Omni Embedding Models for Speech Tasks.

Hydra-configured. The RL loop is a stub — fill it in per the work's approach:
RL over contrastive/retrieval objectives for embeddings.
"""
from __future__ import annotations

import hydra
from omegaconf import DictConfig, OmegaConf

from speechrl_common import get_logger, seed_everything

log = get_logger("omni_embedding_rl")


@hydra.main(version_base=None, config_path="../../configs", config_name="config")
def main(cfg: DictConfig) -> None:
    seed_everything(cfg.seed)
    log.info("Resolved config:\n%s", OmegaConf.to_yaml(cfg))
    log.info("TODO: implement the RL loop (%s) for %s", cfg.rl.algo, cfg.work_name)


if __name__ == "__main__":
    main()
