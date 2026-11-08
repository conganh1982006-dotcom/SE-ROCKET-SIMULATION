"""Reproducible evidence that clean trajectories pass and copies with faults fail."""
import argparse
from copy import deepcopy
import csv
import json
from pathlib import Path
from rocket import Parameters, simulate
import numpy as np
from .trajectory import verify_trajectory, TrajectoryTolerances
from dataclasses import asdict


def mutation_study(simulator=simulate):
    clean_reports, cases = [], []
    for c in [0.0, 0.002]:
        clean = simulator(Parameters(c=c), dt=0.02, method="rk4")
        saved_y, saved_a = clean.y.copy(), clean.a.copy()
        saved_burnout, saved_apogee = deepcopy(clean.burnout), deepcopy(clean.apogee)
        clean_checks = verify_trajectory(clean)
        clean_reports.append({"c_kg_m": c, "sample_count": len(clean.t),
                              "passed": all(x.passed for x in clean_checks),
                              "checks": [x.to_dict() for x in clean_checks]})
        for at_time in [1.0, 3.0]:
            for field, delta, unit, dynamics in [
                ("v", 25.0, "m/s", "dynamics_v_prime"),
                ("h", 1.0, "m", "dynamics_h_prime"),
                ("m", 0.02, "kg", "dynamics_m_prime_burn" if at_time < clean.params.burn_time else "dynamics_m_prime_coast"),
                ("a", 25.0, "m/s^2", "dynamics_acceleration"),
            ]:
                bad = deepcopy(clean)
                index = int(np.argmin(abs(bad.t-at_time)))
                getattr(bad, field)[index] += delta
                checks = verify_trajectory(bad)
                failed = [x.name for x in checks if not x.passed]
                reference = f"trajectory_{field}" if field != "a" else None
                detected = dynamics in failed and (reference is None or reference in failed)
                untouched = (np.array_equal(clean.y, saved_y) and np.array_equal(clean.a, saved_a)
                             and np.array_equal(bad.burnout.state, saved_burnout.state)
                             and np.array_equal(bad.apogee.state, saved_apogee.state)
                             and bad.burnout.t == saved_burnout.t and bad.apogee.t == saved_apogee.t)
                cases.append({"c_kg_m": c, "field": field, "time_s": float(bad.t[index]),
                              "sample_index": index, "delta": delta, "unit": unit,
                              "expected_reference_failure": reference, "expected_dynamics_failure": dynamics,
                              "actual": "FAIL" if failed else "PASS", "detected": detected,
                              "original_and_events_unchanged": untouched,
                              "demonstration_pass": detected and untouched,
                              "failed_checks": failed, "checks": [x.to_dict() for x in checks]})
    passed = all(x["passed"] for x in clean_reports) and all(x["demonstration_pass"] for x in cases)
    return {"format": "c5-local-trajectory-verification-v2", "official_wmlab": False,
            "tolerances": asdict(TrajectoryTolerances()), "clean": clean_reports,
            "mutations": cases, "passed": passed,
            "detected_count": sum(x["detected"] for x in cases), "mutation_count": len(cases)}


def write_mutation_report(output="outputs", simulator=simulate):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = mutation_study(simulator)
    (output/"trajectory_verification.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    rows = []
    for case in report["clean"]+report["mutations"]:
        for check in case["checks"]:
            if "max_absolute_error" not in check:
                continue
            rows.append({"case": "clean" if "field" not in case else f"{case['field']}@{case['time_s']:.6g}s",
                         "c_kg_m": case["c_kg_m"], "check": check["name"], "status": check["status"],
                         **{k: check[k] for k in ["unit", "sample_count", "max_absolute_error", "max_relative_error",
                                                 "relative_undefined_count", "max_error_ratio", "worst_time_s",
                                                 "min_allowed_error", "max_allowed_error", "allowed_error_at_worst"]}})
    with (output/"trajectory_verification.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs")
    args = parser.parse_args()
    report = write_mutation_report(args.output)
    for clean in report["clean"]:
        print(f"Clean c={clean['c_kg_m']}: {'PASS' if clean['passed'] else 'FAIL'} ({clean['sample_count']} samples)")
    print(f"Detected mutations: {report['detected_count']}/{report['mutation_count']}")
    print("Demonstration:", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
