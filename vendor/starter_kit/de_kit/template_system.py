"""<PROJECT TITLE> — one-line description of the physical system.

    <write the differential equation(s) here, e.g.  m x'' + c x' + k x = F(t)>

params : <name> [unit] meaning, ...                 (keep units consistent!)
initial: <name> [unit] meaning, ...
Analytic solution: <yes / only when ... / no — explain>

Group: <names and student IDs>
"""
import numpy as np

NAME = "my_system"            # TODO: short lowercase name, no spaces (used as `system:` in scenario files)
STATE = ["x", "v"]            # TODO: names of the state variables, in the order of the vector y
CONVERGENCE_MODE = "analytic" # "analytic" if analytic() works for your baseline case, otherwise "self"
INVARIANT_NAME = "energy"     # TODO (optional): name of the conserved quantity, if your system has one


# =============================================================== 1. THE MODEL
def rhs(t, y, p):
    """Right-hand side f(t, y) of the first-order system y' = f(t, y).
    A second-order equation x'' = g(t, x, x') must be rewritten as y = [x, v], y' = [v, g]."""
    x, v = y
    # TODO: replace with your equations
    return np.array([v, -p["k"] / p["m"] * x])


# =============================================================== 2. NUMERICAL METHODS (provided)
def _step(f, t, y, h, p, method):
    if method == "euler":
        return y + h * f(t, y, p)
    if method == "heun":
        k1 = f(t, y, p)
        k2 = f(t + h, y + h * k1, p)
        return y + h / 2 * (k1 + k2)
    k1 = f(t, y, p)
    k2 = f(t + h / 2, y + h / 2 * k1, p)
    k3 = f(t + h / 2, y + h / 2 * k2, p)
    k4 = f(t + h, y + h * k3, p)
    return y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


def simulate(p, init, t_span, dt):
    """Do not change the signature. Returns t (n+1,) and Y (n+1, len(STATE))."""
    n = int(round((t_span[1] - t_span[0]) / dt))
    t = t_span[0] + dt * np.arange(n + 1)
    Y = np.empty((n + 1, len(STATE)))
    Y[0] = [init["x0"], init["v0"]]          # TODO: build the initial state vector from `init`
    method = p.get("method", "rk4")
    for i in range(n):
        Y[i + 1] = _step(rhs, t[i], Y[i], dt, p, method)
        # TODO (optional): stop or flag events here (hitting the ground, tank empty, ...)
    return t, Y


# =============================================================== 3. ANALYTIC SOLUTION
def analytic(p, init, t):
    """Return the exact solution as an array shaped like Y, or None when no closed form exists
    for these parameters (e.g. the nonlinear case). Derive it by hand and show it in the report."""
    # TODO
    return None


# =============================================================== 4. QUANTITIES OF INTEREST
def quantities(p, init, t, Y):
    """Numbers the project asks for (period, max height, time to empty, final size...).
    Every key here can be used as `question.quantity` in a scenario file."""
    # TODO
    return {"x_final": float(Y[-1, 0])}


def reference_quantities(p, init):
    """OPTIONAL: the same quantities from an INDEPENDENT formula (exact, asymptotic, small-angle...),
    used by the `reference_match` check. Return {} when no formula applies."""
    return {}


# =============================================================== 5. PHYSICAL CONSTRAINTS
def energy(p, Y):
    """OPTIONAL: total energy along the trajectory (enables energy_conserved / energy_nonincreasing)."""
    x, v = Y[:, 0], Y[:, 1]
    return 0.5 * p["m"] * v ** 2 + 0.5 * p["k"] * x ** 2


def invariant(p, Y):
    """OPTIONAL: any other conserved quantity (total population, angular momentum, Lotka–Volterra V...)."""
    return energy(p, Y)


def bounds(p):
    """OPTIONAL: {column index: (min, max)} for physically allowed values; None = no limit.
    Example: populations >= 0, water height between 0 and the tank height."""
    return {}


EXTRA_CHECKS = {}             # OPTIONAL: {"check_name": function(sc, mod, t, Y, **kw) -> dict}, see example_cooling.py


# =============================================================== 6. RANDOM SCENARIOS (dataset)
def sample(rng):
    """Return (params, initial, t_span, dt) drawn from PHYSICALLY REASONABLE ranges.
    The same t_span and dt must be used for every draw. Document the ranges in system_card.yaml."""
    p = {"m": float(rng.uniform(0.5, 2.0)), "k": float(rng.uniform(1.0, 10.0)), "method": "rk4"}
    init = {"x0": float(rng.uniform(-1, 1)), "v0": float(rng.uniform(-1, 1))}
    return p, init, [0.0, 20.0], 0.01
