"""
RID Framework — Core Formula Unit Tests
20 tests covering all canonical formulas: RLE, LTP, RSR, S_n, SEOL,
thermodynamics, FIDF, and phase boundary logic.

All tests are self-contained and depend only on the `rid` package.
Run: pytest tests/test_formulas.py -v
"""

import pytest
from rid import (
    rle_n, loss_fraction, invariant_preserving_factorization_identity,
    ltp_n, rsr_n, stability_scalar, rate_scaling, divergence_indicator, diagnostic_step,
    lambda_min_carnot, eta_max_carnot, lambda_mismatch, coupling_amplified_loss,
    temporal_mismatch_condition, cost_depth_factorial,
    effective_system_efficiency, voltage_law_violated,
    phase_boundary_divergence_near, discrepancy_01,
)


# ─── RLE ────────────────────────────────────────────────────────────────────

def test_rle_n_basic():
    assert rle_n(E_next=95.0, U_n=5.0, E_n=100.0) == 0.9

def test_rle_n_clamp():
    assert rle_n(100.0, 0.0, 100.0) == 1.0
    assert rle_n(0.0, 100.0, 100.0) == 0.0

def test_loss_fraction():
    assert abs(loss_fraction(0.9) - 0.1) < 1e-9


# ─── LTP ────────────────────────────────────────────────────────────────────

def test_ltp_n_adequacy():
    assert ltp_n(10.0, 10.0) == 1.0
    assert ltp_n(5.0, 10.0) == 0.5
    assert ltp_n(15.0, 10.0) == 1.0

def test_ltp_n_invalid():
    with pytest.raises(ValueError):
        ltp_n(1.0, 0.0)


# ─── RSR ────────────────────────────────────────────────────────────────────

def test_rsr_n():
    assert rsr_n(1.0, 1.0) == 1.0
    assert rsr_n(0.9, 0.9) == 1.0
    assert rsr_n(1.0, 0.0) == 0.0


# ─── S_n ────────────────────────────────────────────────────────────────────

def test_stability_scalar_unity():
    assert stability_scalar(1.0, 1.0, 1.0) == 1.0
    assert stability_scalar(0.5, 0.5, 0.5) == 0.125

def test_stability_scalar_product_property():
    """S_n = RSR × LTP × RLE — multiplicative."""
    for rsr, ltp, rle in [(0.9, 0.8, 0.7), (1.0, 0.5, 0.5), (0.3, 0.3, 0.3)]:
        assert abs(stability_scalar(rsr, ltp, rle) - (rsr * ltp * rle)) < 1e-12


# ─── Thermodynamics ─────────────────────────────────────────────────────────

def test_carnot_bound():
    assert lambda_min_carnot(300.0, 600.0) == 0.5
    assert eta_max_carnot(300.0, 600.0) == 0.5

def test_lambda_mismatch():
    assert lambda_mismatch(10.0, 10.0) == 0.0
    assert lambda_mismatch(5.0, 10.0) == 0.5

def test_coupling_amplified_loss():
    assert abs(coupling_amplified_loss([0.1, 0.1]) - 0.19) < 1e-9
    assert coupling_amplified_loss([]) == 0.0

def test_temporal_mismatch_condition():
    assert temporal_mismatch_condition(2.0, 1.0) is True
    assert temporal_mismatch_condition(1.0, 2.0) is False

def test_cost_depth_factorial():
    assert cost_depth_factorial(0) == 1.0
    assert cost_depth_factorial(4) == 24.0


# ─── SEOL ───────────────────────────────────────────────────────────────────

def test_effective_system_efficiency():
    assert effective_system_efficiency(0.95, 1.0) == 0.95
    assert effective_system_efficiency(0.95, 0.8) == 0.8
    assert effective_system_efficiency(0.5, 0.8) == 0.5

def test_voltage_law_violated():
    assert voltage_law_violated(0.95, 0.8) is True
    assert voltage_law_violated(0.7, 0.8) is False


# ─── LTP Principle ──────────────────────────────────────────────────────────

def test_invariant_preserving_factorization_identity():
    assert invariant_preserving_factorization_identity(5.0, 3.0) is True
    assert invariant_preserving_factorization_identity(5.0, 0.0) is False

def test_phase_boundary_divergence_near():
    assert phase_boundary_divergence_near(0.1, 1e7) is True
    assert phase_boundary_divergence_near(2.0, 1e7) is False
    assert phase_boundary_divergence_near(0.1, 100.0) is False


# ─── Triangle ───────────────────────────────────────────────────────────────

def test_rate_scaling():
    assert rate_scaling(1.0, 2.0) == 0.5
    assert rate_scaling(0.8, 1.0) == 0.8

def test_divergence_indicator():
    assert divergence_indicator(0.4, 0.35) > 0   # headroom
    assert divergence_indicator(0.3, 0.35) < 0   # feedback risk


# ─── FIDF Diagnostic ────────────────────────────────────────────────────────

def test_diagnostic_step_nominal():
    res = diagnostic_step(1.0, 1.0, 1.0)
    assert res.action == "continue"
    assert res.state.S_n >= 0.999

def test_diagnostic_step_intervene_rle():
    res = diagnostic_step(1.0, 1.0, 0.8)
    assert res.action == "intervene_rle"
