from pathlib import Path

from omni_embedding_rl.evaluation.tool_intent import (
    ToolIntentRetrievalConfig,
    _label_descriptions,
    _task_label,
)


def test_task_label_reads_intent():
    assert _task_label({"intent": "alarm_set"}, "intent") == "alarm_set"


def test_label_descriptions_use_examples_and_boundaries():
    rows = [
        {"intent": "alarm_set", "domain": "alarm", "text": "set an alarm"},
        {"intent": "alarm_query", "domain": "alarm", "text": "show my alarms"},
        {"intent": "music_play", "domain": "music", "text": "play jazz"},
    ]
    config = ToolIntentRetrievalConfig(
        manifest=Path("manifest.jsonl"),
        output=Path("out.json"),
        model="dummy",
        label_description_style="contrastive_boundary_tool",
    )

    descriptions = _label_descriptions(rows, ["alarm_query", "alarm_set", "music_play"], config)

    assert "Positive example: set an alarm" in descriptions["alarm_set"]
    assert "alarm_query" in descriptions["alarm_set"]
    assert "music_play" not in descriptions["alarm_set"]
