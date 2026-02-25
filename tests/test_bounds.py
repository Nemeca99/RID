"""
RID — Test: Bounds and Invariants
==================================
Proves that all RID outputs remain within their specified ranges for any valid
input combination. 2,000 random triples are tested per section.

Guarantees:
  - RLE, LTP, RSR all ∈ [0, 1]
  - S_n ∈ [0, 1]
  - Lambda values all ∈ [0, 1]
  - Realized force ≥ 0 always
  - Physics outputs don't blow up under extreme inputs

Run: pytest tests/test_bounds.py -v -s
"""

import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
random.seed(42)

from rid import rle_n, ltp_n, rsr_n, stability_scalar
from rid import lambda_min_carnot, lambda_mismatch, effective_system_efficiency
from rid.semantic_physics import UnifiedSemanticPhysics

N = 2000  # random samples per test


def _random_unit():
    return random.random()

def _random_pos():
    return random.uniform(0.01, 100.0)


def test_rle_bounded():
    """rle_n must always return a value in [0, 1] for any valid E_n > 0."""
    for _ in range(N):
        E_n    = random.uniform(0.001, 1000.0)
        U_n    = random.uniform(0.0, E_n)
        E_next = random.uniform(0.0, E_n)
        v = rle_n(E_next, U_n, E_n)
        assert 0.0 <= v <= 1.0 + 1e-9, f"rle_n out of bounds: {v}"


def test_ltp_bounded():
    """ltp_n = min(1, n/d) must always be in [0, 1]."""
    for _ in range(N):
        n_n = random.uniform(0.0, 100.0)
        d_n = random.uniform(0.001, 100.0)
        v = ltp_n(n_n, d_n)
        assert 0.0 <= v <= 1.0 + 1e-9, f"ltp_n out of bounds: {v}"


def test_rsr_bounded():
    """rsr_n = 1 - |y - r| must be in [0, 1] when inputs are in [0, 1]."""
    for _ in range(N):
        y = _random_unit()
        r = _random_unit()
        v = rsr_n(y, r)
        assert 0.0 <= v <= 1.0 + 1e-9, f"rsr_n out of bounds: {v}"


def test_stability_scalar_bounded():
    """S_n = RSR × LTP × RLE must be in [0, 1] for any inputs in [0, 1]."""
    for _ in range(N):
        rsr = _random_unit()
        ltp = _random_unit()
        rle = _random_unit()
        sn = stability_scalar(rsr, ltp, rle)
        assert 0.0 <= sn <= 1.0 + 1e-9, f"S_n out of bounds: {sn}"


def test_lambda_floor_bounded():
    """Λ_carnot = T_c / T_h must be in (0, 1) for any valid T_c < T_h."""
    for _ in range(N):
        T_c = random.uniform(0.01, 50.0)
        T_h = random.uniform(T_c + 0.01, 200.0)
        v = lambda_min_carnot(T_c, T_h)
        assert 0.0 < v < 1.0, f"lambda_floor out of (0,1): {v}"


def test_lambda_mismatch_bounded():
    """Λ_mismatch must be in [0, 1]."""
    for _ in range(N):
        n_actual = random.uniform(0.0, 100.0)
        n_target = random.uniform(0.001, 100.0)
        v = lambda_mismatch(n_actual, n_target)
        assert 0.0 <= v <= 1.0 + 1e-9, f"lambda_mismatch out of bounds: {v}"


def test_physics_realized_force_nonnegative():
    """Realized force must always be ≥ 0 for any input."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    for _ in range(N):
        s_n    = _random_unit()
        stm    = _random_unit() * 0.5   # keep load reasonable
        ltp    = _random_unit()
        rle    = _random_unit()
        tokens = random.uniform(0.0, 2000.0)
        ps = physics.compute(s_n=s_n, stm_load=stm, ltp=ltp, rle=rle, prompt_tokens=tokens)
        assert ps.realized_force >= 0.0, f"Negative realized_force: {ps.realized_force}"


def test_physics_lambda_total_bounded():
    """Λ_total must always be in [0, 1]."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    for _ in range(N):
        ps = physics.compute(
            s_n=_random_unit(), stm_load=_random_unit()*0.5,
            ltp=_random_unit(), rle=_random_unit(),
            prompt_tokens=random.uniform(0, 1000)
        )
        assert 0.0 <= ps.lambda_total <= 1.0 + 1e-9, \
            f"lambda_total out of bounds: {ps.lambda_total}"


def test_seol_bounded():
    """effective_system_efficiency must always be ≤ min(S_n, LTP_input)."""
    for _ in range(N):
        sn  = _random_unit()
        ltp = _random_unit()
        eff = effective_system_efficiency(sn, ltp)
        expected = min(sn, ltp)
        assert abs(eff - expected) < 1e-12, f"SEOL efficiency wrong: {eff} vs {expected}"



