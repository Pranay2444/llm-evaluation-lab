from __future__ import annotations

from collections import Counter

from .models import ToolCall


def check_required_terms(output: str, required_terms: tuple[str, ...]) -> list[str]:
    """Return required terms that are absent from an output, case-insensitively."""
    normalized = output.casefold()
    return [term for term in required_terms if term.casefold() not in normalized]


def validate_tool_trace(
    calls: tuple[ToolCall, ...],
    allowed_tools: tuple[str, ...],
    *,
    forbid_duplicates: bool = True,
) -> list[str]:
    """Check allow-list and duplicate-call invariants without using an LLM judge."""
    violations: list[str] = []
    allow_list = set(allowed_tools)

    for call in calls:
        if call.name not in allow_list:
            violations.append(f"tool-not-allowed:{call.name}")

    if forbid_duplicates:
        counts = Counter((call.name, repr(sorted(call.arguments.items()))) for call in calls)
        for (name, _), count in counts.items():
            if count > 1:
                violations.append(f"duplicate-tool-call:{name}")

    return violations
