# ==========================================
# RID: System Efficiency Operations Layer (SEOL)
# Source: the SEOL (System Efficiency Operations Layer) framework.pdf
# ==========================================
"""
Operational state relative to peak potential. Healthy system: internal RLE chain
equals Input LTP. Target System Efficiency = 1.0. Efficiency cannot exceed Input LTP.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class SEOLProtocolStep:
    """Single step in the operational protocol."""
    name: str
    description: str


def operational_protocol() -> List[SEOLProtocolStep]:
    """
    SEOL diagnostic protocol when System Efficiency < 1.0.
    Locate -> Identify -> Investigate -> Stabilize.
    """
    return [
        SEOLProtocolStep("Locate", "If SEOL < 1.0, trace the multiplicative chain."),
        SEOLProtocolStep("Identify", "Find the specific coupling or pipe where the value is non-unitary."),
        SEOLProtocolStep("Investigate", "Use the X value to identify the specific manifold for human inspection."),
        SEOLProtocolStep("Stabilize", "Adjust the structure (LTP) or flow (RLE) to return the unit to 1.0."),
    ]


def voltage_law_summary() -> str:
    """Input LTP defines max potential; output LTP is realized work. Efficiency cannot exceed input quality."""
    return (
        "Input LTP defines the maximum possible potential (source). Output LTP is "
        "the final realized work after the internal chain. Efficiency can never "
        "exceed the quality of the Input LTP. You cannot engineer your way out of a dirty source."
    )


def effective_system_efficiency(S_n: float, LTP_input: float) -> float:
    """
    Voltage law: efficiency cannot exceed Input LTP (the source ceiling).
    Returns min(S_n, LTP_input) so you never report more than the source allows.
    """
    return min(max(0.0, min(1.0, S_n)), max(0.0, min(1.0, LTP_input)))


def voltage_law_violated(S_n: float, LTP_input: float) -> bool:
    """True if raw S_n would exceed Input LTP (shouldn't happen in a lawful system)."""
    return S_n > LTP_input


def interface_efficiency(LTP_n: float, X: float) -> float:
    """
    SEOL/RSR: Interface Efficiency = LTP / X.
    X = number of independent variables sharing a single coordinate of structural support.
    As X increases, support per variable decreases, increasing phase divergence risk.
    """
    if X <= 0:
        raise ValueError("X (coupling count) must be positive")
    return max(0.0, min(1.0, LTP_n / X))
