# ==========================================
# RID: Fourth Invariant Dimensionless Framework (FIDF)
# Source: Fourth Invariant Dimensionless Framework (FIDF).pdf
# Layers 0-3: Observer -> Stability Triangle -> Logic Gate -> For-Loop
# ==========================================

from dataclasses import dataclass, field
from typing import Callable, Optional

from .triangle import (
    stability_scalar,
    rsr_n,
    ltp_n,
    diagnostic_step,
    TriangleState,
    DiagnosticResult,
)
from .axioms import rle_n


@dataclass
class FIDFConfig:
    """Layer 0: time anchor. dt = sampling interval (refresh rate)."""
    dt: float = 1.0
    max_steps: Optional[int] = None  # None = run until external reset


@dataclass
class FIDFState:
    """Current state of the FIDF loop."""
    step: int = 0
    RSR_n: float = 1.0
    LTP_n: float = 1.0
    RLE_n: float = 1.0
    S_n: float = 1.0
    action: str = "continue"
    message: str = ""


def layer1_rsr_ltp_rle(
    y_n: float,
    recon_n: float,
    n_n: float,
    d_n: float,
    E_n: float,
    U_n: float,
    E_next: float,
) -> FIDFState:
    """
    Layer 1: Stability Triangle. Phase 1 RSR, Phase 2 LTP, Phase 3 RLE.
    Returns state with S_n = RSR_n * LTP_n * RLE_n.
    """
    RSR_n = rsr_n(y_n, recon_n)
    LTP_n = ltp_n(n_n, d_n)
    RLE_n = rle_n(E_next, U_n, E_n)
    S_n = stability_scalar(RSR_n, LTP_n, RLE_n)
    return FIDFState(RSR_n=RSR_n, LTP_n=LTP_n, RLE_n=RLE_n, S_n=S_n)


def layer2_logic_gate(state: FIDFState, step: int = 0) -> DiagnosticResult:
    """
    Layer 2: IF (S==1) GOTO RSR; ELSE IF (S<1) TRIGGER LTP_Descent, GOTO RSR;
    ELSE IF (External_Time_Reset) EXIT, GOTO Layer 0.
    """
    return diagnostic_step(
        state.RSR_n, state.LTP_n, state.RLE_n,
        step=step,
        rsr_low_threshold=0.9,
        ltp_adequacy_threshold=1.0,
    )


def run_fidf_loop(
    config: FIDFConfig,
    get_observable: Callable[[int], float],
    get_reconstruction: Callable[[int], float],
    get_support_demand: Callable[[int], tuple],
    get_capacity: Callable[[int], tuple],
    on_step: Optional[Callable[[int, FIDFState, DiagnosticResult], None]] = None,
    external_reset: Optional[Callable[[int], bool]] = None,
) -> FIDFState:
    """
    Layer 3: For-loop over RSR -> LTP -> RLE -> Logic Gate.

    get_observable(n) -> y_n
    get_reconstruction(n) -> reconstruction of prior state
    get_support_demand(n) -> (n_n, d_n)
    get_capacity(n) -> (E_n, U_n, E_next)
    on_step(n, state, diagnostic) called each step (optional).
    external_reset(n) -> True to exit and goto Layer 0 (optional).
    """
    import time
    state = FIDFState()
    n = 0
    while True:
        if config.max_steps is not None and n >= config.max_steps:
            break
        if external_reset and external_reset(n):
            break
        y_n = get_observable(n)
        recon_n = get_reconstruction(n)
        n_n, d_n = get_support_demand(n)
        E_n, U_n, E_next = get_capacity(n)
        state = layer1_rsr_ltp_rle(y_n, recon_n, n_n, d_n, E_n, U_n, E_next)
        state.step = n
        diag = layer2_logic_gate(state, step=n)
        state.action = diag.action
        state.message = diag.message
        if on_step:
            on_step(n, state, diag)
        if state.S_n >= 1.0 - 1e-9:
            n += 1
            continue
        if diag.action == "mandatory_descent":
            n += 1
            time.sleep(config.dt)
            continue
        n += 1
        time.sleep(config.dt)
    return state
