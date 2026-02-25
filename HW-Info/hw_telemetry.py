"""
hw_telemetry.py — Live HWiNFO CSV Reader
=========================================
Reads the most recent row from the live HWiNFO CSV and returns
structured GPU telemetry.

HWiNFO appends a new row every polling interval (typically 1–5s).
We always read the LAST row to get current state.
"""

import csv
import os
from dataclasses import dataclass
from pathlib import Path

CSV_PATH = Path(__file__).parent / "2_25_2026_test_1.CSV"

# Column indices from scan (confirmed against header row 2025-02-25):
COL = {
    # ── GPU ───────────────────────────────────────────────────────────────────
    "GPU_TEMP_C":         340,   # GPU Temperature [°C]
    "GPU_HOTSPOT_C":      341,   # GPU Hot Spot Temperature [°C] ← T_hot for GPU Carnot
    "GPU_THERMAL_LIMIT":  342,   # GPU Thermal Limit [°C]
    "GPU_POWER_W":        350,   # GPU Power [W]
    "GPU_TDP_PCT":        385,   # Total GPU Power [% of TDP]
    "GPU_CORE_LOAD_PCT":  365,   # GPU Core Load [%]
    "GPU_MEM_LOAD_PCT":   369,   # GPU Memory Usage [%]
    "GPU_MEM_AVAIL_MB":   417,   # GPU Memory Available [MB]
    "GPU_MEM_ALLOC_MB":   418,   # GPU Memory Allocated [MB]
    "GPU_CLOCK_MHZ":      360,   # GPU Clock [MHz]
    "GPU_EFF_CLOCK_MHZ":  363,   # GPU Effective Clock [MHz]

    # ── CPU ───────────────────────────────────────────────────────────────────
    # For the liquid-cooled CPU (AIO), coolant is the true T_cold reservoir.
    # For the air-cooled GPU, coolant temp is used as a proxy for case ambient air.
    "COOLANT_TEMP_C":     336,   # AIO Coolant Temperature [°C]
    "CPU_CORE_AVG_C":     95,    # Core Temperatures (avg) [°C]
    "CPU_IA_CORES_C":     146,   # CPU IA Cores [°C]  ← T_hot for CPU Carnot
    "CPU_TJMAX_DIST_AVG": 104,   # Distance to TjMAX avg [°C]  (TjMAX - cpu_temp)
    "CPU_PACKAGE_W":      149,   # CPU Package Power [W]
    "CPU_IA_CORES_W":     150,   # IA Cores Power [W]
}

GPU_VRAM_TOTAL_MB  = 8192.0      # RTX 3060 Ti — fixed physical fact
CPU_TJMAX_C        = 100.0       # i7-11700F Rocket Lake TjMAX — verified from Distance-to-TjMAX
CPU_TDP_W          = 125.0       # i7-11700F base TDP


@dataclass
class GPUTelemetry:
    # Temperatures (Kelvin for Carnot math, Celsius stored too)
    gpu_die_c:      float   # GPU die temperature °C
    gpu_hotspot_c:  float   # GPU hot spot °C   (the TRUE T_hot for Carnot)
    thermal_limit_c:float   # NV thermal throttle limit °C
    ambient_c:      float   # Case ambient air proxy °C (from coolant sensor)

    # Kelvin versions
    @property
    def gpu_hotspot_K(self): return self.gpu_hotspot_c + 273.15
    @property
    def ambient_K(self):     return self.ambient_c + 273.15
    @property
    def thermal_limit_K(self): return self.thermal_limit_c + 273.15

    # Power
    gpu_power_w:    float   # Instantaneous board power draw
    gpu_tdp_pct:    float   # % of TDP consumed

    # Memory
    vram_alloc_mb:  float   # Currently allocated VRAM
    vram_avail_mb:  float   # Currently free VRAM
    vram_total_mb:  float   # Physical total (always 8192)

    @property
    def vram_used_mb(self): return self.vram_total_mb - self.vram_avail_mb
    @property
    def vram_used_frac(self): return self.vram_used_mb / self.vram_total_mb

    # Load
    gpu_core_load_pct: float
    gpu_mem_load_pct:  float
    gpu_clock_mhz:     float
    gpu_eff_clock_mhz: float


@dataclass
class CPUTelemetry:
    """CPU thermal state from HWiNFO.

    The i7-11700F has an AIO liquid cooler — the AIO makes this a
    genuine two-reservoir system: CPU die (T_hot) and coolant return (T_cold).
    This is the best Carnot analog in the system.
    """
    cpu_ia_c:       float   # CPU IA Cores temp °C  ← T_hot (compute silicon)
    cpu_core_avg_c: float   # Core average temp °C
    tjmax_dist_c:   float   # Distance to TjMAX °C (100°C - cpu_ia_c should match)
    coolant_c:      float   # AIO coolant return °C ← T_cold
    package_w:      float   # CPU Package Power [W]
    ia_cores_w:     float   # IA Cores Power [W]

    @property
    def cpu_ia_K(self):     return self.cpu_ia_c + 273.15
    @property
    def coolant_K(self):    return self.coolant_c + 273.15
    @property
    def tjmax_K(self):      return CPU_TJMAX_C + 273.15
    @property
    def thermal_headroom_c(self): return CPU_TJMAX_C - self.cpu_ia_c
    @property
    def load_fraction(self): return self.package_w / CPU_TDP_W


def _safe_float(val: str, default=0.0) -> float:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return default


def _row_to_gpu(row: list) -> GPUTelemetry:
    def g(col): return _safe_float(row[COL[col]] if COL[col] < len(row) else "0")
    return GPUTelemetry(
        gpu_die_c        = g("GPU_TEMP_C"),
        gpu_hotspot_c    = g("GPU_HOTSPOT_C"),
        thermal_limit_c  = g("GPU_THERMAL_LIMIT"),
        ambient_c        = g("COOLANT_TEMP_C"),
        gpu_power_w      = g("GPU_POWER_W"),
        gpu_tdp_pct      = g("GPU_TDP_PCT"),
        vram_alloc_mb    = g("GPU_MEM_ALLOC_MB"),
        vram_avail_mb    = g("GPU_MEM_AVAIL_MB"),
        vram_total_mb    = GPU_VRAM_TOTAL_MB,
        gpu_core_load_pct= g("GPU_CORE_LOAD_PCT"),
        gpu_mem_load_pct = g("GPU_MEM_LOAD_PCT"),
        gpu_clock_mhz    = g("GPU_CLOCK_MHZ"),
        gpu_eff_clock_mhz= g("GPU_EFF_CLOCK_MHZ"),
    )


def _row_to_cpu(row: list) -> CPUTelemetry:
    def g(col): return _safe_float(row[COL[col]] if COL[col] < len(row) else "0")
    return CPUTelemetry(
        cpu_ia_c       = g("CPU_IA_CORES_C"),
        cpu_core_avg_c = g("CPU_CORE_AVG_C"),
        tjmax_dist_c   = g("CPU_TJMAX_DIST_AVG"),
        coolant_c      = g("COOLANT_TEMP_C"),
        package_w      = g("CPU_PACKAGE_W"),
        ia_cores_w     = g("CPU_IA_CORES_W"),
    )


def _last_row(csv_path: Path) -> list[str]:
    last: list[str] = []
    with open(csv_path, encoding='latin-1') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if row:
                last = row
    if not last:
        raise RuntimeError("CSV is empty or header-only")
    return last


def read_latest(csv_path: Path = CSV_PATH) -> GPUTelemetry:
    """Read the most recent row — returns GPUTelemetry."""
    return _row_to_gpu(_last_row(csv_path))


def read_cpu_latest(csv_path: Path = CSV_PATH) -> CPUTelemetry:
    """Read the most recent row — returns CPUTelemetry."""
    return _row_to_cpu(_last_row(csv_path))


def read_all_rows(csv_path: Path = CSV_PATH, max_rows: int = 5000):
    """Read all data rows, return (GPUTelemetry, CPUTelemetry) tuple list."""
    rows = []
    col_max = max(COL.values())
    with open(csv_path, encoding='latin-1') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if not row or len(row) < col_max + 1:
                continue
            rows.append((_row_to_gpu(row), _row_to_cpu(row)))
            if len(rows) >= max_rows:
                break
    return rows


if __name__ == "__main__":
    gpu = read_latest()
    cpu = read_cpu_latest()

    print("── GPU ──────────────────────────────────────")
    print(f"  Die:         {gpu.gpu_die_c:.1f}°C")
    print(f"  Hot Spot:    {gpu.gpu_hotspot_c:.1f}°C  ({gpu.gpu_hotspot_K:.1f}K)  ← T_hot")
    print(f"  Ambient:     {gpu.ambient_c:.1f}°C  ({gpu.ambient_K:.1f}K)   ← T_cold (case air proxy)")
    print(f"  GPU Carnot:  {gpu.ambient_K/gpu.gpu_hotspot_K:.4f}  (T_cold/T_hot)")
    print(f"  Power:       {gpu.gpu_power_w:.1f}W  ({gpu.gpu_tdp_pct:.1f}% TDP)")
    print(f"  VRAM:        {gpu.vram_used_mb:.0f}/{gpu.vram_total_mb:.0f}MB  ({gpu.vram_used_frac*100:.1f}%)")

    print("\n── CPU (i7-11700F, AIO liquid) ──────────────")
    print(f"  IA Cores:    {cpu.cpu_ia_c:.1f}°C  ({cpu.cpu_ia_K:.1f}K)  ← T_hot")
    print(f"  Coolant:     {cpu.coolant_c:.1f}°C  ({cpu.coolant_K:.1f}K)  ← T_cold")
    print(f"  TjMAX dist:  {cpu.tjmax_dist_c:.1f}°C  headroom")
    print(f"  CPU Carnot:  {cpu.coolant_K/cpu.cpu_ia_K:.4f}  (T_cold/T_hot)")
    print(f"  Package:     {cpu.package_w:.1f}W  ({cpu.load_fraction*100:.1f}% TDP)")
    print(f"  IA Cores W:  {cpu.ia_cores_w:.1f}W")

