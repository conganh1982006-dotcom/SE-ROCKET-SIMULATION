"""Projectile with quadratic drag: a = g_vec - (k/m)|v| v. State: x, y, vx, vy.
params: g (m/s^2), k_over_m (1/m; 0 means no drag), m (kg; used only for energy)
initial: v0 (m/s), angle_deg, h0 (m)"""
import numpy as np

from ._integ import rk4

STATE = ["x", "y", "vx", "vy"]


def _y0(init):
    a = np.radians(init["angle_deg"])
    return [0.0, init.get("h0", 0.0), init["v0"] * np.cos(a), init["v0"] * np.sin(a)]


def simulate(p, init, t_span, dt):
    g, b = p.get("g", 9.81), p.get("k_over_m", 0.0)

    def f(t, s):
        vx, vy = s[2], s[3]
        sp = np.hypot(vx, vy)
        return np.array([vx, vy, -b * sp * vx, -g - b * sp * vy])

    return rk4(f, _y0(init), t_span, dt)


def analytic(p, init, t):
    if p.get("k_over_m", 0.0) != 0.0:
        return None
    g = p.get("g", 9.81)
    x0, y0, vx, vy = _y0(init)
    return np.column_stack([x0 + vx * t, y0 + vy * t - g * t ** 2 / 2,
                            np.full_like(t, vx), vy - g * t])


def energy(p, Y):
    m, g = p.get("m", 1.0), p.get("g", 9.81)
    return 0.5 * m * (Y[:, 2] ** 2 + Y[:, 3] ** 2) + m * g * Y[:, 1]


def quantities(p, init, t, Y):
    y = Y[:, 1]
    q = {"max_height": float(y.max())}
    idx = np.where((y[:-1] > 0) & (y[1:] <= 0))[0]
    idx = idx[t[idx] > 0]
    if len(idx):
        i = idx[0]
        w = y[i] / (y[i] - y[i + 1])  # Linear interpolation of ground impact.
        q["flight_time"] = float(t[i] + w * (t[i + 1] - t[i]))
        q["range"] = float(Y[i, 0] + w * (Y[i + 1, 0] - Y[i, 0]))
        v = Y[i] + w * (Y[i + 1] - Y[i])
        q["impact_speed"] = float(np.hypot(v[2], v[3]))
    return q


def sample(rng):
    p = {"g": 9.81, "k_over_m": float(rng.choice([0.0, rng.uniform(0.001, 0.03)])), "m": 1.0}
    init = {"v0": float(rng.uniform(5, 40)), "angle_deg": float(rng.uniform(10, 80)),
            "h0": float(rng.uniform(0, 10))}
    return p, init, [0.0, 10.0], 0.005
