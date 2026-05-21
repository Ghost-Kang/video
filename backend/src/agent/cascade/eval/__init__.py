"""P2-6 LLM rewrite eval harness.

Provides a repeatable, structured evaluation of `rewrite_for_niche` outputs
so prompt iterations / model swaps / provider switches have a regression
baseline.

Public surface:
- run_eval(niches, mode, baseline_path) -> EvalReport
- EvalReport / PerCaseReport / PerNicheReport / CheckResult
- save_baseline / load_latest_baseline / diff_baselines
"""

from agent.cascade.eval.baselines import (
    diff_baselines,
    load_latest_baseline,
    save_baseline,
)
from agent.cascade.eval.checks import CheckResult, run_checks
from agent.cascade.eval.judge import judge_one
from agent.cascade.eval.report import (
    EvalReport,
    PerCaseReport,
    PerNicheReport,
    render_markdown,
)
from agent.cascade.eval.runner import run_eval

__all__ = [
    "CheckResult",
    "EvalReport",
    "PerCaseReport",
    "PerNicheReport",
    "diff_baselines",
    "judge_one",
    "load_latest_baseline",
    "render_markdown",
    "run_checks",
    "run_eval",
    "save_baseline",
]
