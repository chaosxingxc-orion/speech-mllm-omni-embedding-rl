from omni_embedding_rl.execution.cache_taxonomy_plan import CacheTaxonomyPlanConfig, run


def test_cache_taxonomy_plan_rag_has_cache_and_eval_steps(tmp_path):
    out = tmp_path / "plan.json"
    report = run(
        CacheTaxonomyPlanConfig(
            task="rag",
            manifest="manifest.jsonl",
            output=out,
            arms=("raw", "policy_grounding"),
            max_samples=12,
            results_dir="results",
        )
    )

    assert out.exists()
    assert len(report["rows"]) == 2
    steps = report["rows"][0]["steps"]
    assert [step["step"] for step in steps] == [
        "cache_text",
        "cache_omni_audio",
        "evaluate_hybrid_from_cache",
    ]
