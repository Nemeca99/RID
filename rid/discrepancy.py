# ==========================================
# RID: Normalized discrepancy D(·,·) for RSR
# Source: RLE-LTP-RSR_Stability_Equation_Canonical_Spec.pdf
# RSR_n ≡ 1 − D(y_n, n_n), D range [0, 1]
# ==========================================

from typing import Callable, Union
import math


def discrepancy_l1(y: Union[float, list], n: Union[float, list]) -> float:
    """
    Normalized L1 discrepancy in [0, 1].
    Scalars: D = |y - n| / (|y| + |n| + 1e-12).
    Vectors: D = mean of element-wise normalized L1.
    """
    if isinstance(y, (int, float)) and isinstance(n, (int, float)):
        denom = abs(y) + abs(n) + 1e-12
        return min(1.0, abs(y - n) / denom)
    if hasattr(y, "__len__") and hasattr(n, "__len__"):
        if len(y) != len(n):
            return 1.0
        total = 0.0
        for a, b in zip(y, n):
            denom = abs(a) + abs(b) + 1e-12
            total += min(1.0, abs(a - b) / denom)
        return total / len(y)
    return 1.0


def discrepancy_l2(y: Union[float, list], n: Union[float, list]) -> float:
    """
    Normalized L2 discrepancy in [0, 1].
    Scalars: D = |y - n| / sqrt(y^2 + n^2 + 1e-12).
    Vectors: D = ||y - n||_2 / (||y||_2 + ||n||_2 + 1e-12), then clamp to [0,1].
    """
    if isinstance(y, (int, float)) and isinstance(n, (int, float)):
        denom = math.sqrt(y * y + n * n + 1e-12)
        return min(1.0, abs(y - n) / denom)
    if hasattr(y, "__len__") and hasattr(n, "__len__"):
        if len(y) != len(n):
            return 1.0
        diff_sq = sum((a - b) ** 2 for a, b in zip(y, n))
        norm_y = math.sqrt(sum(a * a for a in y)) + 1e-12
        norm_n = math.sqrt(sum(b * b for b in n)) + 1e-12
        denom = norm_y + norm_n
        return min(1.0, math.sqrt(diff_sq) / denom)
    return 1.0


def discrepancy_01(y: Union[float, list], n: Union[float, list]) -> float:
    """
    For values in [0, 1]: D = |y - n|. Simple and already normalized.
    Vectors: mean of element-wise |y_i - n_i|.
    """
    if isinstance(y, (int, float)) and isinstance(n, (int, float)):
        return min(1.0, abs(y - n))
    if hasattr(y, "__len__") and hasattr(n, "__len__"):
        if len(y) != len(n):
            return 1.0
        return sum(abs(a - b) for a, b in zip(y, n)) / len(y)
    return 1.0


# Type for pluggable discrepancy: (observable, reconstruction) -> [0, 1]
DiscrepancyFunc = Callable[[Union[float, list], Union[float, list]], float]
