"""1D heat equation: u_t = alpha u_xx on [0, L], u(0)=u(L)=0.
params: alpha, L, nx (grid points including boundaries), scheme ("ftcs" or "cn")
initial: modes = {n: b_n}  ->  u(x,0) = sum b_n sin(n pi x / L)
Analytical solution: u = sum b_n sin(n pi x/L) exp(-alpha (n pi/L)^2 t).
Y has shape (number of time steps, nx)."""
import numpy as np

CONVERGENCE_MODE = "self"


def grid(p):
    return np.linspace(0.0, p.get("L", 1.0), int(p.get("nx", 51)))


def _u0(p, init, x):
    L = p.get("L", 1.0)
    return sum(float(b) * np.sin(int(n) * np.pi * x / L) for n, b in init["modes"].items())


def stability_number(p, dt):
    x = grid(p)
    return p["alpha"] * dt / (x[1] - x[0]) ** 2


def simulate(p, init, t_span, dt):
    x = grid(p)
    nx = len(x)
    r = stability_number(p, dt)
    n = int(round((t_span[1] - t_span[0]) / dt))
    t = t_span[0] + dt * np.arange(n + 1)
    U = np.empty((n + 1, nx))
    u = _u0(p, init, x)
    u[0] = u[-1] = 0.0
    U[0] = u
    scheme = p.get("scheme", "cn")
    if scheme == "cn":
        m = nx - 2
        A = np.diag(np.full(m, 1 + r)) + np.diag(np.full(m - 1, -r / 2), 1) + np.diag(np.full(m - 1, -r / 2), -1)
        B = np.diag(np.full(m, 1 - r)) + np.diag(np.full(m - 1, r / 2), 1) + np.diag(np.full(m - 1, r / 2), -1)
        Ainv_B = np.linalg.solve(A, B)
    for i in range(n):
        if scheme == "ftcs":
            u = u.copy()
            u[1:-1] = u[1:-1] + r * (u[2:] - 2 * u[1:-1] + u[:-2])
        else:
            u = u.copy()
            u[1:-1] = Ainv_B @ u[1:-1]
        U[i + 1] = u
    return t, U


def analytic(p, init, t):
    x = grid(p)
    L, a = p.get("L", 1.0), p["alpha"]
    out = np.zeros((len(t), len(x)))
    for n, b in init["modes"].items():
        k = int(n) * np.pi / L
        out += float(b) * np.outer(np.exp(-a * k ** 2 * t), np.sin(k * x))
    return out


def quantities(p, init, t, Y):
    x = grid(p)
    L = p.get("L", 1.0)
    mid = len(x) // 2
    return {"u_mid_final": float(Y[-1, mid]),
            "heat_final": float(np.trapezoid(Y[-1], x)),
            "decay_time_mode1": float(1.0 / (p["alpha"] * (np.pi / L) ** 2)),
            "stability_number": float(stability_number(p, t[1] - t[0]))}


def sample(rng):
    modes = {str(n): float(rng.uniform(-1, 1)) for n in rng.choice([1, 2, 3, 4, 5], size=rng.integers(1, 4), replace=False)}
    p = {"alpha": float(rng.uniform(0.01, 0.1)), "L": 1.0, "nx": 51, "scheme": "cn"}
    return p, {"modes": modes}, [0.0, 1.0], 0.002
