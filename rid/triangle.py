# ==========================================
# RID: RLE–LTP–RSR Stability Triangle
# Source: RLE-LTP-RSR_Stability_Equation_Canonical_Spec.pdf
# Version: 1.0 | Canonical stability equation with rate normalization
# ==========================================

from typing import Callable, Optional, Tuple, Union
from dataclasses import dataclass

from .axioms import rle_n
from .discrepancy import discrepancy_01, DiscrepancyFunc


# ---------------------------------------------------------------------------
# Variables (domains from spec)
# ---------------------------------------------------------------------------
# ∆t  (0, ∞)   sampling interval
# f   (0, ∞)   update frequency f = 1/∆t
# E_n (0, ∞)   usable capacity before transition n→n+1
# U_n [0, E_n] irrecoverable loss during n→n+1
# RLE_n [0,1]  retained usable fraction
# RSR_n [0,1]  reconstruction fidelity
# n_n (0, ∞)   structural support at current layer
# d_n (0, ∞)   compression demand
# LTP_n [0,1]  structural adequacy index
# S_n [0,1]    system stability / efficiency scalar
# ---------------------------------------------------------------------------


def ltp_n(n_n: float, d_n: float) -> float:
    """
    Layer Transition Principle index (structural adequacy).

    LTP_n = min(1, n_n / d_n).

    If n_n ≥ d_n then LTP_n = 1 (structure meets demand).
    If n_n < d_n then LTP_n < 1 (structural strain; descent may be required).
    """
    if d_n <= 0:
        raise ValueError("d_n must be positive")
    return min(1.0, max(0.0, n_n / d_n))


def rsr_n(
    y_n: Union[float, list],
    n_n_reconstruction: Union[float, list],
    D: Optional[DiscrepancyFunc] = None,
) -> float:
    """
    Recursive State Reconstruction: reconstruction fidelity.

    RSR_n = 1 − D(y_n, n_n).

    y_n = current observable input
    n_n_reconstruction = system's reconstruction (filtered/delayed echo) of prior output/state
    D = normalized discrepancy in [0, 1]; default discrepancy_01 for [0,1]-valued signals.
    """
    if D is None:
        D = discrepancy_01
    d_val = D(y_n, n_n_reconstruction)
    return max(0.0, min(1.0, 1.0 - d_val))


def stability_scalar(RSR_n: float, LTP_n: float, RLE_n: float) -> float:
    """
    System stability / efficiency scalar (multiplicative closure of the triangle).

    S_n = RSR_n · LTP_n · RLE_n,  S_n ∈ [0, 1].

    S_n = 1: nominally aligned (no reconstruction drift, no structural inadequacy,
             full retained fraction). S_n < 1: hidden loss/strain in the triangle.
    """
    return max(0.0, min(1.0, RSR_n * LTP_n * RLE_n))


def rate_scaling(S_old: float, m: float) -> float:
    """
    Expected normalized stability when rate changes by multiplier m.

    m = f_new / f_old = ∆t_old / ∆t_new (internal structure fixed).

    S_expected(new) ≈ S_old / m.
    """
    if m <= 0:
        raise ValueError("Rate multiplier m must be positive")
    return max(0.0, min(1.0, S_old / m))


def divergence_indicator(
    S_observed_new: float, S_expected_new: float
) -> float:
    """
    ∆S = S_observed(new) − S_expected(new).

    ∆S < 0: system may not maintain new rate (feedback onset risk).
    ∆S ≥ 0: headroom at that rate.
    """
    return S_observed_new - S_expected_new


# ---------------------------------------------------------------------------
# Diagnostic logic (operational loop)
# ---------------------------------------------------------------------------

@dataclass
class TriangleState:
    """One step's RLE–LTP–RSR values and stability S_n."""

    RSR_n: float = 0.0
    LTP_n: float = 0.0
    RLE_n: float = 0.0
    S_n: float = 0.0
    step: int = 0

    @classmethod
    def from_components(
        cls,
        RSR_n: float,
        LTP_n: float,
        RLE_n: float,
        step: int = 0,
    ) -> "TriangleState":
        S_n = stability_scalar(RSR_n, LTP_n, RLE_n)
        return cls(RSR_n=RSR_n, LTP_n=LTP_n, RLE_n=RLE_n, S_n=S_n, step=step)


@dataclass
class DiagnosticResult:
    """Result of one diagnostic step: state + recommended action."""

    state: TriangleState
    action: str  # "continue" | "check_ltp" | "mandatory_descent" | "intervene_rsr" | "intervene_ltp" | "intervene_rle"
    message: str = ""


def diagnostic_step(
    RSR_n: float,
    LTP_n: float,
    RLE_n: float,
    step: int = 0,
    rsr_low_threshold: float = 0.9,
    ltp_adequacy_threshold: float = 1.0,
) -> DiagnosticResult:
    """
    Minimal diagnostic logic gate (spec Section 6).

    At each step n:
    1) Compute RSR_n (foreground signal).
    2) If RSR_n below threshold, evaluate LTP_n (structure vs demand).
    3) If LTP_n < 1, perform mandatory descent / structural expansion.
    4) After any action/transition, compute RLE_n and update S_n.

    Pseudologic:
      IF S_n == 1: continue (RSR loop)
      ELSE: locate which factor is non-unitary (RSR, LTP, or RLE) and intervene.
    """
    S_n = stability_scalar(RSR_n, LTP_n, RLE_n)
    state = TriangleState(RSR_n=RSR_n, LTP_n=LTP_n, RLE_n=RLE_n, S_n=S_n, step=step)

    if S_n >= 1.0 - 1e-9:
        return DiagnosticResult(
            state=state,
            action="continue",
            message="S_n nominally 1; continue RSR loop.",
        )

    # Locate non-unitary factor; spec: if RSR low then evaluate LTP
    if RSR_n < rsr_low_threshold:
        action = "check_ltp"
        msg = "RSR below threshold; evaluate LTP (structure vs demand)."
        if LTP_n < ltp_adequacy_threshold:
            action = "mandatory_descent"
            msg = "LTP < 1; perform mandatory descent / structural expansion."
    elif LTP_n < ltp_adequacy_threshold:
        action = "intervene_ltp"
        msg = "Structural adequacy LTP < 1; intervene at structure/demand layer."
    elif RLE_n < 1.0 - 1e-9:
        action = "intervene_rle"
        msg = "Retained fraction RLE < 1; intervene at transition/loss layer."
    else:
        action = "intervene_rsr"
        msg = "Reconstruction fidelity RSR < 1; intervene at RSR layer."

    return DiagnosticResult(state=state, action=action, message=msg)


def frequency_from_dt(dt: float) -> float:
    """f = 1 / ∆t (Hz)."""
    if dt <= 0:
        raise ValueError("∆t must be positive")
    return 1.0 / dt


def frequency_from_rpm(rpm: float) -> float:
    """f = RPM / 60 (Hz)."""
    if rpm <= 0:
        raise ValueError("RPM must be positive")
    return rpm / 60.0


def interface_efficiency_rsr(LTP_n: float, X: float) -> float:
    """
    RSR universal law: Interface Efficiency = LTP / X.
    X = number of systems meeting at a coupling. X > 1 distributes structural support.
    """
    if X <= 0:
        raise ValueError("X (coupling count) must be positive")
    return max(0.0, min(1.0, LTP_n / X))
