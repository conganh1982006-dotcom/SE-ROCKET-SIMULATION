import argparse
import json
from pathlib import Path
import yaml
from rocket import Parameters, simulate
from rocket.analytic import no_drag_quantities
from .independent import scipy_reference
from .checks import physical_checks, reference_checks, coast_checks
from .trajectory import verify_trajectory, TrajectoryTolerances


def run_scenario(path, simulator=simulate):
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if spec.get("format") != "c5-local-scenario-v1":
        raise ValueError("Only provisional c5-local-scenario-v1 is supported.")
    if spec["expected"] not in ["PASS", "FAIL"]:
        raise ValueError("Expected must be PASS or FAIL.")
    p = Parameters(**spec["parameters"])
    r = simulator(p, **spec["numerical"])
    checks = physical_checks(r)
    ref_type = spec["reference"]
    if ref_type == "analytic_no_drag":
        reference = no_drag_quantities(p)
    elif ref_type == "scipy_dop853":
        reference = scipy_reference(p)
    else:
        raise ValueError(f"Unsupported reference {ref_type}")
    checks += reference_checks(r, reference, **spec.get("tolerances", {}))
    checks += coast_checks(r)
    checks += verify_trajectory(r, params=p,
                                tolerances=TrajectoryTolerances(**spec.get("trajectory_tolerances", {})))
    failed = [c.name for c in checks if not c.passed]
    actual = "FAIL" if failed else "PASS"
    # A FAIL counts as detected only if the named check fails; crashes are errors.
    expected_fail = spec.get("must_fail_check")
    demonstration_pass = actual == spec["expected"] and (spec["expected"] == "PASS" or expected_fail in failed)
    return {"id": spec["id"], "format": spec["format"], "official_wmlab": False,
            "expected": spec["expected"], "actual": actual, "demonstration_pass": demonstration_pass,
            "failed_checks": failed, "checks": [c.to_dict() for c in checks]}


def run_all(directory="scenarios", output="outputs/scenarios", simulator=simulate):
    paths = sorted(Path(directory).glob("*.yaml"))
    if not paths:
        raise ValueError("No scenario YAML files found.")
    Path(output).mkdir(parents=True, exist_ok=True)
    reports = []
    for path in paths:
        report = run_scenario(path, simulator)
        (Path(output)/f"{path.stem}.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        reports.append(report)
    return reports


def main():
    parser = argparse.ArgumentParser(description="LOCAL verifier; no wmlab results are claimed.")
    parser.add_argument("--directory", default="scenarios")
    parser.add_argument("--output", default="outputs/scenarios")
    args = parser.parse_args()
    reports = run_all(args.directory, args.output)
    for r in reports:
        print(f"{r['id']}: actual={r['actual']} expected={r['expected']} "
              f"demonstration={'PASS' if r['demonstration_pass'] else 'FAIL'}; failures={r['failed_checks']}")
    return 0 if all(r["demonstration_pass"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
