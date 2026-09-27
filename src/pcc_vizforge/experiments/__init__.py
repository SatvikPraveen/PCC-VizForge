"""Reproducible experiment runs and Monte Carlo estimator validation."""

from __future__ import annotations

from pcc_vizforge.experiments.runner import (
    DOMAINS,
    RunResult,
    analyze,
    run_experiment,
    verify_run,
)
from pcc_vizforge.experiments.validation import STUDIES, StudyResult, run_study

__all__ = [
    "DOMAINS",
    "STUDIES",
    "RunResult",
    "StudyResult",
    "analyze",
    "run_experiment",
    "run_study",
    "verify_run",
]
