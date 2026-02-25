"""
RID Framework — Master Verification Runner
==========================================
Runs all verification checks and the full test suite. Prints a combined
summary report. Use this to confirm the entire RID package is consistent.

Run: python verify/run_all.py
"""

import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

STEPS = [
    ("Formula Verifier (16 doc–code checks)",
     [PYTHON, "verify/verify_formulas.py"]),
    ("pytest: Core Formulas (20 tests)",
     [PYTHON, "-m", "pytest", "tests/test_formulas.py", "-v", "--tb=short"]),
    ("pytest: B1 Load Sweep",
     [PYTHON, "-m", "pytest", "tests/test_b1_load_sweep.py", "-v", "--tb=short"]),
    ("pytest: B5 Mismatch Descent",
     [PYTHON, "-m", "pytest", "tests/test_b5_mismatch.py", "-v", "--tb=short"]),
    ("pytest: B6 GPU Scaling",
     [PYTHON, "-m", "pytest", "tests/test_b6_gpu_scaling.py", "-v", "--tb=short"]),
    ("pytest: B7 RSR Physics Coupling",
     [PYTHON, "-m", "pytest", "tests/test_b7_rsr_physics.py", "-v", "--tb=short"]),
    ("pytest: B8 Isolation Comparison",
     [PYTHON, "-m", "pytest", "tests/test_b8_isolation.py", "-v", "--tb=short"]),
    ("pytest: Monotonicity Proofs",
     [PYTHON, "-m", "pytest", "tests/test_monotonicity.py", "-v", "--tb=short"]),
    ("pytest: Bounds & Invariants (2000 samples)",
     [PYTHON, "-m", "pytest", "tests/test_bounds.py", "-v", "--tb=short"]),
    ("pytest: FIDF Endurance (500 steps)",
     [PYTHON, "-m", "pytest", "tests/test_fidf_loop.py", "-v", "--tb=short"]),
    ("pytest: Physics Stress (10,000 samples)",
     [PYTHON, "-m", "pytest", "tests/test_physics_stress.py", "-v", "--tb=short"]),
]


def run_step(label, cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    ok = result.returncode == 0
    return ok, result.stdout + result.stderr


def main():
    SEP = "=" * 80
    print(SEP)
    print("  RID Complete — Master Verification Runner")
    print(SEP)

    passed_steps, failed_steps = [], []

    for label, cmd in STEPS:
        print(f"\n[→] {label}")
        ok, output = run_step(label, cmd)
        # Print last 10 lines
        lines = [l for l in output.strip().splitlines() if l.strip()]
        for line in lines[-10:]:
            print(f"    {line}")
        if ok:
            passed_steps.append(label)
            print(f"  [PASS] {label}")
        else:
            failed_steps.append(label)
            print(f"  [FAIL] {label}")

    print(f"\n{SEP}")
    print(f"  RESULTS: {len(passed_steps)} passed, {len(failed_steps)} failed")
    if failed_steps:
        print("  FAILED:")
        for f in failed_steps:
            print(f"    - {f}")
        print(SEP)
        sys.exit(1)
    print("  ALL CHECKS PASS — RID package is complete and consistent.")
    print(SEP)


if __name__ == "__main__":
    main()

