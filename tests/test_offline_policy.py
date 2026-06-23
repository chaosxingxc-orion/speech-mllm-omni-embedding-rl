import json

from omni_embedding_rl.training.offline_policy import OfflinePolicyConfig, run


def test_offline_policy_selects_from_validation(tmp_path):
    rows = []
    for i in range(12):
        rows.append(
            {
                "sample_id": f"s{i}",
                "asr_rank": 1 if i < 4 else 4,
                "omni_rank": 1 if i >= 4 else 4,
                "rrf_rank": 1,
                "disagreement": True,
                "confidence": 0.3,
            }
        )
    hybrid = {"metrics": {"test": {"rows": rows}}}
    inp = tmp_path / "hybrid.json"
    out = tmp_path / "policy.json"
    inp.write_text(json.dumps(hybrid), encoding="utf-8")

    report = run(
        OfflinePolicyConfig(
            hybrid_result=inp,
            output=out,
            max_rows=12,
            bootstrap_rounds=100,
        )
    )

    assert out.exists()
    assert out.with_suffix(".leaderboard.csv").exists()
    assert report["selected_policy_id"]
    assert report["split_counts"]["locked_test"] > 0
