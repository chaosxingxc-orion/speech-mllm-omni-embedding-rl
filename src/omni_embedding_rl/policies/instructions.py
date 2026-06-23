"""Structured instruction taxonomy for speech omni-embedding tasks."""

from __future__ import annotations

import re


INSTRUCTION_ARMS: dict[str, str] = {
    "raw": "",
    "exact_condition_matching": (
        "Represent the spoken audio for exact condition matching. Preserve numbers, "
        "negation, exceptions, and constraints."
    ),
    "policy_grounding": (
        "Represent the spoken question for retrieving the business rule that directly "
        "grounds the answer."
    ),
    "semantic_qa": (
        "Represent the spoken audio as a semantic question or utterance. Focus on the "
        "meaning needed to match an answer, passage, transcript, or knowledge item."
    ),
    "negation_exception_sensitive": (
        "Represent the spoken audio with special attention to negation, exclusion, "
        "exceptions, and boundary conditions."
    ),
    "tool_specific_intent": (
        "Represent the spoken command for selecting the most specific tool or intent, "
        "not a generic nearby action."
    ),
    "transcript_like": (
        "Represent the spoken audio by what the speaker literally says, preserving "
        "transcript-level content."
    ),
    "emotion_or_paralinguistic": (
        "Represent the spoken audio for emotion, tone, speaker intent, and "
        "paralinguistic cues."
    ),
    "dialect_robust_semantic": (
        "Represent the user's underlying semantic intent even when accent, dialect, "
        "or ASR-like surface forms are noisy."
    ),
}


TASK_DEFAULT_ARMS: dict[str, tuple[str, ...]] = {
    "rag": (
        "raw",
        "exact_condition_matching",
        "policy_grounding",
        "negation_exception_sensitive",
        "dialect_robust_semantic",
    ),
    "tool": (
        "raw",
        "tool_specific_intent",
        "exact_condition_matching",
        "negation_exception_sensitive",
        "dialect_robust_semantic",
    ),
    "asr_like": (
        "raw",
        "transcript_like",
        "semantic_qa",
        "dialect_robust_semantic",
        "exact_condition_matching",
    ),
    "dialect": (
        "raw",
        "dialect_robust_semantic",
        "policy_grounding",
        "transcript_like",
    ),
}


def slugify(value: str) -> str:
    """Return a stable ASCII slug for filenames and policy ids."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "empty"


def arm_items(task: str, requested: list[str] | tuple[str, ...] | None = None) -> list[tuple[str, str]]:
    arms = tuple(requested) if requested else TASK_DEFAULT_ARMS.get(task, tuple(INSTRUCTION_ARMS))
    missing = [arm for arm in arms if arm not in INSTRUCTION_ARMS]
    if missing:
        raise ValueError(f"Unknown instruction arms: {missing}. Known: {sorted(INSTRUCTION_ARMS)}")
    return [(arm, INSTRUCTION_ARMS[arm]) for arm in arms]
