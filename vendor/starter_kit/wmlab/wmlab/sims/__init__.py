"""Reference simulators. Each module provides:
    simulate(p, init, t_span, dt) -> (t, Y)
    analytic(p, init, t)          -> Y or None (when no analytical solution exists)
    quantities(p, init, t, Y)     -> dict of quantities available for question fields
    sample(rng)                  -> random (p, init, t_span, dt) for dataset generation
and optionally energy(p, Y).
Students add a system by implementing this interface and registering it in REGISTRY."""
from ._integ import rk4  # noqa: F401
from . import projectile_drag, oscillator, heat1d, lorenz, langevin, lorentz, heat2d

REGISTRY = {
    "projectile_drag": projectile_drag,
    "oscillator": oscillator,
    "heat1d": heat1d,
    "lorenz": lorenz,
    "langevin": langevin,
    "lorentz": lorentz,
    "heat2d": heat2d,
}
