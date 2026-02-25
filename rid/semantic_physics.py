# ==========================================
# RID: Unified Semantic Physics Engine
# Source: Semantic physics engine.pdf
# ==========================================
"""
Translates the dimensionless RID framework (S_n) into physical quantities
for localized hardware limits: Newtonian output force and a capacity-scaled
irreducible loss floor.

The dimensionless S_n tells you IF the system is stable.
The physics engine tells you HOW MUCH force the system can actually exert
through the hardware, after accounting for structural loss and friction.

                       ┌────────────────────────────────────────┐
                       │   Dimensionless Layer (existing)       │
                       │   S_n = RSR × LTP × RLE  ∈ [0, 1]     │
                       └──────────────┬─────────────────────────┘
                                      │
                       ┌──────────────▼─────────────────────────┐
                       │   Physical Layer (this module)          │
                       │   F_realized = F_raw - friction - loss  │
                       │   F_realized ≤ 0 → kernel descent      │
                       └────────────────────────────────────────┘

IMPORTANT — Epistemic Category of Λ_floor
------------------------------------------
Λ_floor = 1 / gpu_vram_gb  is a CAPACITY-SCALED IRREDUCIBLE LOSS FLOOR.

It is a structural invariant proxy: a deterministic, hardware-capacity-normalized
floor on minimum loss per inference step. Larger hardware → smaller irreducible
floor → higher realized force.

It is INSPIRED BY the functional form of the Carnot efficiency formula
(which uses T_c / T_h), but this is NOT a thermodynamic Carnot bound.
We are NOT using live thermal telemetry. We are NOT measuring GPU die
temperature or ambient temperature. The analogy operates at the form level:
a ratio of minimum to maximum capacity. The physical domain is hardware
memory capacity, not heat flow. These are different epistemic categories.

Summary:
  ✓ Capacity-scaled irreducible loss floor (structural invariant proxy)
  ✗ Thermodynamic Carnot bound derived from heat flow
"""

import math
from dataclasses import dataclass
from typing import Optional

from .thermodynamics import lambda_mismatch


# ─── Physical Constants ─────────────────────────────────────────────────────

DEFAULT_GPU_VRAM_GB = 8.0        # RTX 3060 Ti
DEFAULT_DT          = 1.0        # 1Hz FIDF heartbeat
TOKEN_DENSITY       = 0.25       # Mass per token (dimensionless density factor)
FRICTION_BASELINE   = 0.05       # Minimum friction even when LTP=1.0
DESCENT_THRESHOLD   = 0.0        # Realized force ≤ this → mandatory descent

# Capacity floor: the minimum VRAM (GB) required to run any inference at all.
# This is hardware-INDEPENDENT — a model needs ~1GB on ANY GPU (weights + KV cache).
# Kept as a named constant so the modeling decision is explicit and reviewable.
CAPACITY_FLOOR_GB   = 1.0


@dataclass
class PhysicsState:
    """
    Physical outputs computed from dimensionless RID values.
    Produced every FIDF tick alongside the ControlEnvelope.

    Note on lambda_floor:
        This is a capacity-scaled irreducible loss floor, NOT a Carnot thermal bound.
        lambda_floor = CAPACITY_FLOOR_GB / hardware_capacity_gb = 1 / vram_gb
        It encodes that smaller hardware carries proportionally higher minimum loss.
    """
    # Inputs (from FIDF)
    s_n:              float = 1.0
    prompt_mass:      float = 0.0
    acceleration:     float = 0.0

    # Loss accounting
    lambda_floor:     float = 0.0     # Capacity-scaled irreducible loss floor (structural proxy)
    lambda_mismatch:  float = 0.0     # Structural mismatch loss (LTP-derived)
    lambda_total:     float = 0.0     # Combined loss fraction
    hidden_loss:      float = 0.0     # Energy absorbed by loss: prompt_mass × lambda_total

    # Newtonian
    gpu_friction:     float = 0.0     # Hardware resistance opposing token generation
    raw_force:        float = 0.0     # F_raw = mass × acceleration (unimpeded)
    realized_force:   float = 0.0     # F_realized = F_raw - friction - hidden_loss

    # Control
    kernel_descent:   bool  = False   # True when realized_force ≤ 0 and mass > 0


class UnifiedSemanticPhysics:
    """
    Translates dimensionless RID scalars into physical quantities.

    hardware_capacity_gb: Physical GPU VRAM in GB (e.g. 8.0 for RTX 3060 Ti)
    time_anchor_dt:       FIDF heartbeat interval in seconds (1.0 = 1Hz)

    The capacity-scaled loss floor is computed once at init:
        lambda_floor = CAPACITY_FLOOR_GB / hardware_capacity_gb

    This is a STRUCTURAL INVARIANT PROXY — a hardware normalization floor —
    not a thermodynamic bound. See module docstring for the epistemic distinction.
    """

    def __init__(self, hardware_capacity_gb: float = DEFAULT_GPU_VRAM_GB,
                 time_anchor_dt: float = DEFAULT_DT):
        self.hw_cap  = hardware_capacity_gb
        self.dt      = time_anchor_dt

        # Capacity-scaled irreducible loss floor:
        #   lambda_floor = CAPACITY_FLOOR_GB / hardware_capacity_gb
        #   8GB  RTX 3060 Ti → 1/8  = 0.1250 (12.5% irreducible floor)
        #   16GB RTX 4080    → 1/16 = 0.0625 (6.25% floor)
        #   24GB RTX 4090    → 1/24 = 0.0417 (4.17% floor)
        #   80GB H100        → 1/80 = 0.0125 (1.25% floor)
        # Larger hardware = smaller floor = higher realized force at same S_n.
        self._lambda_floor = CAPACITY_FLOOR_GB / hardware_capacity_gb

    def compute(
        self,
        s_n:          float,
        stm_load:     float,
        ltp:          float,
        rle:          float,
        prompt_tokens: float = 0.0,
    ) -> PhysicsState:
        """
        Compute physical state from current dimensionless values.

        s_n:            Current stability scalar
        stm_load:       Current STM load fraction (used as prompt mass proxy)
        ltp:            Current LTP value (structural adequacy)
        rle:            Current RLE value (retained fraction)
        prompt_tokens:  Approximate token count of current prompt (0 = idle)

        Returns a PhysicsState with all physical quantities.
        """
        state = PhysicsState(s_n=s_n)

        # ── 1. Prompt Mass ───────────────────────────────────────────────
        # Mass = token count × density factor. Higher mass = harder to accelerate.
        effective_tokens = max(prompt_tokens, stm_load * 10.0)
        state.prompt_mass = effective_tokens * TOKEN_DENSITY

        # ── 2. Acceleration ──────────────────────────────────────────────
        # S_n IS the acceleration scalar. Perfect stability = max acceleration.
        state.acceleration = s_n

        # ── 3. Loss Accounting ───────────────────────────────────────────
        # lambda_floor: capacity-scaled irreducible loss floor (structural proxy).
        # NOT a Carnot thermal bound — see module docstring.
        state.lambda_floor = self._lambda_floor

        # lambda_mismatch: additional loss when LTP < 1 (structure can't
        # match demand). Uses n_n=ltp (normalized), d_n=1.0 (full demand).
        state.lambda_mismatch = lambda_mismatch(ltp, 1.0)

        # Total loss fraction (clamped to [0, 1])
        state.lambda_total = min(1.0, state.lambda_floor + state.lambda_mismatch)

        # Hidden loss: energy absorbed by structural and capacity losses
        state.hidden_loss = state.prompt_mass * state.lambda_total

        # ── 4. GPU Friction ──────────────────────────────────────────────
        # Friction opposes motion. Higher memory pressure (low RLE) = more friction.
        rle_friction = (1.0 - rle) * state.prompt_mass * 0.5
        state.gpu_friction = FRICTION_BASELINE + rle_friction

        # ── 5. Newtonian Force ───────────────────────────────────────────
        # F_raw = m × a (raw force before losses)
        state.raw_force = state.prompt_mass * state.acceleration

        # F_realized = F_raw - friction - hidden_loss
        state.realized_force = max(0.0, state.raw_force - state.gpu_friction - state.hidden_loss)

        # ── 6. Kernel Descent Check ──────────────────────────────────────
        if state.prompt_mass > 0 and state.realized_force <= DESCENT_THRESHOLD:
            state.kernel_descent = True

        return state

    def describe(self, state: PhysicsState) -> str:
        """Human-readable summary of the physical state."""
        lines = [
            f"  Prompt Mass     : {state.prompt_mass:.4f}",
            f"  Acceleration    : {state.acceleration:.4f} (= S_n)",
            f"  Raw Force       : {state.raw_force:.4f} (F = m × a)",
            f"  GPU Friction    : {state.gpu_friction:.4f}",
            f"  Hidden Loss     : {state.hidden_loss:.4f} (Λ={state.lambda_total:.4f})",
            f"  Λ_floor         : {state.lambda_floor:.4f} (capacity-scaled irreducible floor)",
            f"  Λ_mismatch      : {state.lambda_mismatch:.4f} (structural mismatch loss)",
            f"  Realized Force  : {state.realized_force:.4f}",
            f"  Kernel Descent  : {'YES' if state.kernel_descent else 'no'}",
        ]
        return "\n".join(lines)
