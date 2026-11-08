"""Explicit steps implemented here, not delegated to scipy."""


def euler(f, t, y, dt):
    return y + dt * f(t, y)


def heun(f, t, y, dt):
    k1 = f(t, y)
    k2 = f(t + dt, y + dt * k1)
    return y + dt * (k1 + k2) / 2


def rk4(f, t, y, dt):
    k1 = f(t, y)
    k2 = f(t + dt / 2, y + dt * k1 / 2)
    k3 = f(t + dt / 2, y + dt * k2 / 2)
    k4 = f(t + dt, y + dt * k3)
    return y + dt * (k1 + 2*k2 + 2*k3 + k4) / 6


METHODS = {"euler": euler, "heun": heun, "rk4": rk4}
ORDERS = {"euler": 1, "heun": 2, "rk4": 4}
