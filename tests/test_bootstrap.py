"""Il CI bootstrap deve essere deterministico (seed fisso) e contenere la mediana."""
from statistics import median

from run_benchmark import bootstrap_ci


def test_bootstrap_is_deterministic():
    data = [10.1, 10.5, 9.8, 11.2, 10.0, 10.7, 9.9, 10.3, 10.6, 10.2]
    assert bootstrap_ci(data) == bootstrap_ci(data)


def test_ci_contains_the_sample_median():
    data = [10.1, 10.5, 9.8, 11.2, 10.0, 10.7, 9.9, 10.3, 10.6, 10.2]
    lo, hi = bootstrap_ci(data)
    assert lo <= median(data) <= hi
    assert lo < hi


def test_wider_spread_gives_wider_ci():
    tight = [10.0, 10.1, 10.2, 10.1, 10.0, 10.15, 10.05, 10.1]
    wide = [5.0, 15.0, 8.0, 12.0, 6.0, 14.0, 7.0, 13.0]
    t_lo, t_hi = bootstrap_ci(tight)
    w_lo, w_hi = bootstrap_ci(wide)
    assert (w_hi - w_lo) > (t_hi - t_lo)
