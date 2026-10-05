"""Original finite landscapes, not fitted or reconstructed empirical data."""
from itertools import product
from math import log

ALPHABET = "ATGC"
CONTRIBUTIONS = (
    {"A": 0.2, "T": 0.1, "G": 0.4, "C": 0.3},
    {"A": 0.4, "T": 0.2, "G": 0.3, "C": 0.6},
    {"A": 0.5, "T": 0.1, "G": 0.2, "C": 0.3},
)


def hamming(first, second):
    """Count differences between equal-length strings."""
    if not isinstance(first, str) or not isinstance(second, str):
        raise TypeError("Strings required")
    if len(first) != len(second):
        raise ValueError("Equal lengths required")
    return sum(a != b for a, b in zip(first, second))


def neighbours(sequence, alphabet=ALPHABET):
    """Generate each single-substitution neighbour exactly once."""
    if len(set(alphabet)) != len(alphabet) or not alphabet:
        raise ValueError("Nonempty alphabet without duplicates required")
    if not set(sequence) <= set(alphabet):
        raise ValueError("Sequence contains a symbol outside the alphabet")
    for position, current in enumerate(sequence):
        for alternative in alphabet:
            if alternative != current:
                yield (sequence[:position] + alternative
                       + sequence[position + 1:])


def additive(sequence):
    """A fixed three-locus additive score with a unique GCA maximum."""
    if len(sequence) != 3 or not set(sequence) <= set(ALPHABET):
        raise ValueError("Three DNA letters required")
    return sum(table[base] for table, base in zip(CONTRIBUTIONS, sequence))


def peaks(values, alphabet):
    """Return strict local peaks; ties are not strict peaks."""
    return sorted(g for g, value in values.items()
                  if all(value > values[n]
                         for n in neighbours(g, alphabet)))


def main():
    values = {"".join(g): additive("".join(g))
              for g in product(ALPHABET, repeat=3)}
    print(f"DNA3: vertices={len(values)}, degree=9, edges=288")
    print(f"additive strict peaks={peaks(values, ALPHABET)}")
    for genotype in ("TAA", "GAA", "GCA"):
        print(f"{genotype}: F={values[genotype]:.3f}")
    reciprocal = {"00": 1.0, "10": 1.2, "01": 1.3, "11": 1.1}
    print(f"reciprocal sign strict peaks={peaks(reciprocal, '01')}")
    raw = 1.32 - 1.1 - 1.2 + 1.0
    logarithmic = log(1.32) - log(1.1) - log(1.2)
    print(f"multiplicative example: raw epsilon={raw:.6f}, "
          f"log epsilon={logarithmic:.6f}")
    effects = (0.01, 0.02, 0.05, 0.10)
    uniform = sum(effects) / len(effects)
    weighted = sum(s * s for s in effects) / sum(effects)
    print(f"beneficial means: generated={uniform:.6f}, "
          f"s-weighted={weighted:.6f}")


if __name__ == "__main__":
    main()
