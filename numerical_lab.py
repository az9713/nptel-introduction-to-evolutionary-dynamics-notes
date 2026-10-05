"""Original teaching models, not a fit to biological measurements.

Moran time is measured in attempted birth/replacement events, including
self-loops. One nominal generation is N such events. Only standard-library
dependencies are needed. Run this file for a reproducible worked example.
"""

import json
import math
import numbers


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


def _real(value, name, minimum=None, strictly_positive=False):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if strictly_positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _moran_args(n, i, r):
    n = _integer(n, "n", 1)
    i = _integer(i, "i")
    if i > n:
        raise ValueError("i must not exceed n")
    r = _real(r, "r", strictly_positive=True)
    return n, i, r


def moran_transition(n, i, r=1.0):
    """Return (p_up, p_down, p_stay) in one attempted Moran event.

    Haploid fixed population; no mutation; constant mutant/resident fitness r.
    The parent and replacement target are sampled independently, so the parent
    may replace itself. States 0 and n are absorbing.
    """
    n, i, r = _moran_args(n, i, r)
    if i == 0 or i == n:
        return 0.0, 0.0, 1.0
    if r >= 1:
        parent_mutant = i / (i + (n - i) / r)
        parent_resident = ((n - i) / r) / (i + (n - i) / r)
    else:
        parent_mutant = r * i / (r * i + n - i)
        parent_resident = (n - i) / (r * i + n - i)
    up = parent_mutant * ((n - i) / n)
    down = parent_resident * (i / n)
    return up, down, max(0.0, 1.0 - up - down)


def fixation_probability(n, i, r=1.0):
    """Probability of reaching n before 0; stable around r=1 and extremes."""
    n, i, r = _moran_args(n, i, r)
    if i == 0:
        return 0.0
    if i == n:
        return 1.0
    if r == 1:
        return i / n
    log_r = math.log(r)
    if log_r > 0:
        return math.expm1(-i * log_r) / math.expm1(-n * log_r)
    a = -log_r
    return (math.exp(-(n - i) * a) * math.expm1(-i * a)
            / math.expm1(-n * a))


def mean_absorption_times(n, r=1.0):
    """Return E[tau | initial i] for i=0,...,n, in attempted events.

    Solve the tridiagonal backward equation in O(n) time and memory. Self-loops
    enter the diagonal p_up+p_down; removing them changes the time convention.
    Times are unconditional: either extinction or fixation ends the clock.
    """
    n, _, r = _moran_args(n, 0, r)
    if n == 1:
        return [0.0, 0.0]
    cprime, dprime = [], []
    for i in range(1, n):
        up, down, _ = moran_transition(n, i, r)
        diagonal = up + down
        pivot = diagonal if i == 1 else diagonal + down * cprime[-1]
        if pivot <= 0 or not math.isfinite(pivot):
            raise ArithmeticError("absorption system lost numerical precision")
        cprime.append(-up / pivot if i < n - 1 else 0.0)
        rhs = 1.0 if i == 1 else 1.0 + down * dprime[-1]
        dprime.append(rhs / pivot)
    result = [0.0] * (n + 1)
    for i in range(n - 1, 0, -1):
        result[i] = dprime[i - 1] - cprime[i - 1] * result[i + 1]
    return result


def exponential_growth(initial, rate, time):
    """X(t)=X(0) exp(rate*t). rate and time must use reciprocal units."""
    initial = _real(initial, "initial", minimum=0)
    rate = _real(rate, "rate")
    time = _real(time, "time", minimum=0)
    if initial == 0:
        return 0.0
    return math.exp(math.log(initial) + rate * time)


def logistic_growth(initial, rate, capacity, time):
    """Positive logistic growth, 0<=initial<=capacity; rate>=0, time>=0."""
    initial = _real(initial, "initial", minimum=0)
    rate = _real(rate, "rate", minimum=0)
    capacity = _real(capacity, "capacity", strictly_positive=True)
    time = _real(time, "time", minimum=0)
    if initial > capacity:
        raise ValueError("initial must not exceed capacity")
    if initial == 0:
        return 0.0
    if initial == capacity:
        return capacity
    log_odds = math.log(initial) - math.log(capacity - initial)
    log_odds += rate * time
    if log_odds >= 0:
        return capacity / (1 + math.exp(-log_odds))
    odds = math.exp(log_odds)
    return capacity * (odds / (1 + odds))


def selection_frequency(initial_frequency, rate_difference, time):
    """Two types growing exponentially: d(log odds)/dt=rate_difference.

    Frequency is dimensionless; the rate difference has reciprocal time units.
    This deterministic model has no sampling drift or finite-N absorption.
    """
    x = _real(initial_frequency, "initial_frequency", minimum=0)
    if x > 1:
        raise ValueError("initial_frequency must not exceed 1")
    delta = _real(rate_difference, "rate_difference")
    time = _real(time, "time", minimum=0)
    if x == 0 or x == 1:
        return x
    log_odds = math.log(x) - math.log1p(-x) + delta * time
    if log_odds >= 0:
        return 1 / (1 + math.exp(-log_odds))
    odds = math.exp(log_odds)
    return odds / (1 + odds)


def worked_example():
    """Synthetic case, chosen to make drift, selection and units inspectable."""
    n, i, r = 50, 1, 1.1
    selected = mean_absorption_times(n, r)[i]
    neutral = mean_absorption_times(n, 1.0)[i]
    return {
        "provenance": "original teaching construction; no measured data",
        "moran": {"n": n, "i": i, "r": r,
                  "transition": moran_transition(n, i, r),
                  "selected_fixation": fixation_probability(n, i, r),
                  "neutral_fixation": fixation_probability(n, i, 1.0),
                  "selected_mean_absorption_events": selected,
                  "neutral_mean_absorption_events": neutral,
                  "selected_nominal_generations": selected / n},
        "growth": {"time_hours": 10, "rate_per_hour": 0.3,
                   "initial_cells": 100, "capacity_cells": 10000,
                   "exponential_cells": exponential_growth(100, 0.3, 10),
                   "logistic_cells": logistic_growth(100, 0.3, 10000, 10)},
        "selection": {"initial_frequency": 0.02,
                      "rate_difference_per_hour": 0.1,
                      "time_hours": 10,
                      "final_frequency": selection_frequency(0.02, 0.1, 10)}}


if __name__ == "__main__":
    print(json.dumps(worked_example(), indent=2, allow_nan=False))
