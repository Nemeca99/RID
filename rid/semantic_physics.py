# ==========================================
# RID: Unified Semantic Physics Engine
# Source: Semantic physics engine.pdf
# ==========================================
"""
Translates the dimensionless RID framework (S_n) into physical
thermodynamic decay and Newtonian motion for localized hardware limits.

The dimensionless S_n tells you IF the system is stable.
The physics engine tells you HOW MUCH force the system can actually exert
through the hardware, bounded by Carnot-derived loss and GPU friction.

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
"""

import math
from dataclasses import dataclass
from typing import Optional

from .thermodynamics import lambda_min_carnot, lambda_mismatch, coupling_amplified_loss


# ─── Physical Constants ─────────────────────────────────────────────────────

DEFAULT_GPU_VRAM_GB = 8.0        # RTX 3060 Ti
DEFAULT_DT          = 1.0        # 1Hz FIDF heartbeat
TOKEN_DENSITY       = 0.25       # Mass per token (dimensionless density factor)
FRICTION_BASELINE   = 0.05       # Minimum friction even when LTP=1.0
DESCENT_THRESHOLD   = 0.0        # Realized force ≤ this → mandatory descent


@dataclass
class PhysicsState:
    """
    Physical outputs computed from dimensionless RID values.
    Produced every FIDF tick alongside the ControlEnvelope.
    """
    # Inputs (from FIDF)
    s_n:              float = 1.0
    prompt_mass:      float = 0.0
    acceleration:     float = 0.0

    # Thermodynamic
    lambda_carnot:    float = 0.0     # Minimum irreducible loss (second law)
    lambda_mismatch:  float = 0.0     # Structural mismatch loss (LTP-derived)
    lambda_total:     float = 0.0     # Combined loss fraction
    hidden_loss:      float = 0.0     # Energy converted to heat (prompt_mass × lambda_total)

    # Newtonian
    gpu_friction:     float = 0.0     # Hardware resistance opposing token generation
    raw_force:        float = 0.0     # F = mass × acceleration (unimpeded)
    realized_force:   float = 0.0     # F_realized = F_raw - friction - hidden_loss

    # Control
    kernel_descent:   bool  = False   # True when realized_force ≤ 0


class UnifiedSemanticPhysics:
    """
    Translates dimensionless RID scalars into physical quantities.

    hardware_capacity_gb: Physical GPU VRAM in GB (e.g. 8.0 for RTX 3060 Ti)
    time_anchor_dt:       FIDF heartbeat interval in seconds (1.0 = 1Hz)
    """

    def __init__(self, hardware_capacity_gb: float = DEFAULT_GPU_VRAM_GB,
                 time_anchor_dt: float = DEFAULT_DT):
        self.hw_cap    = hardware_capacity_gb
        self.dt        = time_anchor_dt

        # Carnot thermal reservoirs:
        # T_h (hot) = hardware capacity in GB (what the GPU CAN do)
        # T_c (cold) = fixed minimum viable compute floor (hardware-INDEPENDENT)
        #
        # T_c = 1.0 represents the irreducible minimum VRAM needed to run any inference
        # at all (~1GB floor for weights + KV cache overhead).
        # It does NOT scale with GPU size — a model needs ~1GB minimum on ANY GPU.
        #
        # This means Λ_carnot = T_c / T_h DOES depend on GPU:
        #   8GB  RTX 3060 Ti → 1.0/8.0  = 0.1250 (12.5% heat floor)
        #   16GB RTX 4080    → 1.0/16.0 = 0.0625 (6.25% heat floor)
        #   24GB RTX 4090    → 1.0/24.0 = 0.0417 (4.17% heat floor)
        #   80GB H100        → 1.0/80.0 = 0.0125 (1.25% heat floor)
        self.T_h = hardware_capacity_gb
        self.T_c = 1.0    # Fixed: minimum viable inference floor (~1GB equivalent)

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
        stm_load:       Current STM load (used as mass proxy)
        ltp:            Current LTP value (structural adequacy)
        rle:            Current RLE value (retained fraction)
        prompt_tokens:  Approximate token count of current prompt (0 = idle)

        Returns a PhysicsState with all physical quantities.
        """
        state = PhysicsState(s_n=s_n)

        # ── 1. Prompt Mass ───────────────────────────────────────────────
        # Mass = token count × density factor. Higher mass = harder to accelerate.
        # Idle (no prompt) has near-zero mass.
        effective_tokens = max(prompt_tokens, stm_load * 10.0)  # STM load as fallback
        state.prompt_mass = effective_tokens * TOKEN_DENSITY

        # ── 2. Acceleration ──────────────────────────────────────────────
        # S_n IS the acceleration scalar. Perfect stability = max acceleration.
        # S_n < 1 = reduced acceleration (system strain slows generation).
        state.acceleration = s_n

        # ── 3. Thermodynamic Loss (Carnot bound) ─────────────────────────
        # Lambda_carnot: irreducible minimum loss from second law
        state.lambda_carnot = lambda_min_carnot(self.T_c, self.T_h)

        # Lambda_mismatch: additional loss when LTP < 1 (structure can't
        # match demand). Uses n_n=ltp (normalized), d_n=1.0 (full demand).
        state.lambda_mismatch = lambda_mismatch(ltp, 1.0)

        # Total loss fraction (clamped to [0, 1])
        state.lambda_total = min(1.0, state.lambda_carnot + state.lambda_mismatch)

        # Hidden loss: energy converted to heat = mass × total loss fraction
        state.hidden_loss = state.prompt_mass * state.lambda_total

        # ── 4. GPU Friction ──────────────────────────────────────────────
        # Friction opposes motion. Higher load = more friction.
        # Base friction exists even at idle (hardware overhead).
        # RLE degradation increases friction (memory pressure = more work).
        rle_friction = (1.0 - rle) * state.prompt_mass * 0.5
        state.gpu_friction = FRICTION_BASELINE + rle_friction

        # ── 5. Newtonian Force ───────────────────────────────────────────
        # F = m × a (raw force the system is trying to push through the GPU)
        state.raw_force = state.prompt_mass * state.acceleration

        # F_realized = F_raw - friction - hidden_loss
        # This is what actually gets through to token generation.
        state.realized_force = max(0.0, state.raw_force - state.gpu_friction - state.hidden_loss)

        # ── 6. Kernel Descent Check ──────────────────────────────────────
        # If realized force is zero or negative, the system cannot produce
        # useful output. Mandatory descent: reduce complexity, shed load.
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
            f"  Realized Force  : {state.realized_force:.4f}",
            f"  Kernel Descent  : {'YES' if state.kernel_descent else 'no'}",
        ]
        return "\n".join(lines)
