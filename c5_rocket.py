"""C5 Model Rocket — module conforming to de_kit/template_system.py, wmlab 0.1.1.

Powered: h'=v; v'=q*ve/m-g-c*v*abs(v)/m; m'=-q. Coast: thrust=0, m=mf.
SI units; upward positive. Group names/IDs are recorded in the scenario YAML files.
The existing NumPy Euler/Heun/RK4 engine is reused without changing its API.
"""
import numpy as np
from rocket import Parameters, Event, Trajectory, quantities as trajectory_quantities
from rocket.simulator import simulate as ascent
from rocket.model import rhs as phase_rhs
from rocket.methods import METHODS
from rocket.analytic import no_drag_quantities
from verification.independent import scipy_reference
from verification.trajectory import reference_history, verify_trajectory
from verification.checks import physical_checks

NAME = "c5_rocket"
STATE = ["h", "v", "m"]
CONVERGENCE_MODE = "analytic"


def parameters(p, init):
    allowed = {"m0", "mf", "q", "ve", "g", "c", "method", "output_mode"}
    if set(p)-allowed or set(init)-{"h0", "v0"}:
        raise ValueError("Unknown parameter/initial key; see c5_rocket.parameters.")
    return Parameters(**{k:v for k,v in p.items() if k not in {"method", "output_mode"}},
                      **init)


def rhs(t, y, p):
    """Public template RHS, right-sided at burnout. Integration locks each phase."""
    physical = parameters(p, {})
    return phase_rhs(t, y, physical, t < physical.burn_time)


def _sample_at(r, times):
    """Evaluate the numerical solution by fractional re-steps, never linear interpolation.

    Each fractional step stays within one phase because the saved history
    includes burnout. No analytic/DOP853 state is used to create simulator data.
    """
    times = np.asarray(times, float)
    if times[0] < 0 or times[-1] > r.t[-1]:
        raise ValueError("Requested grid must be inside the computed ascent.")
    result = np.empty((len(times), 3))
    step = METHODS[r.method]
    for j, target in enumerate(times):
        i = int(np.searchsorted(r.t, target, side="right")-1)
        if r.t[i] == target:
            result[j] = r.y[i]
        else:
            powered = r.t[i] < r.params.burn_time
            f = lambda time, state: phase_rhs(time, state, r.params, powered)
            result[j] = step(f, r.t[i], r.y[i], target-r.t[i])
    return result


def simulate(p, init, t_span, dt):
    """Official signature -> t (N,), Y (N,3).

    events (default): return burnout/apogee events, or stop exactly at a shorter
    requested horizon (needed by the toolkit convergence check).
    fixed_grid: dataset observations on a common grid strictly before apogee.
    Full ascent is computed first; the extra cost avoids a second integration engine.
    """
    if len(t_span) != 2 or not np.all(np.isfinite(t_span)) or t_span[0] != 0 or t_span[1] <= 0:
        raise ValueError("Use launch-relative t_span=[0, positive finite end].")
    physical = parameters(p, init)
    r = ascent(physical, dt=dt, method=p.get("method", "rk4"))
    end = float(t_span[1])
    mode = p.get("output_mode", "events")
    if mode == "fixed_grid":
        if end >= r.apogee.t:
            raise ValueError("Dataset horizon must precede apogee; padding/continued flight is forbidden.")
        n = int(round(end/dt))
        if not np.isclose(n*dt, end, rtol=0, atol=1e-10):
            raise ValueError("fixed_grid requires a horizon divisible by dt.")
        times = np.linspace(0, end, n+1)
        return times, _sample_at(r, times)
    if mode != "events":
        raise ValueError("output_mode must be events or fixed_grid.")
    if end >= r.apogee.t:
        return r.t.copy(), r.y.copy()
    mask = r.t < end
    times = np.r_[r.t[mask], end]
    return times, np.vstack([r.y[mask], _sample_at(r, np.array([end]))])


def analytic(p, init, t):
    physical = parameters(p, init)
    return reference_history(physical, t) if physical.c == 0 else None


def observed_trajectory(p, init, t, Y, dt=0.02):
    """Rehydrate only supplied observations; no cache and no simulator re-run.

    wmlab's three-column contract contains NO acceleration channel. a and the
    one-sided accelerations are derived for compatibility, not independently
    verified data. The official custom checks explicitly omit those tautologies.
    """
    physical = parameters(p, init)
    t, Y = np.asarray(t, float), np.asarray(Y, float)
    if (t.ndim != 1 or len(t) < 3 or Y.shape != (len(t), 3)
            or not np.all(np.isfinite(t)) or not np.all(np.isfinite(Y))
            or np.any(np.diff(t) <= 0) or np.any(Y[:, 2] <= 0)):
        raise ValueError("Invalid finite trajectory contract.")
    ib = int(np.argmin(abs(t-physical.burn_time)))
    if abs(t[ib]-physical.burn_time) > 1e-10:
        raise ValueError("Observed history has no exact burnout event.")
    if t[-1] <= physical.burn_time or abs(Y[-1, 1]) > 1e-8:
        raise ValueError("Observed history does not end at apogee.")
    acc = np.array([phase_rhs(ti, yi, physical, ti < physical.burn_time)[1] for ti,yi in zip(t,Y)])
    before = float(phase_rhs(t[ib], Y[ib], physical, True)[1])
    after = float(phase_rhs(t[ib], Y[ib], physical, False)[1])
    bo = Event(float(t[ib]), Y[ib].copy(), before, after)
    apex = Event(float(t[-1]), Y[-1].copy(), float(acc[-1]), float(acc[-1]))
    return Trajectory(t, Y, acc, bo, apex, physical, p.get("method", "rk4"), dt)


def quantities(p, init, t, Y):
    """Full-flight quantities come from supplied t,Y, never a re-run or reference."""
    return trajectory_quantities(observed_trajectory(p, init, t, Y))


def reference_quantities(p, init):
    physical = parameters(p, init)
    return no_drag_quantities(physical) if physical.c == 0 else scipy_reference(physical)


def bounds(p):
    physical = parameters(p, {})
    return {0:(0, None), 1:(0, None), 2:(physical.mf, physical.m0)}


def _custom(sc, t, Y, name, select):
    try:
        r = observed_trajectory(sc["params"], sc["initial"], t, Y, sc["dt"])
        if name == "event_consistency":
            checks = [c for c in physical_checks(r) if c.name != "thrust_switch"]
        else:
            checks = [c for c in verify_trajectory(r) if select(c)]
        failed = sum(not c.passed for c in checks)
        return {"name":name, "passed":bool(checks) and failed == 0, "value":float(failed),
                "threshold":0, "note":"Checks operate on supplied t,Y. Acceleration is not an exported channel; "
                "no independent acceleration-output claim here (use the v2 Trajectory adapter for that).",
                "details":[c.to_dict() for c in checks]}
    except (ValueError, FloatingPointError) as exc:
        return {"name":name, "passed":False, "value":None, "threshold":0, "note":str(exc)}


def trajectory_reference(sc, mod, t, Y, **_):
    return _custom(sc, t, Y, "trajectory_reference", lambda c: c.category in {"trajectory_contract", "trajectory_reference"})


def dynamics_consistency(sc, mod, t, Y, **_):
    return _custom(sc, t, Y, "dynamics_consistency",
                   lambda c: c.category in {"trajectory_contract", "dynamics_consistency"} and c.name != "dynamics_acceleration")


def event_consistency(sc, mod, t, Y, **_):
    return _custom(sc, t, Y, "event_consistency", lambda c: True)


EXTRA_CHECKS = {"trajectory_reference":trajectory_reference,
                "dynamics_consistency":dynamics_consistency,
                "event_consistency":event_consistency}


def sample(rng):
    """Common [0,4] s, dt=0.02 observations; these are ascent SEGMENTS, not full flights.

    Physically admissible draws use the same documented domain as the local
    dataset. A horizon guard in simulate rejects any draw reaching apogee early.
    Full flights with variable event times remain in local_dataset_200.npz.
    """
    m0 = float(rng.uniform(0.8,1.2))
    mf = m0*(1-float(rng.uniform(0.25,0.45)))
    ve = float(rng.uniform(400,550))
    twr = float(rng.uniform(1.2,15))
    p = {"m0":m0, "mf":mf, "q":twr*m0*9.81/ve, "ve":ve, "g":9.81,
         "c":float(rng.uniform(0,0.003)), "method":"rk4", "output_mode":"fixed_grid"}
    return p, {"h0":0.0, "v0":0.0}, [0.0,4.0], 0.02
