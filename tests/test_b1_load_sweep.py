"""
RID Framework — Test B1: STM Load Sweep (Standalone)
=====================================================
Simulates increasing Short-Term Memory load WITHOUT any AIOS V2 classes.
Uses the canonical STM math directly: capacity=4096 tokens, item_weight=tokens/4096.

Proves: As memory load increases, RLE degrades linearly while RSR and LTP remain
constant — axis independence at the memory-load level.

Run: pytest tests/test_b1_load_sweep.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid import rle_n, ltp_n, rsr_n, stability_scalar

# ─── STM Math (from AIOS V2 hemispheres.py) ───────────────────────────────
# capacity = 4096 tokens (STM context window)
# item_weight = token_count / 4096
# current_load = sum(item_weights)  -- cumulative fraction of capacity used
# E_n = 1.0 (normalized), U_n = 0.0, E_next = 1.0 - current_load
# → RLE = (E_next - U_n) / E_n = 1 - current_load

STM_CAPACITY = 4096          # tokens
Y_N_BASELINE = 0.0122        # soul fidelity (RSR baseline, no drift)
N_N, D_N    = 100.0, 100.0  # kernel support == demand (LTP = 1.0)

TOKEN_SIZES = [0, 25, 50, 100, 200, 400, 800]


def run_b1():
    rows = []
    cumulative_load = 0.0

    print("=" * 80)
    print("  RID | Test B1: STM Load Sweep (Standalone)")
    print("=" * 80)
    print(f"{'Tokens':>7} | {'Load%':>7} | {'RLE':>7} | {'LTP':>7} | {'RSR':>7} | {'S_n':>7} | Action")
    print("-" * 80)

    for tokens in TOKEN_SIZES:
        if tokens > 0:
            cumulative_load += tokens / STM_CAPACITY

        E_n, U_n, E_next = 1.0, 0.0, max(0.0, 1.0 - cumulative_load)
        RSR = rsr_n(Y_N_BASELINE, Y_N_BASELINE)   # no drift → RSR = 1.0
        LTP = ltp_n(N_N, D_N)                      # support == demand → LTP = 1.0
        RLE = rle_n(E_next, U_n, E_n)
        S_n = stability_scalar(RSR, LTP, RLE)

        action = "continue" if S_n >= 1.0 - 1e-9 else "intervene_rle"
        display_load = cumulative_load * 100

        print(f"{tokens:>7} | {display_load:>7.2f} | {RLE:>7.4f} | {LTP:>7.4f} | {RSR:>7.4f} | {S_n:>7.4f} | {action}")
        rows.append(dict(tokens=tokens, load=cumulative_load, RLE=RLE, LTP=LTP, RSR=RSR, S_n=S_n))

    print("=" * 80)
    return rows


def test_rle_degrades_under_load():
    """RLE must decrease as tokens accumulate in STM."""
    rows = run_b1()
    rle_values = [r["RLE"] for r in rows]
    for i in range(1, len(rle_values)):
        assert rle_values[i] <= rle_values[i - 1], \
            f"RLE should not increase: {rle_values[i-1]:.4f} → {rle_values[i]:.4f}"


def test_rsr_stays_constant():
    """RSR must remain exactly 1.0 throughout (no identity drift applied)."""
    rows = run_b1()
    for r in rows:
        assert abs(r["RSR"] - 1.0) < 1e-9, f"RSR drifted: {r['RSR']}"


def test_ltp_stays_constant():
    """LTP must remain exactly 1.0 (support meets demand throughout)."""
    rows = run_b1()
    for r in rows:
        assert abs(r["LTP"] - 1.0) < 1e-9, f"LTP drifted: {r['LTP']}"


def test_sn_equals_rle():
    """With RSR=1.0 and LTP=1.0, S_n = RLE exactly."""
    rows = run_b1()
    for r in rows:
        assert abs(r["S_n"] - r["RLE"]) < 1e-12, \
            f"S_n != RLE: {r['S_n']} vs {r['RLE']}"


def test_sn_in_unit_interval():
    """S_n must always be in [0, 1]."""
    rows = run_b1()
    for r in rows:
        assert 0.0 <= r["S_n"] <= 1.0


if __name__ == "__main__":
    run_b1()
