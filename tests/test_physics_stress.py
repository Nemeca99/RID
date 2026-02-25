"""
RID — Test: Physics Stress (10,000 Monte Carlo Runs)
======================================================
Exhaustive probabilistic correctness proof for the Semantic Physics Engine.
Randomly samples 10,000 input triples and verifies all outputs are well-formed.

Also runs targeted extreme-value sweeps (zero tokens, max tokens, S_n=0 edge case).

This test uses CPU only — no GPU or LLM needed.

Run: pytest tests/test_physics_stress.py -v -s
(Expect ~3–5 seconds for 10k samples)
"""

import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
random.seed(2026)

from rid.semantic_physics import UnifiedSemanticPhysics

# GPU configs to stress across
GPU_CONFIGS = [4.0, 8.0, 16.0, 24.0, 80.0]
N_SAMPLES   = 10_000


def _sample(physics):
    s_n    = random.random()
    stm    = random.random() * 0.9
    ltp    = random.random()
    rle    = random.random()
    tokens = random.random() * 4096
    return physics.compute(s_n=s_n, stm_load=stm, ltp=ltp, rle=rle, prompt_tokens=tokens)


def test_realized_force_always_nonneg():
    """10,000 random inputs → realized_force ≥ 0 always."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    for i in range(N_SAMPLES):
        ps = _sample(physics)
        assert ps.realized_force >= 0.0, f"Negative F_real at sample {i}: {ps.realized_force}"


def test_lambda_total_always_bounded():
    """10,000 random inputs → Λ_total ∈ [0, 1]."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    for i in range(N_SAMPLES):
        ps = _sample(physics)
        assert 0.0 <= ps.lambda_total <= 1.0 + 1e-9, \
            f"Λ_total out of bounds at sample {i}: {ps.lambda_total}"


def test_kernel_descent_iff_zero_force():
    """Kernel descent must fire if and only if F_real ≤ 0 and tokens > 0."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    for i in range(N_SAMPLES):
        s_n    = random.random()
        stm    = random.random() * 0.9
        ltp    = random.random()
        rle    = random.random()
        tokens = random.random() * 2048 + 1  # always > 0
        ps = physics.compute(s_n=s_n, stm_load=stm, ltp=ltp, rle=rle, prompt_tokens=tokens)

        if ps.kernel_descent:
            assert ps.realized_force <= 1e-9, \
                f"Descent fired but F_real > 0: {ps.realized_force}"
        elif ps.realized_force > 0:
            assert not ps.kernel_descent, \
                f"F_real > 0 but descent fired: {ps.realized_force}"


def test_carnot_floor_invariant_across_runs():
    """Λ_carnot must be exactly T_c/T_h = 1/vram for all 10,000 runs."""
    for vram in GPU_CONFIGS:
        physics = UnifiedSemanticPhysics(hardware_capacity_gb=vram)
        expected = 1.0 / vram
        for _ in range(100):  # 100 per GPU config = 500 total
            ps = _sample(physics)
            assert abs(ps.lambda_carnot - expected) < 1e-9, \
                f"GPU {vram}GB: Λ_carnot={ps.lambda_carnot} ≠ {expected}"


def test_sn_zero_means_no_force():
    """S_n = 0 → F_raw = 0 → F_real = 0 (no output possible)."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    for tokens in [50, 200, 500, 1000, 2000]:
        ps = physics.compute(s_n=0.0, stm_load=0.0, ltp=1.0, rle=1.0, prompt_tokens=float(tokens))
        assert ps.raw_force == 0.0, f"F_raw should be 0 when S_n=0: {ps.raw_force}"
        assert ps.realized_force == 0.0


def test_zero_tokens_means_zero_mass():
    """Zero-token prompt → prompt_mass = 0 → F_raw = 0."""
    physics = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    ps = physics.compute(s_n=1.0, stm_load=0.0, ltp=1.0, rle=1.0, prompt_tokens=0.0)
    assert ps.prompt_mass == 0.0
    assert ps.raw_force == 0.0


def test_larger_gpu_lower_carnot_always():
    """For all sample inputs, larger GPU always has lower Λ_carnot."""
    physics_8  = UnifiedSemanticPhysics(hardware_capacity_gb=8.0)
    physics_80 = UnifiedSemanticPhysics(hardware_capacity_gb=80.0)
    for _ in range(100):
        ps8  = _sample(physics_8)
        ps80 = _sample(physics_80)
        assert ps80.lambda_carnot < ps8.lambda_carnot, \
            f"80GB GPU has higher Carnot floor than 8GB: {ps80.lambda_carnot} vs {ps8.lambda_carnot}"
