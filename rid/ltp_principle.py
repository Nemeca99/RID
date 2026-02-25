# ==========================================
# RID: Layer Transition Principle (LTP) — full axiom
# Source: (V2) The Layer Transition Principle (LTP).pdf
# ==========================================
"""
When and how a system must transition between levels of compression and precision
to remain valid, predictive, and controllable. Descent is mandatory when compressed
invariants fail, phase transitions are approached, or control assumptions break.
"""

from enum import Enum
from typing import List, Tuple


class DescentTrigger(Enum):
    """Mandatory triggers for descent to a lower layer (LTP Section 5)."""

    INVARIANT_STRAIN = "invariant_strain"
    # Observed behavior deviates from predictions despite nominal invariant values.

    CONTROL_FAILURE = "control_failure"
    # Adjustments at current layer no longer produce proportional/predictable effects.

    COST_ESCALATION_WITHOUT_BENEFIT = "cost_escalation"
    # Increasing effort/energy yields diminishing or negative returns at observable level.

    HIDDEN_COUPLING_EXPOSURE = "hidden_coupling"
    # Response reveals sensitivity to order, history, or internal interactions not at current layer.

    TEMPORAL_MISMATCH = "temporal_mismatch"
    # Response times exceed control or observation timescales assumed by current layer.

    PHASE_TRANSITION_ENCOUNTER = "phase_transition"
    # Behavior approaches or crosses a phase boundary without lower-layer structure represented.


def mandatory_descent_triggers() -> List[Tuple[DescentTrigger, str]]:
    """Return (trigger, short description) for all six mandatory descent conditions."""
    return [
        (DescentTrigger.INVARIANT_STRAIN, "Observed behavior deviates from predictions despite nominal invariants"),
        (DescentTrigger.CONTROL_FAILURE, "Adjustments at current layer no longer produce proportional effects"),
        (DescentTrigger.COST_ESCALATION_WITHOUT_BENEFIT, "Increasing effort yields diminishing or negative returns"),
        (DescentTrigger.HIDDEN_COUPLING_EXPOSURE, "Sensitivity to order, history, or internal interactions not represented"),
        (DescentTrigger.TEMPORAL_MISMATCH, "Response times exceed control/observation timescales"),
        (DescentTrigger.PHASE_TRANSITION_ENCOUNTER, "Approaching or crossing phase boundary without lower-layer representation"),
    ]


def compression_baseline_definition() -> str:
    """Compression baseline: bounded region where current layer's invariant remains valid without descent."""
    return (
        "The bounded region of conditions under which the current layer's invariant "
        "remains valid without requiring descent. Within the baseline: compressed "
        "representations are stable, perturbations propagate predictably, and "
        "higher-layer invariants (e.g., RLE) remain sufficient for control."
    )


def phase_transition_definition() -> str:
    """Phase transition: continuous variation in parameters produces discontinuous internal reconfiguration."""
    return (
        "When continuous variation in external parameters (pressure, temperature, load, "
        "flow, constraint) produces discontinuous internal reconfiguration. At phase "
        "boundaries: internal degrees of freedom multiply, state-space dimensionality "
        "expands abruptly, and many-to-one mappings between observables and internal "
        "states collapse. Phase transitions amplify hidden structure and invalidate "
        "compressed assumptions faster than any other mechanism."
    )


def phase_boundary_divergence_near(delta_x: float, delta_omega: float, omega_threshold: float = 1e6) -> bool:
    """
    Law 2 E2.1: Near phase boundary, lim_{delta_x -> 0} delta_Omega -> infinity.
    Omega = internal state-space size; x = control parameter.
    Returns True when delta_x is small and delta_omega is large (phase-boundary regime).
    """
    return delta_x < 1.0 and delta_omega >= omega_threshold


def cost_of_descent() -> List[str]:
    """Descent incurs irreducible cost; possible manifestations."""
    return [
        "increased computational complexity",
        "expanded state-space size",
        "increased energy expenditure",
        "increased measurement and control precision",
        "increased cognitive or organizational burden",
    ]


def asymmetry_of_layer_movement() -> str:
    """Ascent is lossy; descent is irreversible in cost even if recompression is possible."""
    return (
        "Ascent (compression): reduces representational size and cost by discarding "
        "internal detail; always possible but always lossy. Descent (expansion): reveals "
        "internal structure and increases precision; irreversible in incurred cost. "
        "Compression hides complexity; expansion exposes it."
    )


def invariance_preservation_rule() -> str:
    """Valid layer transitions must preserve the core invariant."""
    return (
        "Descent must not alter the RLE value. Ascent must not introduce behavior "
        "inconsistent with lower-layer structure. Violations indicate either an "
        "invalid descent or an incorrect invariant. Layer transitions change what "
        "is visible, not what is true."
    )


def canonical_statement() -> str:
    """Canonical statement of the Layer Transition Principle (LTP Section 11)."""
    return (
        "A system may be represented at multiple layers of compression. Higher layers "
        "minimize cost but obscure internal structure; lower layers expose structure "
        "at increasing cost. Descent is mandatory when compressed invariants fail, "
        "phase transitions are approached, or control assumptions break. The system "
        "itself remains invariant across all layers."
    )
