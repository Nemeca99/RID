# RID — Recursive Identity Dynamics

**A deterministic, dimensionless stability framework grounded in physics.**

> *"This is no longer conceptual scaffolding. It's a measurable stability control system."*
> — External Review, ChatGPT GPT-4o

---

## What Is RID?

RID (RLE–LTP–RSR) is a three-axis stability framework for recursive, resource-constrained systems. It produces a single **stability scalar** `S_n ∈ [0, 1]` from three independent, dimensionless ratios:

| Axis | Formula | What It Measures |
|------|---------|-----------------|
| **RLE** | `(E_next − U_n) / E_n` | Recursive Load Efficiency — remaining memory capacity |
| **LTP** | `min(1, n_n / d_n)` | Layer Transition Principle — structural support vs demand |
| **RSR** | `1 − D(y_n, recon_n)` | Recursive State Reconstruction — identity continuity |
| **S_n** | `RSR × LTP × RLE` | Master stability scalar |

When `S_n = 1.0` the system is stable. When `S_n < 1.0`, the failing axis is identified and an intervention is prescribed.

---

## Phase 13: Semantic Physics Engine

The latest addition translates dimensionless `S_n` into **physically grounded** Newtonian and thermodynamic quantities:

```
F_raw      = prompt_mass × S_n          (Newton's 2nd Law)
Λ_floor   = T_c / T_h = 1 / gpu_vram  (capacity loss floor — irreducible heat loss)
Λ_mismatch = 1 − LTP_n                  (additional loss from structural mismatch)
F_realized = max(0, F_raw − friction − mass × Λ_total)
```

**Key finding (B8):** `S_n = 0.8535` looks like a 14.65% degradation in the dimensionless view — but translates to **25.1% of realized hardware force lost** due to nonlinear compounding with the capacity floor.

---

## Package Structure

```
RID/
├── rid/                    Python package (10 modules)
│   ├── axioms.py           RLE formula
│   ├── triangle.py         LTP, RSR, S_n, diagnostic step
│   ├── discrepancy.py      D(y, r) implementations
│   ├── thermodynamics.py   Carnot, mismatch, coupling loss
│   ├── ltp_principle.py    LTP axioms, mandatory descent
│   ├── seol.py             SEOL voltage law
│   ├── fidf.py             FIDF multi-step loop
│   └── semantic_physics.py Phase 13 physics engine
├── tests/                  Full test suite (10 files, ~60+ assertions)
│   ├── test_formulas.py    20 core unit tests
│   ├── test_b1_load_sweep.py
│   ├── test_b5_mismatch.py       → kernel descent at LTP < 0.2
│   ├── test_b6_gpu_scaling.py    → capacity floor vs GPU VRAM
│   ├── test_b7_rsr_physics.py    → identity crisis → F_real = 0
│   ├── test_b8_isolation.py      → 3-section layer comparison
│   ├── test_monotonicity.py      → 300-point axis sweeps
│   ├── test_bounds.py            → 2,000 random-sample proofs
│   ├── test_fidf_loop.py         → 500-step endurance
│   └── test_physics_stress.py    → 10,000 Monte Carlo samples
├── verify/
│   ├── verify_formulas.py  16 doc-vs-code consistency checks
│   └── run_all.py          Master verification runner
├── pdfs/                   10 source specification PDFs
├── RID_Complete.md         Complete framework paper
├── AIOS_V2_VALIDATION.md   Empirical validation (AIOS V2 traces)
└── requirements.txt
```

---

## Quick Start

```bash
# Install
pip install pytest numpy

# Run the full verification suite
python verify/run_all.py

# Or run tests directly
pytest tests/ -v

# Or just the formula verifier
python verify/verify_formulas.py

# Launch the Streamlit SCADA Dashboard
L:\.venv\Scripts\streamlit run app.py
```

**Expected output:**
```
All 11 verification steps: PASS
pytest: 60+ assertions across 10 test files: all PASS
verify_formulas.py: 16/16 PASS — No contradictions found
```

---

## Empirical Results (AIOS V2, 2026-02-24)

| Test | Result |
|------|--------|
| B1: STM load sweep | RLE degrades linearly; RSR, LTP remain 1.0 — axis independence confirmed |
| B4: Physics regression | Dimensionless layer unchanged; Λ_floor = 0.125 (8GB GPU) |
| B5: Mismatch sweep | Kernel descent fires at LTP < 0.2 (deterministic threshold) |
| B6: GPU scaling | 8GB → 85.2% efficiency; H100 → 97.1% efficiency |
| B7: RSR crisis | F_realized = 0.0 at identity spike; full recovery by beat 12 |
| B8: Isolation comparison | S_n=0.8535 costs 25.1% realized force vs physical ceiling |

---

## Source Specifications

The framework derives from 10 source PDFs (in `pdfs/`):
1. RLE Axioms — Law of Compressed State Dynamics
2. RLE–LTP–RSR Stability Equation Canonical Spec
3. (V2) The Layer Transition Principle
4. Bridge Document — From Experimental to Mathematical RLE
5. Equation
6. Fourth Invariant Dimensionless Framework (FIDF)
7. Recursive State Reconstruction (RSR) as a Universal System Law
8. RLE–LTP Framework
9. SEOL (System Efficiency Operations Layer)
10. Semantic Physics Engine *(Phase 13)*

---

## Full Paper

See [`RID_Complete.md`](RID_Complete.md) for the complete framework reference including formal definitions, extrusion application, internal/external consistency verification, and full test results.

---

*No identifying information. For publication or technical review.*

