"""Structured instruction taxonomy for speech omni-embedding tasks."""

from __future__ import annotations

import re

from omni_embedding_rl.policies.instruction_builder import built_instruction_arms


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
    "translation_semantic": (
        "Represent the spoken audio by its cross-lingual meaning for matching an "
        "equivalent translation in another language. Preserve named entities, "
        "numbers, negation, and core predicate-argument meaning."
    ),
    "v2_asr_literal_boundary": (
        "Represent the spoken audio for transcript-candidate retrieval. Match the "
        "candidate that preserves the literal utterance, including function words, "
        "numbers, names, negation, and word-level distinctions. Do not choose a "
        "candidate that is merely on the same topic."
    ),
    "v2_qa_answer_boundary": (
        "Represent the spoken question for answer-bearing evidence retrieval. Match "
        "the passage or rule that entails the answer to the question. Preserve the "
        "question focus, entities, quantities, constraints, exceptions, and answer "
        "type. Reject same-topic passages that cannot directly answer the question."
    ),
    "v2_tool_action_boundary": (
        "Represent the spoken command for executable tool selection. Match the tool "
        "whose domain, requested action, object, and user goal are all correct. "
        "Reject nearby tools that share words or domain but would execute a "
        "different action."
    ),
    "v2_translation_argument_boundary": (
        "Represent the spoken source sentence for translation matching. Match the "
        "target-language sentence with the same proposition: who did what to whom, "
        "with the same entities, numbers, polarity, tense, and constraints. Reject "
        "translations that only share broad topic or scene."
    ),
}

INSTRUCTION_ARMS.update(built_instruction_arms())


TASK_DEFAULT_ARMS: dict[str, tuple[str, ...]] = {
    "rag": (
        "raw",
        "exact_condition_matching",
        "policy_grounding",
        "v2_qa_answer_boundary",
        "constructed_rag_grounding",
        "negation_exception_sensitive",
        "dialect_robust_semantic",
    ),
    "tool": (
        "raw",
        "tool_specific_intent",
        "v2_tool_action_boundary",
        "constructed_tool_intent",
        "exact_condition_matching",
        "negation_exception_sensitive",
        "dialect_robust_semantic",
    ),
    "asr_like": (
        "raw",
        "transcript_like",
        "v2_asr_literal_boundary",
        "constructed_asr_transcript",
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
    "translation": (
        "raw",
        "translation_semantic",
        "v2_translation_argument_boundary",
        "constructed_translation",
        "semantic_qa",
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
