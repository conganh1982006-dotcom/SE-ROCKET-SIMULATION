"""Lorenz system: x' = sigma (y - x), y' = x (rho - z) - y, z' = x y - beta z.
params: sigma, rho, beta        initial: x, y, z
No analytical solution. Verification quantity: largest Lyapunov exponent
(reference approximately 0.906 for sigma=10, rho=28, beta=8/3)."""
import numpy as np

from ._integ import rk4

STATE = ["x", "y", "z"]
REFERENCE_LYAPUNOV = {(10.0, 28.0, round(8 / 3, 6)): 0.9056}


def _f(p):
    s, r, b = p.get("sigma", 10.0), p.get("rho", 28.0), p.get("beta", 8 / 3)
    return lambda t, u: np.array([s * (u[1] - u[0]), u[0] * (r - u[2]) - u[1], u[0] * u[1] - b * u[2]])


def simulate(p, init, t_span, dt):
    return rk4(_f(p), [init["x"], init["y"], init["z"]], t_span, dt)


def analytic(p, init, t):
    return None


def max_lyapunov(p, init, T=200.0, dt=0.01, transient=20.0, d0=1e-8):
    """Benettin method: two nearby trajectories, renormalizing separation after each step."""
    f = _f(p)

    def step(u):
        k1 = f(0, u); k2 = f(0, u + dt / 2 * k1); k3 = f(0, u + dt / 2 * k2); k4 = f(0, u + dt * k3)
        return u + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    u = np.array([init["x"], init["y"], init["z"]], float)
    for _ in range(int(transient / dt)):
        u = step(u)
    v = u + np.array([d0, 0, 0])
    s = 0.0
    n = int(T / dt)
    for _ in range(n):
        u, v = step(u), step(v)
        d = np.linalg.norm(v - u)
        s += np.log(d / d0)
        v = u + (v - u) * (d0 / d)
    return s / (n * dt)


def reference_lyapunov(p):
    key = (float(p.get("sigma", 10.0)), float(p.get("rho", 28.0)), round(float(p.get("beta", 8 / 3)), 6))
    return REFERENCE_LYAPUNOV.get(key)


def quantities(p, init, t, Y):
    return {"lyapunov_max": float(max_lyapunov(p, init)), "z_mean": float(Y[len(Y) // 2:, 2].mean())}


def sample(rng):
    p = {"sigma": 10.0, "rho": float(rng.uniform(20, 35)), "beta": 8 / 3}
    init = {"x": float(rng.uniform(-10, 10)), "y": float(rng.uniform(-10, 10)), "z": float(rng.uniform(10, 40))}
    return p, init, [0.0, 10.0], 0.01
