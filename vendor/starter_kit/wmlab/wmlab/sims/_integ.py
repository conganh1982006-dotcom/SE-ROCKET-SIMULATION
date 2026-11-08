import numpy as np


def rk4(f, y0, t_span, dt):
    t0, t1 = t_span
    n = int(round((t1 - t0) / dt))
    t = t0 + dt * np.arange(n + 1)
    Y = np.empty((n + 1, len(y0)))
    Y[0] = y = np.asarray(y0, float)
    for i in range(n):
        ti = t[i]
        k1 = f(ti, y)
        k2 = f(ti + dt / 2, y + dt / 2 * k1)
        k3 = f(ti + dt / 2, y + dt / 2 * k2)
        k4 = f(ti + dt, y + dt * k3)
        y = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        Y[i + 1] = y
    return t, Y
