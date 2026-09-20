import os
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from llm_evaluation_lab import load_cases


pytestmark = pytest.mark.live_eval
DATASET = Path(__file__).parents[2] / "datasets" / "chatbot.json"


@pytest.mark.parametrize("case", load_cases(DATASET), ids=lambda case: case.case_id)
def test_chatbot_answer_quality(case) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live LLM-judge evaluations")

    test_case = LLMTestCase(
        input=case.input,
        actual_output=case.actual_output,
        expected_output=case.expected_output,
    )
    correctness = GEval(
        name="Correctness",
        criteria=(
            "Determine whether the actual output preserves the meaning "
            "of the expected output."
        ),
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        threshold=0.7,
    )
    assert_test(
        test_case,
        metrics=[AnswerRelevancyMetric(threshold=0.7), correctness],
    )
