"""Local adapter contract only. This is NOT an official wmlab API."""
from dataclasses import dataclass, field
from typing import Protocol
import numpy as np
from .model import Parameters


@dataclass
class Event:
    t: float
    state: np.ndarray  # [h (m), v (m/s), m (kg)]
    a_before: float
    a_after: float


@dataclass
class Trajectory:
    t: np.ndarray
    y: np.ndarray  # rows are times, columns h, v, m
    a: np.ndarray  # m/s^2, right-sided value at burnout
    burnout: Event
    apogee: Event
    params: Parameters
    method: str
    dt: float
    diagnostics: list[str] = field(default_factory=list)

    @property
    def h(self): return self.y[:, 0]

    @property
    def v(self): return self.y[:, 1]

    @property
    def m(self): return self.y[:, 2]


class Simulator(Protocol):
    def __call__(self, params: Parameters, dt: float = 0.02,
                 method: str = "rk4") -> Trajectory: ...


def quantities(result: Trajectory) -> dict[str, float]:
    """Peak estimates use samples AND both one-sided burnout accelerations.

    max_acceleration_g is max |d v/dt| / g (coordinate acceleration).
    max_proper_acceleration_g is max |d v/dt + g| / g.
    Interior peaks are sampled estimates; refine dt to quantify their error.
    """
    acc = np.r_[result.a, result.burnout.a_before, result.burnout.a_after]
    return {
        "v_burnout": float(result.burnout.state[1]),
        "h_burnout": float(result.burnout.state[0]),
        "apogee": float(result.apogee.state[0]),
        "t_burnout": float(result.burnout.t),
        "t_apogee": float(result.apogee.t),
        "max_acceleration_g": float(np.max(np.abs(acc)) / result.params.g),
        "max_upward_acceleration_g": float(np.max(acc) / result.params.g),
        "max_proper_acceleration_g": float(np.max(np.abs(acc + result.params.g)) / result.params.g),
    }
