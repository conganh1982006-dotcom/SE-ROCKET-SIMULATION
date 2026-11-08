"""Errors are against independent closed forms, never against this RK4 solver."""
import argparse
import json
from pathlib import Path
import numpy as np
from rocket import Parameters, simulate, quantities
from rocket.analytic import no_drag_quantities
from rocket.methods import ORDERS


def convergence_study(simulator=simulate, steps=(0.1, 0.05, 0.025, 0.0125), params=None):
    p = Parameters() if params is None else params
    exact = no_drag_quantities(p)
    steps = np.array(steps, dtype=float)
    if len(steps) < 3 or np.any(steps <= 0) or np.any(np.diff(steps) >= 0):
        raise ValueError("Need >=3 positive, strictly decreasing time steps.")
    report = {}
    for method, theoretical in ORDERS.items():
        solutions = [quantities(simulator(p, float(dt), method)) for dt in steps]
        metrics = {}
        for key in ["v_burnout", "h_burnout", "apogee", "t_apogee"]:
            errors = np.array([abs(x[key]-exact[key]) for x in solutions])
            floor = 32*np.finfo(float).eps*max(1, abs(exact[key]))
            resolved = errors > floor
            local = [float(np.log(errors[i]/errors[i+1])/np.log(steps[i]/steps[i+1]))
                     if resolved[i] and resolved[i+1] else None for i in range(len(steps)-1)]
            order = float(np.polyfit(np.log(steps[resolved]), np.log(errors[resolved]), 1)[0]) if resolved.sum() >= 3 else None
            passed = order is not None and abs(order-theoretical) <= 0.35
            metrics[key] = {"reference": exact[key], "absolute_errors": errors.tolist(),
                            "relative_errors": (errors/abs(exact[key])).tolist(),
                            "pairwise_orders": local, "fitted_order": order,
                            "roundoff_floor": floor, "order_tolerance": 0.35,
                            "status": "PASS" if passed else "INCONCLUSIVE" if order is None else "FAIL"}
        report[method] = {"format": "c5-local-convergence-v1", "official_wmlab": False,
                          "dt_s": steps.tolist(), "theoretical_order": theoretical,
                          "metrics": metrics,
                          "passed": all(v["status"] == "PASS" for v in metrics.values())}
    return report


def save_convergence(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for method, result in report.items():
        (output/f"{method}.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="convergence")
    args = parser.parse_args()
    report = convergence_study()
    save_convergence(report, args.output)
    for method, r in report.items():
        print(method, {k: v["fitted_order"] for k,v in r["metrics"].items()}, "PASS" if r["passed"] else "FAIL")
    return 0 if all(r["passed"] for r in report.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
