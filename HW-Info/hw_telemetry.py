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
    # GPU Die and Hot Spot
    "GPU_TEMP_C":         340,   # GPU Temperature [°C]
    "GPU_HOTSPOT_C":      341,   # GPU Hot Spot Temperature [°C]
    "GPU_THERMAL_LIMIT":  342,   # GPU Thermal Limit [°C]
    # Ambient proxy (coolant return = closest to ambient intake)
    "COOLANT_TEMP_C":     336,   # Coolant Temperature [°C]
    # Power
    "GPU_POWER_W":        350,   # GPU Power [W]
    "GPU_TDP_PCT":        385,   # Total GPU Power [% of TDP]
    # Load & Memory
    "GPU_CORE_LOAD_PCT":  365,   # GPU Core Load [%]
    "GPU_MEM_LOAD_PCT":   369,   # GPU Memory Usage [%]
    "GPU_MEM_AVAIL_MB":   417,   # GPU Memory Available [MB]
    "GPU_MEM_ALLOC_MB":   418,   # GPU Memory Allocated [MB]
    # Clock
    "GPU_CLOCK_MHZ":      360,   # GPU Clock [MHz]
    "GPU_EFF_CLOCK_MHZ":  363,   # GPU Effective Clock [MHz]
}

GPU_VRAM_TOTAL_MB = 8192.0       # RTX 3060 Ti — fixed physical fact


@dataclass
class GPUTelemetry:
    # Temperatures (Kelvin for Carnot math, Celsius stored too)
    gpu_die_c:      float   # GPU die temperature °C
    gpu_hotspot_c:  float   # GPU hot spot °C   (the TRUE T_hot for Carnot)
    thermal_limit_c:float   # NV thermal throttle limit °C
    ambient_c:      float   # Coolant/intake temp °C  (T_cold proxy)

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


def _safe_float(val: str, default=0.0) -> float:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return default


def read_latest(csv_path: Path = CSV_PATH) -> GPUTelemetry:
    """Read the most recent (last) row from the HWiNFO CSV."""
    last_row = None
    with open(csv_path, encoding='latin-1') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if row:
                last_row = row

    if last_row is None:
        raise RuntimeError("CSV is empty or header-only")

    def g(col_name):
        idx = COL[col_name]
        return _safe_float(last_row[idx] if idx < len(last_row) else "0")

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


def read_all_rows(csv_path: Path = CSV_PATH, max_rows: int = 5000):
    """Read all data rows, return list of GPUTelemetry objects."""
    rows = []
    with open(csv_path, encoding='latin-1') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if not row or len(row) < max(COL.values()) + 1:
                continue
            def g(col):
                return _safe_float(row[COL[col]])
            rows.append(GPUTelemetry(
                gpu_die_c         = g("GPU_TEMP_C"),
                gpu_hotspot_c     = g("GPU_HOTSPOT_C"),
                thermal_limit_c   = g("GPU_THERMAL_LIMIT"),
                ambient_c         = g("COOLANT_TEMP_C"),
                gpu_power_w       = g("GPU_POWER_W"),
                gpu_tdp_pct       = g("GPU_TDP_PCT"),
                vram_alloc_mb     = g("GPU_MEM_ALLOC_MB"),
                vram_avail_mb     = g("GPU_MEM_AVAIL_MB"),
                vram_total_mb     = GPU_VRAM_TOTAL_MB,
                gpu_core_load_pct = g("GPU_CORE_LOAD_PCT"),
                gpu_mem_load_pct  = g("GPU_MEM_LOAD_PCT"),
                gpu_clock_mhz     = g("GPU_CLOCK_MHZ"),
                gpu_eff_clock_mhz = g("GPU_EFF_CLOCK_MHZ"),
            ))
            if len(rows) >= max_rows:
                break
    return rows


if __name__ == "__main__":
    t = read_latest()
    print(f"GPU Die:        {t.gpu_die_c:.1f} °C  ({t.gpu_die_c+273.15:.1f} K)")
    print(f"GPU Hot Spot:   {t.gpu_hotspot_c:.1f} °C  ({t.gpu_hotspot_K:.1f} K)  ← T_hot")
    print(f"Ambient/Coolant:{t.ambient_c:.1f} °C  ({t.ambient_K:.1f} K)  ← T_cold")
    print(f"Thermal Limit:  {t.thermal_limit_c:.1f} °C")
    print(f"GPU Power:      {t.gpu_power_w:.1f} W  ({t.gpu_tdp_pct:.1f}% TDP)")
    print(f"VRAM Used/Total:{t.vram_used_mb:.0f}/{t.vram_total_mb:.0f} MB  ({t.vram_used_frac*100:.1f}%)")
    print(f"GPU Core Load:  {t.gpu_core_load_pct:.1f}%")
    print(f"GPU Clock:      {t.gpu_clock_mhz:.0f} MHz (eff: {t.gpu_eff_clock_mhz:.0f})")
