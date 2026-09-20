# LLM Evaluation Lab

A project-ready evaluation harness for chatbots, RAG pipelines, and tool-using agents, built with Python, Pytest, and [DeepEval](https://deepeval.com/).

The repository separates cheap deterministic checks from model-judged evaluations so normal CI stays fast, predictable, and free of hidden model calls.

## What this evaluates

| System | Deterministic checks | DeepEval metrics |
|---|---|---|
| Chatbot | schema, required terms, refusal contract | answer relevancy, correctness, tone, safety |
| RAG | citations, context presence, empty retrieval | faithfulness, contextual precision/recall/relevancy |
| Agent | tool allow-list, arguments, duplicates, permission boundaries | task completion, tool/argument correctness |

## Repository map

```text
datasets/                  Version-controlled goldens
docs/                      Metric strategy and project onboarding
src/llm_evaluation_lab/    Loaders and deterministic quality gates
tests/unit/                Fast tests used on every push
tests/evals/               Live LLM-judge evaluations
.github/workflows/         Safe CI and manual live-eval workflows
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
pytest tests/unit
```

Run the live DeepEval suite only when you intend to use an LLM judge:

```bash
cp .env.example .env.local
# add OPENAI_API_KEY to .env.local
deepeval test run tests/evals
```

DeepEval loads `.env.local`; the file is ignored by Git. Never commit credentials or production customer data.

## Add your first project

1. Copy a sample in `datasets/` and replace it with your own version-controlled goldens.
2. Write a thin adapter that returns the actual response, retrieved context, and tool trace.
3. Start with one business-critical metric and one deterministic invariant.
4. Calibrate thresholds against human-reviewed examples before making the metric a blocking gate.
5. Add edge cases: ambiguity, missing context, unsafe requests, dependency failure, duplicate tool calls, and unauthorized actions.

See [`docs/ADDING_A_PROJECT.md`](docs/ADDING_A_PROJECT.md) for the full checklist and [`docs/METRIC_STRATEGY.md`](docs/METRIC_STRATEGY.md) for recommended metrics.

## CI policy

- `ci.yml` runs unit checks on every push and pull request.
- `live-evals.yml` is manual and requires the repository secret `OPENAI_API_KEY`.
- LLM-judge scores should be reviewed for variance before they block deployment.
- Safety and authorization invariants should use deterministic checks whenever possible.

## Current starter datasets

- `chatbot.json`: grounded answer and uncertainty examples
- `rag.json`: answer plus retrieved evidence
- `agent.json`: expected tools, arguments, and permission decisions

Replace the samples with cases from your own projects; do not treat them as a production benchmark.
