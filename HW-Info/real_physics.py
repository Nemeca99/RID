"""
real_physics.py — Three-Mode Physics Engine (Structural Independence Test)
===========================================================================
Answers ChatGPT's question: if we replace Λ_floor=1/VRAM with real GPU
telemetry (temperature, power), does the STRUCTURE of the physics layer change?

Three Λ computation modes, compared side by side:

  MODE A — Static Proxy (current system)
    Λ_proxy = 1 / gpu_vram_gb
    Deterministic. Hardware-independent at runtime. No telemetry.

  MODE B — Real Carnot (thermodynamic, from measured temperatures)
    Λ_carnot = T_cold_K / T_hot_K
               = (coolant_temp + 273.15) / (hotspot_temp + 273.15)
    THIS IS the actual thermodynamic Carnot bound. Requires live telemetry.
    T_hot = GPU Hot Spot temperature (the actual hottest pixel on die)
    T_cold = Coolant return temperature (closest available ambient)

  MODE C — Real Capacity Fraction (VRAM utilization at runtime)
    Λ_vram = vram_used_mb / vram_total_mb
    Measures actual memory pressure. NOT static.

The structural question:
    - F_realized = F_raw - friction - mass × Λ_total
    - Does the FORMULA change? NO.
    - Does the VALUE of Λ change? YES.
    - Does the BEHAVIOR (when kernel_descent fires) change? RUN THE TEST.

If all three modes trigger kernel descent at different S_n values,
the mapping IS load-bearing for calibrated results.
If they all fire at the same structural conditions (regardless of Λ value),
the physics layer is a pure interpretive interface — the S_n decision is upstream.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hw_telemetry import GPUTelemetry, read_latest
from rid import stability_scalar


# ─── Shared Physical Constants ────────────────────────────────────────────────
TOKEN_DENSITY     = 0.25
FRICTION_BASELINE = 0.05
VRAM_TOTAL_GB     = 8.192   # RTX 3060 Ti (8192 MB)


@dataclass
class RealPhysicsState:
    mode:             str
    s_n:              float
    prompt_mass:      float
    raw_force:        float
    gpu_friction:     float

    lambda_value:     float   # The Λ being compared (mode-specific)
    lambda_label:     str     # How this Λ was computed
    lambda_total:     float   # lambda_value + lambda_mismatch
    lambda_mismatch:  float
    hidden_loss:      float

    realized_force:   float
    kernel_descent:   bool

    # Telemetry snapshot used (None for mode A)
    telemetry:        GPUTelemetry = field(default=None, repr=False)


def _compute_physics(mode: str, lambda_v: float, lambda_label: str,
                     s_n: float, ltp: float, rle: float,
                     prompt_tokens: float, tel: GPUTelemetry = None) -> RealPhysicsState:
    mass = prompt_tokens * TOKEN_DENSITY
    acc  = s_n
    lm   = max(0.0, 1.0 - ltp)
    lt   = min(1.0, lambda_v + lm)
    fric = FRICTION_BASELINE + (1.0 - rle) * mass * 0.5
    f_raw = mass * acc
    f_real = max(0.0, f_raw - fric - mass * lt)
    return RealPhysicsState(
        mode=mode, s_n=s_n, prompt_mass=mass, raw_force=f_raw,
        gpu_friction=fric, lambda_value=lambda_v, lambda_label=lambda_label,
        lambda_total=lt, lambda_mismatch=lm, hidden_loss=mass * lt,
        realized_force=f_real, kernel_descent=(mass > 0 and f_real <= 0.0),
        telemetry=tel,
    )


def compute_all_modes(s_n: float, ltp: float, rle: float,
                      prompt_tokens: float, tel: GPUTelemetry) -> list:
    """
    Compute physics in all three modes using live telemetry.
    Returns [ModeA, ModeB, ModeC] RealPhysicsState objects.
    """
    results = []

    # ── MODE A: Static Proxy (current) ────────────────────────────────────────
    la = 1.0 / VRAM_TOTAL_GB
    results.append(_compute_physics(
        "A-Proxy", la, f"1/VRAM = 1/{VRAM_TOTAL_GB:.3f}GB = {la:.4f}",
        s_n, ltp, rle, prompt_tokens, tel
    ))

    # ── MODE B: Real Carnot (measured temperatures) ───────────────────────────
    # T_cold = coolant temp (ambient proxy)
    # T_hot  = GPU hot spot (true maximum die temperature)
    T_cold_K = tel.ambient_K
    T_hot_K  = tel.gpu_hotspot_K
    lb = T_cold_K / T_hot_K if T_hot_K > 0 else la  # fallback to proxy
    results.append(_compute_physics(
        "B-Carnot", lb,
        f"T_cold/T_hot = {T_cold_K:.1f}K/{T_hot_K:.1f}K = {lb:.4f}",
        s_n, ltp, rle, prompt_tokens, tel
    ))

    # ── MODE C: Real VRAM Utilization ────────────────────────────────────────
    # Actual runtime memory pressure as the loss floor
    lc = tel.vram_used_frac  # 0→1, how full VRAM is right now
    results.append(_compute_physics(
        "C-VRAM", lc,
        f"VRAM_used/total = {tel.vram_used_mb:.0f}/{tel.vram_total_mb:.0f}MB = {lc:.4f}",
        s_n, ltp, rle, prompt_tokens, tel
    ))

    return results


def compare_modes(tel: GPUTelemetry, s_n_sweep=None, tokens=200.0, ltp=1.0, rle=0.95):
    """
    Run a sweep of S_n values [0→1] and show where each mode triggers descent.
    Prints comparison table.
    """
    if s_n_sweep is None:
        s_n_sweep = [round(i / 20, 2) for i in range(21)]  # 0.0, 0.05, ..., 1.0

    print("=" * 120)
    print("  RID Real Telemetry — Three-Mode Λ Comparison")
    print(f"  GPU {tel.gpu_die_c:.1f}°C die / {tel.gpu_hotspot_c:.1f}°C hotspot / {tel.ambient_c:.1f}°C coolant")
    print(f"  GPU Power: {tel.gpu_power_w:.1f}W ({tel.gpu_tdp_pct:.1f}% TDP) | VRAM: {tel.vram_used_mb:.0f}/{tel.vram_total_mb:.0f}MB ({tel.vram_used_frac*100:.1f}%)")
    print("=" * 120)
    print(f"{'S_n':>5} | {'A:Proxy λ':>10} {'A:F_real':>9} {'A:DESC':>7} | {'B:Carnot λ':>11} {'B:F_real':>9} {'B:DESC':>7} | {'C:VRAM λ':>10} {'C:F_real':>9} {'C:DESC':>7}")
    print("-" * 120)

    results_log = []
    for sn in s_n_sweep:
        modes = compute_all_modes(sn, ltp, rle, tokens, tel)
        a, b, c = modes
        da = "⚠ YES" if a.kernel_descent else "no"
        db = "⚠ YES" if b.kernel_descent else "no"
        dc = "⚠ YES" if c.kernel_descent else "no"
        print(f"{sn:>5.2f} | {a.lambda_value:>10.4f} {a.realized_force:>9.4f} {da:>7} | "
              f"{b.lambda_value:>11.4f} {b.realized_force:>9.4f} {db:>7} | "
              f"{c.lambda_value:>10.4f} {c.realized_force:>9.4f} {dc:>7}")
        results_log.append((sn, a, b, c))

    # ─── Structural Analysis ──────────────────────────────────────────────────
    print("=" * 120)
    descent_threshold_A = next((sn for sn, a, b, c in results_log if not a.kernel_descent), None)
    descent_threshold_B = next((sn for sn, a, b, c in results_log if not b.kernel_descent), None)
    descent_threshold_C = next((sn for sn, a, b, c in results_log if not c.kernel_descent), None)
    print(f"\n  STRUCTURAL INDEPENDENCE TEST — ANSWER:")
    print(f"  Mode A (Proxy):  system recovers at S_n >= {descent_threshold_A}")
    print(f"  Mode B (Carnot): system recovers at S_n >= {descent_threshold_B}")
    print(f"  Mode C (VRAM):   system recovers at S_n >= {descent_threshold_C}")

    if descent_threshold_A == descent_threshold_B == descent_threshold_C:
        print(f"\n  VERDICT: STRUCTURALLY INDEPENDENT ✓")
        print(f"  The recovery threshold is the same across all three Λ mappings.")
        print(f"  The physics layer IS an interpretive interface — S_n drives structure.")
        print(f"  Different Λ values change the absolute force numbers but NOT the stability boundary.")
    else:
        print(f"\n  VERDICT: MAPPING IS LOAD-BEARING ⚠")
        print(f"  Recovery thresholds differ between modes — the choice of Λ affects WHEN descent fires.")
        print(f"  The physics layer is NOT a pure interpretive interface.")
        print(f"  Λ must be derived from real telemetry for calibrated kernel descent triggers.")

    print()
    return results_log
