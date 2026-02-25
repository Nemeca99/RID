"""
RID — Test B8: Isolation Comparison (Standalone)
=================================================
Three-phase isolation experiment — no AIOS V2 dependencies.

SECTION 1: Expanded RID Alone (Physics Engine, S_n=1.0)
  Pure Newtonian-Carnot math at maximum acceleration.
  Establishes the physical ceiling — what the hardware delivers at perfect stability.

SECTION 2: Original RID Alone (S_n = RSR × LTP × RLE)
  Dimensionless-only view. No force, no physics.
  Shows what the framework knew before Phase 13.

SECTION 3: Combined (S_n feeds Physics as acceleration)
  S_n from the original triangle becomes the acceleration scalar.
  Δ_force = F_real(S_n) - F_real(1.0) shows the hardware cost of instability.

Run: pytest tests/test_b8_isolation.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid import rle_n, rsr_n, ltp_n, stability_scalar
from rid.semantic_physics import UnifiedSemanticPhysics

physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0, time_anchor_dt=1.0)

# STM simulation parameters (from AIOS V2 hemispheres.py math)
STM_CAPACITY = 4096
Y_N = 0.0122   # soul baseline (no drift)
N_N = D_N = 100.0  # support == demand

TOKEN_SIZES = [0, 25, 100, 200, 400, 600]


def _make_row(tokens):
    load = tokens / STM_CAPACITY
    E_n, U_n, E_next = 1.0, 0.0, max(0.0, 1.0 - load)
    RSR = rsr_n(Y_N, Y_N)
    LTP = ltp_n(N_N, D_N)
    RLE = rle_n(E_next, U_n, E_n)
    S_n = stability_scalar(RSR, LTP, RLE)
    return dict(tokens=tokens, load=load, RSR=RSR, LTP=LTP, RLE=RLE, S_n=S_n)


def run_b8():
    rows = [_make_row(t) for t in TOKEN_SIZES]

    # Section 1: Physics engine, S_n pinned to 1.0
    ceiling = {}
    print("\n=== SECTION 1: Expanded RID Alone (S_n = 1.0) ===")
    print(f"{'Tokens':>7} | {'Mass':>8} | {'F_raw':>8} | {'Λ_total':>8} | {'F_real':>8}")
    for r in rows:
        ps = physics.compute(s_n=1.0, stm_load=r["load"], ltp=1.0, rle=1.0,
                             prompt_tokens=float(r["tokens"]))
        ceiling[r["tokens"]] = ps.realized_force
        print(f"{r['tokens']:>7} | {ps.prompt_mass:>8.4f} | {ps.raw_force:>8.4f} | "
              f"{ps.lambda_total:>8.4f} | {ps.realized_force:>8.4f}")

    # Section 2: Original RID only
    print("\n=== SECTION 2: Original RID Alone (No Physics) ===")
    print(f"{'Tokens':>7} | {'S_n':>7} | {'RLE':>7} | Action")
    for r in rows:
        action = "continue" if r["S_n"] >= 1.0 - 1e-9 else "intervene_rle"
        print(f"{r['tokens']:>7} | {r['S_n']:>7.4f} | {r['RLE']:>7.4f} | {action}")

    # Section 3: Combined
    results3 = []
    print("\n=== SECTION 3: Combined (S_n feeds Physics) ===")
    print(f"{'Tokens':>7} | {'S_n':>7} | {'F_real':>8} | {'Δ_force':>9} | {'Cost%':>7}")
    for r in rows:
        ps = physics.compute(s_n=r["S_n"], stm_load=r["load"], ltp=r["LTP"], rle=r["RLE"],
                             prompt_tokens=float(r["tokens"]))
        ref = ceiling[r["tokens"]]
        delta = ps.realized_force - ref
        cost_pct = abs(delta) / ref * 100 if ref > 0 else 0.0
        print(f"{r['tokens']:>7} | {r['S_n']:>7.4f} | {ps.realized_force:>8.4f} | "
              f"{delta:>+9.4f} | {cost_pct:>6.1f}%")
        results3.append(dict(row=r, ps=ps, delta=delta, cost_pct=cost_pct, ref=ref))

    return rows, ceiling, results3


def test_ceiling_has_max_force():
    """Section 1: Physics alone at S_n=1 must produce the maximum possible force."""
    rows, ceiling, results3 = run_b8()
    for r3 in results3:
        if r3["row"]["tokens"] > 0:
            assert r3["ps"].realized_force <= r3["ref"] + 1e-9, \
                "Combined force must never exceed the S_n=1.0 ceiling"


def test_combined_force_below_ceiling():
    """Section 3 realized force must be ≤ Section 1 (non-trivial for tokens > 0)."""
    rows, ceiling, results3 = run_b8()
    for r3 in results3:
        if r3["row"]["tokens"] > 0 and r3["row"]["S_n"] < 1.0:
            assert r3["delta"] < 0, "With S_n < 1, combined force must be below ceiling"


def test_cost_increases_with_load():
    """The physical cost % of instability should grow as load increases."""
    rows, ceiling, results3 = run_b8()
    costs = [r["cost_pct"] for r in results3 if r["row"]["tokens"] > 0]
    for i in range(1, len(costs)):
        assert costs[i] >= costs[i - 1] - 0.01, \
            f"Cost% should not decrease with load: {costs[i-1]:.1f} → {costs[i]:.1f}"


def test_original_rid_no_physics_info():
    """Section 2: RSR=1.0, LTP=1.0 throughout (no drift applied in load sweep)."""
    rows = [_make_row(t) for t in TOKEN_SIZES]
    for r in rows:
        assert abs(r["RSR"] - 1.0) < 1e-9
        assert abs(r["LTP"] - 1.0) < 1e-9


if __name__ == "__main__":
    run_b8()
