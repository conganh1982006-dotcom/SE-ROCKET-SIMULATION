"""Independent two-state DOP853 cross-check, with algebraic mass.

    Intentionally does not import rocket.rhs or rocket.methods.
"""
import numpy as np
from scipy.integrate import solve_ivp


def scipy_history(p, times, rtol=2e-12, atol=2e-12):
    """Independent dense solution evaluated at the requested times, not a grid.

    Each phase is integrated separately. Coast is integrated to the requested
    final time, even if it is slightly after the independent apogee. There is no
    dense-output extrapolation and no seeding from the simulator's burnout state.
    This small continuation tests time-aligned states; it is not a new simulator.
    """
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or not len(times) or not np.all(np.isfinite(times)) or np.any(times < 0):
        raise ValueError("Reference times must be a nonempty finite 1D array, t >= 0.")
    tb = p.burn_time

    def burn(t, state):
        mass = p.m0 - p.q*t
        return [state[1], (p.q*p.ve-p.c*state[1]*abs(state[1]))/mass-p.g]

    first = solve_ivp(burn, (0, tb), [p.h0, p.v0], method="DOP853",
                      dense_output=True, rtol=rtol, atol=atol)
    if not first.success:
        raise RuntimeError(first.message)
    y = np.empty((len(times), 3))
    powered = times <= tb
    y[powered, :2] = first.sol(times[powered]).T
    if np.any(~powered):
        def coast(t, state):
            return [state[1], -p.g-p.c*state[1]*abs(state[1])/p.mf]
        second = solve_ivp(coast, (tb, float(times.max())), first.y[:, -1],
                           method="DOP853", dense_output=True, rtol=rtol, atol=atol)
        if not second.success:
            raise RuntimeError(second.message)
        y[~powered, :2] = second.sol(times[~powered]).T
    y[:, 2] = p.m0-p.q*np.minimum(times, tb)
    return y


def scipy_reference(p, rtol=2e-12, atol=2e-12):
    def burn(t, state):
        h, v = state
        mass = p.m0 - p.q*t
        return [v, p.q*p.ve/mass - p.g - p.c*v*abs(v)/mass]

    first = solve_ivp(burn, (0, p.burn_time), [p.h0, p.v0], method="DOP853",
                      rtol=rtol, atol=atol, dense_output=True)
    if not first.success:
        raise RuntimeError(first.message)
    hb, vb = first.y[:, -1]

    def coast(t, state):
        return [state[1], -p.g - p.c*state[1]*abs(state[1])/p.mf]

    def apex(t, state): return state[1]
    apex.direction = -1
    apex.terminal = True
    second = solve_ivp(coast, (p.burn_time, p.burn_time+1.1*vb/p.g+1),
                       [hb, vb], method="DOP853", rtol=rtol, atol=atol,
                       events=apex, dense_output=True)
    if not second.success or len(second.t_events[0]) != 1:
        raise RuntimeError("Independent reference did not reach apogee.")
    return {"v_burnout": float(vb), "h_burnout": float(hb),
            "apogee": float(second.y_events[0][0, 0]),
            "t_burnout": p.burn_time, "t_apogee": float(second.t_events[0][0])}
