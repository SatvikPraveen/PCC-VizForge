"""Statistical analysis and estimation routines.

Sub-modules
-----------
inference
    Hypothesis tests, bootstrap confidence intervals, multiple testing.
diffusion
    MSD / TAMSD, anomalous-exponent fitting, ergodicity breaking, DFA,
    first-passage times.
probability
    Exact dice-sum PMFs by convolution, die moments, CLT bands.
seismology
    Gutenberg-Richter b-value MLEs, magnitude of completeness, Omori-Utsu
    fitting, inter-event statistics.
"""

from __future__ import annotations

from pcc_vizforge.analysis import diffusion, probability, seismology
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
    "diffusion",
    "ljung_box",
    "probability",
    "runs_test",
    "seismology",
]
