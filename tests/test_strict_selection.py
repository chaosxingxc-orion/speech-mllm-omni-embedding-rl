import json

from omni_embedding_rl.policies.strict_selection import StrictSelectionConfig, run


def _rag_result(ranks):
    return {
        "experiment": "audio_memory_hybrid_retrieval",
        "metrics": {
            "test": {
                "rows": [
                    {"sample_id": f"s{i}", "omni_rank": rank}
                    for i, rank in enumerate(ranks)
                ]
            }
        },
    }


def test_strict_selection_keeps_locked_test_separate(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    out = tmp_path / "strict.json"
    first.write_text(json.dumps(_rag_result([1, 1, 4, 4, 4, 4, 4, 4, 4, 4])), encoding="utf-8")
    second.write_text(json.dumps(_rag_result([4, 4, 1, 1, 1, 1, 1, 1, 1, 1])), encoding="utf-8")

    report = run(
        StrictSelectionConfig(
            task="rag",
            candidates=(f"first:{first}", f"second:{second}"),
            output=out,
            proposal_ratio=0.2,
            selection_ratio=0.3,
            bootstrap_rounds=100,
        )
    )

    assert out.exists()
    assert report["split_counts"] == {"proposal": 2, "selection": 3, "locked_test": 5}
    assert report["selected_by_selection"]["name"] in {"first", "second"}
    assert "locked_test_delta_ci_vs_first_candidate" in report
