import json

from omni_embedding_rl.data.manifest import ManifestSummaryConfig, summarize_manifest


def test_manifest_summary_counts_fields(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"sample_id": "a", "text": "hello world", "domain": "bank", "intent": "pay"}),
                json.dumps({"sample_id": "b", "text": "refund", "domain": "travel", "intent": "refund"}),
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "summary.json"

    summary = summarize_manifest(
        ManifestSummaryConfig(manifest=manifest, output=output, check_audio_exists=False)
    )

    assert output.exists()
    assert summary["count"] == 2
    assert ("bank", 1) in [tuple(item) for item in summary["domains"]]
    assert summary["field_presence"]["intent"] == 2
