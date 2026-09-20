# Adding a project

## 1. Define the decision

Write down what the evaluation protects: a pull request, a release, a prompt version, a retrieval change, or a production alert. A metric without a decision is only a dashboard number.

## 2. Create goldens

Add a dataset containing:

- stable `case_id`
- user input
- expected behavior or reference answer
- actual output from the system under test
- retrieved evidence for RAG
- tool calls and arguments for agents
- risk tags such as `safety`, `authorization`, `edge-case`, or `regression`

Use synthetic or sanitized data in a public repository.

## 3. Add deterministic gates first

Prefer ordinary assertions for exact, objective rules:

- output schema
- required fields and citations
- tool allow-lists
- permission checks
- duplicate or repeated side effects
- latency and token budgets
- retry and idempotency behavior

## 4. Add model-judged metrics

Use DeepEval when quality is semantic: faithfulness, answer relevance, correctness, tone, task completion, or tool-argument quality. Start with a small human-reviewed set and calibrate the threshold before blocking CI.

## 5. Separate execution modes

- Unit suite: deterministic, quick, every pull request
- Live eval suite: intentional, credentialed, cost-aware
- Scheduled benchmark: larger regression dataset, trend reporting
- Production monitoring: sampled traces with privacy controls

## 6. Review failures

Store the input, output, context, trace, metric score, reason, model, prompt version, and code revision. A useful evaluation failure must be reproducible.
