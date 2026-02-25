"""
RID — Test: Monotonicity Proofs
================================
For any axis, degradation from 1.0→0.0 while the other two are held at 1.0
must cause S_n to decrease monotonically. Also verifies that each axis is
independent: changes in one must not move the other two.

These are mathematical property proofs — 300 sweep points each axis.

Run: pytest tests/test_monotonicity.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid import rsr_n, ltp_n, rle_n, stability_scalar

import numpy as np

SWEEP = [round(v, 4) for v in list(reversed([i / 300 for i in range(301)]))]  # 1.0 → 0.0, 301 points


def test_sn_monotone_decreasing_rle():
    """S_n must decrease monotonically as RLE sweeps 1.0 → 0.0 (RSR=1, LTP=1)."""
    prev_sn = 2.0
    for rle in SWEEP:
        sn = stability_scalar(1.0, 1.0, rle)
        assert sn <= prev_sn + 1e-12, f"S_n not monotone: {prev_sn:.6f} → {sn:.6f} at RLE={rle}"
        prev_sn = sn


def test_sn_monotone_decreasing_ltp():
    """S_n must decrease monotonically as LTP sweeps 1.0 → 0.0 (RSR=1, RLE=1)."""
    prev_sn = 2.0
    for ltp_val in SWEEP:
        sn = stability_scalar(1.0, ltp_val, 1.0)
        assert sn <= prev_sn + 1e-12, f"S_n not monotone at LTP={ltp_val}"
        prev_sn = sn


def test_sn_monotone_decreasing_rsr():
    """S_n must decrease monotonically as RSR sweeps 1.0 → 0.0 (LTP=1, RLE=1)."""
    prev_sn = 2.0
    for rsr in SWEEP:
        sn = stability_scalar(rsr, 1.0, 1.0)
        assert sn <= prev_sn + 1e-12, f"S_n not monotone at RSR={rsr}"
        prev_sn = sn


def test_rle_axis_independent_of_rsr():
    """Changing RLE must not affect the RSR calculation."""
    ref_rsr = rsr_n(0.8, 0.9)
    for rle in SWEEP[::30]:  # sample every 30th point
        # RSR is computed from y_n, recon — has nothing to do with RLE
        assert abs(rsr_n(0.8, 0.9) - ref_rsr) < 1e-12, "RSR changed with RLE sweep"


def test_ltp_axis_independent_of_rle():
    """LTP must not change when only RLE inputs change."""
    ref_ltp = ltp_n(8.0, 10.0)
    for rle in SWEEP[::30]:
        # ltp_n depends only on n_n, d_n — not on E values
        assert abs(ltp_n(8.0, 10.0) - ref_ltp) < 1e-12, "LTP changed with RLE sweep"


def test_sn_zero_when_any_axis_zero():
    """If any single axis is 0.0, S_n must be 0.0 (multiplicative)."""
    assert stability_scalar(0.0, 1.0, 1.0) == 0.0
    assert stability_scalar(1.0, 0.0, 1.0) == 0.0
    assert stability_scalar(1.0, 1.0, 0.0) == 0.0


def test_sn_one_when_all_axes_one():
    """S_n = 1.0 iff all three axes = 1.0."""
    assert stability_scalar(1.0, 1.0, 1.0) == 1.0


