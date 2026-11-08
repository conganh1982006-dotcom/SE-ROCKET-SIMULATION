"""Student CLI. Delegate all physics and verification to the existing V3 modules."""
import argparse
from dataclasses import fields
import math
from pathlib import Path
import subprocess
import sys

from rocket import Parameters


ROOT = Path(__file__).resolve().parent
SIMULATION_MODES = ("no-drag", "with-drag", "compare")
PARAMETER_LABELS = {
    "m0": "Initial mass (kg)",
    "mf": "Dry mass (kg)",
    "q": "Propellant consumption rate (kg/s)",
    "ve": "Exhaust velocity (m/s)",
    "g": "Gravitational acceleration (m/s²)",
    "h0": "Initial altitude (m)",
    "v0": "Initial velocity (m/s)",
}


def finite_number(value):
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Enter a number, for example 0.02.") from exc
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("The value must be finite; NaN/Inf are not allowed.")
    return number


def positive_number(value):
    number = finite_number(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("The value must be greater than 0.")
    return number


def build_parser():
    parser = argparse.ArgumentParser(
        description="C5 Rocket V3.1 — simulation, verification and reporting.",
        epilog="No arguments: open the menu. Guide: QUICKSTART_EN.md.",
    )
    commands = parser.add_subparsers(dest="mode", metavar="MODE")
    defaults = {field.name: field.default for field in fields(Parameters)}
    for mode, description in [
        ("no-drag", "No Drag Simulation"),
        ("with-drag", "With Drag Simulation"),
        ("compare", "Compare No Drag vs With Drag"),
    ]:
        command = commands.add_parser(mode, help=description, description=description)
        command.add_argument("--method", type=str.lower, choices=("euler", "heun", "rk4"),
                             default="rk4", help="Numerical method (default: rk4)")
        command.add_argument("--dt", type=positive_number, default=0.02,
                             help="Time step in seconds (default: 0.02)")
        if mode != "no-drag":
            command.add_argument("--c", type=positive_number, default=0.002,
                                 help="Drag coefficient in kg/m, > 0 (default: 0.002)")
        for name, label in PARAMETER_LABELS.items():
            command.add_argument(f"--{name}", type=finite_number, default=defaults[name],
                                 help=f"{label} (default: {defaults[name]:g})")
    commands.add_parser("verify", help="Run Verification — pytest, local checks and the actual wmlab toolkit")
    commands.add_parser("report", help="Generate Report — reproduce all evidence and reports")
    return parser


def run_modules(modules):
    """Use the current environment and project directory, even from another cwd."""
    for arguments in modules:
        print(f"\nRunning: {' '.join(arguments)}", flush=True)
        result = subprocess.run([sys.executable, "-m", *arguments], cwd=ROOT)
        if result.returncode:
            print(f"Stopped: the preceding step returned exit code {result.returncode}.", file=sys.stderr)
            return result.returncode
    return 0


def execute(args):
    if args.mode in SIMULATION_MODES:
        from experiments.quick_runs import run_quick

        params = Parameters(**{name: getattr(args, name) for name in PARAMETER_LABELS},
                            c=0.0 if args.mode == "no-drag" else args.c)
        run_quick(args.mode, params, args.dt, args.method, project_root=ROOT)
        return 0
    if args.mode == "verify":
        print("Checking the V3 configurations. The deliberately inaccurate Euler case must be detected as FAIL.", flush=True)
        code = run_modules([
            ["pytest", "-q"],
            ["verification.scenarios"],
            ["verification.convergence"],
            ["verification.mutations"],
            ["scripts.wmlab_verify"],
        ])
        if code == 0:
            print("Verification complete: all outcomes match expectations.")
        return code
    if args.mode == "report":
        print("Reproducing the V3 tests, experiments, wmlab checks, datasets and standard report.\n"
              "Standard results in outputs/ will be updated; quick_runs/ will be retained.", flush=True)
        return run_modules([["scripts.reproduce"]])
    raise ValueError(f"Unsupported mode: {args.mode}")


def ask_number(label, default, *, positive=False):
    while True:
        value = input(f"{label} [{default:g}]: ").strip()
        try:
            return (positive_number if positive else finite_number)(value or str(default))
        except argparse.ArgumentTypeError as exc:
            print(f"Invalid input: {exc}")


def interactive_arguments(mode):
    args = build_parser().parse_args([mode])
    if mode not in SIMULATION_MODES:
        return args
    print("Press Enter to use the default value.")
    while True:
        method = input("Method euler / heun / rk4 [rk4]: ").strip().lower() or "rk4"
        if method in ("euler", "heun", "rk4"):
            args.method = method
            break
        print("Choose euler, heun or rk4.")
    args.dt = ask_number("Time step dt (s)", args.dt, positive=True)
    if mode != "no-drag":
        args.c = ask_number("Drag coefficient c (kg/m)", args.c, positive=True)
    while True:
        choice = input("Change the other physical parameters? y/n [n]: ").strip().lower() or "n"
        if choice in ("y", "n"):
            break
        print("Enter y or n.")
    if choice == "y":
        for name, label in PARAMETER_LABELS.items():
            setattr(args, name, ask_number(label, getattr(args, name)))
    return args


def error_message(exc):
    print(f"Unable to complete: {exc}\n"
          "Check: m0 > mf > 0; q, ve, g > 0; h0, v0 >= 0; q*ve > m0*g.\n"
          "If the integration step is unstable, try reducing dt. See QUICKSTART_EN.md.",
          file=sys.stderr)


def interactive_menu():
    modes = {"1": "no-drag", "2": "with-drag", "3": "compare", "4": "verify", "5": "report"}
    while True:
        print("\nC5 ROCKET — CONTROL MENU\n"
              "  1. No Drag Simulation\n"
              "  2. With Drag Simulation\n"
              "  3. Compare No Drag vs With Drag\n"
              "  4. Run Verification (local + official wmlab)\n"
              "  5. Generate Report\n"
              "  0. Exit")
        choice = input("Select [0–5]: ").strip()
        if choice == "0":
            return 0
        if choice not in modes:
            print("Please select a number from 0 to 5.")
            continue
        try:
            code = execute(interactive_arguments(modes[choice]))
        except (ValueError, RuntimeError, ArithmeticError, OSError) as exc:
            error_message(exc)
            continue
        if code:
            return code


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return interactive_menu() if args.mode is None else execute(args)
    except (EOFError, KeyboardInterrupt):
        print("\nMenu closed / operation interrupted.")
        return 130
    except (ValueError, RuntimeError, ArithmeticError, OSError) as exc:
        error_message(exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
