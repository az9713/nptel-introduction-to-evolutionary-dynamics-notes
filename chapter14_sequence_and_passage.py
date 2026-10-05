"""Original opportunity-count and serial-passage teaching calculations."""
from fractions import Fraction
from itertools import product
from math import isfinite, log2

BASES = "TCAG"
AMINO_ACIDS = (
    "FFLLSSSSYY**CC*W"
    "LLLLPPPPHHQQRRRR"
    "IIIMTTTTNNKKSSRR"
    "VVVVAAAADDEEGGGG"
)
CODE = dict(zip(("".join(c) for c in product(BASES, repeat=3)),
                AMINO_ACIDS))


def sense_codon(codon):
    if not isinstance(codon, str) or codon not in CODE:
        raise ValueError("Require an uppercase DNA codon")
    if CODE[codon] == "*":
        raise ValueError("Require a sense codon")
    return CODE[codon]


def opportunities(codon):
    amino_acid = sense_codon(codon)
    synonymous = nonsynonymous = stop = 0
    for position in range(3):
        for base in BASES:
            if base == codon[position]:
                continue
            mutant = codon[:position] + base + codon[position + 1:]
            if CODE[mutant] == "*":
                stop += 1
            elif CODE[mutant] == amino_acid:
                synonymous += 1
            else:
                nonsynonymous += 1
    return synonymous, nonsynonymous, stop


def count_ratio(reference, comparison):
    if not reference or len(reference) != len(comparison):
        raise ValueError("Require nonempty, equal-length codon sequences")
    ks = kn = synonymous = nonsynonymous = 0
    for ancestor, descendant in zip(reference, comparison):
        first = sense_codon(ancestor)
        second = sense_codon(descendant)
        s, n, _ = opportunities(ancestor)
        ks += s
        kn += n
        differences = sum(a != b for a, b in zip(ancestor, descendant))
        if differences > 1:
            raise ValueError("Multiple differences need a path model")
        if differences:
            if first == second:
                synonymous += 1
            else:
                nonsynonymous += 1
    if ks == 0 or kn == 0 or synonymous == 0:
        raise ValueError("Count ratio has a zero denominator")
    ratio = Fraction(nonsynonymous * ks, kn * synonymous)
    return ks, kn, synonymous, nonsynonymous, ratio


def passage_clock(fold_increase, cycles):
    if type(fold_increase) not in (int, float):
        raise ValueError("Require a numeric fold increase")
    if not isfinite(fold_increase) or fold_increase < 1:
        raise ValueError("Require finite fold increase at least one")
    if type(cycles) is not int or cycles < 0:
        raise ValueError("Require a nonnegative integer cycle count")
    return cycles * log2(fold_increase)


def main():
    reference = ("CCC",) * 4
    comparison = ("CCG", "CAC", "ACC", "CCT")
    ks, kn, ds, dn, ratio = count_ratio(reference, comparison)
    print(f"K_S={ks}; K_N={kn}; D_S={ds}; D_N={dn}")
    print(f"normalized_count_ratio={ratio}")
    print(f"CCC opportunities={opportunities('CCC')}")
    print(f"TGG opportunities={opportunities('TGG')}")
    for fold in (100, 1000):
        print(f"fold={fold}; 30-cycle doublings="
              f"{passage_clock(fold, 30):.6f}")
    print(f"miss_at_bottleneck={(1 - 0.001) ** 1000:.6f}")


if __name__ == "__main__":
    main()
