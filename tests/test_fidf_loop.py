"""
RID — Test: FIDF Multi-Step Loop Endurance
===========================================
Runs the FIDF loop for multiple steps under various perturbation patterns.
Proves: the loop runs stably, S_n moves correctly in response to simulated
state changes, and the mandatory_descent diagnostic fires as expected.

Note: run_fidf_loop returns the FINAL FIDFState (not a list).
We use on_step callback to collect per-step states.

Run: pytest tests/test_fidf_loop.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid import run_fidf_loop, FIDFConfig, diagnostic_step

# ─── Callback Factories ──────────────────────────────────────────────────────

def make_stable_callbacks():
    """Returns callbacks for a fully stable system."""
    def observable(n):       return 0.5
    def reconstruction(n):   return 0.5
    def support_demand(n):   return (10.0, 10.0)
    def capacity_flow(n):    return (1.0, 0.0, 1.0)
    return observable, reconstruction, support_demand, capacity_flow


def make_degrading_rle_callbacks(rle_rate=0.001):
    """Returns callbacks where RLE degrades each step."""
    def observable(n):     return 0.5
    def reconstruction(n): return 0.5
    def support_demand(n): return (10.0, 10.0)
    def capacity_flow(n):
        load = n * rle_rate
        E_next = max(0.0, 1.0 - load)
        return (1.0, load, E_next)
    return observable, reconstruction, support_demand, capacity_flow


def make_rsr_spike_callbacks(spike_at=50):
    """Returns callbacks with an RSR spike at a specific step."""
    def observable(n):     return 1.0 if n == spike_at else 0.5
    def reconstruction(n): return 0.5
    def support_demand(n): return (10.0, 10.0)
    def capacity_flow(n):  return (1.0, 0.0, 1.0)
    return observable, reconstruction, support_demand, capacity_flow


def _collect_states(n_steps, obs, rec, sd, cf):
    """Helper: runs FIDF and collects per-step states via on_step callback."""
    history = []
    def on_step(n, state, diag):
        history.append((n, state.S_n, state.RSR_n, state.LTP_n, state.RLE_n))

    cfg = FIDFConfig(dt=0.0, max_steps=n_steps)  # dt=0 for fast tests
    run_fidf_loop(cfg, obs, rec, sd, cf, on_step=on_step)
    return history


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_fidf_stable_500_steps():
    """FIDF loop runs 500 steps at full stability; S_n = 1.0 throughout."""
    obs, rec, sd, cf = make_stable_callbacks()
    history = _collect_states(500, obs, rec, sd, cf)
    assert len(history) == 500
    for step, sn, rsr, ltp, rle in history:
        assert abs(sn - 1.0) < 1e-9, f"Step {step}: S_n = {sn} (expected 1.0)"


def test_fidf_rle_degradation_detected():
    """FIDF loop detects and reflects RLE degradation over 100 steps."""
    obs, rec, sd, cf = make_degrading_rle_callbacks(rle_rate=0.001)
    history = _collect_states(100, obs, rec, sd, cf)
    sn_values = [sn for _, sn, *_ in history]
    assert sn_values[-1] < sn_values[0], "S_n should degrade as RLE worsens"
    for i in range(1, len(sn_values)):
        assert sn_values[i] <= sn_values[i-1] + 1e-9, "S_n should decrease monotonically"


def test_fidf_rsr_spike_detected():
    """FIDF detects identity spike as RSR collapse at the expected step."""
    obs, rec, sd, cf = make_rsr_spike_callbacks(spike_at=50)
    history = _collect_states(100, obs, rec, sd, cf)
    sn_at_49 = history[49][1]
    sn_at_50 = history[50][1]
    assert sn_at_50 < sn_at_49, f"S_n must drop at spike: {sn_at_49:.4f} → {sn_at_50:.4f}"


def test_fidf_diagnostic_mandatory_descent():
    """diagnostic_step triggers appropriate action when RSR < 0.3."""
    # diagnostic_step(rsr, ltp, rle) — positional
    result = diagnostic_step(0.2, 0.95, 0.95)
    assert result.action in ("mandatory_descent", "check_rsr"), \
        f"Expected descent-related action; got: {result.action}"


def test_fidf_n_steps_matches_output():
    """on_step is called exactly n_steps times."""
    obs, rec, sd, cf = make_stable_callbacks()
    for n in [1, 10, 100, 200]:
        history = _collect_states(n, obs, rec, sd, cf)
        assert len(history) == n, f"Expected {n} steps, got {len(history)}"


def test_fidf_sn_bounded():
    """S_n from FIDF must be in [0, 1] at every step."""
    obs, rec, sd, cf = make_rsr_spike_callbacks(spike_at=25)
    history = _collect_states(200, obs, rec, sd, cf)
    for step, sn, *_ in history:
        assert 0.0 <= sn <= 1.0 + 1e-9, f"Step {step}: S_n={sn} out of [0,1]"
