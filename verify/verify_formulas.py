"""
RID Framework — Formula Verifier
=================================
Verifies that all formulas in RID_Complete.md (Section 9 Appendix) match
the actual `rid` package implementation. 16 checks must all pass.

Run from repo root: python verify/verify_formulas.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid import (
    rle_n, ltp_n, rsr_n, stability_scalar,
    effective_system_efficiency, voltage_law_violated, discrepancy_01,
)


def _approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def run_checks():
    results = []

    # ── RLE ──────────────────────────────────────────────────────────────────
    r = rle_n(E_next=95.0, U_n=5.0, E_n=100.0)
    results.append(("RLE formula (95,5,100) = 0.9",         _approx(r, 0.9),         f"got {r}"))

    r0 = rle_n(100.0, 0.0, 100.0); r1 = rle_n(0.0, 100.0, 100.0)
    results.append(("RLE clamp: 1.0 and 0.0",               _approx(r0, 1.0) and _approx(r1, 0.0), f"{r0},{r1}"))

    # ── LTP ──────────────────────────────────────────────────────────────────
    ok = _approx(ltp_n(10,10), 1.0) and _approx(ltp_n(5,10), 0.5) and _approx(ltp_n(15,10), 1.0)
    results.append(("LTP min(1,n/d): (10,10)=1,(5,10)=.5,(15,10)=1", ok, ""))

    ltp_90, ltp_80 = ltp_n(90,75), ltp_n(80,75)
    results.append(("Extrusion LTP 75A demand, 90A/80A cap = 1", _approx(ltp_90,1) and _approx(ltp_80,1), f"{ltp_90},{ltp_80}"))

    # ── RSR ──────────────────────────────────────────────────────────────────
    d = discrepancy_01(0.65, 0.70)
    results.append(("Discrepancy_01(0.65,0.70) = 0.05",     _approx(d, 0.05),        f"got {d}"))

    rsr = rsr_n(0.70, 0.65)
    results.append(("RSR 415 vs 420°F normalized = 0.95",   _approx(rsr, 0.95),      f"got {rsr}"))

    rsr1, rsr0 = rsr_n(1.0, 1.0), rsr_n(1.0, 0.0)
    results.append(("RSR (1,1)=1 and (1,0)=0",             _approx(rsr1, 1.0) and _approx(rsr0, 0.0), f"{rsr1},{rsr0}"))

    # ── S_n ──────────────────────────────────────────────────────────────────
    s1, s2 = stability_scalar(1,1,1), stability_scalar(.5,.5,.5)
    results.append(("S_n (1,1,1)=1 and (0.5,0.5,0.5)=0.125", _approx(s1,1) and _approx(s2,0.125), f"{s1},{s2}"))

    # ── SEOL ──────────────────────────────────────────────────────────────────
    eff = effective_system_efficiency(0.95, 0.8)
    results.append(("eff(0.95,0.8)=0.8 (capped)",          _approx(eff, 0.8),       f"got {eff}"))

    eff2 = effective_system_efficiency(0.7, 0.8)
    results.append(("eff(0.7,0.8)=0.7 (not capped)",       _approx(eff2, 0.7),      f"got {eff2}"))

    vt, vf = voltage_law_violated(0.95,0.8), voltage_law_violated(0.7,0.8)
    results.append(("voltage_law_violated: True iff S_n>LTP", vt is True and vf is False, f"{vt},{vf}"))

    # ── Extrusion RLE Proxy ───────────────────────────────────────────────────
    for u, exp in [(0,1.0),(25,0.5),(50,0.0)]:
        r = rle_n(E_next=100.0-u, U_n=float(u), E_n=100.0)
        results.append((f"Extrusion proxy U_n={u} → RLE={exp}", _approx(r, exp, 1e-6), f"got {r}"))

    r0, r25, r50 = (rle_n(100,0,100), rle_n(75,25,100), rle_n(50,50,100))
    results.append(("Extrusion: RLE decreases as demand increases", r0 > r25 > r50, f"{r0:.3f}>{r25:.3f}>{r50:.3f}"))

    # ── Extrusion Full Step ───────────────────────────────────────────────────
    y, rec = (420-350)/100, (415-350)/100
    rsr_v  = rsr_n(y, rec)
    rle_v  = rle_n(100-75, 75, 100)
    ok = _approx(rsr_v, 0.95, 0.01) and _approx(ltp_n(90,75), 1.0) and rle_v < rsr_v
    results.append(("Doc narrative: RSR≈0.95, LTP=1, RLE worst leg", ok,
                    f"RSR={rsr_v:.3f} LTP=1 RLE={rle_v:.3f}"))

    return results


def main():
    print("RID Formula Verifier — 16 checks\n")
    results = run_checks()
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    for name, ok, msg in results:
        tag  = "PASS" if ok else "FAIL"
        note = f"  ({msg})" if msg and not ok else ""
        print(f"  [{tag}] {name}{note}")
    print(f"\nTotal: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("No contradictions found — document and rid package are consistent.")


if __name__ == "__main__":
    main()
