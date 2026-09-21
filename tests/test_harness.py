

def test_holm_correction_step_down():
    from run_benchmark import holm_correction
    # 12 tests: the 11th sorted p (0.028) fails 0.05/2, so it and everything after it are rejected
    ps = [3e-6] * 8 + [4.9e-4, 4.2e-3, 2.8e-2, 0.229]
    assert holm_correction(ps) == [True] * 10 + [False, False]
    # order-preserving and None-safe
    assert holm_correction([0.2, 1e-4, None]) == [False, True, False]
