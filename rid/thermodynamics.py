# ==========================================
# RID: Thermodynamic reproduction (Bridge / Equation / RLE-LTP Framework)
# Lambda_min = T_c/T_h (Carnot); Lambda = Lambda_min + Lambda_mismatch
# ==========================================

from typing import List


def lambda_min_carnot(T_c: float, T_h: float) -> float:
    """
    Minimum loss fraction from second law (cyclic heat engine).
    Lambda_min = T_c / T_h. Lambda >= Lambda_min.
    """
    if T_h <= 0 or T_c < 0:
        raise ValueError("T_h must be positive, T_c non-negative")
    return T_c / T_h


def eta_max_carnot(T_c: float, T_h: float) -> float:
    """Carnot efficiency bound: eta <= 1 - T_c/T_h."""
    return 1.0 - lambda_min_carnot(T_c, T_h)


def lambda_mismatch(ell: float, d: float) -> float:
    """
    Additional loss when structural support cannot match compression demand.
    Lambda_mismatch = 1 - min(1, ell/d). From Bridge/Equation: loss appears when
    compression outpaces structure.
    """
    if d <= 0 or ell < 0:
        raise ValueError("d must be positive, ell non-negative")
    return 1.0 - min(1.0, ell / d)


def lambda_total(T_c: float, T_h: float, ell: float, d: float) -> float:
    """
    Total loss: Lambda = Lambda_min + Lambda_mismatch.
    Thermodynamics says minimum loss exists; LTP adds mismatch loss.
    """
    return min(1.0, lambda_min_carnot(T_c, T_h) + lambda_mismatch(ell, d))


def coupling_amplified_loss(lambdas: List[float]) -> float:
    """
    System-wide loss from coupled local losses (RLE-LTP Framework Law 3).
    Lambda_system = 1 - prod_i (1 - Lambda_i).
    """
    if not lambdas:
        return 0.0
    p = 1.0
    for lam in lambdas:
        p *= 1.0 - max(0.0, min(1.0, lam))
    return min(1.0, 1.0 - p)


def temporal_mismatch_condition(tau_response: float, tau_control: float) -> bool:
    """
    Law 4: Control mismatch condition. Instability from lag.
    Returns True when condition is violated (response slower than control).
    """
    return tau_response > tau_control


def cost_depth_factorial(k: int) -> float:
    """
    Law 5 E5.1: Factorial cost growth. Cost(k) proportional to k!.
    Explains exponential expense of deep stabilization; depth, combinatorics, energy cost.
    """
    if k < 0:
        raise ValueError("k must be non-negative")
    import math
    return float(math.factorial(k))
