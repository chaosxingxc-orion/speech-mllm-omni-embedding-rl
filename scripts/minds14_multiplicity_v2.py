"""scripts/minds14_multiplicity_v2.py — MInDS-14 v2 factorial: Holm/max-T over the 5 UNIQUE
pairwise contrasts (RI mechanical remediation 2026-07-12, item 4; forensic finding 续15:
'MInDS "7/7" 实为 5 独特对比').

Why this script exists: the committed ``_repro/minds14_v2_multiplicity.json`` reports "7/7 deltas
survive Holm at alpha=0.05", but its OWN ``note_on_duplicates`` field already documents that 2 of
the 7 named rows are numerically IDENTICAL duplicates of 2 other rows —
``factor_isolation_deltas.instruction_effect__cards_absent`` == ``deltas_vs_naive.instruction_only``
and ``factor_isolation_deltas.cards_effect__instruction_absent`` == ``deltas_vs_naive.cards_only``
(both computed twice, under two different report keys, by the SAME ``paired_bootstrap(...)`` call in
``scripts/repro_minds14_toolintent_v2.py``). Running a Holm/max-T family-wise correction over a
7-hypothesis family that silently double-counts 2 hypotheses is the wrong correction (it dilutes the
per-comparison alpha budget over a family one-and-a-third times too large, and the max-T step
implicitly treats the duplicate pair as if it were 2 independent-ish draws of correlated evidence
rather than literally the same number twice). This script recomputes the SAME statistical machinery
(W1's ``scripts/baselines/stats.py``: paired-cluster bootstrap, Holm-Bonferroni, bootstrap max-T)
over the 5 UNIQUE contrasts only.

Also closes a provenance gap: no committed script ever generated the prior (7-row)
``_repro/minds14_v2_multiplicity.json`` -- ``git log --all --diff-filter=A --name-only`` shows it
landing in commit f154886 with no corresponding generator. This script is that generator (for the
corrected v2 analysis), fully committed, with provenance (git sha, input sha256, exact command).

The 5 unique pairwise contrasts (dedup mapping, derived from the raw per-item ``hits`` dicts in
``_repro/minds14_toolintent_v2.json``'s ``arms`` block -- NOT from the pre-computed, duplicate-laden
``deltas_vs_naive``/``factor_isolation_deltas`` summary blocks, so this script is an independent
recomputation from the per-item data, not a re-statement of the old summary numbers):

  1. instruction_only          - naive                   (== old factor_isolation_deltas.instruction_effect__cards_absent)
  2. cards_only                - naive                   (== old factor_isolation_deltas.cards_effect__instruction_absent)
  3. instruction_plus_cards    - naive                   (unique; no old duplicate)
  4. instruction_plus_cards    - cards_only               (old factor_isolation_deltas.instruction_effect__cards_present)
  5. instruction_plus_cards    - instruction_only          (old factor_isolation_deltas.cards_effect__instruction_present)

No group/speaker/session metadata exists in ``minds14_toolintent_v2.json`` per item (same honest
fallback the original run used) -- ``stats.py``'s own cluster-bootstrap degrades to item-level
bootstrap and flags ``bootstrap_unit: "item"`` rather than silently reporting a cluster-shaped result.

Reads:  _repro/minds14_toolintent_v2.json  (per-item 'hits' dict per arm: item_id -> 0/1 correct)
Writes (atomic): _repro/minds14_v2_multiplicity_v2.json, with a provenance block (this repo's git
sha/dirty flag, the input file's sha256, and the exact reproduce command).

The prior (7-row, double-counted) ``_repro/minds14_v2_multiplicity.json`` is left in place, append-
only, per CLAUDE.md's research-integrity discipline (records are append-only; re-grade via a new
artifact, never rewrite) -- see the sidecar
``_repro/minds14_v2_multiplicity.superseded-note.md`` pointing here.

Run (WSL venv; only needs stdlib + numpy, no torch/GPU):
    cd projects/speech-mllm-omni-embedding-rl
    ~/.venvs/speechrl/bin/python -u scripts/minds14_multiplicity_v2.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
INPUT_PATH = REPO_ROOT / "_repro" / "minds14_toolintent_v2.json"
OUTPUT_PATH = REPO_ROOT / "_repro" / "minds14_v2_multiplicity_v2.json"

# Cross-repo import: W1 (speech-mllm-training-free-rl) owns the shared bootstrap/Holm/max-T stats
# core (scripts/baselines/stats.py) -- both work repos live side by side under projects/ in the
# same umbrella checkout, and the prior (uncommitted) multiplicity analysis already used this same
# module (see _repro/minds14_v2_multiplicity.json's "method" field), so this script keeps the same
# machinery for an apples-to-apples comparison against that (now-superseded) 7-row result.
W1_BASELINES_DIR = REPO_ROOT.parent / "speech-mllm-training-free-rl" / "scripts" / "baselines"
if str(W1_BASELINES_DIR) not in sys.path:
    sys.path.insert(0, str(W1_BASELINES_DIR))
import stats  # type: ignore  # noqa: E402  (W1 scripts/baselines/stats.py)

ALPHA = 0.05
NBOOT = 10000
BOOT_SEED = 42

# (report name, base_arm, other_arm) -- comparison is always other_arm - base_arm, matching the
# sign convention of the original repro_minds14_toolintent_v2.py deltas.
CONTRASTS: list[tuple[str, str, str]] = [
    ("instruction_only_minus_naive", "naive", "instruction_only"),
    ("cards_only_minus_naive", "naive", "cards_only"),
    ("instruction_plus_cards_minus_naive", "naive", "instruction_plus_cards"),
    ("instruction_plus_cards_minus_cards_only", "cards_only", "instruction_plus_cards"),
    ("instruction_plus_cards_minus_instruction_only", "instruction_only", "instruction_plus_cards"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_provenance(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=str(repo_root), text=True).strip()

    try:
        sha = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain"))
    except Exception as exc:  # pragma: no cover - environment dependent
        sha, dirty = f"UNKNOWN ({exc})", True
    return {"git_sha": sha, "git_dirty": dirty}


def write_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_name, str(path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main() -> int:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    arms = data["arms"]
    # Naive/instruction_only store per-item hits under "hits"; the card arms (cards_only,
    # instruction_plus_cards) run >= 3 disjoint support draws and store the POOLED (mean-over-draws)
    # per-item hit rate under "pooled_hits" instead (see repro_minds14_toolintent_v2.py's module
    # docstring: "the pooled per-row hit rate is the unit used for the arm's paired-bootstrap
    # deltas") -- same shape (item_id -> float in [0, 1]), just a different dict key per arm kind.
    def hits_of(arm: str) -> dict[str, float]:
        a = arms[arm]
        return a["hits"] if "hits" in a else a["pooled_hits"]

    eval_ids = sorted(hits_of("naive").keys())  # deterministic item order across all arms
    n_items = len(eval_ids)
    groups = [None] * n_items  # no speaker/session metadata in this artifact -- honest fallback

    comparisons: list[dict[str, Any]] = []
    maxT_input: list[dict[str, Any]] = []
    for name, base_arm, other_arm in CONTRASTS:
        hits_base = hits_of(base_arm)
        hits_other = hits_of(other_arm)
        scores_a = [float(hits_other[i]) for i in eval_ids]
        scores_b = [float(hits_base[i]) for i in eval_ids]

        deltas, point, n_clusters, n_i, unit = stats._paired_cluster_bootstrap_deltas(
            scores_a, scores_b, groups, nboot=NBOOT, seed=BOOT_SEED
        )
        p = stats.bootstrap_pvalue(deltas)
        comparisons.append({
            "name": name,
            "base_arm": base_arm,
            "other_arm": other_arm,
            "comparison": f"{other_arm} - {base_arm}",
            "n_items": n_i,
            "bootstrap_unit": unit,
            "observed_delta": round(point, 4),
            "raw_bootstrap_p": p,
        })
        maxT_input.append({"scores_a": scores_a, "scores_b": scores_b, "groups": groups})

    pvals = [c["raw_bootstrap_p"] for c in comparisons]
    holm = stats.holm_bonferroni(pvals, alpha=ALPHA)
    maxT = stats.max_t_adjusted_pvalues(maxT_input, nboot=NBOOT, seed=BOOT_SEED, alpha=ALPHA)

    for i, c in enumerate(comparisons):
        c["holm_adjusted_p"] = holm["adjusted_p"][i]
        c["holm_reject_at_alpha"] = holm["reject"][i]
        c["maxT_observed_z"] = maxT["observed_z"][i]
        c["maxT_adjusted_p"] = maxT["adjusted_p"][i]
        c["maxT_reject_at_alpha"] = maxT["reject"][i]

    survivors_holm = [c["name"] for c in comparisons if c["holm_reject_at_alpha"]]
    survivors_maxT = [c["name"] for c in comparisons if c["maxT_reject_at_alpha"]]

    provenance = git_provenance(REPO_ROOT)
    provenance.update({
        "input_path": str(INPUT_PATH.relative_to(REPO_ROOT)),
        "input_sha256": sha256_file(INPUT_PATH),
        "command": "python scripts/minds14_multiplicity_v2.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    })

    out = {
        "experiment": "minds14_toolintent_v2_factorial -- family-wise multiplicity, v2 (5 UNIQUE contrasts)",
        "supersedes": (
            "_repro/minds14_v2_multiplicity.json (RI item 4 / 续15 finding: that 7-row family "
            "double-counted 2 report-key duplicates -- see this file's own note_on_duplicates and "
            "_repro/minds14_v2_multiplicity.superseded-note.md)"
        ),
        "dedup_note": (
            "The prior 7-row analysis reported factor_isolation_deltas.instruction_effect__cards_absent "
            "and deltas_vs_naive.instruction_only as two rows; they are the SAME comparison "
            "(instruction_only - naive) computed twice under two report keys. Likewise "
            "factor_isolation_deltas.cards_effect__instruction_absent duplicates "
            "deltas_vs_naive.cards_only (cards_only - naive). This script recomputes over the 5 "
            "UNIQUE pairwise contrasts that remain after removing both duplicates."
        ),
        "alpha": ALPHA,
        "nboot": NBOOT,
        "boot_seed": BOOT_SEED,
        "comparisons": comparisons,
        "n_survive_holm": len(survivors_holm),
        "survivors_holm": survivors_holm,
        "n_survive_maxT": len(survivors_maxT),
        "survivors_maxT": survivors_maxT,
        "provenance": provenance,
    }

    write_atomic(OUTPUT_PATH, out)
    print(f"wrote {OUTPUT_PATH}", flush=True)
    print(f"n_survive_holm={len(survivors_holm)}/5  n_survive_maxT={len(survivors_maxT)}/5", flush=True)
    for c in comparisons:
        sig = "HOLM-SIG" if c["holm_reject_at_alpha"] else "holm-n.s."
        print(f"  {c['name']}: delta={c['observed_delta']:+.4f} raw_p={c['raw_bootstrap_p']:.4g} "
              f"holm_p={c['holm_adjusted_p']:.4g} ({sig})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
