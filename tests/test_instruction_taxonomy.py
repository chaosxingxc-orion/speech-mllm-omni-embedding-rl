from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS, arm_items, slugify


def test_slugify_is_stable_ascii():
    assert slugify("Policy Grounding!") == "policy_grounding"
    assert slugify("  ") == "empty"


def test_task_arm_items_include_raw():
    rag = dict(arm_items("rag"))
    assert "raw" in rag
    assert "policy_grounding" in rag
    assert set(rag).issubset(INSTRUCTION_ARMS)
