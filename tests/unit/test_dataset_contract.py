from pathlib import Path

import pytest

from llm_evaluation_lab import load_cases

DATASETS = Path(__file__).parents[2] / "datasets"


@pytest.mark.parametrize("filename", ["chatbot.json", "rag.json", "agent.json"])
def test_dataset_has_unique_ids_and_required_fields(filename: str) -> None:
    cases = load_cases(DATASETS / filename)

    assert cases
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(case.input.strip() for case in cases)
    assert all(case.actual_output.strip() for case in cases)
