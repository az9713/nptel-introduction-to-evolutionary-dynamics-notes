"""Original replay diagnostics; no experimental raw-data reconstruction."""
from math import comb, isfinite, log
from numbers import Real


def positive_real(value, name):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or value <= 0):
        raise ValueError(name + " must be a finite positive real number")


def zero_event_upper(exposure, alpha=0.05):
    """One-sided Poisson upper bound after zero detected independent events."""
    positive_real(exposure, "exposure")
    positive_real(alpha, "alpha")
    if alpha >= 1:
        raise ValueError("alpha must be less than one")
    return -log(alpha) / exposure


def late_enrichment_tail(early_success, early_trials,
                         late_success, late_trials):
    """One-sided conditional exact tail, conditioning on total successes."""
    for value in (early_success, early_trials, late_success, late_trials):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Counts must be nonnegative integers")
    if (early_trials == 0 or late_trials == 0
            or early_success > early_trials or late_success > late_trials):
        raise ValueError("Both groups require trials and valid successes")
    total_success = early_success + late_success
    denominator = comb(early_trials + late_trials, total_success)
    numerator = sum(comb(late_trials, count)
                    * comb(early_trials, total_success - count)
                    for count in range(late_success,
                                       min(late_trials, total_success) + 1)
                    if 0 <= total_success - count <= early_trials)
    return numerator / denominator


def nested_components(groups):
    """Balanced random-intercept ANOVA; retain negative raw estimates."""
    try:
        groups = [list(group) for group in groups]
    except TypeError as error:
        raise ValueError("Groups must be iterables of trait values") from error
    count = len(groups)
    if count < 2:
        raise ValueError("At least two histories required")
    size = len(groups[0])
    if size < 2 or any(len(group) != size for group in groups):
        raise ValueError("At least two replicates; groups must be balanced")
    for group in groups:
        for value in group:
            if (isinstance(value, bool) or not isinstance(value, Real)
                    or not isfinite(value)):
                raise ValueError("Trait values must be finite real numbers")
    means = [sum(group) / size for group in groups]
    grand = sum(means) / count
    within_ss = sum((value - mean) ** 2
                    for group, mean in zip(groups, means) for value in group)
    between_ss = size * sum((mean - grand) ** 2 for mean in means)
    within_ms = within_ss / (count * (size - 1))
    between_ms = between_ss / (count - 1)
    return {"grand_mean": grand, "within_variance": within_ms,
            "history_variance_raw": (between_ms - within_ms) / size}


def main():
    print(f"zero-event rate upper {zero_event_upper(1e10):.9g}")
    print("original20/20 trial comparison;0early and5late successes")
    print(f"conditional one-sided tail "
          f"{late_enrichment_tail(0, 20, 5, 20):.6f}")
    histories = [[1.28, 1.30, 1.32], [1.48, 1.50, 1.52],
                 [1.68, 1.70, 1.72]]
    for key, value in nested_components(histories).items():
        print(f"{key} {value:.6f}")
    print("Original examples; variance components are not causal fractions.")


if __name__ == "__main__":
    main()
