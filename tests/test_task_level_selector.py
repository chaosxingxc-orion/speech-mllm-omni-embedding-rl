import json

from omni_embedding_rl.policies.task_level_selector import (
    TaskLevelSelectorConfig,
    affine_rank_order,
    rank_order,
    run,
)


def write_result(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "experiment": "synthetic_rank_result",
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def row(sample_id, rank, group="g", target=None, margin=None):
    item = {
        "sample_id": sample_id,
        "text_rank": rank,
        "text_hit_at_1": rank == 1,
        "dataset_config": group,
    }
    if target is not None:
        item["target"] = target
    if margin is not None:
        item["scores"] = [
            {"rank": 1, "score": 1.0},
            {"rank": 2, "score": 1.0 - margin},
        ]
    return item


def test_selector_falls_back_to_raw_when_candidates_regress(tmp_path):
    raw = tmp_path / "raw.json"
    bad = tmp_path / "bad.json"
    write_result(raw, [row("a", 1), row("b", 1), row("c", 2), row("d", 2)])
    write_result(bad, [row("a", 2), row("b", 1), row("c", 2), row("d", 2)])

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"bad={bad}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=0.5,
            bootstrap_rounds=200,
        )
    )

    assert report["decision"] == "raw_fallback"
    assert report["selected_by_selection"]["name"] == "raw"


def test_selector_accepts_positive_candidate(tmp_path):
    raw = tmp_path / "raw.json"
    good = tmp_path / "good.json"
    write_result(raw, [row("a", 2), row("b", 2), row("c", 2), row("d", 2)])
    write_result(good, [row("a", 1), row("b", 1), row("c", 1), row("d", 1)])

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"good={good}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=0.5,
            bootstrap_rounds=200,
        )
    )

    assert report["decision"] == "accepted"
    assert report["selected_by_selection"]["name"] == "good"


def test_selector_rejects_high_regression_rate(tmp_path):
    raw = tmp_path / "raw.json"
    risky = tmp_path / "risky.json"
    write_result(
        raw,
        [row("a", 2), row("b", 2), row("c", 2), row("d", 1), row("e", 1), row("f", 1)],
    )
    write_result(
        risky,
        [row("a", 1), row("b", 1), row("c", 1), row("d", 2), row("e", 2), row("f", 1)],
    )

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"risky={risky}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=1 / 2,
            bootstrap_rounds=200,
            max_regression_rate=0.03,
            min_worst_group_delta=-1.0,
        )
    )

    risky_row = next(row for row in report["leaderboards"]["selection"] if row["name"] == "risky")
    assert "regression_rate_too_high" in risky_row["reject_reasons"]
    assert report["selected_by_selection"]["name"] == "raw"


def test_selector_labels_harmful_rejected_when_raw_is_selected(tmp_path):
    raw = tmp_path / "raw.json"
    bad = tmp_path / "bad.json"
    write_result(
        raw,
        [row("a", 1), row("b", 1), row("c", 1), row("d", 1)],
    )
    write_result(
        bad,
        [row("a", 2), row("b", 2), row("c", 1), row("d", 1)],
    )

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"bad={bad}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=0.5,
            bootstrap_rounds=200,
            max_regression_rate=0.03,
        )
    )

    assert report["decision"] == "harmful_rejected"
    assert report["diagnostic_candidate_by_selection"]["candidate_status"] == "harmful_rejected"


def test_selector_labels_underpowered_positive(tmp_path):
    raw = tmp_path / "raw.json"
    small_gain = tmp_path / "small_gain.json"
    write_result(
        raw,
        [row("a", 1), row("b", 2), row("c", 1), row("d", 1)],
    )
    write_result(
        small_gain,
        [row("a", 1), row("b", 1), row("c", 1), row("d", 1)],
    )

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"small_gain={small_gain}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=0.5,
            bootstrap_rounds=200,
        )
    )

    assert report["decision"] == "underpowered_positive"
    assert (
        report["diagnostic_candidate_by_selection"]["candidate_status"]
        == "underpowered_positive"
    )


def test_selector_rejects_protected_high_margin_regression(tmp_path):
    raw = tmp_path / "raw.json"
    risky = tmp_path / "risky.json"
    write_result(
        raw,
        [
            row("a", 2, target="alarm_query", margin=0.001),
            row("b", 2, target="alarm_query", margin=0.001),
            row("c", 1, target="email_query", margin=0.05),
            row("d", 1, target="email_query", margin=0.05),
        ],
    )
    write_result(
        risky,
        [
            row("a", 1, target="alarm_query", margin=0.001),
            row("b", 1, target="alarm_query", margin=0.001),
            row("c", 2, target="email_query", margin=0.05),
            row("d", 1, target="email_query", margin=0.05),
        ],
    )

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"risky={risky}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=0.5,
            bootstrap_rounds=200,
            max_regression_rate=1.0,
            margin_protect_threshold=0.01,
            max_protected_regression_rate=0.0,
            min_worst_group_delta=-1.0,
        )
    )

    risky_row = next(row for row in report["leaderboards"]["selection"] if row["name"] == "risky")
    assert risky_row["protected_regression_count"] == 1
    assert "protected_regression_rate_too_high" in risky_row["reject_reasons"]


def test_target_prefix_group_reports_worst_group(tmp_path):
    raw = tmp_path / "raw.json"
    risky = tmp_path / "risky.json"
    write_result(
        raw,
        [
            row("a", 1, target="alarm_query"),
            row("b", 1, target="email_query"),
            row("c", 2, target="email_send"),
            row("d", 2, target="alarm_set"),
        ],
    )
    write_result(
        risky,
        [
            row("a", 1, target="alarm_query"),
            row("b", 2, target="email_query"),
            row("c", 2, target="email_send"),
            row("d", 1, target="alarm_set"),
        ],
    )

    report = run(
        TaskLevelSelectorConfig(
            candidates=(f"raw={raw}", f"risky={risky}"),
            output=tmp_path / "selector.json",
            proposal_ratio=0.0,
            selection_ratio=0.5,
            bootstrap_rounds=200,
            group_field="target_prefix",
            min_worst_group_delta=-1.0,
        )
    )

    risky_row = next(row for row in report["leaderboards"]["selection"] if row["name"] == "risky")
    assert risky_row["worst_group"] == "email"


def test_positive_affine_score_scaling_preserves_rank_order():
    scores = [0.2, -0.1, 0.8, 0.8]

    assert affine_rank_order(scores, alpha=2.5, beta=-3.0) == rank_order(scores)
