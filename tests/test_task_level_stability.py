import json

from omni_embedding_rl.policies.task_level_stability import (
    TaskLevelStabilityConfig,
    run,
)


def write_selector_result(path, name, locked_delta, locked_lcb, locked_passed):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "task_level_omni_policy_selector",
        "task_card": {"task_name": "synthetic", "task_family": "qa"},
        "selected_by_selection": {
            "name": name,
            "hit_delta": 0.1,
        },
        "selected_locked_test": {
            "name": name,
            "hit_delta": locked_delta,
            "hit_lcb": locked_lcb,
            "regression_rate": 0.0,
            "accepted": locked_passed,
        },
        "locked_test_gate_passed": locked_passed,
        "decision": "accepted" if locked_passed else "selected_not_validated",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_stability_accepts_frequent_validated_action(tmp_path):
    paths = []
    for index in range(3):
        path = tmp_path / f"run_good_{index}.json"
        write_selector_result(path, "good", 0.1, 0.02, True)
        paths.append(path)
    other = tmp_path / "run_other.json"
    write_selector_result(other, "other", 0.05, -0.01, False)
    paths.append(other)

    report = run(
        TaskLevelStabilityConfig(
            selector_results=tuple(paths),
            output=tmp_path / "stability.json",
            min_selection_rate=0.6,
            min_locked_pass_rate=0.6,
        )
    )

    assert report["decision"] == "accepted"
    assert report["selected"]["name"] == "good"


def test_stability_rejects_unstable_action(tmp_path):
    paths = []
    for index in range(2):
        path = tmp_path / f"run_good_{index}.json"
        write_selector_result(path, "good", 0.1, 0.02, True)
        paths.append(path)
    for index in range(2):
        path = tmp_path / f"run_other_{index}.json"
        write_selector_result(path, "other", 0.05, 0.01, True)
        paths.append(path)

    report = run(
        TaskLevelStabilityConfig(
            selector_results=tuple(paths),
            output=tmp_path / "stability.json",
            min_selection_rate=0.6,
            min_locked_pass_rate=0.6,
        )
    )

    assert report["decision"] == "no_stable_policy"
