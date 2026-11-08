from dataclasses import asdict, replace
import numpy as np
from scipy.optimize import minimize_scalar
from rocket import Parameters, simulate, quantities
from rocket.analytic import no_drag_quantities
from rocket.simulator import NumericalError
from verification.independent import scipy_reference
from verification.checks import physical_checks


def flight_for_rate(q, c, refinement=1):
    p = Parameters(q=float(q), c=c)
    # Resolve even the shortest burn; always report the actual requested step.
    dt = min(0.025, p.burn_time/120)/refinement
    return simulate(p, dt)


def burn_rate_study():
    base = Parameters()
    threshold = base.m0*base.g/base.ve
    lower = 1.05*threshold
    sweep = []
    for c in [0.0, 0.002]:
        for q in np.geomspace(lower, 2.0, 65):
            r = flight_for_rate(q, c)
            sweep.append({"q_kg_s": float(q), "c_kg_m": c, "burn_time_s": r.params.burn_time,
                          "dt_s": r.dt, **quantities(r)})
    optima = []
    for c in [0.0, 0.002]:
        for upper in [0.5, 1.0, 2.0]:
            # Broad scan before local bounded refinement; do not presume unimodality.
            grid = np.geomspace(lower, upper, 65)
            heights = np.array([quantities(flight_for_rate(q, c))["apogee"] for q in grid])
            candidates = [(float(grid[0]), float(heights[0])), (float(grid[-1]), float(heights[-1]))]
            for i in range(1, len(grid)-1):
                if heights[i] >= heights[i-1] and heights[i] >= heights[i+1]:
                    opt = minimize_scalar(lambda q: -quantities(flight_for_rate(q, c))["apogee"],
                                          bounds=(grid[i-1], grid[i+1]), method="bounded",
                                          options={"xatol": 1e-9})
                    if not opt.success:
                        raise RuntimeError("Burn rate optimizer failed.")
                    candidates.append((float(opt.x), float(-opt.fun)))
            q_star, ha = max(candidates, key=lambda x:x[1])
            r = flight_for_rate(q_star, c)
            refined = quantities(flight_for_rate(q_star, c, refinement=2))
            independent = scipy_reference(r.params)
            optima.append({"c_kg_m": c, "lower_q": lower, "upper_q": upper,
                           "q_star": q_star, "apogee_m": ha,
                           "location": "lower_boundary" if q_star == lower else "upper_boundary" if q_star == upper else "interior",
                           "dt_s": r.dt, "refined_apogee_m": refined["apogee"],
                           "refinement_difference_m": abs(refined["apogee"]-ha),
                           "dop853_difference_m": abs(independent["apogee"]-ha),
                           "max_acceleration_g": quantities(r)["max_acceleration_g"]})
    return {"lift_off_threshold_kg_s": threshold, "search_lower_kg_s": lower,
            "domain_reason": "Assumption: 5% initial thrust margin; upper bounds 0.5, 1, 2 kg/s test sensitivity, not motor specifications.",
            "global_guarantee": False, "sweep": sweep, "optima": optima}


def stability_accuracy_study():
    p = Parameters(c=0.002)
    reference = scipy_reference(p)
    rows = []
    for method in ["euler", "heun", "rk4"]:
        for dt in [8.0, 4.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05, 0.025, 0.0125]:
            row = {"method": method, "dt_s": dt}
            try:
                r = simulate(p, dt, method)
                error = abs(quantities(r)["apogee"]-reference["apogee"])
                z = -2*p.c*np.abs(r.v[:-1])/r.m[:-1]*np.diff(r.t)
                amplification = 1+z
                if method in ["heun", "rk4"]: amplification += z*z/2
                if method == "rk4": amplification += z**3/6+z**4/24
                physical = all(c.passed for c in physical_checks(r))
                row.update(status="PASS" if physical and error <= 0.05 else "ACCURACY_OR_BOUNDS_FAIL",
                           apogee_error_m=error, physical_bounds_pass=physical,
                           frozen_linear_max_amplification=float(np.max(abs(amplification))),
                           reason="Frozen scalar linearization is a diagnostic, not a nonlinear stability proof.")
            except NumericalError as exc:
                row.update(status="GUARD_REJECTED", apogee_error_m=None,
                           physical_bounds_pass=False, frozen_linear_max_amplification=None,
                           reason=str(exc))
            rows.append(row)
    return rows


def peak_study():
    rows = []
    for c in [0, 0.002]:
        for dt in [0.1, 0.05, 0.025, 0.0125]:
            q = quantities(simulate(Parameters(c=c), dt))
            rows.append({"c_kg_m": c, "dt_s": dt,
                         "coordinate_peak_g": q["max_acceleration_g"],
                         "proper_peak_g": q["max_proper_acceleration_g"]})
    return rows


def sample_parameters(n=200, seed=20261024):
    """Illustrative numerical test domain, not experimentally calibrated motors."""
    rng = np.random.default_rng(seed)
    for _ in range(n):
        m0 = rng.uniform(0.8, 1.2)
        mf = m0*(1-rng.uniform(0.25, 0.45))
        ve = rng.uniform(400, 550)
        thrust_weight = rng.uniform(1.2, 15)
        yield Parameters(m0=m0, mf=mf, ve=ve, q=thrust_weight*m0*9.81/ve,
                         c=rng.uniform(0, 0.003))


def generate_local_dataset(path, n=200, seed=20261024):
    times, states, accelerations, parameters, summaries = [], [], [], [], []
    offsets, param_names, quantity_names = [0], None, None
    for p in sample_parameters(n, seed):
        r = simulate(p, min(0.04, p.burn_time/100))
        if not all(c.passed for c in physical_checks(r)):
            raise RuntimeError("Dataset physical verification failed.")
        times.append(r.t); states.append(r.y); accelerations.append(r.a)
        offsets.append(offsets[-1]+len(r.t))
        pd, qd = asdict(p), quantities(r)
        param_names, quantity_names = list(pd), list(qd)
        parameters.append(list(pd.values())); summaries.append(list(qd.values()))
    np.savez_compressed(path, format="c5-local-dataset-v1", official_wmlab=False,
                        seed=seed, offsets=np.array(offsets), t=np.concatenate(times),
                        y=np.concatenate(states), a=np.concatenate(accelerations),
                        parameter_names=param_names, parameters=parameters,
                        quantity_names=quantity_names, quantities=summaries,
                        consent_physeval=False)
    return {"count": n, "seed": seed, "samples": offsets[-1],
            "physical_checks_passed": n, "official_wmlab": False}
