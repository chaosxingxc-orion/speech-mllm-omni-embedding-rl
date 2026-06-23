"""Task-conditioning variants for Operator A (the disentanglement hook).

Each variant is the ``text`` paired with the audio in the omni-embed document item. The model
auto-prepends its "passage: " document prompt, so ``None`` is the vanilla baseline (audio only).
Instruction strings reuse the shared ``speechrl_common.models.prompts`` vocabulary.
"""
from __future__ import annotations

from speechrl_common.models.prompts import instruction_for

# conditioning name -> task_prompt passed to embed_batch (None = vanilla baseline)
CONDITIONINGS: dict[str, str | None] = {
    "baseline": None,
    "content": instruction_for("asr"),   # "Transcribe the spoken audio into text, verbatim."
    "emotion": instruction_for("ser"),   # "Identify the speaker's emotion from the audio."
    "speaker": instruction_for("sid"),   # "Identify who is speaking in the audio."
}

# which CREMA-D factor each non-baseline conditioning is meant to elicit
CONDITIONING_FACTOR: dict[str, str] = {
    "content": "content",
    "emotion": "emotion",
    "speaker": "speaker",
}

# content = sentence-ID (12 fixed sentences); emotion = 6 classes; speaker = 91 ids.
FACTORS = ["content", "emotion", "speaker"]
