"""Run offline by default; bring your own agent using --agent module:function."""

import argparse
import importlib
import json
from pathlib import Path

from .lab import baseline_agent, load_scenarios, run_case, summarize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="datasets/security/authorization.json")
    parser.add_argument("--output", default="reports/security/results.json")
    parser.add_argument("--agent", help="Importable Python module:function (may call your LLM)")
    args = parser.parse_args()
    agent = baseline_agent
    if args.agent:
        module, name = args.agent.split(":", 1)
        agent = getattr(importlib.import_module(module), name)
    results = [run_case(case, agent) for case in load_scenarios(args.dataset)]
    report = {
        "schema_version": 1,
        "agent": args.agent or "scripted-baseline-not-an-llm",
        "summary": summarize(results),
        "results": results,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Evidence report: {target}")
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
