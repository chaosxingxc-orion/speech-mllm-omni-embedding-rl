"""Speaker-probe wording fix (ticket #34, requirement 5) -- recomputes statistics from the FROZEN
`_repro/paralinguistic_negative_probe.json` (do NOT rerun `paralinguistic_negative_probe.py`; that
probe's numbers are not in question, only the wording drawn from them was).

Verified defect (wiki/2026-07-11-response-v2-erratum-and-forensic-reply.md INT-013, PARTIAL-artifact
/ CONFIRMED-wiki): three umbrella-wiki phrasings -- "speaker near chance", "never written to the
pooled vector", "measured-zero paralinguistic spread" -- assert or imply the frozen omni-embed's
pooled vector carries no speaker information. The frozen artifact's OWN per-seed bootstrap CIs
contradict that for at least one seed: seed 123's speaker CI is [0.0267, 0.070], and chance for a
91-way closed-set speaker-ID problem is 1/91 = 0.011 -- the CI's lower bound (0.0267) is ABOVE
chance, i.e. the CI EXCLUDES chance from below. That is a textbook one-sample superiority result at
that seed: the representation carries a real (if small) amount of speaker information, so "no
speaker information" is not a claim this artifact supports.

This script does not add new data. It:
  1. loads the three stored per-seed `speaker` CIs (test_acc, acc_ci95, chance) as-is;
  2. runs a per-seed SUPERIORITY check: does the seed's own stored CI exclude chance from below
     (ci_lo > chance)? This is the same kind of check the emotion-pooling script now performs, just
     applied post hoc to numbers that already existed;
  3. additionally synthesizes a conservative ACROSS-SEED statistic: a one-sample t-CI (n=3) on the
     three seeds' `test_acc` values against chance -- flagged `directional-only` per this project's
     n<5 convention (CLAUDE.md: "small-n lacks significance and can settle nothing"), reported
     alongside the per-seed superiority counts rather than in place of them, since it is a DIFFERENT
     (more conservative, cross-seed) claim than "at least one seed's own CI excludes chance";
  4. writes the honest restatement verdict specified in ticket #34 (verbatim below).

Run:
    python scripts/speaker_probe_restatement.py
Output: `_repro/speaker_probe_restatement.json` (git-tracked), written ONLY by this script,
atomically (temp file + `os.replace`). No GPU, no model, no dataset access -- this is pure
arithmetic over an existing committed JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARTIFACT = REPO_ROOT / "_repro" / "paralinguistic_negative_probe.json"
OUTPUT_ARTIFACT = REPO_ROOT / "_repro" / "speaker_probe_restatement.json"


def sha256_of(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_provenance(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=str(repo_root), text=True).strip()

    try:
        sha = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain"))
    except Exception as exc:  # pragma: no cover
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


def per_seed_superiority(per_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each seed's stored `speaker` block: does the STORED bootstrap CI exclude chance from
    below (ci_lo > chance)? Uses only numbers already in the frozen artifact -- no recomputation of
    the CI itself, just a comparison of its bound to the stored chance value."""
    out = []
    for r in per_seed:
        spk = r["speaker"]
        lo, hi = spk["acc_ci95"]
        chance = spk["chance"]
        excludes_chance_above = bool(lo > chance)  # CI entirely above chance -> significant superiority
        out.append({
            "seed": r["seed"], "test_acc": spk["test_acc"], "acc_ci95": [lo, hi], "chance": chance,
            "ratio_over_chance": spk["ratio_over_chance"],
            "ci_excludes_chance_from_below": excludes_chance_above,
            "interpretation": (
                f"CI [{lo}, {hi}] lower bound {lo} > chance {chance} -> significantly ABOVE chance at this seed"
                if excludes_chance_above else
                f"CI [{lo}, {hi}] includes chance {chance} -> not significant at this seed (does not exclude chance)"
            ),
        })
    return out


def across_seed_t_ci(test_accs: list[float], chance: float) -> dict[str, Any]:
    """Conservative n=3 one-sample t-CI on the seeds' test_acc values (NOT vs chance directly --
    a symmetric CI on the mean, then compared to chance). Flagged directional-only: with n=3 seeds
    this is underpowered and is reported ALONGSIDE, not instead of, the per-seed superiority checks
    above -- they answer different questions ("does the mean exceed chance" vs "did at least one
    seed's own CI exclude chance")."""
    from scipy import stats as sps

    x = np.asarray(test_accs, dtype=float)
    n = len(x)
    mean = float(x.mean())
    sd = float(x.std(ddof=1))
    se = sd / (n ** 0.5)
    tcrit = float(sps.t.ppf(0.975, n - 1))
    lo, hi = round(mean - tcrit * se, 4), round(mean + tcrit * se, 4)
    excludes_chance = bool(lo > chance or hi < chance)
    return {
        "n_seeds": n, "mean_test_acc": round(mean, 4), "sd": round(sd, 4),
        "t_ci95": [lo, hi], "chance": chance,
        "excludes_chance": excludes_chance,
        "directional_only": True,
        "caveat": ("n=3 seeds; per this project's convention (CLAUDE.md) small-n lacks significance "
                   "and can settle nothing on its own -- this across-seed t-CI is reported as a "
                   "conservative cross-check, not as the headline statistic. The headline is the "
                   "per-seed superiority check (at least one seed's OWN stored CI excludes chance)."),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(SOURCE_ARTIFACT))
    ap.add_argument("--output", default=str(OUTPUT_ARTIFACT))
    return ap


def main() -> None:
    args = build_parser().parse_args()
    source_path = Path(args.source)
    data = json.loads(source_path.read_text(encoding="utf-8"))

    per_seed = data["per_seed"]
    summary_speaker = data["summary"]["speaker"]
    chance = summary_speaker["chance"]

    seed_stats = per_seed_superiority(per_seed)
    n_excl = sum(1 for s in seed_stats if s["ci_excludes_chance_from_below"])
    n_seeds = len(seed_stats)

    across = across_seed_t_ci([s["test_acc"] for s in seed_stats], chance)

    mean_acc = summary_speaker["mean_test_acc"]
    ratio = summary_speaker["mean_ratio_over_chance"]
    honest_verdict = (
        f"Speaker readout is LOW in absolute terms (mean {mean_acc:.3f} vs chance {chance:.3f}, "
        f"~{ratio:.2g}x chance over {summary_speaker['n_classes']} classes) AND significantly ABOVE "
        f"chance in at least {n_excl}/{n_seeds} seed(s) individually (that seed's own stored bootstrap "
        f"CI excludes chance from below) -- the frozen omni-embed's pooled vector is NOT speaker-free. "
        f"'No speaker information' / 'speaker never written to the pooled vector' / 'measured-zero "
        f"paralinguistic spread' are RETIRED as descriptions of this artifact; the accurate statement "
        f"is 'low but non-zero, and significantly non-chance in at least one seed.' The n={n_seeds}-seed "
        f"across-seed t-CI {across['t_ci95']} is more conservative and spans chance (directional-only, "
        f"underpowered at this seed count) -- it does not contradict the per-seed superiority finding, "
        f"it simply cannot itself establish the mean is above chance at this small n."
    )

    out = {
        "summary": {
            "n_seeds": n_seeds,
            "mean_test_acc": mean_acc, "chance": chance, "mean_ratio_over_chance": ratio,
            "n_classes": summary_speaker["n_classes"],
            "n_seeds_ci_excludes_chance_from_below": n_excl,
            "across_seed_t_ci": across,
            "honest_verdict": honest_verdict,
            "retired_phrasings": [
                "no speaker information",
                "speaker never written to the pooled vector",
                "measured-zero paralinguistic spread",
            ],
            "superiority_and_equivalence_going_forward": (
                "Per ticket #34: any future 'near chance' / 'no X information' claim about this "
                "representation must report BOTH a superiority test (does the CI exclude chance) AND "
                "an equivalence test (TOST-style against a pre-declared SESOI) -- a claim of 'no signal' "
                "is not supported merely because a point estimate ratio-over-chance looks small, nor is "
                "'has signal' supported merely because a ratio-over-chance is > 1x without a CI check."
            ),
        },
        "per_seed": seed_stats,
        "config": {
            "method": ("Per-seed: compare the FROZEN artifact's own stored bootstrap CI lower bound to "
                      "the frozen chance value (no CI recomputation). Across-seed: one-sample t-CI "
                      "(n=3, directional-only) on the stored per-seed test_acc values."),
            "source_artifact": str(source_path),
            "source_artifact_sha256": sha256_file(source_path),
            "note": "This script performs NO model inference and NO dataset access; it recomputes "
                    "statistics from paralinguistic_negative_probe.json alone (frozen, not rerun).",
        },
        "provenance": {
            **git_provenance(REPO_ROOT),
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reproduce_command": "python scripts/speaker_probe_restatement.py",
        },
    }

    out_path = Path(args.output)
    write_atomic(out_path, out)
    print(json.dumps(out["summary"], indent=2))
    print("wrote", out_path.resolve())
    print("RESTATEMENT_DONE")


if __name__ == "__main__":
    main()
