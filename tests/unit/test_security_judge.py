import json
import sys

from llm_evaluation_lab.security import judge
from llm_evaluation_lab.security.lab import baseline_agent, run_case, summarize


def test_judge_scores_saved_observations_and_preserves_raw_report(tmp_path, monkeypatch):
    # Stub only model execution. Exercise real DeepEval imports and LLMTestCase construction.
    from deepeval.metrics import GEval

    case = {
        "id": "judge-fixture",
        "token": "lab-token-a",
        "path": "/campaigns/campaign-b",
        "vulnerable": True,
        "expected_finding": True,
        "expected_explanation": "Tenant A received tenant B's campaign; enforce ownership.",
    }
    rows = [run_case(case, baseline_agent)]
    raw = tmp_path / "raw.json"
    output = tmp_path / "judged.json"
    raw.write_text(json.dumps({"summary": summarize(rows), "results": rows}))
    original = raw.read_text()

    def fake_init(self, **kwargs):
        assert kwargs["threshold"] == 0.8
        self.score = None
        self.reason = None

    def fake_measure(self, test_case):
        assert "tenant-b" in test_case.input
        assert test_case.actual_output == rows[0]["actual"]["explanation"]
        self.score = 0.4
        self.reason = "Stub score: test failure propagation without calling a model"

    monkeypatch.setattr(GEval, "__init__", fake_init)
    monkeypatch.setattr(GEval, "measure", fake_measure)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key-never-sent")
    monkeypatch.setattr(
        sys,
        "argv",
        ["judge", "--report", str(raw), "--output", str(output), "--model", "test-model"],
    )
    assert judge.main() == 1
    scored = json.loads(output.read_text())
    assert scored["summary"]["explanation_correctness"] == 0.4
    assert not scored["summary"]["passed"]
    assert raw.read_text() == original
