import json

from omni_embedding_rl.tasks.rag_answer import RAGAnswerEvalConfig, run


def test_rag_answer_eval_local_rules(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "q1",
                        "document_id": "d1",
                        "text": "Can online consultation be reimbursed?",
                        "document_text": "Online hospital consultation can be reimbursed with prescription and payment record.",
                        "domain": "medical",
                        "intent": "reimbursement",
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "q2",
                        "document_id": "d2",
                        "text": "Can travel refund be changed?",
                        "document_text": "Travel refunds follow the departure-time rule.",
                        "domain": "travel",
                        "intent": "refund",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    keys = tmp_path / "keys.json"
    keys.write_text(
        json.dumps(
            {
                "keys": {
                    "q1": {
                        "gold_answer": "Online hospital consultation can be reimbursed with prescription and payment record.",
                        "key_decision": "online consultation reimbursed",
                        "required_terms": [["reimbursed"], ["prescription"], ["payment record"]],
                        "forbidden_terms": ["cannot be reimbursed"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    retrieval = tmp_path / "retrieval.json"
    retrieval.write_text(
        json.dumps(
            {
                "metrics": {
                    "test": {
                        "rows": [
                            {
                                "sample_id": "q1",
                                "target": "Can online consultation be reimbursed?",
                                "asr_text": "online consultation reimbursement",
                                "asr_top_k": [
                                    {
                                        "sample_id": "q1",
                                        "document_id": "d1",
                                        "document": "Online hospital consultation can be reimbursed with prescription and payment record.",
                                    }
                                ],
                                "omni_top_k": [
                                    {
                                        "sample_id": "q2",
                                        "document_id": "d2",
                                        "document": "Travel refunds follow the departure-time rule.",
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    report = run(
        RAGAnswerEvalConfig(
            retrieval_result=retrieval,
            manifest=manifest,
            answer_keys=keys,
            output=out,
            generator_mode="first_document",
            judge_mode="local_rule",
        )
    )

    assert out.exists()
    assert report["metrics"]["answer_pass"] == 1.0
    assert report["rows"][0]["error_type"] == "none"
