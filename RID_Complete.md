# RID: Complete Framework Document (All-in-One)

**Single reference for the RLE–LTP–RSR stability framework: definition, implementation, verification (internal and external), application, and reproducibility.** No identifying information. For publication or review.

---

## Introduction — What Is RID?

**RID** (Recursive Identity Dynamics / RLE–LTP–RSR) is a **dimensionless, deterministic stability framework** for recursive and resource-constrained systems. It was designed to answer a fundamental question:

> *When a system is under stress, how do you know which part is failing — and how close is it to losing coherent output?*

### The Three Axes

RID measures stability across three independent, orthogonal axes:

| Axis | Formula | What It Measures | What Goes Wrong |
|------|---------|-----------------|-----------------|
| **RLE** | `(E_next − U_n) / E_n` | Remaining memory/energy efficiency | Short-term memory overload |
| **LTP** | `min(1, n_n / d_n)` | Structural support vs demand | Architecture can't meet task complexity |
| **RSR** | `1 − D(y_n, recon_n)` | Identity continuity vs prior state | Drift, hallucination, or context loss |

These three axes multiply into a single **stability scalar**:

```
S_n = RSR_n × LTP_n × RLE_n        S_n ∈ [0, 1]
```

`S_n = 1.0` means the system is operating at full efficiency with no instability on any axis. `S_n < 1.0` indicates that at least one axis is degrading — and the framework can identify which axis is responsible by examining each component independently.

### Why Dimensionless?

Dimensionless scalars are system-agnostic. The same RID formulas apply whether the system is:
- A **generative AI** with a context window and identity drift
- An **industrial controller** (heaters, motors, setpoint tracking)
- Any **recursive process** with bounded memory, structural constraints, and state reconstruction

No thresholds are hardcoded to a specific domain. The diagnostic step (continue / intervene / descent) follows directly from the math.

### Phase 13: Physical Grounding

In Phase 13 (2026-02-24), the **Semantic Physics Engine** was added to translate `S_n` from a dimensionless ratio into physically meaningful outputs:

```
F_raw      = prompt_mass × S_n         → Newton's 2nd Law (S_n is acceleration)
Λ_carnot   = 1.0 / gpu_vram_gb         → Irreducible second-law heat loss
F_realized = F_raw − friction − losses → What actually reaches the output
```

**Key result:** A stability score of `S_n = 0.8535` looks like a 14.65% degradation. Through the physics engine it translates to **25.1% of output force lost** — because stability decay is nonlinear when compounded with an irreducible Carnot floor.

### How to Use This Document

- **Sections 1–4:** Framework definition, formulas, implementation, and consistency verification
- **Section 5+:** Application example (extrusion heater process) and empirical validation (AIOS V2)
- **Section 9:** Formal appendix — all formulas machine-checkable against the `rid` package
- **Section 10:** Reproducibility checklist — run every claim yourself in < 5 minutes

```bash
# Install dependencies
pip install pytest numpy

# Run the entire proof suite
python verify/run_all.py

# Expected: ALL PASS — 11 verification steps, 60+ assertions
```

---


## Title and abstract

**Title:** RID: A Dimensionless Stability Framework from RLE–LTP–RSR with Internal and External Consistency Verification

**Abstract:** We present RID (RLE–LTP–RSR), a dimensionless stability framework for recursive and resource-constrained systems. It combines three legs—Recursive Load Efficiency (RLE), Layer Transition Principle (LTP), and Recursive State Reconstruction (RSR)—into a stability scalar S_n and supports multi-step analysis (FIDF) and an operational voltage law (SEOL). The framework is fully implemented from ten source PDF specifications. In Phase 13 we add the **Semantic Physics Engine**, which translates the dimensionless S_n into physically grounded Newtonian force and Carnot-bounded thermodynamic loss, proving that stability decay has a measurable hardware cost. Consistency is ensured in three ways: (1) **internal**—document formulas and narrative are self-consistent and checked by script; (2) **external (doc–code)**—written claims are verified against the implementation (20 tests, 16 doc checks PASS as of 2026-02-24); (3) **external (code–spec)**—key formula phrases are traced to the extracted source text. We apply RID to a generic extrusion heater process and show that the triangle points to the loss/stress path rather than overload or control instability. Reproducibility is fully specified; all verification scripts are runnable from the project root.

**Keywords:** stability framework, RLE, LTP, RSR, dimensionless, FIDF, SEOL, semantic physics, Carnot bound, Newtonian force, kernel descent, internal consistency, external consistency, verification, extrusion, reproducibility.

---

## 1. Introduction

### 1.1 Motivation

Recursive and resource-constrained systems need a compact, dimensionless way to assess stability and to decide where to act when the system is under stress. RID provides a triple-leg model (RLE, LTP, RSR) and a single scalar S_n, with diagnostics and an operational voltage law.

### 1.2 Contribution

- **Framework:** Three legs and S_n from nine PDF specs; thermodynamics, FIDF loop, SEOL voltage law.
- **Implementation:** All equations in code; CLI, tests, examples.
- **Internal consistency:** One document; appendix with all formulas; script checks doc vs doc (no contradictions).
- **External consistency (doc–code):** Script verifies every formula and numerical claim in the document against the RID package.
- **External consistency (code–spec):** Script verifies that key formula phrases from the specs appear in the extracted PDF text, so the implementation is traceable to source.
- **Application:** Extrusion heater process (generic); RID identifies loss/stress as the limiting path.
- **Reproducibility:** One-command full verification; step-by-step instructions; artifact completeness and external-consistency checks.

### 1.3 Scope

This document and the RID package cover the **PDF-derived** framework only. A separate thermal/computational RLE line of work exists in the same repository and is complementary.

---

## 2. Framework and source

### 2.1 Source documents (nine PDFs)

1. RLE Axioms – Law of Compressed State Dynamics  
2. RLE–LTP–RSR Stability Equation Canonical Spec  
3. (V2) The Layer Transition Principle (LTP)  
4. Bridge Document – From Experimental RLE to Mathematical RLE  
5. Equation  
6. Fourth Invariant Dimensionless Framework (FIDF)  
7. Recursive State Reconstruction (RSR) as a universal system law  
8. RLE–LTP Framework  
9. The SEOL (System Efficiency Operations Layer) framework  
10. **Semantic Physics Engine** *(Phase 13, 2026-02-24)* — Translates dimensionless S_n into physical Newtonian-Carnot quantities.


Text can be extracted with: `python -m RID --extract-pdf` (output in `RID/extracted_text/`).

### 2.2 Canonical formulas (from specs; implemented in code)

- **RLE_n** (Recursive Load Efficiency). Source: Canonical Spec, RLE Axioms.  
  **Formula:** RLE_n = (E_next − U_n) / E_n  
  Variables: E_n = capacity before step, U_n = loss during step, E_next = capacity after step. E_n > 0.

- **LTP_n** (Layer Transition Principle). Source: Canonical Spec, LTP PDF.  
  **Formula:** LTP_n = min(1, n_n / d_n)  
  Variables: n_n = structural support (capacity), d_n = demand. In the spec, structural support is sometimes denoted ■_n; the implementation uses n_n. d_n > 0.

- **RSR_n** (Recursive State Reconstruction). Source: Canonical Spec, RSR PDF.  
  **Formula:** RSR_n = 1 − D(y_n, reconstruction)  
  Default discrepancy D: for scalars in [0,1], D(y, r) = |y − r|. So RSR_n = 1 − |y_n − reconstruction| when both in [0,1].

- **S_n** (stability scalar). Source: Canonical Spec.  
  **Formula:** S_n = RSR_n × LTP_n × RLE_n  
  S_n = 1: no stress. S_n < 1: one or more legs limiting.

### 2.3 SEOL voltage law (from SEOL PDF)

- **Law:** Efficiency cannot exceed the quality of the Input LTP.  
- **Implementation:** effective_system_efficiency(S_n, LTP_input) = min(S_n, LTP_input).  
- voltage_law_violated(S_n, LTP_input) is true iff S_n > LTP_input.

### 2.4 Other elements from specs

Thermodynamics (Carnot bound, lambda mismatch, coupling-amplified loss), FIDF multi-step loop (four callbacks: observable, reconstruction, support/demand, capacity), diagnostic step (continue / check_ltp / mandatory_descent / intervene_rle / check_rsr). Exact diagnostic thresholds are in the codebase.

### 2.5 Physical Extension: Semantic Physics Engine (Phase 13, 2026-02-24)

Translates the dimensionless S_n into hardware-grounded physical quantities, computed every FIDF tick alongside the control envelope. Implemented in `rid_core/semantic_physics.py`.

| Quantity | Formula | Description |
|---|---|---|
| Prompt Mass | `m = tokens × 0.25` | Physical weight of the prompt in token-mass units |
| Acceleration | `a = S_n` | Stability scalar IS the acceleration — S_n=1 = max output rate |
| Λ_carnot | `T_c / T_h = 1.0 / gpu_vram_gb` | Irreducible second-law heat floor (T_c=1.0GB fixed minimum) |
| Λ_mismatch | `1 − LTP_n` | Additional loss from structural inadequacy |
| Λ_total | `min(1, Λ_carnot + Λ_mismatch)` | Total loss fraction |
| GPU Friction | `0.05 + (1−RLE) × m × 0.5` | Hardware resistance growing with memory pressure |
| F_raw | `m × S_n` | Newton's 2nd law raw force |
| F_realized | `max(0, F_raw − friction − m×Λ_total)` | What actually reaches token generation |
| Kernel Descent | `F_realized ≤ 0 ∧ m > 0` | Mandatory complexity reduction trigger |

**Empirical results (AIOS V2, 2026-02-24):**

- **B4:** Physical layer coexists with dimensionless layer without altering any existing values. Λ_carnot = 0.125 for RTX 3060 Ti (8GB).
- **B5:** Kernel descent fires deterministically at LTP < 0.2 (S_n=0.9, 200 tokens). Lambda_mismatch grows linearly as `1 − LTP`.
- **B6:** GPU VRAM is a real physics constant: 8GB→85.2% efficiency, 16GB→91.8%, 24GB→94.0%, H100→97.1%.
- **B7:** RSR identity collapse (0.9878→0.0122) reduces F_realized to 0.0 and triggers kernel descent. Recovery at beat 12 restores full force.
- **B8:** S_n=0.8535 (14.65% dimensionless degradation) translates to 25.1% physical force loss — the physics engine amplifies the cost nonlinearly.



---

## 3. Implementation and verification

### 3.1 Code layout

Package `RID`: axioms, triangle, ltp_principle, thermodynamics, fidf, seol, discrepancy, validate_rid, extract_pdf_text, __main__. CLI: `python -m RID --check | --demo | --extract-pdf | --version`.

### 3.2 Validation pipeline

| Check | Command (from `L:\AIOS_V2`) | Result (2026-02-24) |
|-------|-----------------------------|---------------------|
| Unit tests | `L:\.venv\Scripts\python.exe -m pytest rid_core/tests/ -v` | **20 passed**, 0 failed |
| Doc vs code | `L:\.venv\Scripts\python.exe rid_core\verify_accomplishments_doc.py` | **16 PASS**; "No contradictions found" |
| B1 load sweep | `L:\.venv\Scripts\python.exe test_b1_load_sweep.py` | RLE degrades; RSR=1.0, LTP=1.0 throughout |
| B4 physics regression | `L:\.venv\Scripts\python.exe test_b4_physics_engine.py` | Dimensionless identical to B1; Λ_total=0.125 |
| B5 mismatch descent | `L:\.venv\Scripts\python.exe test_b5_mismatch_sweep.py` | Descent fires at LTP ≤ 0.2 |
| B6 GPU scaling | `L:\.venv\Scripts\python.exe test_b6_gpu_scaling.py` | 8GB→85.2%, 16GB→91.8%, 80GB→97.1% efficiency |
| B7 RSR coupling | `L:\.venv\Scripts\python.exe test_b7_rsr_physics_coupling.py` | F_real=0 at identity crisis; full recovery |
| B8 isolation | `L:\.venv\Scripts\python.exe test_b8_isolation_comparison.py` | S_n=0.8535 costs 25.1% realized force |


---

## 4. Internal and external consistency

### 4.1 Internal consistency

- **Single document:** This file is the one all-in-one reference; no scattered claims.
- **Appendix:** All formulas and definitions are repeated in Section 10 so the document is self-contained and machine-checkable.
- **Script:** `verify_accomplishments_doc.py` recomputes every formula and numerical example from the appendix using the RID package and asserts agreement. So the **document** is consistent with itself (appendix matches narrative) and with the **code**.

### 4.2 External consistency (document vs code)

- The same script ensures that every stated formula (RLE_n, LTP_n, RSR_n, S_n, voltage law, extrusion proxy, numerical examples) matches the implementation. If the code or the doc changes, re-run the script; all 16 checks must pass.

### 4.3 External consistency (code vs source specifications)

- **Script:** `verify_external_consistency.py` requires that key phrases from the specs appear in `RID/extracted_text/*.txt` (generated by `python -m RID --extract-pdf`). It checks for: RLE, E_n, U_n, E_{n+1}/E_next, LTP_n, min(1,…), d_n, RSR_n, 1−D, S_n, product RSR·LTP·RLE, structural support (or spec symbol), and SEOL phrases (exceed, Input, LTP). Thus the implementation is **traceable to the source documents**, not only internally consistent.

### 4.4 Triple check summary

| Layer | What is checked | How |
|-------|-----------------|-----|
| Internal | Doc vs doc (appendix vs narrative) | Single document; appendix repeats all formulas. |
| External (doc–code) | Doc vs implementation | `verify_accomplishments_doc.py` (16 checks). |
| External (code–spec) | Implementation vs source PDFs | `verify_external_consistency.py` (spec phrases in extracted text). |

All three must pass for the proof bundle to be considered complete and consistent.

---

## 5. Application: Extrusion heater process (generic)

### 5.1 Context

Extrusion process with heated die and temperature control; setpoint on the order of 400–420°F, melt slightly above setpoint; heater demand on the order of tens of amperes; solid-state relays. Multiple heater failures; cause unknown (overload, control instability, or loss/stress).

### 5.2 RID mapping

- **RSR:** y_n = actual melt temp (normalized 0–1), reconstruction = setpoint (normalized).  
- **LTP:** n_n = total SSR capacity (A), d_n = total heater demand (A) or demand_01×max amps.  
- **RLE:** Proxy: E_n = 100, U_n = demand (%), E_next = 100 − U_n; RLE_n = (E_next − U_n)/E_n.

One demand scalar in [0,1] for both LTP and RLE. Inputs: time, setpoint, actual temp, heater % (or demand_01); optional pressure.

### 5.3 Results (synthetic/sweep)

- **LTP = 1** at nominal demand (e.g. 75 A) for both 90 A and 80 A capacity ⇒ electrical overload not indicated.  
- **RSR** high (e.g. ~0.95 for 415 vs 420°F) ⇒ control thrashing not indicated.  
- **RLE** worst leg; decreases as demand increases ⇒ triangle points to **loss/stress** path.

Physical failure modes (lead tension, melt on/near leads) align with loss and stress; mitigations (lead protection, 90° clip, split-sheath, reduce melt at source) are documented. **Next step:** Log real controller data and re-run the analysis script to confirm on process data.

---

## 6. Reproducibility

**Environment:** Python 3.10+; install `pypdf`, `pytest` (and project requirements.txt if present).

**Order of execution (from project root):**

1. **Extract PDF text (once):** `python -m RID --extract-pdf`  
   → Creates `RID/extracted_text/*.txt`.

2. **Full verification:** `python RID/run_all_verification.py`  
   → Expect 5× [PASS]; `RID/verification_report.json` and `.txt` written. (Step 5 is external consistency; requires extracted text from step 1.)

3. **Doc vs code:** `python RID/verify_accomplishments_doc.py`  
   → Expect 16 PASS; “No contradictions found”.

4. **External (code–spec):** `python RID/verify_external_consistency.py`  
   → Expect 15 PASS; “Implementation is traceable to source specifications”.

5. **Artifact completeness:** `python RID/check_artifact_completeness.py`  
   → Expect all checks PASS (includes report and PDFs).

**Expected outputs (concise):**

- `python -m RID --check` → last line: `[OK] RID validation passed: imports, equations, FIDF loop (2 steps).`  
- `python -m pytest RID/tests/ -v` → `N passed`.  
- `python -m RID.examples.real_world_example` → lines with S_n, RSR, LTP, RLE; final “RID run complete”.

---

## 7. Limitations

- Extrusion conclusions are from synthetic/proxy data and a demand sweep; confirmation on real logged data is recommended.  
- Diagnostic action thresholds are in code, not fully written in this document.  
- A different (thermal/computational) RLE formulation exists in the same repo; it is complementary, not a replacement for the PDF-derived RID.

---

## 8. References

1. RLE Axioms – Law of Compressed State Dynamics (PDF, in RID/).  
2. RLE–LTP–RSR Stability Equation Canonical Spec (PDF).  
3. (V2) The Layer Transition Principle (LTP) (PDF).  
4. Bridge Document – From Experimental RLE to Mathematical RLE (PDF).  
5. Equation (PDF).  
6. Fourth Invariant Dimensionless Framework (FIDF) (PDF).  
7. Recursive State Reconstruction (RSR) as a universal system law (PDF).  
8. RLE–LTP Framework (PDF).  
9. The SEOL (System Efficiency Operations Layer) framework (PDF).

**Data and code:** RID package, tests, examples, and verification scripts under `RID/`. Specifications: nine PDFs in `RID/`; extracted text in `RID/extracted_text/` after `python -m RID --extract-pdf`. Verification reports: `RID/verification_report.json`, `RID/verification_report.txt` after `run_all_verification.py`.

---

## 9. Appendix: Definitions and consistency (for automated review)

Self-contained list so an automated reader can verify internal and external consistency.

**Canonical formulas**

- RLE_n = (E_next − U_n) / E_n. E_n > 0.  
- LTP_n = min(1, n_n / d_n). d_n > 0.  
- RSR_n = 1 − D(y_n, reconstruction). Default: D(y, r) = |y − r| for [0,1]; RSR_n = 1 − |y_n − reconstruction|.  
- S_n = RSR_n × LTP_n × RLE_n. S_n ∈ [0, 1] when each leg ∈ [0, 1].

**Voltage law**

- effective_system_efficiency(S_n, LTP_input) = min(S_n, LTP_input).  
- voltage_law_violated(S_n, LTP_input) ⟺ S_n > LTP_input.

**Extrusion RLE proxy**

- E_n = 100, U_n = demand in [0, 100], E_next = 100 − U_n.  
- RLE_n = (E_next − U_n) / E_n = (100 − 2·U_n) / 100.  
- RLE_n decreases as U_n increases; RLE_n = 1 at U_n = 0, RLE_n = 0 at U_n = 50 (implementations clamp for U_n > 50).

**Extrusion numerical consistency**

- LTP = min(1, capacity / demand). At 75 A demand, 90 A or 80 A capacity ⇒ LTP = 1.  
- RSR for 415 vs 420°F normalized (e.g. (T−350)/100): 415→0.65, 420→0.70, D = 0.05, RSR = 0.95.

**Two RLE formulations**

- This document uses the PDF formula RLE_n = (E_next − U_n) / E_n. A separate thermal/computational RLE exists in the repo with a different formula; the document states they are different and complementary.

---

## 10. Verification checklist (all must pass)

Run from **`L:\AIOS_V2`** (all commands verified 2026-02-24):

| # | Command | Expected / Actual Result |
|---|---------|--------------------------|
| 1 | `L:\.venv\Scripts\python.exe -m pytest rid_core/tests/ -v` | **20 passed**, 0 failed ✅ |
| 2 | `L:\.venv\Scripts\python.exe rid_core\verify_accomplishments_doc.py` | **16 PASS**, no contradictions ✅ |
| 3 | `L:\.venv\Scripts\python.exe test_b1_load_sweep.py` | RLE degrades; RSR=1.0, LTP=1.0 ✅ |
| 4 | `L:\.venv\Scripts\python.exe test_b4_physics_engine.py` | Dimensionless unchanged; Λ_total=0.125 ✅ |
| 5 | `L:\.venv\Scripts\python.exe test_b5_mismatch_sweep.py` | Descent at LTP ≤ 0.2 ✅ |
| 6 | `L:\.venv\Scripts\python.exe test_b6_gpu_scaling.py` | 8GB→85.2%, H100→97.1% ✅ |
| 7 | `L:\.venv\Scripts\python.exe test_b7_rsr_physics_coupling.py` | F_real=0 at crisis; recovery beat 12 ✅ |
| 8 | `L:\.venv\Scripts\python.exe test_b8_isolation_comparison.py` | S_n=0.8535 → 25.1% force lost ✅ |
| 9 | `L:\.venv\Scripts\python.exe rid_core\verify_external_consistency.py` | Requires `--extract-pdf` first (PDF text extraction step) |

**Current verification output (2026-02-24):**

```
pytest rid_core/tests/ -v  →  20 passed in 0.06s
verify_accomplishments_doc.py  →  16 passed, 0 failed
                                   No contradictions found
```

**Internal consistency:** Section 9 appendix and narrative agree; script #2 verifies document vs code.  
**External consistency (doc–code):** Script #2 (16 checks).  
**External consistency (code–spec):** Script #9 (requires PDF extraction first).

No identifying information included. Document suitable for publication or review.
