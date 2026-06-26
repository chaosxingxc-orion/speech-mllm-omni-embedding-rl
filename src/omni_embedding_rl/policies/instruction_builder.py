"""Structured construction for task-conditioned audio instructions.

The builder turns an explicit task card into an audio-side instruction.  It is
deliberately small and deterministic: the generated instruction is a policy arm
that must still be selected by validation reward and accept gates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import re


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "empty"


@dataclass(frozen=True)
class TaskInstructionSpec:
    """A task card for constructing one audio-side instruction."""

    task_id: str
    task_role: str
    target_object: str
    equivalence: str
    boundary_condition: str = ""
    negative_warning: str = ""
    preserve: tuple[str, ...] = ()

    def validate(self) -> None:
        required = {
            "task_id": self.task_id,
            "task_role": self.task_role,
            "target_object": self.target_object,
            "equivalence": self.equivalence,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(f"TaskInstructionSpec missing required fields: {missing}")

    def to_jsonable(self) -> dict[str, Any]:
        data = asdict(self)
        data["preserve"] = list(self.preserve)
        return data


BUILTIN_TASK_SPECS: dict[str, TaskInstructionSpec] = {
    "constructed_asr_transcript": TaskInstructionSpec(
        task_id="constructed_asr_transcript",
        task_role="transcript-level ASR semantic matching",
        target_object="the literal transcript candidate",
        equivalence="same spoken content, not merely same topic",
        boundary_condition="word order, named entities, numbers, negation, and short function words",
        negative_warning="do not collapse to a generic semantic topic when transcript details matter",
        preserve=("names", "numbers", "negation", "literal wording"),
    ),
    "constructed_rag_grounding": TaskInstructionSpec(
        task_id="constructed_rag_grounding",
        task_role="spoken question evidence retrieval",
        target_object="the passage or rule that directly supports the answer",
        equivalence="grounded answer support rather than surface lexical overlap",
        boundary_condition="entities, constraints, dates, quantities, exceptions, and answer-bearing facts",
        negative_warning="do not prefer a neighboring passage that is on topic but cannot answer the question",
        preserve=("entities", "constraints", "answer-bearing facts", "exceptions"),
    ),
    "constructed_tool_intent": TaskInstructionSpec(
        task_id="constructed_tool_intent",
        task_role="spoken command tool selection",
        target_object="the most specific executable tool or intent schema",
        equivalence="same user action and operational intent",
        boundary_condition="tool boundaries, required action, domain, object, and unsafe confusions",
        negative_warning="do not choose a generic nearby action when a more specific tool is implied",
        preserve=("action", "domain", "object", "tool boundary"),
    ),
    "constructed_translation": TaskInstructionSpec(
        task_id="constructed_translation",
        task_role="cross-lingual speech translation matching",
        target_object="the equivalent target-language translation candidate",
        equivalence="same cross-lingual meaning",
        boundary_condition="named entities, numbers, negation, tense, and predicate-argument structure",
        negative_warning="do not match only by topic when the target sentence changes who did what",
        preserve=("named entities", "numbers", "negation", "predicate-argument meaning"),
    ),
}


def build_instruction(spec: TaskInstructionSpec) -> str:
    """Build a deterministic audio-side instruction from a task card."""

    spec.validate()
    parts = [
        f"Represent the spoken audio for {spec.task_role}.",
        f"Match it to {spec.target_object}.",
        f"Treat candidates as equivalent only when they express {spec.equivalence}.",
    ]
    if spec.boundary_condition:
        parts.append(f"Pay special attention to {spec.boundary_condition}.")
    if spec.preserve:
        parts.append("Preserve " + ", ".join(spec.preserve) + ".")
    if spec.negative_warning:
        parts.append(spec.negative_warning[0].upper() + spec.negative_warning[1:] + ".")
    return " ".join(parts)


def built_instruction_arms() -> dict[str, str]:
    """Return built-in constructed arms keyed by stable task ids."""

    return {_slugify(name): build_instruction(spec) for name, spec in BUILTIN_TASK_SPECS.items()}


def spec_report(specs: dict[str, TaskInstructionSpec] | None = None) -> dict[str, Any]:
    """Return a JSON-ready report for docs, tests, or CLI inspection."""

    specs = specs or BUILTIN_TASK_SPECS
    rows = []
    for name, spec in specs.items():
        arm = _slugify(name)
        rows.append(
            {
                "arm": arm,
                "spec": spec.to_jsonable(),
                "instruction": build_instruction(spec),
            }
        )
    return {"instruction_builder": "task_card_v1", "rows": rows}
