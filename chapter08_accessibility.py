"""Original finite landscapes: path counts and stochastic uphill endpoints."""
from math import expm1, isfinite, log
from numbers import Real


def validate_landscape(values):
    """Return dimension for a complete binary cube of finite real scores."""
    count = len(values)
    if count < 2 or count & (count - 1):
        raise ValueError("Supply a complete binary cube of dimension >= 1")
    if any(isinstance(x, bool) or not isinstance(x, Real)
           or not isfinite(x) for x in values):
        raise ValueError("Landscape scores must be finite real numbers")
    return count.bit_length() - 1


def accessible_orders(values):
    """Count strictly increasing shortest paths from all-zero to all-one."""
    dimension = validate_landscape(values)
    counts = [0] * len(values)
    counts[0] = 1
    for vertex in range(1, len(values)):
        for locus in range(dimension):
            bit = 1 << locus
            if vertex & bit:
                parent = vertex ^ bit
                if values[vertex] > values[parent]:
                    counts[vertex] += counts[parent]
    return counts[-1]


def endpoint_probabilities(values):
    """Uniform choice among fitter one-bit neighbours, starting anywhere."""
    dimension = validate_landscape(values)
    endpoints = {}
    for vertex in sorted(range(len(values)),
                         key=lambda v: values[v], reverse=True):
        uphill = [vertex ^ (1 << j) for j in range(dimension)
                  if values[vertex ^ (1 << j)] > values[vertex]]
        if not uphill:
            endpoints[vertex] = {vertex: 1.0}
            continue
        distribution = {}
        for neighbour in uphill:
            for peak, probability in endpoints[neighbour].items():
                distribution[peak] = (distribution.get(peak, 0.0)
                                      + probability / len(uphill))
        endpoints[vertex] = distribution
    return endpoints


def log_enrichment(variant_initial, reference_initial, variant_final,
                   reference_final):
    """Dimensionless log change of a variant/reference count ratio."""
    counts = (variant_initial, reference_initial, variant_final,
              reference_final)
    if any(isinstance(n, bool) or not isinstance(n, int) or n <= 0
           for n in counts):
        raise ValueError("All four sequencing counts must be positive ints")
    return (log(variant_final) - log(reference_final)
            - log(variant_initial) + log(reference_initial))


def sign_landscape():
    """Five-site toy: locus0 must precede locus1 on a shortest ascent."""
    pair = (1.0, 1.04, 0.98, 1.09)
    extra = (0.02, 0.03, 0.04)
    values = []
    for vertex in range(32):
        independent = sum(effect for j, effect in enumerate(extra, 2)
                          if vertex & (1 << j))
        values.append(pair[vertex & 3] + independent)
    return values


def diminishing_landscape():
    """Strictly increasing concave transform of additive latent effects."""
    effects = (0.1, 0.2, 0.3, 0.4, 0.5)
    return [1.0 - 0.5 * expm1(-sum(
        effect for j, effect in enumerate(effects) if v & (1 << j)))
            for v in range(32)]


def main():
    for name, values in (("sign", sign_landscape()),
                         ("diminishing", diminishing_landscape())):
        endpoints = endpoint_probabilities(values)
        peaks = sorted(v for v, result in endpoints.items()
                       if result == {v: 1.0})
        print(name, "paths", accessible_orders(values), "peaks", peaks)
    # Integer vertices read as binary labels, locus0 the rightmost bit.
    values = [0.0, 2.0, 1.0, 0.5, 1.5, 0.7, 1.8, 3.0]
    distribution = endpoint_probabilities(values)[0]
    print("two-peak start000", sorted(distribution.items()))
    print(f"log-enrichment {log_enrichment(200, 100, 600, 100):.6f}")


if __name__ == "__main__":
    main()
