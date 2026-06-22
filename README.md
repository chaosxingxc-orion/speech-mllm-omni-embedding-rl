# RL-Based Omni Embedding Models for Speech Tasks

> **Status: 🟡 Skeleton.** Hydra scaffold in place; the `omni-embed-nemotron-3b` download target is
> wired. RL objective to be filled in. Use W1
> ([speech-mllm-training-free-rl](https://github.com/chaosxingxc-orion/speech-mllm-training-free-rl))
> as the reference pattern.
>
> Part of the **chaos speech-multimodal-LLM RL** series. Shares code via the
> `speechrl-common` package (installed from `../../common`).
> Umbrella: [exploring-l4-intelligence](https://github.com/chaosxingxc-orion/exploring-l4-intelligence).

## Idea

RL-optimized omni/embedding models for speech, targeting personalized performance across diverse downstream tasks.

**RL approach:** RL over contrastive/retrieval objectives for embeddings.

## Setup (WSL2)

```bash
source ~/.venvs/speechrl/bin/activate          # shared env, see ../../docs/setup.md
uv pip install -e ../../common -e .
```

## Run

```bash
bash scripts/train.sh                          # train (Hydra config in configs/)
bash scripts/train.sh rl.learning_rate=2e-6    # override any config key
bash scripts/eval.sh                           # evaluate
```

## Layout

- `src/omni_embedding_rl/main.py` — Hydra entrypoint (fill in the RL loop)
- `configs/` — Hydra configs: `model/`, `dataset/`, `rl/`, `experiment/`
- `scripts/` — `train.sh`, `eval.sh`
- depends on `speechrl_common` for audio I/O, reward functions, MLflow tracking, prompts

## Status & roadmap

Skeleton. Next: implement the contrastive/retrieval RL objective and a retrieval evaluation; the W4
omni-embedding model (`omni-embed-nemotron-3b`) download target is already wired in the umbrella's
data scripts. Track progress on the umbrella Wiki's
[Per-Work-Status](https://github.com/chaosxingxc-orion/exploring-l4-intelligence/wiki/Per-Work-Status).

---

## 中文

面向语音的 RL 优化 omni/嵌入模型，目标是在多样下游任务上的个性化表现。**当前是骨架**：Hydra 脚手架已就
位，`omni-embed-nemotron-3b` 下载目标已接好，RL 目标（对比/检索）待实现，请以 W1 为参考范式。环境与命令
见上（详见 `../../docs/setup.md`）。
