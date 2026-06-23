import json

from omni_embedding_rl.policies.accept_gate import AcceptGateConfig, run


def test_tool_accept_gate_rejects_regression(tmp_path):
    baseline = {
        "metrics": {
            "omni_audio": {
                "n": 2,
                "metrics": {
                    "accuracy_at_1": 1.0,
                    "accuracy_at_3": 1.0,
                    "accuracy_at_5": 1.0,
                    "mrr": 1.0,
                    "mean_rank": 1.0,
                },
                "rows": [
                    {"sample_id": "a", "prediction": "bank_transfer", "target": "bank_transfer"},
                    {"sample_id": "b", "prediction": "travel_refund", "target": "travel_refund"},
                ],
            }
        }
    }
    candidate = {
        "metrics": {
            "omni_audio": {
                "n": 2,
                "metrics": {
                    "accuracy_at_1": 0.5,
                    "accuracy_at_3": 1.0,
                    "accuracy_at_5": 1.0,
                    "mrr": 0.75,
                    "mean_rank": 1.5,
                },
                "rows": [
                    {"sample_id": "a", "prediction": "bank_transfer", "target": "bank_transfer"},
                    {"sample_id": "b", "prediction": "bank_cancel", "target": "travel_refund"},
                ],
            }
        }
    }
    base_path = tmp_path / "base.json"
    cand_path = tmp_path / "cand.json"
    out_path = tmp_path / "gate.json"
    base_path.write_text(json.dumps(baseline), encoding="utf-8")
    cand_path.write_text(json.dumps(candidate), encoding="utf-8")

    report = run(
        AcceptGateConfig(
            family="tool",
            baseline=base_path,
            candidates=(f"candidate={cand_path}",),
            output=out_path,
            bootstrap_rounds=100,
        )
    )

    item = report["candidates"][0]
    assert out_path.exists()
    assert not item["accepted"]
    assert "primary_metric_regression" in item["reject_reasons"]
