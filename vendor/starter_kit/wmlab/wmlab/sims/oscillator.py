"""Forced damped oscillator: m x'' + c x' + k x = F0 cos(w t). State: x, v.
params: m, c, k, F0, w        initial: x0, v0
Full analytical solution for underdamped, critically damped and overdamped cases."""
import numpy as np

from ._integ import rk4

STATE = ["x", "v"]


def simulate(p, init, t_span, dt):
    m, c, k = p["m"], p.get("c", 0.0), p["k"]
    F0, w = p.get("F0", 0.0), p.get("w", 0.0)

    def f(t, s):
        return np.array([s[1], (F0 * np.cos(w * t) - c * s[1] - k * s[0]) / m])

    return rk4(f, [init["x0"], init["v0"]], t_span, dt)


def _forced(p):
    m, c, k = p["m"], p.get("c", 0.0), p["k"]
    F0, w = p.get("F0", 0.0), p.get("w", 0.0)
    if F0 == 0:
        return 0j
    Z = k - m * w ** 2 + 1j * c * w
    if abs(Z) < 1e-12:
        raise ValueError("undamped resonance (c=0, w=sqrt(k/m)): the solution grows linearly; this formula does not apply")
    return F0 / Z


def analytic(p, init, t):
    m, c, k, w = p["m"], p.get("c", 0.0), p["k"], p.get("w", 0.0)
    X = _forced(p)
    xp = (X * np.exp(1j * w * t)).real
    vp = (1j * w * X * np.exp(1j * w * t)).real
    a0, b0 = init["x0"] - X.real, init["v0"] - (1j * w * X).real
    disc = complex(c ** 2 - 4 * m * k)
    r1 = (-c + np.sqrt(disc)) / (2 * m)
    r2 = (-c - np.sqrt(disc)) / (2 * m)
    if abs(r1 - r2) < 1e-10:  # Critical damping.
        r = r1
        A, B = a0, b0 - r * a0
        xh = (A + B * t) * np.exp(r * t)
        vh = (B + r * (A + B * t)) * np.exp(r * t)
    else:
        B = (b0 - r1 * a0) / (r2 - r1)
        A = a0 - B
        xh = A * np.exp(r1 * t) + B * np.exp(r2 * t)
        vh = A * r1 * np.exp(r1 * t) + B * r2 * np.exp(r2 * t)
    return np.column_stack([(xh + xp).real, (vh + vp).real])


def energy(p, Y):
    return 0.5 * p["m"] * Y[:, 1] ** 2 + 0.5 * p["k"] * Y[:, 0] ** 2


def quantities(p, init, t, Y):
    m, c, k = p["m"], p.get("c", 0.0), p["k"]
    q = {"x_final": float(Y[-1, 0]), "natural_period": float(2 * np.pi * np.sqrt(m / k))}
    if c > 0:
        q["quality_factor"] = float(np.sqrt(m * k) / c)
    if c ** 2 < 4 * m * k:
        q["damped_period"] = float(2 * np.pi / np.sqrt(k / m - (c / (2 * m)) ** 2))
    if p.get("F0", 0.0) != 0:
        q["steady_amplitude"] = float(abs(_forced(p)))
    return q


def sample(rng):
    p = {"m": float(rng.uniform(0.5, 2)), "k": float(rng.uniform(1, 20)),
         "c": float(rng.uniform(0.05, 1.0)), "F0": float(rng.choice([0.0, rng.uniform(0.1, 2)])),
         "w": float(rng.uniform(0.5, 5))}
    init = {"x0": float(rng.uniform(-1, 1)), "v0": float(rng.uniform(-1, 1))}
    return p, init, [0.0, 20.0], 0.01
