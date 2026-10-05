"""Original modifier race and locally matched adaptation curves."""
from math import isfinite, log1p, exp
from numbers import Real


def nonnegative(value, name):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or value < 0):
        raise ValueError(name + " must be finite and nonnegative")


def first_mutator_probability(frequency, multiplier):
    """Equal birth/establishment rates; fixed frequencies until first event."""
    nonnegative(frequency, "frequency")
    nonnegative(multiplier, "multiplier")
    if frequency > 1:
        raise ValueError("frequency must not exceed one")
    total = 1 - frequency + multiplier * frequency
    if total == 0:
        raise ValueError("No successful mutation supply")
    return multiplier * frequency / total


def matched_curves(time, slope=1e-5, exponent=0.1):
    """Return hyperbola and power law with equal first two derivatives at0."""
    nonnegative(time, "time")
    nonnegative(slope, "slope")
    if slope == 0:
        raise ValueError("slope must be positive")
    if (isinstance(exponent, bool) or not isinstance(exponent, Real)
            or not isfinite(exponent) or not 0 < exponent < 1):
        raise ValueError("exponent must lie strictly between zero and one")
    capacity = 2 * exponent / (1 - exponent)
    half_time = capacity / slope
    coefficient = slope / exponent
    hyperbola = 1 + capacity * time / (half_time + time)
    power = exp(exponent * log1p(coefficient * time))
    return hyperbola, power


def slowing_rate_solution(time, coefficient, penalty):
    """Solve dw/dt=coefficient*w**(-penalty), w(0)=1."""
    for value, name in ((time, "time"), (coefficient, "coefficient"),
                        (penalty, "penalty")):
        nonnegative(value, name)
    return exp(log1p((penalty + 1) * coefficient * time) / (penalty + 1))


def main():
    probability = first_mutator_probability(0.01, 100)
    print(f"mutator first-event probability {probability:.6f}")
    print("generation hyperbola power")
    for time in (0, 20000, 40000, 1000000):
        hyperbola, power = matched_curves(time)
        print(f"{time:10d} {hyperbola:.6f} {power:.6f}")
    print("These curves are original constructions, not fitted LTEE data.")


if __name__ == "__main__":
    main()
