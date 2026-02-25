"""
stress_compare.py — GPU Stress Test + Real Telemetry RID Comparison
====================================================================
Pushes the RTX 3060 Ti to max GPU load using PyTorch CUDA matrix multiplications,
while simultaneously reading live HWiNFO telemetry and comparing three Λ modes.

This is the definitive empirical answer to:
"If we replaced Λ_floor=1/VRAM with real temperature telemetry, does
 the structure of the physics layer change?"

HOW IT WORKS:
  Phase 0: Idle baseline — read telemetry at rest
  Phase 1: Mild load — 1024×1024 matrix ops at 50% intensity
  Phase 2: Heavy load — 4096×4096 ops (GPU ~80–90%)
  Phase 3: Max stress — 8192×8192 ops (GPU ~100%)
  Phase 4: Cool-down — stop GPU work, read recovery

At each phase: read telemetry → compute all 3 Λ modes → compare F_realized
→ record when modes agree/disagree on kernel_descent

Run:  L:\.venv\Scripts\python.exe stress_compare.py
"""

import sys, os, time, threading, csv, math
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    HAS_CUDA = False

from hw_telemetry import read_latest, read_all_rows, GPUTelemetry
from real_physics import compute_all_modes, compare_modes

CSV_PATH = Path(__file__).parent / "2_25_2026_test_1.CSV"

# ── RID state for each phase (using fixed cognitive workload parameters) ──────
RID_PARAMS = {
    # Simulates a language model mid-inference under different memory pressures
    "idle":   dict(s_n=0.98, ltp=1.0, rle=0.99, tokens=50.0),
    "mild":   dict(s_n=0.92, ltp=0.95, rle=0.95, tokens=200.0),
    "heavy":  dict(s_n=0.85, ltp=0.88, rle=0.90, tokens=600.0),
    "stress": dict(s_n=0.70, ltp=0.80, rle=0.82, tokens=1200.0),
}

# ═════════════════════════════════════════════════════════════════════════════
# GPU STRESS ENGINE
# ═════════════════════════════════════════════════════════════════════════════

_stop_flag = threading.Event()


def _gpu_stress_worker(matrix_size: int):
    """Runs continuous CUDA matrix multiplications to load GPU."""
    if not HAS_CUDA:
        return
    device = torch.device("cuda")
    # Allocate tensors and pin them
    a = torch.randn(matrix_size, matrix_size, device=device, dtype=torch.float32)
    b = torch.randn(matrix_size, matrix_size, device=device, dtype=torch.float32)
    while not _stop_flag.is_set():
        c = torch.matmul(a, b)
        # Prevent optimizer from eliding
        _ = c.sum().item()


def start_stress(matrix_size: int) -> threading.Thread:
    _stop_flag.clear()
    t = threading.Thread(target=_gpu_stress_worker, args=(matrix_size,), daemon=True)
    t.start()
    return t


def stop_stress():
    _stop_flag.set()
    time.sleep(0.5)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN COMPARISON LOOP
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class PhaseResult:
    phase: str
    matrix_size: int
    telemetry: GPUTelemetry
    rid: dict
    mode_A_lambda: float
    mode_B_lambda: float
    mode_C_lambda: float
    mode_A_force: float
    mode_B_force: float
    mode_C_force: float
    agree_on_descent: bool
    descents: tuple  # (A, B, C) True/False


PHASES = [
    ("idle",   0,    "No GPU work",                  5),
    ("mild",   1024, "Mild (1024² matmul)",           8),
    ("heavy",  4096, "Heavy (4096² matmul)",          10),
    ("stress", 8192, "MAX STRESS (8192² matmul)",     12),
    ("cool",   0,    "Cool-down (stress stopped)",    6),
]


def run_comparison():
    print("\n" + "=" * 90)
    print("  RID REAL HARDWARE TELEMETRY — STRUCTURAL INDEPENDENCE TEST")
    print("  RTX 3060 Ti 8GB | HWiNFO Live CSV")
    print("=" * 90)

    if HAS_CUDA:
        dev_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  CUDA Device: {dev_name}  ({vram:.1f}GB)")
    else:
        print("  WARNING: No CUDA — GPU stress disabled. Thermal data still valid.")
    print()

    results: List[PhaseResult] = []
    thread = None

    for phase_name, matrix_size, desc, wait_s in PHASES:
        # Start/stop GPU stress
        if matrix_size > 0 and HAS_CUDA:
            if thread:
                stop_stress()
            print(f"  [→] Launching {desc}...")
            thread = start_stress(matrix_size)
            time.sleep(3)  # let temps settle
        elif matrix_size == 0 and thread:
            stop_stress()
            thread = None
            time.sleep(2)

        # Wait for thermals to stabilize
        print(f"  [⏱] Recording {desc} for {wait_s}s...")
        time.sleep(wait_s)

        # Read latest telemetry
        tel = read_latest(CSV_PATH)
        rid = RID_PARAMS.get(phase_name, RID_PARAMS["stress"])

        # Compute all three modes
        modes = compute_all_modes(
            s_n=rid["s_n"], ltp=rid["ltp"], rle=rid["rle"],
            prompt_tokens=rid["tokens"], tel=tel
        )
        A, B, C = modes

        desc_A, desc_B, desc_C = A.kernel_descent, B.kernel_descent, C.kernel_descent
        agree = (desc_A == desc_B == desc_C)

        results.append(PhaseResult(
            phase=phase_name, matrix_size=matrix_size, telemetry=tel, rid=rid,
            mode_A_lambda=A.lambda_value, mode_B_lambda=B.lambda_value,
            mode_C_lambda=C.lambda_value,
            mode_A_force=A.realized_force, mode_B_force=B.realized_force,
            mode_C_force=C.realized_force,
            agree_on_descent=agree, descents=(desc_A, desc_B, desc_C),
        ))

        # Print live row
        print(f"  Phase {phase_name.upper():7s} | "
              f"T={tel.gpu_die_c:.0f}°C/{tel.gpu_hotspot_c:.0f}°C HS | "
              f"Pwr={tel.gpu_power_w:.0f}W ({tel.gpu_tdp_pct:.0f}%TDP) | "
              f"VRAM={tel.vram_used_mb:.0f}MB ({tel.vram_used_frac*100:.0f}%)")
        print(f"  S_n={rid['s_n']:.2f} | "
              f"λA={A.lambda_value:.4f}/F={A.realized_force:.3f}/{'↓' if desc_A else '✓'} | "
              f"λB={B.lambda_value:.4f}/F={B.realized_force:.3f}/{'↓' if desc_B else '✓'} | "
              f"λC={C.lambda_value:.4f}/F={C.realized_force:.3f}/{'↓' if desc_C else '✓'} | "
              f"AGREE={'YES' if agree else '⚠ NO'}")
        print()

    # Stop any remaining stress
    if thread:
        stop_stress()

    # ─── Final Analysis ───────────────────────────────────────────────────────
    print("=" * 90)
    print("  STRUCTURAL INDEPENDENCE ANALYSIS")
    print("=" * 90)

    # Did all three modes agree on descent at every phase?
    all_agree = all(r.agree_on_descent for r in results)

    # Range of λ values across all modes and phases
    all_lambdas_A = [r.mode_A_lambda for r in results]
    all_lambdas_B = [r.mode_B_lambda for r in results]
    all_lambdas_C = [r.mode_C_lambda for r in results]

    lambda_range_A = max(all_lambdas_A) - min(all_lambdas_A)
    lambda_range_B = max(all_lambdas_B) - min(all_lambdas_B)
    lambda_range_C = max(all_lambdas_C) - min(all_lambdas_C)

    print(f"\n  Λ_A (Proxy):  range = {min(all_lambdas_A):.4f}–{max(all_lambdas_A):.4f} (Δ={lambda_range_A:.4f}) — STATIC, no runtime variation")
    print(f"  Λ_B (Carnot): range = {min(all_lambdas_B):.4f}–{max(all_lambdas_B):.4f} (Δ={lambda_range_B:.4f}) — live temp ratio")
    print(f"  Λ_C (VRAM):   range = {min(all_lambdas_C):.4f}–{max(all_lambdas_C):.4f} (Δ={lambda_range_C:.4f}) — live memory pressure")

    print(f"\n  Descent agreement across all phases: {'ALL AGREE' if all_agree else 'DISAGREEMENT DETECTED'}")
    for r in results:
        tag = "✓" if r.agree_on_descent else "⚠"
        print(f"  {tag} {r.phase:8s}: A={'↓' if r.descents[0] else '✓'} B={'↓' if r.descents[1] else '✓'} C={'↓' if r.descents[2] else '✓'}")

    print("\n  ─── VERDICT ───")
    if lambda_range_B < 0.02 and lambda_range_C < 0.05:
        print("  B and C are also relatively stable at these load levels.")
        print("  The structure of the physics layer would NOT fundamentally change")
        print("  with real telemetry IF the system is running at moderate load.")
    else:
        print("  B (Carnot) and C (VRAM) vary significantly across stress phases.")
        print("  The proxy Λ_A is a fixed anchor that doesn't respond to hardware state.")

    if all_agree:
        print("\n  → PHYSICS LAYER IS STRUCTURALLY INDEPENDENT")
        print("    All three Λ mappings produce the same DESCENT DECISION at these RID values.")
        print("    The physics layer is an interpretive interface — S_n drives the structure.")
        print("    Swapping Λ changes absolute force numbers, NOT the stability topology.")
        print("\n    That said: real Carnot (Mode B) and VRAM fraction (Mode C) are")
        print("    RICHER signals — they reflect actual hardware state dynamically.")
        print("    The proxy is simpler and valid. Real telemetry is more informative.")
    else:
        print("\n  → MAPPING IS LOAD-BEARING FOR CALIBRATED THRESHOLDS")
        print("    Descent decisions differ between modes at some phases.")
        print("    Using real telemetry would change WHEN the system intervenes.")
        print("    Λ must be derived from measured quantities for precise control.")

    print("=" * 90)

    # Full S_n sweep at current thermal state
    print("\n  Running full S_n sweep [0.0→1.0] at current hardware state...")
    tel_now = read_latest(CSV_PATH)
    compare_modes(tel_now, tokens=200.0, ltp=1.0, rle=0.95)

    return results


if __name__ == "__main__":
    run_comparison()
