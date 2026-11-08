"""Charged particle in uniform electric and magnetic fields: m dv/dt = q (E + v x B).
State: x, y, z, vx, vy, vz.
params: q, m, E [Ex,Ey,Ez], B [Bx,By,Bz], scheme ("boris" or "rk4")
initial: r0 [x,y,z], v0 [vx,vy,vz]
For E = 0, the magnetic force does no work: speed should be conserved. The Boris pusher preserves it,
whereas RK4 drifts gradually, illustrating the choice of a scheme that respects physical structure."""
import numpy as np

from ._integ import rk4


def _vecs(p):
    return float(p["q"]), float(p["m"]), np.asarray(p.get("E", [0, 0, 0]), float), np.asarray(p.get("B", [0, 0, 0]), float)


def simulate(p, init, t_span, dt):
    q, m, E, B = _vecs(p)
    y0 = np.concatenate([np.asarray(init["r0"], float), np.asarray(init["v0"], float)])
    if p.get("scheme", "boris") == "rk4":
        return rk4(lambda t, s: np.concatenate([s[3:], q / m * (E + np.cross(s[3:], B))]), y0, t_span, dt)
    n = int(round((t_span[1] - t_span[0]) / dt))
    t = t_span[0] + dt * np.arange(n + 1)
    Y = np.empty((n + 1, 6))
    r, v = y0[:3].copy(), y0[3:].copy()
    Y[0] = y0
    qm = q / m * dt / 2
    tv = qm * B
    sv = 2 * tv / (1 + tv @ tv)
    for i in range(n):
        vm = v + qm * E
        vp = vm + np.cross(vm + np.cross(vm, tv), sv)
        v = vp + qm * E
        r = r + v * dt
        Y[i + 1, :3], Y[i + 1, 3:] = r, v
    return t, Y


def analytic(p, init, t):
    q, m, E, B = _vecs(p)
    if np.any(E) or B[0] or B[1] or not B[2]:
        return None  # Only implemented for E = 0 and B along the z axis.
    w = q * B[2] / m
    x0, y0, z0 = init["r0"]
    vx0, vy0, vz0 = init["v0"]
    c, s = np.cos(w * t), np.sin(w * t)
    vx = vx0 * c + vy0 * s
    vy = -vx0 * s + vy0 * c
    x = x0 + (vx0 * s - vy0 * (c - 1)) / w
    y = y0 + (vx0 * (c - 1) + vy0 * s) / w
    return np.column_stack([x, y, z0 + vz0 * t, vx, vy, np.full_like(t, vz0)])


def energy(p, Y):
    q, m, E, _ = _vecs(p)
    return 0.5 * m * (Y[:, 3:] ** 2).sum(1) - q * Y[:, :3] @ E


def quantities(p, init, t, Y):
    q, m, E, B = _vecs(p)
    out = {"speed_final": float(np.linalg.norm(Y[-1, 3:]))}
    Bn = np.linalg.norm(B)
    if Bn:
        v0 = np.asarray(init["v0"], float)
        vperp = np.linalg.norm(v0 - (v0 @ B) / Bn ** 2 * B)
        out["larmor_radius"] = float(m * vperp / (abs(q) * Bn))
        out["cyclotron_period"] = float(2 * np.pi * m / (abs(q) * Bn))
    if Bn and np.any(E):
        out["drift_speed"] = float(np.linalg.norm(np.cross(E, B)) / Bn ** 2)
    return out


def sample(rng):
    p = {"q": 1.0, "m": 1.0, "E": [float(rng.uniform(-0.5, 0.5)), 0.0, 0.0],
         "B": [0.0, 0.0, float(rng.uniform(0.5, 2))], "scheme": "boris"}
    init = {"r0": [0.0, 0.0, 0.0], "v0": [float(rng.uniform(-1, 1)), float(rng.uniform(-1, 1)), float(rng.uniform(-0.2, 0.2))]}
    return p, init, [0.0, 20.0], 0.01
