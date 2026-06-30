"""Pooling-method probe, RIGOROUS upgrade (W4 adversarial-review round): dev-selection + paired-delta CI + multi-seed.

Fixes two methodological flaws in `pool_method_probe.py` that the adversarial review flagged:
  (a) it test-selected the best layer (oracle / winner's curse);
  (b) it reported two MARGINAL bootstrap CIs, not a CI on the baseline->selected DELTA.

This script instead:
  1. selects the per-pool layer on a DEV-internal validation split (dev_fit -> dev_val), never on test;
  2. refits the kNN probe on the FULL dev at the dev-selected layer and evaluates ONCE on the locked test;
  3. computes a PAIRED bootstrap CI on the per-clip (selected - baseline) accuracy delta (same test clips);
  4. repeats over >=5 seeds and reports the across-seed delta + how many seeds' paired CI excludes 0;
  5. reports a content contamination probe (CREMA-D's 12 fixed sentences -> near-ceiling content readout);
  6. writes a results JSON for provenance.

Baseline pool = `audio` (first-order audio-token mean, the deployed read-out).
Selected pool = `audio_attn` (weight-free attentive statistics; still training-free, no params).

Run (RTX 5090 / WSL2, venv ~/.venvs/speechrl):
  reproduce: SPEECHRL_DATA_DIR=<repo>/speechrl-data HF_HUB_OFFLINE=1 \
    ~/.venvs/speechrl/bin/python projects/speech-mllm-omni-embedding-rl/scripts/pool_method_probe_paired.py
  env: PP_SEEDS=42,7,123,2024,31337  PP_DEV=600  PP_TEST=300  PP_LAYERS=0,8,16,24,32,36
       PP_BASE=audio  PP_SEL=audio_attn  PP_NBOOT=2000  PP_DEVVAL=150
"""
import os, json, time
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import KNeighborsClassifier

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.layer_probe import extract_pooled
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
SEEDS = [int(x) for x in os.environ.get("PP_SEEDS", "42,7,123,2024,31337").split(",")]
DEV = int(os.environ.get("PP_DEV", "600"))
TEST = int(os.environ.get("PP_TEST", "300"))
LAYERS = [int(x) for x in os.environ.get("PP_LAYERS", "0,8,16,24,32,36").split(",")]
BASE = os.environ.get("PP_BASE", "audio")
SEL = os.environ.get("PP_SEL", "audio_attn")
NBOOT = int(os.environ.get("PP_NBOOT", "2000"))
DEVVAL = int(os.environ.get("PP_DEVVAL", "150"))   # held-out validation size for layer selection
POOLS = [BASE, SEL]
K = 5
OUT = os.path.join(os.path.dirname(__file__), "..", "_repro", "emotion_pool_paired_v2.json")


def knn_correct(Xtr, ytr, Xte, yte):
    """Per-clip 0/1 correctness vector of a k-NN probe fit on (Xtr,ytr), evaluated on (Xte,yte)."""
    clf = KNeighborsClassifier(n_neighbors=K)
    clf.fit(np.asarray(Xtr), np.asarray(ytr))
    preds = clf.predict(np.asarray(Xte))
    return (preds == np.asarray(yte)).astype(float)


def dev_select_layer(Ed, pool, yfit, yval, n_fit):
    """Pick the layer maximizing kNN(dev_fit -> dev_val) accuracy; NEVER touches test."""
    best_L, best_acc = LAYERS[0], -1.0
    for L in LAYERS:
        X = Ed[pool][L]
        Xfit, Xval = X[:n_fit], X[n_fit:]
        acc = knn_correct(Xfit, yfit, Xval, yval).mean()
        if acc > best_acc:
            best_L, best_acc = L, acc
    return best_L, best_acc


def run_seed(model, seed):
    splits = D.load_splits(ROOT, seed=seed, dev_size=DEV, test_size=TEST)
    dev, test = splits["dev"], splits["test"]
    wd = [load_audio(c.path, target_sr=16000) for c in dev]
    wt = [load_audio(c.path, target_sr=16000) for c in test]
    yd_emo = np.asarray(D.labels(dev, "emotion")); yt_emo = np.asarray(D.labels(test, "emotion"))
    yd_con = np.asarray(D.labels(dev, "content")); yt_con = np.asarray(D.labels(test, "content"))

    class E: pass
    emb = E(); emb.model = model
    Ed = extract_pooled(emb, wd, layers=LAYERS, pools=POOLS, batch_size=8)
    Et = extract_pooled(emb, wt, layers=LAYERS, pools=POOLS, batch_size=8)

    n_fit = DEV - DEVVAL
    yfit, yval = yd_emo[:n_fit], yd_emo[n_fit:]

    # dev-select a layer for each pool, then lock and evaluate on test
    Lb, dvb = dev_select_layer(Ed, BASE, yfit, yval, n_fit)
    Ls, dvs = dev_select_layer(Ed, SEL, yfit, yval, n_fit)
    cb = knn_correct(Ed[BASE][Lb], yd_emo, Et[BASE][Lb], yt_emo)   # baseline correctness on test
    cs = knn_correct(Ed[SEL][Ls], yd_emo, Et[SEL][Ls], yt_emo)     # selected correctness on test
    acc_b, acc_s = float(cb.mean()), float(cs.mean())
    delta = acc_s - acc_b

    # paired bootstrap on the per-clip delta (same resampled test indices for both)
    rng = np.random.default_rng(seed)
    n = len(cb)
    deltas = np.empty(NBOOT)
    for i in range(NBOOT):
        idx = rng.integers(0, n, n)
        deltas[i] = cs[idx].mean() - cb[idx].mean()
    dlo, dhi = float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))

    # contamination probe: content readout on the 12 fixed sentences (dev-selected layer of SEL)
    cc = knn_correct(Ed[SEL][Ls], yd_con, Et[SEL][Ls], yt_con)
    content_acc = float(cc.mean())

    return {
        "seed": seed, "base_pool": BASE, "base_layer": Lb, "base_devval_acc": round(dvb, 4),
        "sel_pool": SEL, "sel_layer": Ls, "sel_devval_acc": round(dvs, 4),
        "acc_base": round(acc_b, 4), "acc_sel": round(acc_s, 4), "delta": round(delta, 4),
        "delta_ci95": [round(dlo, 4), round(dhi, 4)], "delta_ci_excludes_0": bool(dlo > 0 or dhi < 0),
        "content_acc": round(content_acc, 4),
    }


def main():
    t0 = time.time()
    print(f"model={MODEL}\nroot={ROOT}\nseeds={SEEDS} dev={DEV} test={TEST} devval={DEVVAL} "
          f"base={BASE} sel={SEL} layers={LAYERS} nboot={NBOOT}")
    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    per_seed = []
    for s in SEEDS:
        r = run_seed(model, s)
        per_seed.append(r)
        print(f"seed {s:>6}: base {BASE}@L{r['base_layer']}={r['acc_base']:.3f}  "
              f"sel {SEL}@L{r['sel_layer']}={r['acc_sel']:.3f}  delta={r['delta']:+.3f} "
              f"CI[{r['delta_ci95'][0]:+.3f},{r['delta_ci95'][1]:+.3f}] "
              f"{'SIG' if r['delta_ci_excludes_0'] else 'n.s.'}  content={r['content_acc']:.3f}")

    deltas = np.array([r["delta"] for r in per_seed])
    accs_b = np.array([r["acc_base"] for r in per_seed]); accs_s = np.array([r["acc_sel"] for r in per_seed])
    n_sig = sum(r["delta_ci_excludes_0"] and r["delta"] > 0 for r in per_seed)
    summary = {
        "n_seeds": len(SEEDS),
        "mean_acc_base": round(float(accs_b.mean()), 4), "mean_acc_sel": round(float(accs_s.mean()), 4),
        "mean_delta": round(float(deltas.mean()), 4),
        "delta_across_seed_std": round(float(deltas.std(ddof=1)), 4),
        "delta_min": round(float(deltas.min()), 4), "delta_max": round(float(deltas.max()), 4),
        "n_seeds_paired_CI_excludes_0_positive": int(n_sig),
        "mean_content_acc": round(float(np.mean([r["content_acc"] for r in per_seed])), 4),
        "verdict": ("emotion gain SURVIVES dev-selection + paired CI" if n_sig == len(SEEDS)
                    else f"emotion gain is FRAGILE: paired CI excludes 0 in only {n_sig}/{len(SEEDS)} seeds"),
    }
    out = {"summary": summary, "per_seed": per_seed,
           "config": {"model": "omni-embed-nemotron-3b", "k": K, "layers": LAYERS,
                      "dev": DEV, "test": TEST, "devval": DEVVAL, "nboot": NBOOT,
                      "method": "dev-selected layer per pool; paired bootstrap on per-clip delta"},
           "elapsed_s": round(time.time() - t0, 1)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("wrote", os.path.abspath(OUT))
    print("PAIRED_PROBE_DONE")


if __name__ == "__main__":
    main()
