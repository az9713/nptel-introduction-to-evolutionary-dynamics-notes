"""Synthetic batch-growth examples; no experimental parameter estimates."""

from math import exp, isclose, log


def lagged_count(initial, rate, lag, time):
    """Count with a fixed lag then exponential growth, time in hours."""
    if initial <= 0 or rate < 0 or lag < 0 or time < 0:
        raise ValueError("Positive count and nonnegative rate/times required")
    return initial * exp(rate * max(0.0, time - lag))


def limiting_composition(a0, b0, ga, gb, capacity):
    """Shared-logistic limit from the unique cumulative exposure root."""
    if min(a0, b0, ga, gb) <= 0 or capacity <= a0 + b0:
        raise ValueError("Positive inputs and capacity above initial sum")
    lo = 0.0
    hi = log(capacity / min(a0, b0)) / min(ga, gb)
    for _ in range(100):
        mid = (lo + hi) / 2.0
        total = a0 * exp(ga * mid) + b0 * exp(gb * mid)
        if total < capacity:
            lo = mid
        else:
            hi = mid
    exposure = (lo + hi) / 2.0
    a = a0 * exp(ga * exposure)
    b = b0 * exp(gb * exposure)
    return exposure, a, b, b / (a + b)


def main():
    """Print the stated original teaching constructions."""
    for time in (4.0, 9.0, 12.0):
        a = lagged_count(100.0, 0.6, 1.0, time)
        b = lagged_count(100.0, 0.8, 3.0, time)
        print(f"t={time:4.1f} h: A={a:9.3f}, B={b:9.3f}, "
              f"x={b / (a + b):.6f}")
    z, a, b, x = limiting_composition(100, 100, 0.6, 0.8, 10000)
    print(f"shared limit: z={z:.6f} h, A={a:.3f}, B={b:.3f}, "
          f"x={x:.6f}")
    assert isclose(a + b, 10000, rel_tol=1e-12)
    assert isclose(log(b / 100), (0.8 / 0.6) * log(a / 100))


if __name__ == "__main__":
    main()
