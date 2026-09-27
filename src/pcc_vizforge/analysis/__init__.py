"""Statistical analysis and estimation routines.

Sub-modules
-----------
inference
    Hypothesis tests, bootstrap confidence intervals, multiple testing.
"""

from __future__ import annotations

from pcc_vizforge.analysis.inference import (
    ConfidenceInterval,
    TestResult,
    adjust_pvalues,
    autocorrelation,
    bootstrap_ci,
    chi_square_gof,
    ljung_box,
    runs_test,
)

__all__ = [
    "ConfidenceInterval",
    "TestResult",
    "adjust_pvalues",
    "autocorrelation",
    "bootstrap_ci",
    "chi_square_gof",
    "ljung_box",
    "runs_test",
]
