# Security evaluation: can an agent find an authorization flaw?

This module evaluates a security-testing agent against a small campaign API
simulation. The scope is OWASP API1:2023 Broken Object Level Authorization (BOLA).
It is a teaching benchmark, not a comprehensive security scanner or certification.

## The experiment

Tenant A owns `campaign-a`; tenant B owns `campaign-b`. Tokens such as
`lab-token-a` are synthetic identifiers, not real credentials. A secure API checks
both authentication and the requested object's tenant. The deliberately vulnerable
variant authenticates but skips the ownership check.

| Request | Vulnerable variant | Secure variant | Expected finding |
|---|---|---|---|
| A reads B's campaign | 200 + B's record | 403, no record | True only for vulnerable variant |
| B reads A's campaign | 200 + A's record | 403, no record | True only for vulnerable variant |
| A reads A's campaign | 200 + A's record | 200 + A's record | False |
| No token reads B's campaign | 401 | 401 | False |

This produces eight cases: two positive findings and six negative controls.
A `200` by itself is not proof of a vulnerability. The finding needs the caller's
identity, the returned object's ownership and the actual response evidence.

## Files and execution

```text
datasets/security/authorization.json          Ground-truth cases (evaluator only)
src/llm_evaluation_lab/security/lab.py         API simulation, runner and scoring
src/llm_evaluation_lab/security/__main__.py    Offline/adapter command
src/llm_evaluation_lab/security/judge.py       Optional DeepEval G-Eval scoring
tests/unit/test_security_lab.py               Regression and negative checks
```

From the repository root after `pip install -e ".[dev]"`:

```bash
python -m llm_evaluation_lab.security
pytest tests/unit/test_security_lab.py
```

You can also run the offline baseline with only Python 3.11+:

```bash
PYTHONPATH=src python -m llm_evaluation_lab.security
```

Reports go to the ignored `reports/security/` directory. Pass `--dataset PATH`
or `--output PATH` to use an alternative. Exit code 1 indicates a failed gate.

## Connect your real agent

Implement a synchronous, importable `run(task, request)` function. The callback is
the only tool the model needs. Expose it to your model as a function tool with
string `method`, string `path`, and nullable string `token` arguments.

1. Send `task` to your model without reading the labelled dataset.
2. Parse the model's requested function call and execute `request(**arguments)`.
3. Send the returned observation back to the model.
4. Parse the final model response into the dict below.
5. Return it unchanged to the evaluator. Record model/prompt versions alongside
   your experiment; repeat runs when comparing nondeterministic models.

```python
# Return contract: the values must come from the agent's actual run.
{
    "finding": True,
    "evidence_ids": [1],
    "explanation": (
        "Tenant A requested campaign-b and received status 200 with tenant-b's "
        "record. This exposes another tenant's campaign. Enforce server-side "
        "object ownership before returning the resource."
    ),
}
```

```bash
python -m llm_evaluation_lab.security \
  --agent my_agent:run --output reports/security/my-agent.json
```

The included `baseline_agent` is a working example of the callable interface,
but it uses rules instead of a language model. A provider-specific LLM agent is
not bundled; connect the adapter for the system you want to evaluate. Async agents
need a synchronous wrapper. Your adapter owns model-call limits and timeouts.

The harness records observations independently; returning fabricated `trace` data
cannot replace them. Mutating the response returned to the adapter does not alter
the saved evidence. The agent is not given variant labels or expected findings.
This is separation of test data, not a sandbox against malicious Python code.

The tool accepts only the current scenario's GET/path/identity. It blocks and logs
other calls and exposes no arbitrary URL or real HTTP listener. No local API server
or cloud deployment is needed. This first module tests analysis of a supplied probe,
not autonomous endpoint discovery, penetration testing breadth or HTTP integration.

## Four evaluation dimensions

| Dimension | Calculation / oracle | Meaning |
|---|---|---|
| Vulnerability detection | Recall = TP / (TP + FN); precision = TP / (TP + FP) | Did the agent identify known exposed records? |
| False positives | FP / number of known-safe cases | Did it accuse secure or permitted requests? |
| Explanation correctness | Optional G-Eval using task, captured trace and expected conclusion | Does the written explanation accurately justify the result? |
| Tool-call correctness | Fraction of cases with exactly one permitted GET using exact path and token | Did the agent execute the prescribed probe correctly? |

Evidence-reference validity separately checks that cited evidence IDs exist and
refer to allowed calls. It does **not** prove the prose is correct. Undefined ratios
are `null`. Invalid outputs on positive cases count as misses; invalid outputs on
negative cases are `INVALID`, not true negatives. They always fail the overall gate.
Review `invalid_output_count` alongside false-positive rate to avoid rewarding an
agent that returns nothing.

The deterministic gate requires every case's correct classification, valid output,
valid evidence reference and exact tool contract. A lucky correct guess without a
tool call still fails. Duplicate tool calls fail this deliberately narrow one-probe
contract; broaden the contract before evaluating exploratory multi-step agents.

## Judge explanation correctness with DeepEval

Run the agent first, then judge that saved report. This avoids substituting a
handwritten expected answer for the agent's actual output. Configure `.env.local`
with `OPENAI_API_KEY`, as in the main README:

```bash
python -m llm_evaluation_lab.security.judge \
  --report reports/security/my-agent.json \
  --output reports/security/my-agent-judged.json \
  --model YOUR_JUDGE_MODEL --threshold 0.8
```

The rubric checks identity/ownership reasoning, observed status and response,
unsupported claims, and a server-side ownership fix for actual flaws. It penalizes
claims that one safe response proves the entire API secure. The judge receives
the synthetic task, trace and explanation, so use synthetic data in this benchmark.
The judge treats evidence as data rather than instructions, but judge reliability
still needs human calibration.

Each case gets a score and reason. The report stores the judge model and threshold,
the average explanation score and an all-cases explanation gate. The overall gate
passes only if deterministic checks pass and every explanation reaches the threshold.
The raw report is preserved separately. The default threshold is an initial lab
choice; calibrate it on human-reviewed correct, misleading and unsupported answers.
Provider/model errors stop the judge command rather than generating invented scores.

Normal CI never calls a model. `explanation_correctness: null` means **not evaluated**.
A perfect baseline result measures harness plumbing, not an LLM's capabilities.
G-Eval is probabilistic and cannot certify absence of security vulnerabilities.

## Practice and extension

1. Make the baseline flag every `200`; observe false positives on own-tenant reads.
2. Return a correct finding but evidence ID `999`; observe the evidence gate fail.
3. Return the wrong identity in the explanation; run human or G-Eval review.
4. Add a `404` non-disclosure policy variant and update its ground truth explicitly.
5. Add role-based actions, missing objects and property-level disclosure in separate
   scenarios. Keep vulnerable and secure controls for each added flaw family.
6. Compare two real agent adapters on the same versioned cases and repeated runs;
   report per-case failures, model versions and variance before quoting a score.

## References

- [OWASP API1:2023 — BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [DeepEval G-Eval](https://deepeval.com/docs/metrics-llm-evals)
- [DeepEval Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness)

The tool gate here uses an explicit deterministic contract. It does not instantiate
DeepEval's ToolCorrectnessMetric; G-Eval is used for the free-text explanation.
