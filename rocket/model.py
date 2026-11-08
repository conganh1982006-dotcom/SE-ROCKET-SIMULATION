"""SI units; positive h and v point upward."""
from dataclasses import dataclass, asdict
import math
import numpy as np


@dataclass(frozen=True)
class Parameters:
    m0: float = 1.0
    mf: float = 0.6
    q: float = 0.2
    ve: float = 500.0
    g: float = 9.81
    c: float = 0.0
    h0: float = 0.0
    v0: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(x) for x in asdict(self).values()):
            raise ValueError("Every physical parameter must be finite.")
        if not (self.m0 > self.mf > 0):
            raise ValueError("Require m0 > mf > 0 kg.")
        if min(self.q, self.ve, self.g) <= 0 or self.c < 0:
            raise ValueError("Require q, ve, g > 0 and c >= 0.")
        if self.h0 < 0 or self.v0 < 0:
            raise ValueError("This ascent-only model requires h0, v0 >= 0.")
        if self.q * self.ve <= self.m0 * self.g:
            raise ValueError("Insufficient initial thrust: require q*ve > m0*g. "
                             "Pad support and delayed liftoff are outside this model.")
        if not math.isfinite(self.burn_time) or self.burn_time <= 0:
            raise ValueError("Burn time must be finite and positive.")

    @property
    def burn_time(self):
        return (self.m0 - self.mf) / self.q


def rhs(t, y, p: Parameters, powered: bool):
    """Phase is explicit so RK endpoint stages never straddle the thrust switch."""
    h, v, m = y
    if m <= 0:
        raise FloatingPointError("Nonpositive stage mass.")
    thrust = p.q * p.ve if powered else 0.0
    return np.array([v, (thrust - p.c * v * abs(v)) / m - p.g,
                     -p.q if powered else 0.0])
