from dataclasses import dataclass, asdict
import math
import numpy as np
from rocket.interface import quantities
from rocket.analytic import coast_apogee


@dataclass
class Check:
    name: str
    category: str
    passed: bool
    observed: float
    reference: float
    absolute_error: float
    relative_error: float | None
    atol: float
    rtol: float
    unit: str
    explanation: str

    def to_dict(self):
        return {**asdict(self), "status": "PASS" if self.passed else "FAIL",
                "allowed_error": self.atol + self.rtol*abs(self.reference)}


def match(name, observed, reference, *, atol, rtol=0, unit="1",
          category="reference_match", explanation="|error| <= atol + rtol*|reference|"):
    observed, reference = float(observed), float(reference)
    error = abs(observed-reference)
    return Check(name, category, bool(math.isfinite(error) and error <= atol+rtol*abs(reference)),
                 observed, reference, error, error/abs(reference) if reference else None,
                 atol, rtol, unit, explanation)


UNITS = {"h_burnout": "m", "v_burnout": "m/s", "apogee": "m",
         "t_burnout": "s", "t_apogee": "s"}
DEFAULT_ATOL = {"h_burnout": 0.01, "v_burnout": 0.01, "apogee": 0.05,
                "t_burnout": 1e-10, "t_apogee": 0.001}


def reference_checks(result, reference, atol=None, rtol=1e-6):
    actual = quantities(result)
    limits = DEFAULT_ATOL if atol is None else {**DEFAULT_ATOL, **atol}
    return [match(key, actual[key], value, atol=limits[key], rtol=rtol, unit=UNITS[key])
            for key, value in reference.items() if key in UNITS]


def physical_checks(r):
    """Tests consume only the local contract; adapters can reuse them unchanged."""
    p = r.params
    def bound(name, violation, tol, unit, explanation):
        return match(name, violation, 0, atol=tol, unit=unit,
                     category="within_bounds", explanation=explanation)

    if (r.y.shape != (len(r.t), 3) or r.a.shape != r.t.shape or len(r.t) < 3
            or not np.all(np.isfinite(r.y)) or not np.all(np.isfinite(r.t))
            or not np.all(np.isfinite(r.a))):
        return [bound("finite_contract", 1, 0, "1", "Finite aligned arrays required.")]
    expected_mass = p.m0-p.q*np.minimum(r.t, p.burn_time)
    coast = r.t >= p.burn_time
    bo_idx = int(np.argmin(abs(r.t-r.burnout.t)))
    checks = [
        bound("increasing_time", float(np.any(np.diff(r.t) <= 0)), 0, "1", "Time must strictly increase."),
        bound("initial_time", abs(r.t[0]), 1e-12, "s", "Start at t=0."),
        bound("mass_above_dry", max(0, p.mf-float(r.m.min())), 1e-10, "kg", "Physical dry-mass lower bound."),
        bound("mass_positive", float(np.any(r.m <= 0)), 0, "1", "Physical positive mass."),
        bound("mass_law", float(np.max(abs(r.m-expected_mass))), 1e-10, "kg", "Assumed constant burn rate, then constant dry mass."),
        bound("coast_mass", float(np.max(abs(r.m[coast]-p.mf))) if np.any(coast) else 1, 1e-10, "kg", "No fuel consumption after burnout."),
        bound("ascent_velocity", max(0, -float(r.v.min())), 1e-8, "m/s", "Ascent-only trajectory; stop at first apogee."),
        bound("nondecreasing_altitude", max(0, -float(np.diff(r.h).min())), 1e-8, "m", "Altitude cannot decrease on ascent."),
        bound("apogee_velocity", abs(r.apogee.state[1]), 1e-8, "m/s", "Root residual before any cosmetic zeroing."),
        bound("terminal_event_time", abs(r.t[-1]-r.apogee.t), 1e-10, "s", "Last sample is the apogee event."),
        bound("burnout_sample_time", abs(r.t[bo_idx]-r.burnout.t), 1e-10, "s", "Store the burnout event exactly."),
        match("burnout_time", r.burnout.t, p.burn_time, atol=1e-10, unit="s", category="within_bounds"),
        bound("event_sequence", float(r.apogee.t <= r.burnout.t), 0, "1", "Apogee follows burnout in this launch domain."),
        match("thrust_switch", r.burnout.a_before-r.burnout.a_after, p.q*p.ve/p.mf,
              atol=1e-9, unit="m/s^2", category="within_bounds"),
    ]
    for j, (name, unit, expected) in enumerate(zip(["h", "v", "m"], ["m", "m/s", "kg"], [p.h0, p.v0, p.m0])):
        checks += [match(f"initial_{name}", r.y[0,j], expected, atol=1e-10, unit=unit, category="within_bounds"),
                   match(f"terminal_{name}", r.y[-1,j], r.apogee.state[j], atol=1e-10, unit=unit, category="within_bounds"),
                   match(f"burnout_{name}", r.y[bo_idx,j], r.burnout.state[j], atol=1e-10, unit=unit, category="within_bounds")]
    return checks


def coast_checks(r, height_atol=0.05, time_atol=0.001):
    h, duration = coast_apogee(r.burnout.state[0], r.burnout.state[1], r.params)
    return [match("coast_height_relation", r.apogee.state[0], h, atol=height_atol, unit="m"),
            match("coast_time_relation", r.apogee.t-r.burnout.t, duration, atol=time_atol, unit="s")]
