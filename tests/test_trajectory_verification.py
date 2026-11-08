"""Exercise the verifier through the same adapter seam used by Member B."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
from rocket import simulate, Parameters
from verification.scenarios import run_scenario
from verification.trajectory import (verify_trajectory, trajectory_reference_checks,
                                     dynamics_checks, reference_history)
from verification.independent import scipy_history

ROOT = Path(__file__).resolve().parents[1]


def test_scenario_rejects_interior_velocity_spike_with_unchanged_events():
    def corrupted_adapter(params, dt, method):
        original = simulate(params, dt, method)
        changed = deepcopy(original)
        index = int(np.argmin(abs(changed.t - 3.0)))
        changed.y[index, 1] += 25.0
        np.testing.assert_array_equal(changed.burnout.state, original.burnout.state)
        np.testing.assert_array_equal(changed.apogee.state, original.apogee.state)
        assert original.y[index, 1] != changed.y[index, 1]
        return changed

    report = run_scenario(ROOT / "scenarios/02_analytic_no_drag.yaml", simulator=corrupted_adapter)
    assert report["actual"] == "FAIL", "An interior +25 m/s velocity spike escaped verification"
    assert not report["demonstration_pass"]


@pytest.fixture(scope="module", params=[0.0, 0.002], ids=["analytic", "dop853"])
def clean(request):
    return simulate(Parameters(c=request.param), dt=0.02)


def failures(checks):
    return {c.name for c in checks if not c.passed}


def test_every_unmodified_sample_passes(clean):
    checks = verify_trajectory(clean)
    assert not failures(checks), [c.to_dict() for c in checks if not c.passed]
    for check in checks:
        if check.name.startswith("trajectory_") and check.name != "trajectory_coverage":
            assert check.sample_count == len(clean.t)


@pytest.mark.parametrize("at_time", [1.0, 3.0], ids=["powered", "coast"])
@pytest.mark.parametrize("field,delta,reference_failure,dynamics_failure", [
    ("v", 25.0, "trajectory_v", "dynamics_v_prime"),
    ("h", 1.0, "trajectory_h", "dynamics_h_prime"),
    ("m", 0.02, "trajectory_m", "mass_slope"),
    ("a", 25.0, None, "dynamics_acceleration"),
])
def test_mutations_are_caught_without_touching_original(clean, at_time, field, delta,
                                                     reference_failure, dynamics_failure):
    original_y, original_a = clean.y.copy(), clean.a.copy()
    original_burn, original_apex = deepcopy(clean.burnout), deepcopy(clean.apogee)
    bad = deepcopy(clean)
    index = int(np.argmin(abs(bad.t-at_time)))
    getattr(bad, field)[index] += delta
    ref_checks = trajectory_reference_checks(bad)
    ode_checks = dynamics_checks(bad)
    if reference_failure:
        assert reference_failure in failures(ref_checks)
    else:
        assert not failures(ref_checks), "h,v,m reference checks must not pretend to verify a"
    if dynamics_failure == "mass_slope":
        dynamics_failure = "dynamics_m_prime_burn" if at_time < bad.params.burn_time else "dynamics_m_prime_coast"
    assert dynamics_failure in failures(ode_checks)
    np.testing.assert_array_equal(clean.y, original_y)
    np.testing.assert_array_equal(clean.a, original_a)
    for name, before in [("burnout", original_burn), ("apogee", original_apex)]:
        assert getattr(bad, name).t == before.t
        np.testing.assert_array_equal(getattr(bad, name).state, before.state)


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_velocity_mutations_at_or_next_to_burnout_are_not_skipped(clean, offset):
    bad = deepcopy(clean)
    ib = int(np.argmin(abs(bad.t-bad.params.burn_time)))
    bad.y[ib+offset, 1] += 25
    assert "trajectory_v" in failures(trajectory_reference_checks(bad))
    assert "dynamics_v_prime" in failures(dynamics_checks(bad))


def test_right_sided_acceleration_at_burnout_is_enforced(clean):
    bad = deepcopy(clean)
    ib = int(np.argmin(abs(bad.t-bad.params.burn_time)))
    bad.a[ib] = bad.burnout.a_before
    assert "dynamics_acceleration" in failures(dynamics_checks(bad))


def test_velocity_and_consistently_recomputed_acceleration_still_fail(clean):
    bad = deepcopy(clean)
    index = int(np.argmin(abs(bad.t-3)))
    bad.y[index, 1] += 25
    p, v, m = bad.params, bad.v[index], bad.m[index]
    bad.a[index] = -p.g-p.c*v*abs(v)/m
    failed = failures(verify_trajectory(bad))
    assert "dynamics_acceleration" not in failed
    assert {"trajectory_v", "dynamics_v_prime"} <= failed


def test_reported_method_and_dt_cannot_inflate_verification_tolerance(clean):
    bad = deepcopy(clean)
    index = int(np.argmin(abs(bad.t-3)))
    bad.y[index, 1] += 25
    before = failures(verify_trajectory(bad))
    bad.dt = 1e6
    bad.method = "euler"
    assert failures(verify_trajectory(bad)) == before
    assert {"trajectory_v", "dynamics_v_prime"} <= before


def test_nonuniform_samples_and_two_sides_of_burnout_pass(clean):
    irregular = deepcopy(clean)
    ib = int(np.argmin(abs(clean.t-clean.params.burn_time)))
    indices = sorted({0, 1, 7, ib//2, ib-1, ib, ib+1, ib+9, len(clean.t)-2, len(clean.t)-1})
    irregular.t = clean.t[indices].copy()
    irregular.y = clean.y[indices].copy()
    irregular.a = clean.a[indices].copy()
    assert not failures(verify_trajectory(irregular))


def test_reference_evaluates_requested_times_even_just_after_apogee():
    p = Parameters()
    r = simulate(p)
    t = np.array([0, 1e-7, 0.77, 2-1e-7, 2, 2+1e-7, 3.13, r.apogee.t+1e-7])
    exact = reference_history(p, t)
    dop = scipy_history(p, t)
    np.testing.assert_allclose(dop, exact, atol=2e-7, rtol=0)


def test_dense_drag_reference_is_stable_under_tighter_tolerances():
    p = Parameters(c=0.002)
    t = np.r_[np.linspace(0, 2, 33), np.linspace(2.01, 9.01, 39)]
    standard = scipy_history(p, t)
    tighter = scipy_history(p, t, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(standard, tighter, atol=1e-7, rtol=0)


@pytest.mark.parametrize("problem", ["missing_burnout", "no_interiors", "duplicate_time", "nan"])
def test_inadequate_or_invalid_coverage_cannot_pass(clean, problem):
    bad = deepcopy(clean)
    ib = int(np.argmin(abs(bad.t-bad.params.burn_time)))
    if problem in ["missing_burnout", "no_interiors"]:
        indices = np.delete(np.arange(len(bad.t)), ib) if problem == "missing_burnout" else [0, ib, len(bad.t)-1]
        bad.t, bad.y, bad.a = bad.t[indices], bad.y[indices], bad.a[indices]
    elif problem == "duplicate_time":
        bad.t[2] = bad.t[1]
    else:
        bad.y[2, 1] = np.nan
    assert "trajectory_coverage" in failures(verify_trajectory(bad))


@pytest.mark.parametrize("field", ["h", "v", "a"])
def test_scenario_adapter_rejects_each_newly_covered_output(field):
    def corrupt(params, dt, method):
        bad = deepcopy(simulate(params, dt, method))
        index = int(np.argmin(abs(bad.t-3)))
        getattr(bad, field)[index] += 1.0 if field == "h" else 25.0
        return bad
    report = run_scenario(ROOT/"scenarios/01_baseline_drag.yaml", simulator=corrupt)
    assert report["actual"] == "FAIL"
    assert not report["demonstration_pass"]
