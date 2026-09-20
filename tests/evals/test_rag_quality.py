import os
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from llm_evaluation_lab import load_cases


pytestmark = pytest.mark.live_eval
DATASET = Path(__file__).parents[2] / "datasets" / "rag.json"


@pytest.mark.parametrize("case", load_cases(DATASET), ids=lambda case: case.case_id)
def test_rag_quality(case) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live LLM-judge evaluations")

    test_case = LLMTestCase(
        input=case.input,
        actual_output=case.actual_output,
        expected_output=case.expected_output,
        retrieval_context=list(case.retrieval_context),
    )
    assert_test(
        test_case,
        metrics=[
            AnswerRelevancyMetric(threshold=0.7),
            FaithfulnessMetric(threshold=0.8),
            ContextualPrecisionMetric(threshold=0.7),
            ContextualRecallMetric(threshold=0.7),
        ],
    )
