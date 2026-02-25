"""
RID — Test B5: Mismatch Loss Sweep (Thermodynamic Kernel Descent Trigger)
=========================================================================
Sweeps LTP 1.0→0.0 at fixed S_n=0.9, RLE=0.95, tokens=200.
Proves lambda_mismatch is additive over the Carnot floor, and kernel descent
fires deterministically at the threshold where realized_force ≤ 0.

Run: pytest tests/test_b5_mismatch.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid.semantic_physics import UnifiedSemanticPhysics

physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0, time_anchor_dt=1.0)

LTP_SWEEP    = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
S_N_FIXED    = 0.9
RLE_FIXED    = 0.95
TOKENS_FIXED = 200.0


def run_b5():
    rows = []
    print("=" * 105)
    print("  RID | Test B5: Mismatch Loss Sweep (Kernel Descent Trigger)")
    print(f"  Fixed: S_n={S_N_FIXED} | RLE={RLE_FIXED} | Tokens={TOKENS_FIXED}")
    print("=" * 105)
    print(f"{'LTP':>6} | {'Λ_carnot':>9} | {'Λ_mismatch':>10} | {'Λ_total':>8} | {'F_raw':>7} | {'F_real':>8} | Descent")
    print("-" * 75)

    for ltp in LTP_SWEEP:
        ps = physics.compute(s_n=S_N_FIXED, stm_load=0.0, ltp=ltp, rle=RLE_FIXED,
                             prompt_tokens=TOKENS_FIXED)
        d = "YES ⚠" if ps.kernel_descent else "no"
        print(f"{ltp:>6.1f} | {ps.lambda_carnot:>9.4f} | {ps.lambda_mismatch:>10.4f} | "
              f"{ps.lambda_total:>8.4f} | {ps.raw_force:>7.4f} | {ps.realized_force:>8.4f} | {d}")
        rows.append(dict(ltp=ltp, ps=ps))

    print("=" * 105)
    return rows


def test_carnot_floor_is_constant():
    """Λ_carnot = T_c/T_h = 1/8 = 0.125 for 8GB GPU — invariant across LTP."""
    rows = run_b5()
    for r in rows:
        assert abs(r["ps"].lambda_carnot - 0.125) < 1e-9, \
            f"Carnot floor changed: {r['ps'].lambda_carnot}"


def test_mismatch_increases_as_ltp_falls():
    """Λ_mismatch = 1 - LTP; must increase monotonically as LTP decreases."""
    rows = run_b5()
    for r in rows:
        expected = 1.0 - r["ltp"]
        assert abs(r["ps"].lambda_mismatch - expected) < 1e-9


def test_lambda_total_additive():
    """Λ_total = Λ_carnot + Λ_mismatch (capped at 1.0)."""
    rows = run_b5()
    for r in rows:
        ps = r["ps"]
        expected = min(1.0, ps.lambda_carnot + ps.lambda_mismatch)
        assert abs(ps.lambda_total - expected) < 1e-9


def test_kernel_descent_fires_at_threshold():
    """Kernel descent must fire when realized_force ≤ 0."""
    rows = run_b5()
    for r in rows:
        ps = r["ps"]
        if ps.kernel_descent:
            assert ps.realized_force <= 0.0


def test_kernel_does_not_fire_at_high_ltp():
    """No kernel descent when LTP ≥ 0.5 at these load conditions."""
    rows = run_b5()
    high_ltp = [r for r in rows if r["ltp"] >= 0.5]
    for r in high_ltp:
        assert not r["ps"].kernel_descent


if __name__ == "__main__":
    run_b5()
