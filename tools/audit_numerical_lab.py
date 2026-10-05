"""Independent reference checks for the original numerical teaching lab."""
import decimal
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT
spec = importlib.util.spec_from_file_location("lab", SOURCE / "numerical_lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
results = []


def check(name, actual, expected, tolerance=2e-10):
    error = abs(actual - expected)
    passed = error <= tolerance * max(1.0, abs(expected))
    results.append({"name": name, "actual": actual, "expected": expected,
                    "absolute_error": error, "tolerance": tolerance,
                    "passed": passed})
    assert passed, results[-1]


def dense_solve(matrix, vector):
    """Pivoted Gaussian elimination, independent of Thomas elimination."""
    rows = [list(row) + [value] for row, value in zip(matrix, vector)]
    size = len(rows)
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(rows[row][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [value / scale for value in rows[col]]
        for row in range(col + 1, size):
            factor = rows[row][col]
            rows[row] = [a - factor * b
                         for a, b in zip(rows[row], rows[col])]
    values = [0.0] * size
    for row in range(size - 1, -1, -1):
        values[row] = rows[row][-1] - sum(
            rows[row][col] * values[col] for col in range(row + 1, size))
    return values


for n in (2, 3, 10, 50):
    for r in (0.1, 0.9, 1.0, 1.000000001, 1.1, 10.0):
        with decimal.localcontext() as context:
            context.prec = 100
            ratio = decimal.Decimal.from_float(r)
            terms = [ratio ** (-j) for j in range(n)]
            denominator = sum(terms)
            for i in range(n + 1):
                expected = float(sum(terms[:i]) / denominator)
                check(f"fixation_decimal_N{n}_i{i}_r{r}",
                      lab.fixation_probability(n, i, r), expected)
        matrix = [[0.0] * (n - 1) for _ in range(n - 1)]
        for i in range(1, n):
            # Assemble probabilities directly, without calling lab transition.
            up = r * i * (n - i) / (n * (r * i + n - i))
            down = i * (n - i) / (n * (r * i + n - i))
            row = i - 1
            matrix[row][row] = up + down
            if i > 1:
                matrix[row][row - 1] = -down
            if i < n - 1:
                matrix[row][row + 1] = -up
            actual_probabilities = lab.moran_transition(n, i, r)
            check(f"transition_normalization_N{n}_i{i}_r{r}",
                  sum(actual_probabilities), 1.0)
            check(f"transition_up_N{n}_i{i}_r{r}",
                  actual_probabilities[0], up)
            check(f"transition_down_N{n}_i{i}_r{r}",
                  actual_probabilities[1], down)
        reference = dense_solve(matrix, [1.0] * (n - 1))
        numpy_reference = np.linalg.solve(np.array(matrix), np.ones(n - 1))
        calculated = lab.mean_absorption_times(n, r)
        for i, expected in enumerate(reference, 1):
            check(f"time_dense_N{n}_i{i}_r{r}", calculated[i], expected)
            check(f"time_numpy_N{n}_i{i}_r{r}", calculated[i],
                  float(numpy_reference[i - 1]))
            up, down, _ = lab.moran_transition(n, i, r)
            recurrence = (up + down) * calculated[i]
            recurrence -= down * calculated[i - 1] + up * calculated[i + 1]
            check(f"time_backward_residual_N{n}_i{i}_r{r}", recurrence, 1.0)
        check(f"time_left_boundary_N{n}_r{r}", calculated[0], 0.0)
        check(f"time_right_boundary_N{n}_r{r}", calculated[-1], 0.0)

check("N2_neutral_absorption_attempted_events", lab.mean_absorption_times(2)[1], 2)
check("N3_neutral_absorption", lab.mean_absorption_times(3)[1], 4.5)
check("N50_neutral_single_harmonic", lab.mean_absorption_times(50)[1],
      50 * sum(1 / j for j in range(1, 50)))
for r in (1e-300, 1e300, 1 - 1e-12, 1 + 1e-12):
    for i in (0, 1, 25, 49, 50):
        u = lab.fixation_probability(50, i, r)
        assert 0 <= u <= 1
        results.append({"name": f"extreme_fixation_domain_i{i}_r{r}",
                        "actual": u, "passed": True})
    times = lab.mean_absorption_times(50, r)
    assert all(math.isfinite(t) and t >= 0 for t in times)
    results.append({"name": f"extreme_time_domain_r{r}", "passed": True})

check("exponential_initial", lab.exponential_growth(100, 0.3, 0), 100)
check("exponential_zero", lab.exponential_growth(0, 1, 10000), 0)
check("exponential_doubling", lab.exponential_growth(100, math.log(2), 3), 800)
check("logistic_initial", lab.logistic_growth(100, 0.3, 10000, 0), 100)
check("logistic_half_capacity", lab.logistic_growth(100, 0.3, 10000,
      math.log(99) / 0.3), 5000)
check("logistic_zero", lab.logistic_growth(0, 0.3, 10000, 10), 0)
check("logistic_capacity", lab.logistic_growth(10000, 0.3, 10000, 10), 10000)
check("logistic_subnormal_initial_long_time", lab.logistic_growth(5e-324, 1, 1e300, 10000), 1e300)
check("selection_equal_rates", lab.selection_frequency(0.2, 0, 10), 0.2)
check("selection_extreme_positive", lab.selection_frequency(0.2, 1000, 100), 1)
check("selection_extreme_negative", lab.selection_frequency(0.2, -1000, 100), 0)
check("selection_log_odds", lab.selection_frequency(0.02, 0.1, 10),
      (0.02 * math.e) / (0.98 + 0.02 * math.e))
check("selection_scipy_expit", lab.selection_frequency(0.02, 0.1, 10),
      float(expit(math.log(0.02 / 0.98) + 1)))
check("same_physical_units_minutes_hours", lab.exponential_growth(100, 0.3, 10),
      lab.exponential_growth(100, 0.3 / 60, 10 * 60))

invalid = [
    (lab.fixation_probability, (True, 0, 1), TypeError),
    (lab.fixation_probability, (2.0, 0, 1), TypeError),
    (lab.fixation_probability, (0, 0, 1), ValueError),
    (lab.fixation_probability, (2, 3, 1), ValueError),
    (lab.fixation_probability, (2, -1, 1), ValueError),
    (lab.fixation_probability, (2, 1, 0), ValueError),
    (lab.fixation_probability, (2, 1, math.inf), ValueError),
    (lab.fixation_probability, (2, 1, math.nan), ValueError),
    (lab.mean_absorption_times, (2, False), TypeError),
    (lab.exponential_growth, (-1, 0.3, 1), ValueError),
    (lab.exponential_growth, (1, 0.3, -1), ValueError),
    (lab.logistic_growth, (10001, 0.3, 10000, 1), ValueError),
    (lab.logistic_growth, (1, -0.3, 10000, 1), ValueError),
    (lab.selection_frequency, (1.1, 0.1, 1), ValueError),
    (lab.selection_frequency, (True, 0.1, 1), TypeError),
]
for function, args, exception in invalid:
    try:
        function(*args)
    except exception:
        results.append({"name": f"invalid_{function.__name__}_{repr(args)}",
                        "expected_exception": exception.__name__, "passed": True})
    else:
        raise AssertionError(f"Expected {exception.__name__}: {function.__name__}{args}")

report = {"status": "passed", "checks": len(results),
          "reference_methods": ["100-digit Decimal geometric sums",
                                "independently assembled dense system with pivoted Gaussian elimination",
                                "NumPy dense solve and SciPy expit references",
                                "exact small-N and neutral harmonic identities",
                                "boundary, unit-conversion and invalid-input checks"],
          "worked_example": lab.worked_example(), "results": results}
target = Path(__file__).with_suffix(".json")
target.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
print(json.dumps({"status": report["status"], "checks": report["checks"],
                  "max_absolute_error": max(row.get("absolute_error", 0)
                                            for row in results)}, indent=2))
