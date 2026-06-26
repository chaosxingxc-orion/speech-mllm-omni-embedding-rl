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


def test_cache_taxonomy_plan_translation_has_constructed_instruction(tmp_path):
    out = tmp_path / "translation_plan.json"
    report = run(
        CacheTaxonomyPlanConfig(
            task="translation",
            manifest="manifest.jsonl",
            output=out,
            arms=("constructed_translation",),
            max_samples=12,
            results_dir="results",
        )
    )

    assert out.exists()
    assert report["rows"][0]["arm"] == "constructed_translation"
    assert report["rows"][0]["steps"][0]["step"] == "evaluate_translation_omni_selection"
    assert report["rows"][0]["steps"][0]["candidate_field"] == "target_text"
