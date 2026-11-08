"""Closed forms derived in docs/MATHEMATICS_VI.md; no integrator dependency."""
import numpy as np
from .model import Parameters


def powered_no_drag(t, p: Parameters):
    t = np.asarray(t, dtype=float)
    if np.any((t < 0) | (t > p.burn_time + 1e-12)):
        raise ValueError("Powered formula only on [0, tb].")
    x = p.q * t / p.m0
    m = p.m0 - p.q * t
    log_ratio = -np.log1p(-x)
    v = p.v0 + p.ve * log_ratio - p.g * t
    integral = x + (1-x) * np.log1p(-x)
    # Prevent cancellation near t=0: sum x^n/[n(n-1)].
    series = sum(x**n / (n*(n-1)) for n in range(2, 9))
    integral = np.where(x < 1e-4, series, integral)
    h = p.h0 + p.v0*t + p.ve*p.m0/p.q*integral - 0.5*p.g*t*t
    return np.stack([h, v, m], axis=-1)


def no_drag_quantities(p: Parameters):
    if p.c != 0:
        raise ValueError("No-drag reference requires c=0.")
    hb, vb, _ = powered_no_drag(p.burn_time, p)
    return {"h_burnout": float(hb), "v_burnout": float(vb),
            "apogee": float(hb + vb*vb/(2*p.g)),
            "t_burnout": p.burn_time, "t_apogee": float(p.burn_time + vb/p.g)}


def no_drag_history(t, p: Parameters):
    if p.c != 0:
        raise ValueError("Requires c=0.")
    t = np.asarray(t, dtype=float)
    ref = no_drag_quantities(p)
    if np.any(t < 0) or np.any(t > ref["t_apogee"] + 1e-9):
        raise ValueError("Reference history is restricted to ascent.")
    y = powered_no_drag(np.minimum(t, p.burn_time), p)
    tau = np.maximum(t-p.burn_time, 0)
    hb, vb = ref["h_burnout"], ref["v_burnout"]
    coast = np.stack([hb+vb*tau-p.g*tau*tau/2, vb-p.g*tau,
                      np.full_like(t, p.mf)], axis=-1)
    return np.where((t > p.burn_time)[..., None], coast, y)


def coast_apogee(hb, vb, p: Parameters):
    """Exact additional height and duration from ANY supplied burnout state.

    With numerical (hb,vb), this only verifies coast propagation, not the burn.
    """
    if vb < 0:
        raise ValueError("Require vb >= 0.")
    k = p.c/p.mf
    if k == 0:
        return float(hb + vb*vb/(2*p.g)), float(vb/p.g)
    x = k*vb*vb/p.g
    ratio = 1.0 if x == 0 else np.arctan(np.sqrt(x))/np.sqrt(x)
    return float(hb + np.log1p(x)/(2*k)), float(vb/p.g*ratio)
