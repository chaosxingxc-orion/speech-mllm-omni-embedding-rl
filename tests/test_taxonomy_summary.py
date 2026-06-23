import json

from omni_embedding_rl.evaluation.taxonomy import TaxonomySummaryConfig, run


def test_taxonomy_summary_ranks_rag_results(tmp_path):
    raw = {
        "metrics": {
            "test": {
                "n": 2,
                "omni": {
                    "text_accuracy": 0.5,
                    "text_recall_at_3": 1.0,
                    "text_recall_at_5": 1.0,
                    "text_mrr": 0.75,
                    "text_mean_rank": 1.5,
                },
            }
        }
    }
    grounded = {
        "metrics": {
            "test": {
                "n": 2,
                "omni": {
                    "text_accuracy": 1.0,
                    "text_recall_at_3": 1.0,
                    "text_recall_at_5": 1.0,
                    "text_mrr": 1.0,
                    "text_mean_rank": 1.0,
                },
            }
        }
    }
    raw_path = tmp_path / "raw.json"
    grounded_path = tmp_path / "grounded.json"
    out_path = tmp_path / "summary.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    grounded_path.write_text(json.dumps(grounded), encoding="utf-8")

    report = run(
        TaxonomySummaryConfig(
            task="rag",
            output=out_path,
            results=(f"raw={raw_path}", f"policy_grounding={grounded_path}"),
            arms=("raw", "policy_grounding"),
        )
    )

    assert out_path.exists()
    assert out_path.with_suffix(".leaderboard.csv").exists()
    assert report["leaderboard"][0]["arm"] == "policy_grounding"
