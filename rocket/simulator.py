import math
import numpy as np
from .model import Parameters, rhs
from .methods import METHODS
from .interface import Event, Trajectory


class NumericalError(RuntimeError):
    """The chosen step cannot resolve a physically admissible ascent."""


def _apogee_step(step, f, t, y, dt, time_tol):
    """Bisect v(step(y, s))=0; re-integrate from the SAME left state.

    Preserves the method's local order; linear endpoint interpolation would
    generally limit high-order event accuracy. This does not remove prior error.
    """
    lo, hi = 0.0, dt
    for _ in range(100):
        mid = (lo + hi) / 2
        trial = step(f, t, y, mid)
        if not np.all(np.isfinite(trial)):
            raise NumericalError("Non-finite apogee trial; reduce dt.")
        if trial[1] > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= time_tol:
            break
    s = (lo + hi) / 2
    return s, step(f, t, y, s)


def simulate(params=None, dt=0.02, method="rk4", *, event_tol=1e-12,
             max_steps=1_000_000):
    p = Parameters() if params is None else params
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive.")
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}; choose {list(METHODS)}.")
    if not math.isfinite(event_tol) or event_tol <= 0 or max_steps < 1:
        raise ValueError("Require event_tol > 0 and max_steps >= 1.")
    step = METHODS[method]
    tb = p.burn_time
    t, y = 0.0, np.array([p.h0, p.v0, p.m0], dtype=float)
    times, states = [t], [y.copy()]
    burnout = None
    for _ in range(max_steps):
        powered = burnout is None
        f = lambda time, state: rhs(time, state, p, powered)
        # t+dt can round to tb even when dt is one ulp below tb-t.
        # Decide the switch using the prospective TIME, not ds equality.
        reaches_burnout = powered and t + dt >= tb
        ds = tb - t if reaches_burnout else dt
        if t + ds == t:
            raise NumericalError("Step below floating-point time resolution.")
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                yn = step(f, t, y, ds)
            except FloatingPointError as exc:
                raise NumericalError("Invalid numerical step; reduce dt.") from exc
        if not np.all(np.isfinite(yn)):
            raise NumericalError("Non-finite trajectory; reduce dt.")
        if powered and (yn[1] < -1e-10 or yn[0] < y[0] - 1e-9):
            raise NumericalError("Powered ascent violated; reduce dt.")
        if not powered:
            if yn[1] > y[1] + 1e-9:
                raise NumericalError("Coasting velocity increased; unresolved step.")
            if yn[1] <= 0:
                ds, yn = _apogee_step(step, f, t, y, ds, event_tol)
                t += ds
                yn[2] = p.mf
                times.append(t)
                states.append(yn.copy())
                a = float(rhs(t, yn, p, False)[1])
                apogee = Event(t, yn.copy(), a, a)
                break
        tn = t + ds
        if reaches_burnout:
            tn = tb
            if abs(yn[2] - p.mf) > 1e-9 * p.m0:
                raise NumericalError("Mass integration is inconsistent at burnout.")
            # Only correct roundoff at the analytically known phase boundary.
            yn[2] = p.mf
            burnout = Event(tn, yn.copy(), float(rhs(tn, yn, p, True)[1]),
                            float(rhs(tn, yn, p, False)[1]))
        t, y = tn, yn
        times.append(t)
        states.append(y.copy())
    else:
        raise NumericalError("max_steps exceeded before apogee; no partial success.")
    time_array, state_array = np.array(times), np.array(states)
    accelerations = np.array([rhs(ti, yi, p, ti < tb)[1]
                              for ti, yi in zip(time_array, state_array)])
    return Trajectory(time_array, state_array, accelerations, burnout, apogee,
                      p, method, dt)
