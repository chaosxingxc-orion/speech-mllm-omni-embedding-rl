"""Paralinguistic-negative probe: how much speaker / emotion does the FROZEN omni CONTENT embedding carry?

Supports the honest NEGATIVE of the collapsed single-model paper: the frozen omni-embed read-out carries
strong content but near-chance speaker and only modest emotion — so training-free selection has little
paralinguistic spread to exploit. We report ABSOLUTE dev-selected test accuracy vs chance per factor
(NOT the "at chance" overstatement): speaker is near-chance; emotion is real-but-modest.

Method (per factor in {speaker, emotion}, per seed):
  1. load seeded, emotion-balanced CREMA-D dev/test splits (closed-set speaker-ID is evaluable);
  2. masked-mean-pool the omni-embed Thinker layers in PP_LAYERS (L2-normed, dim 2048);
  3. dev-select the best layer on an internal dev_fit -> dev_val kNN split (NEVER on test);
  4. refit kNN on full dev at the selected layer, evaluate ONCE on the locked test;
  5. bootstrap CI on test accuracy; compare to chance (1/#classes).
Reports across-seed mean accuracy + range and a committed JSON.

Run (RTX 5090 / WSL2, venv ~/.venvs/speechrl):
  SPEECHRL_DATA_DIR=<repo>/speechrl-data HF_HUB_OFFLINE=1 \
    ~/.venvs/speechrl/bin/python projects/speech-mllm-omni-embedding-rl/scripts/paralinguistic_negative_probe.py
  env: PP_SEEDS=42,7,123  PP_DEV=600  PP_TEST=300  PP_LAYERS=0,8,16,24,32,36  PP_DEVVAL=150
"""
import os, json, time
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import KNeighborsClassifier

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.layer_probe import extract_layer_embeddings
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
SEEDS = [int(x) for x in os.environ.get("PP_SEEDS", "42,7,123").split(",")]
DEV = int(os.environ.get("PP_DEV", "600"))
TEST = int(os.environ.get("PP_TEST", "300"))
LAYERS = [int(x) for x in os.environ.get("PP_LAYERS", "0,8,16,24,32,36").split(",")]
DEVVAL = int(os.environ.get("PP_DEVVAL", "150"))
NBOOT = int(os.environ.get("PP_NBOOT", "2000"))
FACTORS = ["speaker", "emotion"]
K = 5
OUT = os.path.join(os.path.dirname(__file__), "..", "_repro", "paralinguistic_negative_probe.json")


def knn_correct(Xtr, ytr, Xte, yte):
    clf = KNeighborsClassifier(n_neighbors=K)
    clf.fit(np.asarray(Xtr), np.asarray(ytr))
    return (clf.predict(np.asarray(Xte)) == np.asarray(yte)).astype(float)


def dev_select_layer(E, yfit, yval, n_fit):
    best_L, best = LAYERS[0], -1.0
    for L in LAYERS:
        X = E[L]
        acc = knn_correct(X[:n_fit], yfit, X[n_fit:], yval).mean()
        if acc > best:
            best_L, best = L, acc
    return best_L, float(best)


def run_seed(model, seed):
    splits = D.load_splits(ROOT, seed=seed, dev_size=DEV, test_size=TEST)
    dev, test = splits["dev"], splits["test"]
    wd = [load_audio(c.path, target_sr=16000) for c in dev]
    wt = [load_audio(c.path, target_sr=16000) for c in test]

    class E: pass
    emb = E(); emb.model = model
    Ed = extract_layer_embeddings(emb, wd, layers=LAYERS, batch_size=8)
    Et = extract_layer_embeddings(emb, wt, layers=LAYERS, batch_size=8)

    n_fit = DEV - DEVVAL
    rng = np.random.default_rng(seed)
    out = {}
    for factor in FACTORS:
        yd = np.asarray(D.labels(dev, factor)); yt = np.asarray(D.labels(test, factor))
        chance = 1.0 / len(set(yd.tolist()))
        Lsel, dv = dev_select_layer(Ed, yd[:n_fit], yd[n_fit:], n_fit)
        corr = knn_correct(Ed[Lsel], yd, Et[Lsel], yt)
        acc = float(corr.mean())
        n = len(corr)
        boots = np.empty(NBOOT)
        for i in range(NBOOT):
            idx = rng.integers(0, n, n)
            boots[i] = corr[idx].mean()
        lo, hi = float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))
        out[factor] = {"sel_layer": Lsel, "devval_acc": round(dv, 4), "test_acc": round(acc, 4),
                       "acc_ci95": [round(lo, 4), round(hi, 4)], "chance": round(chance, 4),
                       "ratio_over_chance": round(acc / chance, 2), "n_classes": len(set(yd.tolist()))}
    return {"seed": seed, **out}


def main():
    t0 = time.time()
    print(f"model={MODEL}\nseeds={SEEDS} dev={DEV} test={TEST} layers={LAYERS}")
    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    per_seed = []
    for s in SEEDS:
        r = run_seed(model, s)
        per_seed.append(r)
        for f in FACTORS:
            d = r[f]
            print(f"seed {s:>4} {f:>8}: acc={d['test_acc']:.3f} CI[{d['acc_ci95'][0]:.3f},{d['acc_ci95'][1]:.3f}] "
                  f"chance={d['chance']:.3f} ({d['ratio_over_chance']}x) @L{d['sel_layer']}", flush=True)

    summary = {}
    for f in FACTORS:
        accs = np.array([r[f]["test_acc"] for r in per_seed])
        chance = per_seed[0][f]["chance"]
        summary[f] = {
            "mean_test_acc": round(float(accs.mean()), 4),
            "acc_range": [round(float(accs.min()), 4), round(float(accs.max()), 4)],
            "chance": round(chance, 4), "mean_ratio_over_chance": round(float(accs.mean() / chance), 2),
            "n_classes": per_seed[0][f]["n_classes"],
        }
    summary["verdict"] = (
        f"Frozen omni-embed content read-out on CREMA-D: SPEAKER near-chance "
        f"(mean acc {summary['speaker']['mean_test_acc']:.3f} vs chance {summary['speaker']['chance']:.3f}, "
        f"{summary['speaker']['mean_ratio_over_chance']}x); EMOTION real-but-modest "
        f"(mean acc {summary['emotion']['mean_test_acc']:.3f} vs chance {summary['emotion']['chance']:.3f}, "
        f"{summary['emotion']['mean_ratio_over_chance']}x). The content encoder carries little exploitable "
        f"paralinguistic spread — consistent with the null training-free paralinguistic gain."
    )
    out = {"summary": summary, "per_seed": per_seed,
           "config": {"model": "omni-embed-nemotron-3b", "k": K, "layers": LAYERS, "dev": DEV, "test": TEST,
                      "devval": DEVVAL, "method": "dev-selected layer per factor; kNN; bootstrap CI on test acc vs chance"},
           "elapsed_s": round(time.time() - t0, 1)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("wrote", os.path.abspath(OUT))
    print("NEGATIVE_PROBE_DONE")


if __name__ == "__main__":
    main()
