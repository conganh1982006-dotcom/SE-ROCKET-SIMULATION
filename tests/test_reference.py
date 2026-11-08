from dataclasses import replace
import numpy as np
import pytest
from scipy.integrate import quad
from rocket import Parameters, simulate, quantities
from rocket.analytic import powered_no_drag, no_drag_quantities, no_drag_history, coast_apogee
from rocket.simulator import NumericalError
from verification.independent import scipy_reference
from verification.checks import physical_checks, reference_checks, coast_checks


@pytest.mark.parametrize("method", ["euler", "heun", "rk4"])
@pytest.mark.parametrize("q", [0.2, 0.23, 0.4])
def test_physical_bounds_and_dynamic_burnout(method, q):
    r = simulate(Parameters(q=q, c=0.002), dt=0.03, method=method)
    assert all(c.passed for c in physical_checks(r))
    assert r.burnout.t == r.params.burn_time
    assert np.count_nonzero(r.t == r.burnout.t) == 1
    assert abs(r.apogee.state[1]) < 1e-8


@pytest.mark.parametrize("c", [0.0, 0.002])
def test_rk4_against_independent_full_flight(c):
    p = Parameters(c=c)
    r = simulate(p, dt=0.02)
    ref = no_drag_quantities(p) if c == 0 else scipy_reference(p)
    limits = {"h_burnout": 1e-5, "v_burnout": 1e-5, "apogee": 1e-4, "t_apogee": 1e-6}
    assert all(x.passed for x in reference_checks(r, ref, atol=limits, rtol=0))
    assert all(x.passed for x in coast_checks(r, height_atol=1e-4, time_atol=1e-6))


def test_powered_altitude_by_independent_quadrature():
    p = Parameters(h0=23, v0=4, q=0.17)
    for t in [0.0, 1e-7, 0.73, p.burn_time]:
        h = p.h0 + quad(lambda s: p.v0+p.ve*np.log(p.m0/(p.m0-p.q*s))-p.g*s, 0, t, epsabs=1e-10)[0]
        assert powered_no_drag(t, p)[0] == pytest.approx(h, abs=1e-9)


def test_published_rounded_values_are_rounded_references():
    q = no_drag_quantities(Parameters())
    assert abs(q["v_burnout"]-235.8) <= 0.05
    assert abs(q["h_burnout"]-214.1) <= 0.05
    assert abs(q["apogee"]-3048) <= 0.5


def test_full_no_drag_history():
    p = Parameters()
    r = simulate(p, 0.025)
    mask = r.t <= no_drag_quantities(p)["t_apogee"]
    np.testing.assert_allclose(r.y[mask], no_drag_history(r.t[mask], p), atol=2e-7, rtol=0)


@pytest.mark.parametrize("c", [0, 1e-15, 0.002, 0.01])
def test_coast_relation_against_independent_solver(c):
    p = Parameters(c=c)
    q = scipy_reference(p)
    ha, duration = coast_apogee(q["h_burnout"], q["v_burnout"], p)
    assert ha == pytest.approx(q["apogee"], abs=2e-7)
    assert p.burn_time+duration == pytest.approx(q["t_apogee"], abs=1e-8)


def test_zero_drag_limit():
    a = quantities(simulate(Parameters(c=0), 0.02))
    b = quantities(simulate(Parameters(c=1e-12), 0.02))
    assert abs(a["apogee"]-b["apogee"]) < 2e-4
    assert abs(a["v_burnout"]-b["v_burnout"]) < 2e-6


def test_general_parameters_nonzero_initial_state():
    p = Parameters(m0=2, mf=1.2, ve=300, q=0.37, g=3.71, h0=30, v0=15, c=0.003)
    r = simulate(p, 0.02)
    assert all(x.passed for x in physical_checks(r)+reference_checks(r, scipy_reference(p)))


@pytest.mark.parametrize("kwargs", [
    {"mf": 0}, {"mf": 1}, {"m0": -1}, {"q": 0}, {"q": -1}, {"q": 0.001},
    {"q": 9.81/500}, {"g": 0}, {"ve": -1}, {"c": -1}, {"v0": -1},
    {"h0": -1}, {"q": float("nan")}, {"c": float("inf")},
])
def test_invalid_physical_domain_is_rejected(kwargs):
    with pytest.raises(ValueError):
        Parameters(**kwargs)


@pytest.mark.parametrize("dt", [0, -1, float("nan"), float("inf")])
def test_bad_numerical_step_is_rejected(dt):
    with pytest.raises(ValueError):
        simulate(dt=dt)


def test_invalid_method_and_step_budget():
    with pytest.raises(ValueError): simulate(method="not-a-method")
    with pytest.raises(NumericalError): simulate(max_steps=1)


def test_burnout_resolved_even_when_dt_exceeds_burn_time():
    r = simulate(Parameters(), dt=3, method="euler")
    assert r.t[1] == 2
    assert r.burnout.state[2] == 0.6
    assert np.min(r.m) >= 0.6


def test_acceleration_includes_both_sides_of_burnout():
    p = Parameters()
    r = simulate(p)
    q = quantities(r)
    expected = p.q*p.ve/p.mf/p.g - 1
    assert q["max_acceleration_g"] == pytest.approx(expected)
    assert q["max_proper_acceleration_g"] == pytest.approx(expected+1)
    ix = np.flatnonzero(r.t == p.burn_time)[0]
    assert r.a[ix] == pytest.approx(-p.g)
    assert r.burnout.a_before-r.burnout.a_after == pytest.approx(p.q*p.ve/p.mf)


def test_dop853_reference_tolerance_refinement():
    p = Parameters(c=0.002)
    loose, tight = scipy_reference(p, rtol=1e-10, atol=1e-10), scipy_reference(p)
    for key in ["h_burnout", "v_burnout", "apogee"]:
        assert abs(loose[key]-tight[key]) < 1e-6


def test_corrupt_mass_is_detected_by_reusable_checks():
    r = simulate()
    bad = replace(r, y=r.y.copy())
    bad.y[1, 2] = 0.5
    failures = {x.name for x in physical_checks(bad) if not x.passed}
    assert {"mass_above_dry", "mass_law"} <= failures


def test_drag_reduces_apogee():
    assert quantities(simulate(Parameters(c=0.002)))["apogee"] < quantities(simulate())["apogee"]


def test_burnout_time_rounds_to_boundary_before_step_length():
    # Found in the burn-rate sweep: t+dt rounds to tb while dt < tb-t.
    p = Parameters(q=0.3565550404549396)
    r = simulate(p, dt=min(0.025, p.burn_time/120))
    assert r.burnout.t == p.burn_time
    assert all(x.passed for x in physical_checks(r))
