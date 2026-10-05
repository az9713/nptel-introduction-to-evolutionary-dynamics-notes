"""Synthetic chemostat and frequency examples; standard library only."""
from math import exp, isfinite, log


def competition(time, initial=10000.0, x0=0.01,
                ga=0.4, gb=0.6, dilution=0.5):
    """Return resident count, mutant count, frequency, and mean rate."""
    values = (time, initial, x0, ga, gb, dilution)
    if not all(isfinite(v) for v in values):
        raise ValueError("Finite inputs required")
    if time < 0 or initial <= 0 or not 0 <= x0 <= 1:
        raise ValueError("Nonnegative time, positive count, valid frequency")
    if min(ga, gb, dilution) < 0:
        raise ValueError("Nonnegative rates required")
    a = initial * (1 - x0) * exp((ga - dilution) * time)
    b = initial * x0 * exp((gb - dilution) * time)
    x = b / (a + b)
    return a, b, x, ga * (1 - x) + gb * x


def break_even(maximum, half_saturation, dilution):
    """Substrate concentration at growth=dilution for Monod kinetics."""
    if not all(isfinite(v) and v > 0 for v in
               (maximum, half_saturation, dilution)):
        raise ValueError("Positive finite inputs required")
    if dilution >= maximum:
        raise ValueError("No finite break-even concentration")
    return half_saturation * dilution / (maximum - dilution)


def main():
    crossing = log(99) / 0.2
    for time in (0.0, 10.0, crossing):
        a, b, x, mean = competition(time)
        print(f"t={time:9.6f} h: total={a + b:10.3f}, "
              f"x={x:.6f}, mean={mean:.6f}/h")
    sa = break_even(0.6, 0.1, 0.2)
    sb = break_even(0.8, 0.3, 0.2)
    invasion = 0.8 * sa / (0.3 + sa) - 0.2
    print(f"S*_A={sa:.6f}, S*_B={sb:.6f} mg/L")
    print(f"B invasion exponent at A equilibrium={invasion:.6f}/h")


if __name__ == "__main__":
    main()
