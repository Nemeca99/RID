"""
RID — Test B7: RSR Drift + Physical Coupling
============================================
Replays the B2 identity perturbation sequence through the Semantic Physics Engine.
Proves that RSR collapse has a physical output consequence — not just a score.

Run: pytest tests/test_b7_rsr_physics.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid import rsr_n, ltp_n, stability_scalar, rle_n, discrepancy_01
from rid.semantic_physics import UnifiedSemanticPhysics

physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0, time_anchor_dt=1.0)

LTP_FIXED    = 1.0
RLE_VALUE    = 0.9878   # matches B1 baseline at minimal load
TOKENS_FIXED = 100.0

BEAT_SEQUENCE = [
    ("0 (stable)",      0.0122, 0.0000),
    ("1-9 (stable)",    0.0122, 0.0122),
    ("10 (JUMP)",       1.0000, 0.0122),   # identity spike → RSR collapses
    ("11 (lag)",        0.0122, 1.0000),   # recon still carries the spike
    ("12-20 (recover)", 0.0122, 0.0122),   # full recovery
]


def run_b7():
    rows = []
    print("=" * 110)
    print("  RID | Test B7: RSR Drift + Physical Coupling")
    print("=" * 110)
    print(f"{'Beat':>15} | {'RSR':>7} | {'S_n':>7} | {'F_raw':>7} | {'F_real':>8} | Descent | Phase")
    print("-" * 110)

    for label, y_n, recon in BEAT_SEQUENCE:
        D   = discrepancy_01(y_n, recon)
        RSR = 1.0 - D
        S_n = stability_scalar(RSR, LTP_FIXED, RLE_VALUE)
        ps  = physics.compute(s_n=S_n, stm_load=0.0, ltp=LTP_FIXED, rle=RLE_VALUE,
                              prompt_tokens=TOKENS_FIXED)
        d   = "YES ⚠" if ps.kernel_descent else "no"
        phase = "IDENTITY CRISIS" if y_n == 1.0 else ("lag" if recon == 1.0 else "stable")
        print(f"{label:>15} | {RSR:>7.4f} | {S_n:>7.4f} | {ps.raw_force:>7.4f} | "
              f"{ps.realized_force:>8.4f} | {d:>7} | {phase}")
        rows.append(dict(label=label, RSR=RSR, S_n=S_n, ps=ps, phase=phase))

    print("=" * 110)
    return rows


def test_stable_baseline_no_descent():
    """Beats 0 and 1-9 must not trigger kernel descent."""
    rows = run_b7()
    stable = [r for r in rows if "stable" in r["label"] and "JUMP" not in r["label"] and "recover" not in r["label"]]
    for r in stable:
        assert not r["ps"].kernel_descent


def test_identity_crisis_triggers_descent():
    """Beat 10 (y_n=1.0 spike) must trigger kernel descent."""
    rows = run_b7()
    crisis = next(r for r in rows if "JUMP" in r["label"])
    assert crisis["ps"].kernel_descent, "Identity crisis must trigger kernel descent"


def test_identity_crisis_rsr_collapses():
    """RSR must collapse near zero at beat 10."""
    rows = run_b7()
    crisis = next(r for r in rows if "JUMP" in r["label"])
    assert crisis["RSR"] < 0.05, f"RSR should collapse: got {crisis['RSR']:.4f}"


def test_recovery_restores_force():
    """Beat 12-20 must restore realized force close to the stable baseline."""
    rows = run_b7()
    stable = next(r for r in rows if "stable" in r["label"] and "JUMP" not in r["label"])
    recover = next(r for r in rows if "recover" in r["label"])
    ref = stable["ps"].realized_force
    actual = recover["ps"].realized_force
    # Allow 10% relative tolerance — RSR recalculation may not be bit-exact
    # but the important proof is that force is non-zero and near baseline
    assert actual > 0, "Recovery should produce positive realized force"
    if ref > 0:
        assert abs(actual - ref) / ref < 0.10, \
            f"Recovery not within 10% of baseline: {actual:.4f} vs {ref:.4f}"



def test_lag_still_in_crisis():
    """Beat 11 (lag) must still be in crisis (recon hasn't caught up)."""
    rows = run_b7()
    lag = next(r for r in rows if "lag" in r["label"])
    assert lag["ps"].kernel_descent, "Lag beat must still be in descent"


if __name__ == "__main__":
    run_b7()
