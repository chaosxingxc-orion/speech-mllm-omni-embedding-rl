from omni_embedding_rl.tasks.tool_schema import rank_metrics, tool_label_description


def test_tool_schema_card_contains_boundaries():
    text = tool_label_description(
        "refund_status",
        "intent",
        "contrastive_boundary_tool",
        label_domain="travel",
        examples=["Check my ticket refund."],
        boundary_labels=["refund_policy", "book_ticket"],
    )

    assert "Tool name: refund_status" in text
    assert "Boundary note" in text
    assert "refund_policy" in text


def test_rank_metrics():
    metrics = rank_metrics([1, 2, 6])
    assert metrics["accuracy_at_1"] == 1 / 3
    assert metrics["accuracy_at_3"] == 2 / 3
    assert metrics["mean_rank"] == 3
