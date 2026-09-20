# Metric strategy

## Chatbots

- Answer relevancy: did the response address the request?
- Correctness/completeness: did it preserve required facts and constraints?
- Tone/style: did it follow communication requirements?
- Safety/refusal: did it refuse only when appropriate and explain the boundary?

## RAG

- Faithfulness: is the answer supported by retrieved context?
- Contextual precision: were the most useful chunks retrieved?
- Contextual recall: did retrieval include the evidence needed for the reference answer?
- Contextual relevancy: how much retrieved material was actually useful?
- Citation validity: do cited identifiers exist and support nearby claims?

## Agents

- Task completion: did the full trace achieve the user's goal?
- Tool selection: was the correct tool chosen?
- Argument correctness: were tool inputs complete and valid?
- Permission boundary: was an unsafe or unauthorized action prevented?
- Efficiency: were calls, retries, tokens, and latency reasonable?
- Recovery: did the agent respond safely to timeouts, partial results, and dependency errors?

## Threshold guidance

1. Label a representative sample with human reviewers.
2. Compare metric scores against those judgments.
3. Choose a threshold based on the cost of false passes and false failures.
4. Re-run cases to measure judge variance.
5. Version the judge model, prompt, metric configuration, dataset, and threshold.

Do not use a single aggregate score to hide a critical safety or authorization failure.
