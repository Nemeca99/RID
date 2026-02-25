"""
RID — Test B6: GPU Hardware Scaling (Carnot Floor Comparison)
=============================================================
Same prompt across 4 GPU sizes. Proves Λ_carnot = T_c/T_h varies with hardware.

Run: pytest tests/test_b6_gpu_scaling.py -v -s
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rid.semantic_physics import UnifiedSemanticPhysics

GPU_CONFIGS = [
    ("RTX 3060 Ti / 3070", 8.0),
    ("RTX 4080",           16.0),
    ("RTX 4090 / A10",     24.0),
    ("H100 (80GB)",        80.0),
]

TOKEN_SIZES = [0, 50, 200, 600, 1200]
S_N = 0.95; RLE = 0.97; LTP = 1.0


def run_b6():
    results = {}
    print("=" * 100)
    print("  RID | Test B6: GPU Hardware Scaling")
    print("=" * 100)

    for gpu_name, vram_gb in GPU_CONFIGS:
        physics = UnifiedSemanticPhysics(hardware_capacity_gb=vram_gb, time_anchor_dt=1.0)
        rows = []
        carnot_floor = 1.0 / vram_gb
        print(f"\n  ┌── {gpu_name} ({vram_gb:.0f}GB, Λ_carnot={carnot_floor:.4f})")
        print(f"  {'Tokens':>7} | {'Mass':>8} | {'F_real':>8} | {'Efficiency':>10}")
        print(f"  {'-'*45}")

        for tokens in TOKEN_SIZES:
            ps = physics.compute(s_n=S_N, stm_load=0.0, ltp=LTP, rle=RLE,
                                 prompt_tokens=float(tokens))
            eff = f"{ps.realized_force/ps.raw_force*100:.1f}%" if ps.raw_force > 0 else "n/a"
            print(f"  {tokens:>7} | {ps.prompt_mass:>8.4f} | {ps.realized_force:>8.4f} | {eff:>10}")
            rows.append(dict(tokens=tokens, ps=ps, carnot=carnot_floor))

        results[gpu_name] = (vram_gb, rows)

    print("=" * 100)
    return results


def test_carnot_floor_inversely_proportional_to_vram():
    """Λ_carnot = 1/vram_gb — bigger GPU burns less minimum heat."""
    results = run_b6()
    prev_carnot = None
    for gpu_name, (vram_gb, rows) in results.items():
        carnot = rows[1]["ps"].lambda_carnot  # token > 0 row
        assert abs(carnot - 1.0 / vram_gb) < 1e-6, f"{gpu_name}: expected {1/vram_gb:.4f} got {carnot:.4f}"
        if prev_carnot is not None:
            assert carnot < prev_carnot, "Larger GPU should have smaller Carnot floor"
        prev_carnot = carnot


def test_larger_gpu_higher_efficiency():
    """Efficiency (realized/raw %) should increase with GPU VRAM."""
    results = run_b6()
    efficiencies = []
    for gpu_name, (vram_gb, rows) in results.items():
        # Use 1200-token row
        row_1200 = next(r for r in rows if r["tokens"] == 1200)
        ps = row_1200["ps"]
        eff = ps.realized_force / ps.raw_force
        efficiencies.append(eff)

    for i in range(1, len(efficiencies)):
        assert efficiencies[i] > efficiencies[i - 1], \
            f"Efficiency should increase with GPU size: {efficiencies[i-1]:.4f} → {efficiencies[i]:.4f}"


def test_realized_force_positive_across_gpus():
    """Realized force must stay > 0 at 1200 tokens with LTP=1.0."""
    results = run_b6()
    for gpu_name, (vram_gb, rows) in results.items():
        for row in rows:
            if row["tokens"] > 0:
                assert row["ps"].realized_force > 0, \
                    f"{gpu_name} at {row['tokens']} tokens: F_real ≤ 0"


if __name__ == "__main__":
    run_b6()
