"""Original finite-window and lineage-exposure teaching calculations."""
from math import exp, expm1, isfinite, log, sqrt


def finite_number(value, label, minimum=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be a finite number')
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} exceeds finite range') from error
    if not isfinite(number) or number < minimum:
        raise ValueError(f'{label} outside finite domain')
    return number


def fold_probability(rate, window):
    rate = finite_number(rate, 'rate')
    window = finite_number(window, 'window')
    product = rate * window
    if not isfinite(product):
        raise ValueError('rate-window product is not finite')
    return -expm1(-product)


def mutation_rate(count, exposure):
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError('count must be a nonnegative integer')
    exposure = finite_number(exposure, 'exposure')
    if exposure == 0:
        raise ValueError('exposure must be positive')
    try:
        result = count / exposure, sqrt(count) / exposure
    except OverflowError as error:
        raise ValueError('count exceeds finite computational range') from error
    if not all(isfinite(value) for value in result):
        raise ValueError('rate estimate exceeds finite range')
    return result


def single_effect_moments(rate, generations, log_effect):
    rate = finite_number(rate, 'rate')
    generations = finite_number(generations, 'generations')
    if (isinstance(log_effect, bool)
            or not isinstance(log_effect, (int, float))):
        raise ValueError('log effect must be a finite number')
    if not isfinite(log_effect):
        raise ValueError('log effect must be finite')
    events = rate * generations
    if not isfinite(events):
        raise ValueError('expected event count must be finite')
    if events == 0:
        return 0.0, 0.0, 1.0
    try:
        result = (events * log_effect, events * log_effect ** 2,
                  exp(events * expm1(log_effect)))
    except OverflowError as error:
        raise ValueError('moments exceed floating-point range') from error
    if not all(isfinite(value) for value in result):
        raise ValueError('moments exceed finite range')
    return result


def zero_count_upper(exposure, tail=0.05):
    exposure = finite_number(exposure, 'exposure')
    tail = finite_number(tail, 'tail')
    if exposure == 0 or not 0 < tail < 1:
        raise ValueError('positive exposure and 0 < tail < 1 required')
    return -log(tail) / exposure


def transfer_equilibrium(transfer, loss):
    transfer = finite_number(transfer, 'transfer')
    loss = finite_number(loss, 'loss')
    if transfer == 0:
        raise ValueError('transfer must be positive')
    return max(0.0, 1.0 - loss / transfer)


if __name__ == '__main__':
    for window in (0.2, 1.0):
        print(f'window={window:.1f}; fold={fold_probability(2, window):.6f}')
    rate, se = mutation_rate(512, 64 * 4000)
    print(f'genome_rate={rate:.6f}; Poisson_SE={se:.8f}')
    mean_log, var_log, mean_w = single_effect_moments(0.002, 4000, -0.01)
    print(f'mean_log={mean_log:.6f}; var_log={var_log:.6f}')
    print(f'mean_fitness={mean_w:.6f}; exp_mean_log={exp(mean_log):.6f}')
    print(f'zero_count_upper={zero_count_upper(256000):.8f}')
    print(f'transfer_equilibrium={transfer_equilibrium(0.4, 0.1):.6f}')
