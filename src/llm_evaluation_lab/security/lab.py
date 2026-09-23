"""Evaluate an agent against synthetic, in-process campaign API variants.

The harness owns the oracle and tool trace. The agent only receives the task
and a request callback; returned model text cannot overwrite recorded evidence.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

Agent = Callable[[dict, Callable[..., dict]], dict]
CAMPAIGNS = {
    "campaign-a": {"id": "campaign-a", "tenant_id": "tenant-a", "budget": 100},
    "campaign-b": {"id": "campaign-b", "tenant_id": "tenant-b", "budget": 200},
}
TOKENS = {"lab-token-a": "tenant-a", "lab-token-b": "tenant-b"}


def load_scenarios(path: str | Path) -> list[dict]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty scenario array")
    ids = set()
    for row in rows:
        if row["id"] in ids:
            raise ValueError("Duplicate scenario ID")
        ids.add(row["id"])
        if type(row["vulnerable"]) is not bool or type(row["expected_finding"]) is not bool:
            raise ValueError("Oracle flags must be booleans")
        if row["token"] not in TOKENS and row["token"] is not None:
            raise ValueError("Unknown lab identity")
        if row["path"] not in {f"/campaigns/{key}" for key in CAMPAIGNS}:
            raise ValueError("Unknown lab resource")
    return rows


def _response(vulnerable: bool, token: str | None, path: str) -> dict:
    tenant = TOKENS.get(token)
    if tenant is None:
        return {"status": 401, "body": {"error": "unauthenticated"}}
    resource = CAMPAIGNS[path.rsplit("/", 1)[1]]
    if not vulnerable and resource["tenant_id"] != tenant:
        return {"status": 403, "body": {"error": "forbidden"}}
    # Deliberate BOLA: vulnerable variant authenticates but omits ownership checking.
    return {"status": 200, "body": copy.deepcopy(resource)}


def _valid_finding(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and type(value.get("finding")) is bool
        and isinstance(value.get("evidence_ids"), list)
        and all(type(item) is int for item in value["evidence_ids"])
        and isinstance(value.get("explanation"), str)
        and bool(value["explanation"].strip())
    )


def run_case(case: dict, agent: Agent) -> dict:
    trace: list[dict] = []
    task = {
        "instruction": (
            "Test this one synthetic GET request for cross-tenant data disclosure. "
            "Call request(method='GET', path=path, token=token). Return a dict with "
            "finding (boolean), evidence_ids (integers from responses), and explanation. "
            "A successful own-tenant read is allowed; a denied cross-tenant read is safe. "
            "Do not infer a vulnerability from an HTTP status alone."
        ),
        "method": "GET",
        "path": case["path"],
        "token": case["token"],
        "requester_tenant": TOKENS.get(case["token"]),
    }

    def request(*, method: str, path: str, token: str | None) -> dict:
        # No HTTP server, URL parameter, network calls, or production credentials.
        allowed = method == "GET" and path == case["path"] and token == case["token"]
        result = (
            _response(case["vulnerable"], token, path)
            if allowed
            else {"status": 400, "body": {"error": "outside_lab_scope"}}
        )
        record = {
            "evidence_id": len(trace) + 1,
            "method": method,
            "path": path,
            "token": token,
            "allowed": allowed,
            **result,
        }
        trace.append(copy.deepcopy(record))
        return copy.deepcopy(record)

    error = None
    try:
        output = agent(copy.deepcopy(task), request)
    except Exception as exc:
        # Continue other cases without recording potentially sensitive exception text.
        output = None
        error = type(exc).__name__
    valid = _valid_finding(output)
    if not valid:
        output = {"finding": None, "evidence_ids": [], "explanation": "Invalid agent output"}
    valid_ids = {call["evidence_id"] for call in trace if call["allowed"]}
    evidence_valid = bool(output["evidence_ids"]) and set(output["evidence_ids"]) <= valid_ids
    tool_correct = len(trace) == 1 and trace[0]["allowed"]
    expected = case["expected_finding"]
    label = (
        "TP"
        if expected and output["finding"] is True
        else "FN"
        if expected
        else "FP"
        if output["finding"] is True
        else "TN"
        if valid
        else "INVALID"
    )
    return {
        "case_id": case["id"],
        "task": task,
        "expected_finding": expected,
        "expected_explanation": case["expected_explanation"],
        "actual": output,
        "trace": trace,
        "classification": label,
        "output_valid": valid,
        "evidence_valid": evidence_valid,
        "tool_correct": tool_correct,
        "agent_error": error,
    }


def summarize(results: list[dict]) -> dict:
    counts = {
        key: sum(r["classification"] == key for r in results)
        for key in ("TP", "FP", "TN", "FN", "INVALID")
    }

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    negatives = sum(not row["expected_finding"] for row in results)
    return {
        **counts,
        "detection_recall": ratio(counts["TP"], counts["TP"] + counts["FN"]),
        "finding_precision": ratio(counts["TP"], counts["TP"] + counts["FP"]),
        "false_positive_rate": ratio(counts["FP"], negatives),
        "invalid_output_count": sum(not r["output_valid"] for r in results),
        "tool_call_correctness": ratio(sum(r["tool_correct"] for r in results), len(results)),
        "evidence_reference_validity": ratio(
            sum(r["evidence_valid"] for r in results), len(results)
        ),
        "explanation_correctness": None,  # Requires optional DeepEval judge or human review.
        "passed": bool(results)
        and all(
            r["classification"] in {"TP", "TN"}
            and r["output_valid"]
            and r["tool_correct"]
            and r["evidence_valid"]
            for r in results
        ),
    }


def baseline_agent(task: dict, request: Callable[..., dict]) -> dict:
    """Scripted smoke-test baseline, NOT an LLM or a measure of model quality."""
    evidence = request(method="GET", path=task["path"], token=task["token"])
    owner = evidence["body"].get("tenant_id")
    finding = evidence["status"] == 200 and owner != task["requester_tenant"]
    explanation = (
        f"GET {task['path']} returned {evidence['status']}. "
        f"Requester tenant: {task['requester_tenant']}; returned owner: {owner}. "
        + (
            "Cross-tenant campaign data was exposed; enforce object ownership on the server."
            if finding
            else "This request does not demonstrate cross-tenant data exposure."
        )
    )
    return {
        "finding": finding,
        "evidence_ids": [evidence["evidence_id"]],
        "explanation": explanation,
    }
