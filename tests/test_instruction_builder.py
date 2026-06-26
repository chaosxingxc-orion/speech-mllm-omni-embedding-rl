from omni_embedding_rl.policies.instruction_builder import (
    BUILTIN_TASK_SPECS,
    build_instruction,
    built_instruction_arms,
    spec_report,
)


def test_builtin_builder_covers_semantic_task_families():
    arms = built_instruction_arms()

    assert set(arms) == {
        "constructed_asr_transcript",
        "constructed_rag_grounding",
        "constructed_tool_intent",
        "constructed_translation",
    }
    assert "literal transcript candidate" in arms["constructed_asr_transcript"]
    assert "directly supports the answer" in arms["constructed_rag_grounding"]
    assert "most specific executable tool" in arms["constructed_tool_intent"]
    assert "target-language translation" in arms["constructed_translation"]


def test_builder_keeps_task_equivalence_distinct():
    asr = build_instruction(BUILTIN_TASK_SPECS["constructed_asr_transcript"])
    rag = build_instruction(BUILTIN_TASK_SPECS["constructed_rag_grounding"])

    assert "same spoken content" in asr
    assert "grounded answer support" in rag
    assert asr != rag


def test_spec_report_is_json_ready():
    report = spec_report()

    assert report["instruction_builder"] == "task_card_v1"
    assert len(report["rows"]) == 4
    assert all(row["arm"].startswith("constructed_") for row in report["rows"])
    assert all("instruction" in row for row in report["rows"])
