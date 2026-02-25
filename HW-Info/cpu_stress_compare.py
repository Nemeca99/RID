"""
cpu_stress_compare.py — CPU AIO Thermal Structural Independence Test
====================================================================
Answers the same ChatGPT question for the CPU:
"If we replaced Λ_floor=1/VRAM_capacity with real CPU temperature
 telemetry, does the structure of the physics layer change?"

The i7-11700F with AIO liquid cooling is a BETTER physical analog than
the GPU because the AIO genuinely forms a two-reservoir thermodynamic system:
  T_hot  = CPU die (IA Cores temp) — where computation generates heat
  T_cold = AIO coolant return — liquid in the loop, cold side of the heat pump

Three modes, same structure as GPU test:

  MODE A — Static Proxy: Λ = 1 / cpu_core_count = 1/8 = 0.125
            Mimics the VRAM proxy but for CPU core capacity.

  MODE B — Real CPU Carnot: Λ = T_cold_K / T_hot_K = coolant_K / cpu_ia_K
            THIS IS a genuine thermodynamic Carnot bound for the CPU.
            The AIO creates real T_hot (die) and T_cold (coolant loop).

  MODE C — CPU Load Fraction: Λ = package_watt / tdp_watt
            Normalized power draw as an efficiency floor.
            High power → high loss floor → lower realized force.

Run: L:\\.venv\\Scripts\\python.exe cpu_stress_compare.py
"""

import sys, time, threading
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from hw_telemetry import read_cpu_latest, CPUTelemetry, CPU_TJMAX_C, CPU_TDP_W, CSV_PATH

# ── CPU Hardware Constants ────────────────────────────────────────────────────
CPU_CORES       = 8       # i7-11700F: 8 physical cores
CPU_THREADS     = 16      # 16 logical threads (HT)
CPU_BASE_MHZ    = 2500.0  # 2.5 GHz base
CPU_BOOST_MHZ   = 4900.0  # ~4.9 GHz all-core boost

# Token density for CPU (CPU inference is slower, different mass scale)
TOKEN_DENSITY   = 0.25
FRICTION_BASE   = 0.05
DESCENT_THRESH  = 0.0

# ── RID parameters per stress phase ──────────────────────────────────────────
RID_PARAMS = {
    "idle":   dict(s_n=0.98, ltp=1.0,  rle=0.99, tokens=50.0),
    "mild":   dict(s_n=0.92, ltp=0.95, rle=0.95, tokens=200.0),
    "heavy":  dict(s_n=0.85, ltp=0.88, rle=0.90, tokens=600.0),
    "stress": dict(s_n=0.70, ltp=0.80, rle=0.82, tokens=1200.0),
}

# ═════════════════════════════════════════════════════════════════════════════
# CPU STRESS ENGINE (numpy, all cores)
# ═════════════════════════════════════════════════════════════════════════════

_stop_flag = threading.Event()


def _cpu_stress_worker(matrix_size: int, n_threads: int):
    """Runs numpy matmul under all cores to heat the die."""
    # numpy will use all available BLAS threads
    a = np.random.randn(matrix_size, matrix_size).astype(np.float32)
    b = np.random.randn(matrix_size, matrix_size).astype(np.float32)
    while not _stop_flag.is_set():
        c = np.matmul(a, b)
        _ = float(c.sum())   # prevent optimizer from eliding


def start_cpu_stress(matrix_size: int, n_threads: int = 4) -> list:
    _stop_flag.clear()
    threads = []
    for _ in range(n_threads):
        t = threading.Thread(target=_cpu_stress_worker,
                             args=(matrix_size, n_threads), daemon=True)
        t.start()
        threads.append(t)
    return threads


def stop_cpu_stress():
    _stop_flag.set()
    time.sleep(0.5)


# ═════════════════════════════════════════════════════════════════════════════
# THREE-MODE PHYSICS ENGINE (CPU version)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class CPUPhysicsResult:
    mode:            str
    lambda_value:    float
    lambda_label:    str
    lambda_mismatch: float
    lambda_total:    float
    raw_force:       float
    realized_force:  float
    kernel_descent:  bool


def _compute(mode, lv, label, s_n, ltp, rle, tokens):
    mass  = tokens * TOKEN_DENSITY
    lm    = max(0.0, 1.0 - ltp)
    lt    = min(1.0, lv + lm)
    fric  = FRICTION_BASE + (1.0 - rle) * mass * 0.5
    f_raw = mass * s_n
    f_r   = max(0.0, f_raw - fric - mass * lt)
    return CPUPhysicsResult(mode, lv, label, lm, lt, f_raw, f_r,
                            mass > 0 and f_r <= DESCENT_THRESH)


def compute_cpu_modes(cpu: CPUTelemetry, s_n, ltp, rle, tokens) -> tuple:
    # Mode A: Static proxy — 1/core_count
    la = 1.0 / CPU_CORES
    A = _compute("A-Proxy",  la, f"1/{CPU_CORES}cores={la:.4f}", s_n, ltp, rle, tokens)

    # Mode B: Real CPU Carnot — coolant_K / cpu_ia_K (AIO two-reservoir system)
    lb = cpu.coolant_K / cpu.cpu_ia_K
    B = _compute("B-Carnot", lb,
                 f"coolant/die={cpu.coolant_K:.1f}K/{cpu.cpu_ia_K:.1f}K={lb:.4f}",
                 s_n, ltp, rle, tokens)

    # Mode C: CPU power fraction — package_W / TDP_W
    lc = min(1.0, max(0.0, cpu.package_w / CPU_TDP_W))
    C = _compute("C-Power",  lc,
                 f"pkg/TDP={cpu.package_w:.1f}/{CPU_TDP_W:.0f}W={lc:.4f}",
                 s_n, ltp, rle, tokens)

    return A, B, C


def sn_sweep(cpu: CPUTelemetry, tokens=200.0, ltp=1.0, rle=0.95):
    sweep = [round(i / 20, 2) for i in range(21)]
    print("=" * 120)
    print(f"  CPU Real Telemetry — Three-Mode Λ Comparison (i7-11700F, AIO Liquid)")
    print(f"  CPU IA Cores: {cpu.cpu_ia_c:.1f}°C ({cpu.cpu_ia_K:.1f}K) die / "
          f"Coolant: {cpu.coolant_c:.1f}°C ({cpu.coolant_K:.1f}K) AIO return")
    print(f"  Package Power: {cpu.package_w:.1f}W ({cpu.load_fraction*100:.1f}% TDP) | "
          f"Thermal headroom: {cpu.thermal_headroom_c:.1f}°C to TjMAX")
    print("=" * 120)
    print(f"{'S_n':>5} | {'A:Proxy λ':>10} {'A:F_real':>9} {'A:DSC':>6} | "
          f"{'B:Carnot λ':>11} {'B:F_real':>9} {'B:DSC':>6} | "
          f"{'C:Power λ':>10} {'C:F_real':>9} {'C:DSC':>6}")
    print("-" * 120)

    thresholds = {"A": None, "B": None, "C": None}
    for sn in sweep:
        A, B, C = compute_cpu_modes(cpu, sn, ltp, rle, tokens)
        da, db, dc = A.kernel_descent, B.kernel_descent, C.kernel_descent
        if not da and thresholds["A"] is None: thresholds["A"] = sn
        if not db and thresholds["B"] is None: thresholds["B"] = sn
        if not dc and thresholds["C"] is None: thresholds["C"] = sn
        print(f"{sn:>5.2f} | {A.lambda_value:>10.4f} {A.realized_force:>9.4f} "
              f"{'↓ YES' if da else '    no':>6} | "
              f"{B.lambda_value:>11.4f} {B.realized_force:>9.4f} "
              f"{'↓ YES' if db else '    no':>6} | "
              f"{C.lambda_value:>10.4f} {C.realized_force:>9.4f} "
              f"{'↓ YES' if dc else '    no':>6}")

    print("=" * 120)
    print(f"\n  Recovery threshold (first S_n with no descent):")
    print(f"  Mode A (Proxy 1/8):    S_n >= {thresholds['A']}")
    print(f"  Mode B (Real Carnot):  S_n >= {thresholds['B']}")
    print(f"  Mode C (Power/TDP):    S_n >= {thresholds['C']}")

    if thresholds["A"] == thresholds["B"] == thresholds["C"]:
        print("\n  VERDICT: STRUCTURALLY INDEPENDENT ✓")
    else:
        print("\n  VERDICT: MAPPING IS LOAD-BEARING ⚠")
        print("  CPU Carnot (AIO) changes WHEN and HOW HARD descent fires.")

    return thresholds


# ═════════════════════════════════════════════════════════════════════════════
# STRESS PHASES
# ═════════════════════════════════════════════════════════════════════════════

PHASES = [
    ("idle",   0,    "Idle — no load",                    5),
    ("mild",   512,  "Mild — 512² matmul ×4 threads",     8),
    ("heavy",  1024, "Heavy — 1024² matmul ×8 threads",   10),
    ("stress", 2048, "MAX — 2048² matmul ×16 threads",    12),
    ("cool",   0,    "Cool-down",                         6),
]


def run():
    print("\n" + "=" * 90)
    print("  CPU REAL HARDWARE TELEMETRY — STRUCTURAL INDEPENDENCE TEST")
    print("  Intel i7-11700F | AIO Liquid Cooler | HWiNFO Live CSV")
    print("  Stress: numpy matmul (fills all 8C/16T)")
    print("=" * 90)

    threads = []
    for phase_name, msize, desc, wait_s in PHASES:
        if msize > 0:
            stop_cpu_stress()
            n_t = 4 if msize <= 512 else (8 if msize <= 1024 else 16)
            print(f"  [→] {desc} ...")
            threads = start_cpu_stress(msize, n_t)
            time.sleep(3)
        elif threads:
            stop_cpu_stress()
            threads = []
            time.sleep(2)

        print(f"  [⏱] Recording {desc} for {wait_s}s...")
        time.sleep(wait_s)

        cpu = read_cpu_latest(CSV_PATH)
        rid = RID_PARAMS.get(phase_name, RID_PARAMS["stress"])
        A, B, C = compute_cpu_modes(cpu, rid["s_n"], rid["ltp"], rid["rle"], rid["tokens"])

        agree = A.kernel_descent == B.kernel_descent == C.kernel_descent
        print(f"  Phase {phase_name.upper():7s} | "
              f"T_hot={cpu.cpu_ia_c:.1f}°C ({cpu.cpu_ia_K:.1f}K) "
              f"T_cold={cpu.coolant_c:.1f}°C ({cpu.coolant_K:.1f}K) "
              f"λ_carnot={cpu.coolant_K/cpu.cpu_ia_K:.4f} | "
              f"Pwr={cpu.package_w:.1f}W ({cpu.load_fraction*100:.0f}%TDP)")
        print(f"  S_n={rid['s_n']:.2f} | "
              f"λA={A.lambda_value:.4f}/F={A.realized_force:.3f}/{'↓' if A.kernel_descent else '✓'} | "
              f"λB={B.lambda_value:.4f}/F={B.realized_force:.3f}/{'↓' if B.kernel_descent else '✓'} | "
              f"λC={C.lambda_value:.4f}/F={C.realized_force:.3f}/{'↓' if C.kernel_descent else '✓'} | "
              f"AGREE={'YES' if agree else '⚠ NO'}")
        print()

    stop_cpu_stress()

    # Full S_n sweep at current state
    print("\n  Full S_n sweep at current hardware state...")
    cpu_now = read_cpu_latest(CSV_PATH)
    sn_sweep(cpu_now)

    print("\n  NOTE: CPU with AIO is a GENUINE thermodynamic two-reservoir system.")
    print("  T_hot (die) and T_cold (coolant return) are measured temperatures.")
    print("  λ_B = T_cold/T_hot is here a REAL Carnot bound, not an analogy.")


if __name__ == "__main__":
    run()
