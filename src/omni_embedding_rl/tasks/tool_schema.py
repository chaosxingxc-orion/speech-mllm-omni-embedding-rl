"""Tool/intent label schema helpers for speech agentic tasks."""

from __future__ import annotations


def label_description(label: str, task: str, label_domain: str | None = None) -> str:
    readable = label.replace("_", " ").replace("-", " ")
    if task == "domain":
        return f"Domain label: {readable}."
    if task == "intent":
        if label_domain:
            return f"Intent label: {readable}. Domain: {label_domain.replace('_', ' ')}."
        return f"Intent label: {readable}."
    raise ValueError(f"Unsupported task: {task}")


def tool_label_description(
    label: str,
    task: str,
    style: str,
    label_domain: str | None = None,
    examples: list[str] | None = None,
    boundary_labels: list[str] | None = None,
) -> str:
    examples = examples or []
    boundary_labels = boundary_labels or []
    readable = label.replace("_", " ").replace("-", " ")
    domain_text = label_domain.replace("_", " ") if label_domain else "unknown"

    if style == "basic":
        return label_description(label, task, label_domain)
    if style == "examples":
        description = label_description(label, task, label_domain)
        if examples:
            description = f"{description} {' '.join(f'Example: {text}.' for text in examples)}"
        return description
    if style == "tool_schema_card":
        return (
            "Tool schema card for spoken command routing. "
            f"Tool name: {label}. Task type: {task}. Domain: {domain_text}. "
            f"Use this tool when the user command asks for: {readable}."
        )
    if style == "example_augmented_tool":
        example_text = " ".join(f"Positive example: {text}." for text in examples)
        return (
            "Tool schema card for spoken command routing. "
            f"Tool name: {label}. Task type: {task}. Domain: {domain_text}. "
            f"Use this tool when the user command asks for: {readable}. "
            f"{example_text}"
        ).strip()
    if style == "contrastive_boundary_tool":
        example_text = " ".join(f"Positive example: {text}." for text in examples)
        boundary_text = ", ".join(boundary_labels) if boundary_labels else "none"
        return (
            "Tool schema card for spoken command routing. "
            f"Tool name: {label}. Task type: {task}. Domain: {domain_text}. "
            f"Use this tool when the user command asks for: {readable}. "
            f"{example_text} "
            f"Boundary note: do not choose this tool for nearby tools or intents: {boundary_text}."
        ).strip()
    raise ValueError(f"Unsupported label description style: {style}")


def rank_metrics(ranks: list[int], ks: tuple[int, ...] = (1, 3, 5)) -> dict[str, float]:
    n = len(ranks)
    if not n:
        return {f"accuracy_at_{k}": 0.0 for k in ks} | {"accuracy": 0.0, "mrr": 0.0, "mean_rank": 0.0}
    out = {f"accuracy_at_{k}": sum(rank <= k for rank in ranks) / n for k in ks}
    out["accuracy"] = out["accuracy_at_1"]
    out["mrr"] = sum(1.0 / rank for rank in ranks) / n
    out["mean_rank"] = sum(ranks) / n
    return out
