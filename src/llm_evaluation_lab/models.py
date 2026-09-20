from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    input: str
    actual_output: str
    expected_output: str | None = None
    retrieval_context: tuple[str, ...] = ()
    required_terms: tuple[str, ...] = ()
    tools_called: tuple[ToolCall, ...] = ()
    allowed_tools: tuple[str, ...] = ()


def load_cases(path: str | Path) -> list[EvaluationCase]:
    """Load a JSON array of version-controlled evaluation cases."""
    source = Path(path)
    rows = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"Expected a JSON array in {source}")

    cases: list[EvaluationCase] = []
    for row in rows:
        cases.append(
            EvaluationCase(
                case_id=row["case_id"],
                input=row["input"],
                actual_output=row["actual_output"],
                expected_output=row.get("expected_output"),
                retrieval_context=tuple(row.get("retrieval_context", [])),
                required_terms=tuple(row.get("required_terms", [])),
                tools_called=tuple(
                    ToolCall(name=call["name"], arguments=call.get("arguments", {}))
                    for call in row.get("tools_called", [])
                ),
                allowed_tools=tuple(row.get("allowed_tools", [])),
            )
        )
    return cases
