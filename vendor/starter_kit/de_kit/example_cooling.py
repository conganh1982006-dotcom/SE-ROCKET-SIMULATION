"""Cooling of a hot drink: Newton (convective) cooling plus optional radiative loss.

    dT/dt = -k (T - T_env) - r (T^4 - T_env^4)          T in kelvin, t in minutes

params : k [1/min] convective rate, r [1/(min K^3)] radiative coefficient (0 = Newton only),
         T_env [K] room temperature, T_target [K] "drinkable" temperature, method ("rk4"|"heun"|"euler")
initial: T0 [K]
Analytic solution exists only when r = 0:  T(t) = T_env + (T0 - T_env) exp(-k t).

This file is the WORKED EXAMPLE for the Differential Equations project. Copy template_system.py
for your own project and follow the same structure.
"""
import numpy as np

NAME = "cooling"                      # system name used in scenario files
STATE = ["T"]                         # names of the state variables (columns of Y)
CONVERGENCE_MODE = "analytic"         # "analytic" if analytic() exists for typical cases, else "self"


# ---------------------------------------------------------------- the model
def rhs(t, y, p):
    T = y[0]
    k, r, Te = p["k"], p.get("r", 0.0), p["T_env"]
    return np.array([-k * (T - Te) - r * (T ** 4 - Te ** 4)])


# ---------------------------------------------------------------- numerical methods
def _step(f, t, y, h, p, method):
    if method == "euler":
        return y + h * f(t, y, p)
    if method == "heun":
        k1 = f(t, y, p)
        k2 = f(t + h, y + h * k1, p)
        return y + h / 2 * (k1 + k2)
    k1 = f(t, y, p)                                   # classical RK4 (default)
    k2 = f(t + h / 2, y + h / 2 * k1, p)
    k3 = f(t + h / 2, y + h / 2 * k2, p)
    k4 = f(t + h, y + h * k3, p)
    return y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


def simulate(p, init, t_span, dt):
    n = int(round((t_span[1] - t_span[0]) / dt))
    t = t_span[0] + dt * np.arange(n + 1)
    Y = np.empty((n + 1, len(STATE)))
    Y[0] = [init["T0"]]
    method = p.get("method", "rk4")
    for i in range(n):
        Y[i + 1] = _step(rhs, t[i], Y[i], dt, p, method)
    return t, Y


# ---------------------------------------------------------------- analytic solution (or None)
def analytic(p, init, t):
    if p.get("r", 0.0) != 0.0:
        return None
    Te = p["T_env"]
    return (Te + (init["T0"] - Te) * np.exp(-p["k"] * np.asarray(t)))[:, None]


# ---------------------------------------------------------------- quantities the project asks for
def _first_crossing(t, x, level):
    idx = np.where((x[:-1] > level) & (x[1:] <= level))[0]
    if not len(idx):
        return float("nan")
    i = idx[0]
    w = (x[i] - level) / (x[i] - x[i + 1])
    return float(t[i] + w * (t[i + 1] - t[i]))


def quantities(p, init, t, Y):
    T = Y[:, 0]
    Te = p["T_env"]
    half = Te + (init["T0"] - Te) / 2
    return {"T_final": float(T[-1]),
            "time_to_target": _first_crossing(t, T, p["T_target"]),
            "half_time": _first_crossing(t, T, half)}


def reference_quantities(p, init):
    """Independent formulas used by the 'reference_match' check (only when r = 0)."""
    if p.get("r", 0.0) != 0.0:
        return {}
    k, Te, T0 = p["k"], p["T_env"], init["T0"]
    return {"time_to_target": float(np.log((T0 - Te) / (p["T_target"] - Te)) / k),
            "half_time": float(np.log(2) / k)}


# ---------------------------------------------------------------- physical constraints
def bounds(p):
    """Column index -> (min, max). A cooling drink stays between room temperature and its start value."""
    return {0: (p["T_env"], None)}


def _monotone_cooling(sc, mod, t, Y, **_):
    """Project-specific check: temperature must never increase while cooling."""
    rise = float(np.diff(Y[:, 0]).max())
    return {"name": "monotone_cooling", "passed": rise <= 1e-12, "value": rise, "threshold": 0.0,
            "note": "largest temperature increase between two steps (must be <= 0)"}


EXTRA_CHECKS = {"monotone_cooling": _monotone_cooling}


# ---------------------------------------------------------------- random scenarios for the dataset
def sample(rng):
    """Draw PHYSICALLY REASONABLE parameters. Every draw must use the same t_span and dt."""
    p = {"k": float(rng.uniform(0.02, 0.10)),
         "r": float(rng.choice([0.0, rng.uniform(1e-10, 4e-10)])),
         "T_env": float(rng.uniform(293.0, 303.0)),
         "T_target": 333.15,
         "method": "rk4"}
    init = {"T0": float(rng.uniform(353.0, 368.0))}
    return p, init, [0.0, 120.0], 0.5
