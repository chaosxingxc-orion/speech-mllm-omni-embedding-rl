# Omni-Embedding Speech Disentanglement via Training-Free RL (Flagship · W4)

> **Status: 🟡 Skeleton → active (flagship).** The first end-to-end proof (CREMA-D two-factor) is
> wired; the per-task fan-out follows.
>
> Part of the **exploring-l4-intelligence** series. Project purpose:
> [Project-Thesis](https://github.com/chaosxingxc-orion/exploring-l4-intelligence/wiki/Project-Thesis).
> Shares code via `speechrl-common` (installed from `../../common`). W1
> ([speech-mllm-training-free-rl](https://github.com/chaosxingxc-orion/speech-mllm-training-free-rl))
> is the mature training-free *pattern* reference this work reuses.

## Idea

Use **training-free RL** — reward-guided, inference-time optimization that changes **no weights and
no structure** — to *activate* the knowledge a frozen omni-embedding model absorbed in pretraining,
and **disentangle** its speech representation: steer task-conditioned embeddings of the *same* audio
so that different conditionings give different, individually-better downstream performance across
content/ASR+ST, speaker-ID, emotion/SER, and language+intent.

- **Backbone (frozen):** `omni-embed-nemotron-3b` — a SentenceTransformer (dim 2048, cosine) on the
  Qwen2.5-Omni Thinker. Instruction-aware: the `text` paired with the audio is the conditioning hook.
- **Operator A (this proof):** encode under each conditioning variant, score with a **verifiable**
  probe/retrieval reward, select the best conditioning per factor — no weight update.
- **Operator B (future):** generative-omni best-of-N / MBR then export an embedding, for factors the
  embedder suppresses.

Math & per-factor operator decision:
[W4-Training-Free-RL-Feasibility](https://github.com/chaosxingxc-orion/exploring-l4-intelligence/wiki/W4-Training-Free-RL-Feasibility).
Full plan: [W4-Research-Plan](https://github.com/chaosxingxc-orion/exploring-l4-intelligence/wiki/W4-Research-Plan).

## Setup (WSL2)

```bash
source ~/.venvs/speechrl/bin/activate          # shared env, see ../../docs/setup.md
uv pip install -e ../../common -e .
# data root (where speechrl-data/{models,datasets} live):
export SPEECHRL_DATA_DIR=/mnt/d/chao_workspace/exploring-l4-intelligence/speechrl-data
```

## Run — the CREMA-D two-factor disentanglement proof

```bash
bash scripts/train.sh seed=42          # encode under each conditioning, build the matrix, log to MLflow
bash scripts/eval.sh                   # +mode=eval — reproduce the matrix from cached embeddings
```

The run logs, per (conditioning × factor), the test probe accuracy, plus the Operator-A
selected-vs-baseline delta per factor with bootstrap CIs, and a `diagonal_dominant` flag. A
diagonal-dominant matrix (emotion-conditioning best for emotion, speaker-conditioning best for
speaker) demonstrates steerable disentanglement; a flat row means that factor is suppressed →
Operator B is prescribed for it (a result, not a failure).

## Layout

- `src/omni_embedding_rl/main.py` — Hydra entrypoint; dispatches `rl.algo=embed_search` to the proof loop
- `src/omni_embedding_rl/{data_cremad,conditioning,probes,eval_harness}.py` — the closed loop
- `configs/` — `model/omni_embed`, `dataset/cremad`, `rl/embed_search`, `experiment/cremad_proof`
- `tests/test_data_cremad.py` — split-contract tests (run without the model)
- depends on `speechrl_common` for the omni-embed loader, verifiable rewards/metrics, eval harness, MLflow

## Data note (CREMA-D)

Emotion label = the **filename** EMO code (6 balanced classes); speaker = filename prefix (91). The
CSV `classname` column is heavily neutral-skewed and is **not** used as the emotion label — CSVs only
define the train/test pools. See the umbrella `docs/data.md`.

## License note

`omni-embed-nemotron-3b` is under NVIDIA OneWay Noncommercial + Qwen Research terms — research/eval
only; do not redistribute weights.

---

## 中文

用**免训练 RL**（奖励引导、推理时、不改权重不改结构）激活一个冻结 omni 嵌入模型在预训练中习得的知识，并
**解耦**其语音表示：引导同一段音频在不同任务条件下的嵌入，使其在内容/ASR+ST、说话人、情感/SER、语言+意图
上产生不同且各自更优的下游表现。底座（冻结）= `omni-embed-nemotron-3b`（SentenceTransformer，2048 维，
基于 Qwen2.5-Omni Thinker；指令感知——随音频附带的 text 即条件化钩子）。**算子 A**（本验证）：在每种条件化
下编码，用可验证探针/检索奖励打分并逐因子选最优条件化，不改权重；**算子 B**（后续）：生成式 best-of-N/MBR
后导出嵌入，用于被压制的因子。首个验证＝CREMA-D 双因子（同音频说话人+情感），`bash scripts/train.sh
seed=42` 一条命令可复现，MLflow 记录条件×因子矩阵、逐因子选中-vs-基线 delta 及自助置信区间；对角占优即解耦
成立，某因子矩阵行平坦则说明被压制→改用算子 B（属结论而非失败）。数学与逐因子算子决策见 Wiki
W4-Training-Free-RL-Feasibility，完整计划见 W4-Research-Plan。CREMA-D 情感标签取**文件名**情感码（6 类均衡），
说话人取文件名前缀；CSV 的 classname 偏 neutral，不作情感标签。模型为 NVIDIA OneWay 非商业 + Qwen Research
许可，仅研究/评测，勿分发权重。
