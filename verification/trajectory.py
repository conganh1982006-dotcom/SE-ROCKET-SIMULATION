"""Independent verification of every exported state and phase-local ODE defects.

No import of rocket.rhs, methods or simulator. See docs/TRAJECTORY_VERIFICATION_VI.md.
"""
from dataclasses import dataclass, asdict
import numpy as np
from rocket.analytic import powered_no_drag
from .checks import match
from .independent import scipy_history


@dataclass(frozen=True)
class TrajectoryTolerances:
    h_atol: float = 0.01       # m: same resolution as the existing burnout check
    v_atol: float = 0.01       # m/s
    m_atol: float = 1e-10      # kg: exact piecewise linear mass law
    state_rtol: float = 1e-6  # for h,v only; mass uses no relative allowance
    a_atol: float = 1e-8       # m/s^2: acceleration is an algebraic output
    a_rtol: float = 1e-10

    def __post_init__(self):
        values = asdict(self)
        if not all(np.isfinite(v) and v >= 0 for v in values.values()):
            raise ValueError("Tolerances must be finite and nonnegative.")
        if min(self.h_atol, self.v_atol, self.m_atol, self.a_atol) <= 0:
            raise ValueError("Absolute tolerances must be positive.")


@dataclass
class SeriesCheck:
    name: str
    category: str
    passed: bool
    sample_count: int
    unit: str
    max_absolute_error: float
    max_relative_error: float | None
    relative_undefined_count: int
    max_error_ratio: float
    worst_time_s: float
    max_absolute_error_time_s: float
    min_allowed_error: float
    max_allowed_error: float
    allowed_error_at_worst: float
    explanation: str

    def to_dict(self):
        return {**asdict(self), "status": "PASS" if self.passed else "FAIL"}


def _series(name, category, actual, expected, times, budget, unit, explanation):
    """PASS iff EVERY sample satisfies its own allowance; never compare maxima."""
    error = np.abs(actual-expected)
    budget = np.broadcast_to(budget, error.shape)
    ratio = error/budget
    worst, largest = int(np.argmax(ratio)), int(np.argmax(error))
    defined = np.abs(expected) > 0
    relative = float(np.max(error[defined]/np.abs(expected[defined]))) if np.any(defined) else None
    return SeriesCheck(name, category, bool(np.all(ratio <= 1)), len(error), unit,
                       float(error[largest]), relative, int(np.sum(~defined)),
                       float(ratio[worst]), float(times[worst]), float(times[largest]),
                       float(budget.min()), float(budget.max()), float(budget[worst]), explanation)


def _contract(r, p):
    """Return a failure instead of accepting empty/invalid verification coverage."""
    t, y, a = np.asarray(r.t), np.asarray(r.y), np.asarray(r.a)
    valid = (t.ndim == 1 and len(t) >= 5 and y.shape == (len(t), 3)
             and a.shape == t.shape and np.all(np.isfinite(t))
             and np.all(np.isfinite(y)) and np.all(np.isfinite(a))
             and np.all(t >= 0) and np.all(np.diff(t) > 0)
             and np.all(y[:, 2] > 0))
    if valid:
        ib = int(np.argmin(abs(t-p.burn_time)))
        valid = abs(t[ib]-p.burn_time) <= 1e-10 and 2 <= ib <= len(t)-3
    return match("trajectory_coverage", 0 if valid else 1, 0, atol=0,
                 category="trajectory_contract",
                 explanation="Finite ordered samples, positive mass, burnout sample within 1e-10 s, "
                             "and at least two intervals in EACH phase are required.")


def reference_history(p, times):
    """Closed forms for c=0, independent DOP853 dense output otherwise.

    The c=0 coast formula is also valid just beyond apogee. Do not clip time or
    use the observed event time as a reference event. rocket APIs stay unchanged.
    """
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or not len(times) or not np.all(np.isfinite(times)) or np.any(times < 0):
        raise ValueError("Reference times must be finite, 1D, nonempty and nonnegative.")
    if p.c != 0:
        return scipy_history(p, times)
    y = powered_no_drag(np.minimum(times, p.burn_time), p)
    hb, vb, _ = powered_no_drag(p.burn_time, p)
    mask = times > p.burn_time
    tau = times[mask]-p.burn_time
    y[mask, 0] = hb+vb*tau-p.g*tau*tau/2
    y[mask, 1] = vb-p.g*tau
    y[mask, 2] = p.mf
    return y


def _state_allowance(ref, tol):
    eps = np.empty_like(ref)
    eps[:, 0] = tol.h_atol+tol.state_rtol*abs(ref[:, 0])
    eps[:, 1] = tol.v_atol+tol.state_rtol*abs(ref[:, 1])
    eps[:, 2] = tol.m_atol
    return eps


def _reference_checks(r, p, tol, ref):
    budget = _state_allowance(ref, tol)
    source = "analytic c=0" if p.c == 0 else "DOP853, rtol=atol=2e-12"
    return [_series(f"trajectory_{name}", "trajectory_reference", r.y[:, j], ref[:, j],
                    r.t, budget[:, j], unit,
                    f"All exported times against {source}; atol+rtol*abs(reference), mass rtol=0. "
                    "Relative error excludes exactly zero reference values; near-zero ratios can be large.")
            for j, (name, unit) in enumerate(zip(["h", "v", "m"], ["m", "m/s", "kg"]))]


def trajectory_reference_checks(r, params=None, tolerances=None):
    p, tol = r.params if params is None else params, tolerances or TrajectoryTolerances()
    contract = _contract(r, p)
    if not contract.passed:
        return [contract]
    return [contract]+_reference_checks(r, p, tol, reference_history(p, r.t))


def _acceleration(y, p, powered):
    """Independent equation evaluation; use phase-local LEFT limit at tb as needed."""
    thrust = np.asarray(powered)*p.q*p.ve
    return (thrust-p.c*y[:, 1]*abs(y[:, 1]))/y[:, 2]-p.g


def _acceleration_allowance(ref, eps, p, powered):
    """Mean-value bound on |F(y)-F(ref)| inside the reference error box."""
    low_m = ref[:, 2]-eps[:, 2]
    if np.any(low_m <= 0):
        raise ValueError("Mass tolerance must be smaller than reference mass.")
    high_v = abs(ref[:, 1])+eps[:, 1]
    thrust = np.asarray(powered)*p.q*p.ve
    lv = 2*p.c*high_v/low_m
    lm = (thrust+p.c*high_v**2)/low_m**2
    return lv*eps[:, 1]+lm*eps[:, 2]


def _dynamics_checks(r, p, tol, ref):
    eps = _state_allowance(ref, tol)
    dt = np.diff(r.t)
    ib = int(np.argmin(abs(r.t-p.burn_time)))
    # No stencil crosses the discontinuity. The burnout sample belongs to BOTH
    # adjacent intervals, with the appropriate one-sided acceleration in each.
    interval_powered = np.arange(len(dt)) < ib
    left_a = _acceleration(r.y[:-1], p, interval_powered)
    right_a = _acceleration(r.y[1:], p, interval_powered)
    ref_left_a = _acceleration(ref[:-1], p, interval_powered)
    ref_right_a = _acceleration(ref[1:], p, interval_powered)
    a_error_left = _acceleration_allowance(ref[:-1], eps[:-1], p, interval_powered)
    a_error_right = _acceleration_allowance(ref[1:], eps[1:], p, interval_powered)

    secants = np.diff(r.y, axis=0)/dt[:, None]
    ref_secants = np.diff(ref, axis=0)/dt[:, None]
    mean_v = (r.v[:-1]+r.v[1:])/2
    ref_mean_v = (ref[:-1, 1]+ref[1:, 1])/2
    mean_a = (left_a+right_a)/2
    ref_mean_a = (ref_left_a+ref_right_a)/2
    # Ref stencil bias is the actual trapezoid differentiation error on this
    # same grid, not an adjustable estimate from possibly corrupted samples.
    bias_h = abs(ref_secants[:, 0]-ref_mean_v)
    bias_v = abs(ref_secants[:, 1]-ref_mean_a)
    state_roundoff = (64*np.finfo(float).eps
                      * np.maximum(1, np.maximum(abs(ref[:-1]), abs(ref[1:]))) / dt[:, None])
    h_budget = (bias_h+(eps[:-1, 0]+eps[1:, 0])/dt
                +(eps[:-1, 1]+eps[1:, 1])/2+state_roundoff[:, 0])
    v_budget = (bias_v+(eps[:-1, 1]+eps[1:, 1])/dt
                +(a_error_left+a_error_right)/2+state_roundoff[:, 1])
    mass_budget = (eps[:-1, 2]+eps[1:, 2])/dt+state_roundoff[:, 2]
    midpoint = (r.t[:-1]+r.t[1:])/2
    explanation = ("Phase-local secant minus trapezoid RHS. Budget = independent-reference "
                   "stencil bias + propagated pointwise state tolerances + roundoff; "
                   "no interval crossing burnout, no candidate-derived tolerance inflation. "
                   "Residual reference is zero, so relative error is undefined; use max_error_ratio.")
    result = [
        _series("dynamics_h_prime", "dynamics_consistency", secants[:, 0]-mean_v,
                np.zeros(len(dt)), midpoint, h_budget, "m/s", explanation),
        _series("dynamics_v_prime", "dynamics_consistency", secants[:, 1]-mean_a,
                np.zeros(len(dt)), midpoint, v_budget, "m/s^2", explanation),
    ]
    for phase, mask, expected in [("burn", interval_powered, -p.q), ("coast", ~interval_powered, 0.0)]:
        result.append(_series(f"dynamics_m_prime_{phase}", "dynamics_consistency",
                              secants[mask, 2], np.full(np.sum(mask), expected),
                              midpoint[mask], mass_budget[mask], "kg/s",
                              "Exact constant mass slope; endpoint mass allowance / interval length + roundoff."))
    sample_powered = np.arange(len(r.t)) < ib  # stored a at burnout is RIGHT sided
    expected_a = _acceleration(r.y, p, sample_powered)
    result.append(_series("dynamics_acceleration", "dynamics_consistency", r.a, expected_a,
                          r.t, tol.a_atol+tol.a_rtol*abs(expected_a), "m/s^2",
                          "Algebraic output a must equal (T-c*v*abs(v))/m-g at every sample; "
                          "right limit at burnout. No finite-difference allowance is needed."))
    return result


def dynamics_checks(r, params=None, tolerances=None):
    p, tol = r.params if params is None else params, tolerances or TrajectoryTolerances()
    contract = _contract(r, p)
    if not contract.passed:
        return [contract]
    return [contract]+_dynamics_checks(r, p, tol, reference_history(p, r.t))


def verify_trajectory(r, params=None, tolerances=None):
    """Shared public entry point for scenarios and Member B adapters."""
    p, tol = r.params if params is None else params, tolerances or TrajectoryTolerances()
    contract = _contract(r, p)
    if not contract.passed:
        return [contract]
    ref = reference_history(p, r.t)
    return [contract]+_reference_checks(r, p, tol, ref)+_dynamics_checks(r, p, tol, ref)
