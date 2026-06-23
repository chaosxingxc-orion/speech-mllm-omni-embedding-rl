import json

from omni_embedding_rl.execution.cache_taxonomy_runner import (
    CacheTaxonomyRunnerConfig,
    command_for_step,
    run,
)


def test_cache_taxonomy_runner_builds_legacy_cache_command(tmp_path):
    step = {
        "step": "cache_omni_audio",
        "manifest": "manifest.jsonl",
        "output": "results/cache.pt",
        "omni_model": "experiments/models/omni",
        "audio_encode_method": "query",
        "text_encode_method": "document",
        "audio_instruction": "Represent speech for RAG.",
        "max_samples": 12,
        "test_size": 0.35,
        "seed": 42,
    }
    command = command_for_step(
        step,
        CacheTaxonomyRunnerConfig(plan=tmp_path / "plan.json", output=tmp_path / "out.json"),
    )

    assert command[:2] == ["python", "mainline/cache_audio_memory_embeddings.py"]
    assert "--cache-kind" in command
    assert "omni" in command
    assert "--audio-query-instruction" in command


def test_cache_taxonomy_runner_dry_run_reports_commands(tmp_path):
    plan = {
        "experiment": "cache_taxonomy_plan",
        "rows": [
            {
                "arm": "raw",
                "audio_instruction": "none",
                "steps": [
                    {
                        "step": "cache_text",
                        "manifest": "missing.jsonl",
                        "output": "results/text.pt",
                        "text_model": "Qwen/Qwen3-Embedding-4B",
                        "query_text_source": "asr",
                        "memory_text_style": "document_memory",
                        "max_samples": 12,
                        "test_size": 0.35,
                        "seed": 42,
                    }
                ],
            }
        ],
    }
    plan_path = tmp_path / "plan.json"
    out = tmp_path / "runner.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    report = run(
        CacheTaxonomyRunnerConfig(
            plan=plan_path,
            output=out,
            legacy_experiments_dir=tmp_path,
        )
    )

    assert out.exists()
    assert report["step_count"] == 1
    assert report["steps"][0]["status"] == "planned"
    assert report["steps"][0]["command"][1] == "mainline/cache_audio_memory_embeddings.py"
    assert report["steps"][0]["warnings"]
