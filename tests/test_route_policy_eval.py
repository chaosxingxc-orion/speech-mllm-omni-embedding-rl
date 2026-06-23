import json

from omni_embedding_rl.evaluation.routing import RouteEvalConfig, run


def test_route_policy_eval_writes_leaderboard(tmp_path):
    hybrid = {
        "metrics": {
            "test": {
                "asr": {"acc_at_1": 0.5},
                "omni": {"acc_at_1": 0.5},
                "rrf": {"acc_at_1": 1.0},
                "best_of_two_oracle": {"acc_at_1": 1.0},
                "routing": {"disagreement_rate": 1.0},
                "rows": [
                    {
                        "sample_id": "a",
                        "asr_rank": 1,
                        "omni_rank": 2,
                        "rrf_rank": 1,
                        "best_of_two_rank": 1,
                        "disagreement": True,
                        "confidence": 0.9,
                        "query_style": "clean",
                    },
                    {
                        "sample_id": "b",
                        "asr_rank": 4,
                        "omni_rank": 1,
                        "rrf_rank": 1,
                        "best_of_two_rank": 1,
                        "disagreement": True,
                        "confidence": 0.4,
                        "query_style": "wu",
                    },
                ],
            }
        }
    }
    input_path = tmp_path / "hybrid.json"
    output_path = tmp_path / "route_eval.json"
    input_path.write_text(json.dumps(hybrid), encoding="utf-8")

    report = run(
        RouteEvalConfig(
            hybrid_result=input_path,
            output=output_path,
            policies=("asr_primary", "omni_primary", "rrf", "dialect_aware_branch"),
            bootstrap_rounds=100,
        )
    )

    assert output_path.exists()
    assert output_path.with_suffix(".leaderboard.csv").exists()
    assert report["n"] == 2
    rrf = next(row for row in report["leaderboard"] if row["policy"] == "rrf")
    assert rrf["acc_at_1"] == 1.0
    dialect = next(row for row in report["leaderboard"] if row["policy"] == "dialect_aware_branch")
    assert dialect["rescue_count"] == 1
