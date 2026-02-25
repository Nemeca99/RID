# ==========================================
# RID: Law of Compressed State Dynamics (RLE Framework)
# Source: RLE_Axioms_Law_of_Compressed_State_Dynamics.pdf
# ==========================================
"""
Axiomatic structure underlying the Recursive Loss Equation (RLE).
Bounded observables arise from additive, combinatorial, and irreversible
internal system dynamics.
"""

from enum import Enum


class Axiom(Enum):
    """Five axioms of the Law of Compressed State Dynamics."""

    # Physical Irreversibility: entropy increases; dissipation/fatigue/degradation
    # cannot be undone by representation or normalization.
    PHYSICAL_IRREVERSIBILITY = "I"

    # Additive State Accretion: evolution is additive; each step adds a new
    # configuration; no state removed; history preserved.
    ADDITIVE_STATE_ACCRETION = "II"

    # Combinatorial Expansion: possible internal configurations grow
    # multiplicatively (exponentially or factorially with depth); real cost,
    # fragility, recovery complexity.
    COMBINATORIAL_EXPANSION = "III"

    # Compression by Normalization: systems use normalization (division) to
    # collapse combinatorial complexity into bounded observables; preserves
    # ratios, discards configurational detail.
    COMPRESSION_BY_NORMALIZATION = "IV"

    # Observational Invariance: distinct internal configurations may map to the
    # same observable; equality of observation ≠ equality of physical state.
    OBSERVATIONAL_INVARIANCE = "V"


# ---------------------------------------------------------------------------
# Core Equation: Recursive Loss Equation
# ---------------------------------------------------------------------------
# RLE_n = (E_{n+1} − U_n) / E_n , where 0 ≤ RLE_n ≤ 1
# Expresses system survivability as a bounded ratio. All exponential/factorial
# behavior lives in hidden internal state; the observable scalar stays bounded.
# ---------------------------------------------------------------------------


def rle_n(E_next: float, U_n: float, E_n: float) -> float:
    """
    Retained usable fraction across transition n → n+1.

    RLE_n = (E_{n+1} − U_n) / E_n

    Constraints (caller should enforce):
        E_n > 0
        0 ≤ U_n ≤ E_n
        E_next, U_n, E_n yield RLE_n in [0, 1]

    Returns:
        RLE_n in [0, 1] (clamped if inputs are out of range).
    """
    if E_n <= 0:
        raise ValueError("E_n must be positive")
    raw = (E_next - U_n) / E_n
    return max(0.0, min(1.0, raw))


def loss_fraction(RLE_n: float) -> float:
    """Derived loss fraction: Λ_n ≡ 1 − RLE_n."""
    return 1.0 - RLE_n


def invariant_preserving_factorization_identity(X: float, f: float) -> bool:
    """
    Law 1 E1.1: X = X * f * f^{-1}. Internal rearrangement without changing invariant.
    Formalizes compression/expansion freedom; multiple internal states map to same RLE.
    Returns True when identity holds (numerically, within float tolerance).
    """
    if f == 0:
        return False
    return abs(X - (X * f * (1.0 / f))) < 1e-12


def law_statement() -> str:
    """
    Law statement (from spec):
    A system may undergo exponential or factorial growth in internal
    configuration space while exhibiting stable bounded observables.
    The cost of depth is paid internally, not reported externally.
    Normalization preserves observability at the expense of hidden fragility.
    """
    return (
        "A system may undergo exponential or factorial growth in internal "
        "configuration space while exhibiting stable bounded observables. "
        "The cost of depth is paid internally, not reported externally. "
        "Normalization preserves observability at the expense of hidden fragility."
    )
