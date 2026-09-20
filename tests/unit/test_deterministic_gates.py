from pathlib import Path

from llm_evaluation_lab import check_required_terms, load_cases, validate_tool_trace


DATASETS = Path(__file__).parents[2] / "datasets"


def test_sample_outputs_contain_required_terms() -> None:
    for filename in ("chatbot.json", "rag.json", "agent.json"):
        for case in load_cases(DATASETS / filename):
            assert check_required_terms(case.actual_output, case.required_terms) == [], case.case_id


def test_agent_traces_respect_tool_allow_lists() -> None:
    for case in load_cases(DATASETS / "agent.json"):
        assert validate_tool_trace(case.tools_called, case.allowed_tools) == [], case.case_id
