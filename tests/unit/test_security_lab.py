import copy
from pathlib import Path

import pytest

from llm_evaluation_lab.security.lab import (
    baseline_agent,
    load_scenarios,
    run_case,
    summarize,
)

CASES = load_scenarios(Path(__file__).parents[2] / "datasets/security/authorization.json")


def test_baseline_distinguishes_vulnerable_secure_and_own_tenant_cases():
    rows = [run_case(case, baseline_agent) for case in CASES]
    summary = summarize(rows)
    assert summary["TP"] == 2
    assert summary["TN"] == 6
    assert summary["detection_recall"] == 1
    assert summary["false_positive_rate"] == 0
    assert summary["explanation_correctness"] is None
    assert summary["passed"]
    denied = [r for r in rows if r["trace"][0]["status"] in {401, 403}]
    assert len(denied) == 4
    assert all("tenant_id" not in r["trace"][0]["body"] for r in denied)


@pytest.mark.parametrize("prediction,expected_counts", [(True, (2, 6, 0)), (False, (0, 0, 2))])
def test_always_flagging_and_never_flagging_cannot_pass(prediction, expected_counts):
    def agent(task, request):
        result = baseline_agent(task, request)
        result["finding"] = prediction
        return result

    summary = summarize([run_case(case, agent) for case in CASES])
    assert (summary["TP"], summary["FP"], summary["FN"]) == expected_counts
    assert not summary["passed"]


def test_invented_evidence_and_missing_tool_call_fail():
    row = run_case(
        CASES[0],
        lambda task, request: {
            "finding": True,
            "evidence_ids": [999],
            "explanation": "It is vulnerable.",
        },
    )
    assert row["classification"] == "TP"  # A correct guess still cannot pass the gate.
    assert not row["tool_correct"]
    assert not row["evidence_valid"]
    assert not summarize([row])["passed"]


@pytest.mark.parametrize(
    "changes",
    [
        {"method": "DELETE"},
        {"path": "https://example.com"},
        {"token": "other-token"},
        {"path": "/campaigns/../secrets"},
    ],
)
def test_out_of_scope_requests_are_recorded_and_blocked(changes):
    def agent(task, request):
        args = {"method": "GET", "path": task["path"], "token": task["token"]}
        args.update(changes)
        response = request(**args)
        assert response["status"] == 400
        return {"finding": False, "evidence_ids": [1], "explanation": "Denied."}

    row = run_case(CASES[0], agent)
    assert not row["tool_correct"]
    assert not row["evidence_valid"]


def test_agent_cannot_mutate_recorded_evidence_or_future_api_responses():
    def agent(task, request):
        evidence = request(method="GET", path=task["path"], token=task["token"])
        evidence["body"]["tenant_id"] = "tenant-a"
        return {"finding": False, "evidence_ids": [1], "explanation": "Same owner."}

    row = run_case(CASES[0], agent)
    assert row["trace"][0]["body"]["tenant_id"] == "tenant-b"
    assert run_case(CASES[0], baseline_agent)["classification"] == "TP"


def test_extra_calls_fail_the_exact_tool_contract():
    def agent(task, request):
        baseline_agent(task, request)
        return baseline_agent(task, request)

    assert not run_case(CASES[0], agent)["tool_correct"]


@pytest.mark.parametrize(
    "output",
    [
        None,
        {},
        {"finding": "false"},
        {"finding": False, "evidence_ids": [True], "explanation": "test"},
    ],
)
def test_malformed_outputs_fail_even_on_a_safe_case(output):
    row = run_case(CASES[-1], lambda task, request: output)
    assert not row["output_valid"]
    assert not summarize([row])["passed"]


def test_exception_does_not_become_a_true_negative():
    def agent(task, request):
        raise RuntimeError("do not leak sensitive exception text")

    row = run_case(CASES[-1], agent)
    assert row["classification"] == "INVALID"
    assert row["agent_error"] == "RuntimeError"


def test_empty_metrics_are_undefined_and_cannot_pass():
    summary = summarize([])
    assert summary["finding_precision"] is None
    assert summary["false_positive_rate"] is None
    assert not summary["passed"]


def test_adapter_receives_no_oracle_labels():
    def agent(task, request):
        assert "vulnerable" not in task
        assert "expected_finding" not in task
        assert "expected_explanation" not in task
        return baseline_agent(task, request)

    before = copy.deepcopy(CASES[0])
    run_case(CASES[0], agent)
    assert CASES[0] == before
