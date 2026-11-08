import argparse
import csv
import json
import platform
from dataclasses import asdict
from pathlib import Path
import importlib.metadata
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
from rocket import Parameters, simulate, quantities
from rocket.analytic import no_drag_quantities
from verification.checks import match
from verification.independent import scipy_reference
from verification.convergence import convergence_study, save_convergence
from verification.scenarios import run_all
from verification.mutations import write_mutation_report
from .studies import burn_rate_study, stability_accuracy_study, peak_study, generate_local_dataset

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def write_csv(path, rows):
    if not rows: raise ValueError("No rows to write")
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def generate(output=None, dataset_n=200):
    out = ROOT/"outputs" if output is None else Path(output)
    out.mkdir(parents=True, exist_ok=True)
    figures = out/"figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 130, "savefig.dpi": 180})
    histories = [simulate(Parameters(c=c), 0.02) for c in [0, 0.002]]
    baseline = [{"c_kg_m": r.params.c, "dt_s": r.dt, **quantities(r)} for r in histories]
    write_csv(out/"baseline.csv", baseline)
    for r, name in zip(histories, ["no_drag", "drag"]):
        np.savetxt(out/f"history_{name}.csv", np.column_stack([r.t, r.y, r.a]), delimiter=",",
                   header="t_s,h_m,v_m_s,m_kg,a_m_s2", comments="")
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.8))
    for r in histories:
        label = f"c = {r.params.c:g} kg/m"
        for ax, data in zip(axes.flat, [r.h, r.v, r.a/r.params.g, r.m]):
            ax.plot(r.t, data, label=label)
            ax.axvline(r.burnout.t, color="#999999", lw=0.5, alpha=0.6)
            ax.set_xlabel("Time (s)"); ax.grid(alpha=0.2)
        axes[0,0].scatter([r.apogee.t], [r.apogee.state[0]], s=22)
        # Display the otherwise missing left limit of acceleration at burnout.
        axes[1,0].plot([r.burnout.t]*2, [r.burnout.a_before/r.params.g, r.burnout.a_after/r.params.g], lw=1)
    for ax, label in zip(axes.flat, ["Altitude (m)", "Velocity (m/s)", "Coordinate acceleration (g)", "Mass (kg)"]): ax.set_ylabel(label)
    axes[0,0].legend(); fig.suptitle("C5 ascent to apogee — RK4, dt = 0.02 s")
    fig.tight_layout(); fig.savefig(figures/"trajectories.png"); plt.close(fig)

    convergence = convergence_study()
    save_convergence(convergence, ROOT/"convergence")
    rows = []
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7))
    for ax, metric in zip(axes, ["v_burnout", "h_burnout", "apogee"]):
        for method, study in convergence.items():
            m = study["metrics"][metric]
            ax.loglog(study["dt_s"], m["absolute_errors"], "o-", label=f"{method}: p={m['fitted_order']:.3f}")
        ax.set(title=metric, xlabel="Time step (s)", ylabel="Absolute error (m/s)" if metric == "v_burnout" else "Absolute error (m)")
        ax.set_xticks([0.0125, 0.025, 0.05, 0.1], labels=["0.0125", "0.025", "0.05", "0.1"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(which="both", alpha=0.25); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figures/"convergence.png"); plt.close(fig)
    for method, study in convergence.items():
        for metric, m in study["metrics"].items():
            for i, dt in enumerate(study["dt_s"]):
                rows.append({"method": method, "metric": metric, "dt_s": dt,
                             "absolute_error": m["absolute_errors"][i], "relative_error": m["relative_errors"][i],
                             "pairwise_order_to_next": m["pairwise_orders"][i] if i < len(study["dt_s"])-1 else None,
                             "fitted_order": m["fitted_order"], "status": m["status"]})
    write_csv(out/"convergence.csv", rows)
    scenarios = run_all(ROOT/"scenarios", out/"scenarios")
    trajectory_verification = write_mutation_report(out)
    print("Convergence and scenarios generated.", flush=True)
    rates = burn_rate_study()
    write_csv(out/"burn_rate_sweep.csv", rates["sweep"])
    write_csv(out/"burn_rate_optima.csv", rates["optima"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for c, ax in zip([0, 0.002], axes):
        selected = [r for r in rates["sweep"] if r["c_kg_m"] == c]
        ax.semilogx([r["q_kg_s"] for r in selected], [r["apogee"] for r in selected], "-o", ms=2)
        for opt in rates["optima"]:
            if opt["c_kg_m"] == c: ax.scatter(opt["q_star"], opt["apogee_m"], marker="x", s=55)
        ax.set(title=f"Drag c = {c:g} kg/m", xlabel="Burn rate q (kg/s)", ylabel="Apogee (m)")
        ax.grid(alpha=.25)
    fig.suptitle("Fixed propellant 0.4 kg; assumed search bounds; crosses = optima")
    fig.tight_layout(); fig.savefig(figures/"burn_rate.png"); plt.close(fig)
    stability = stability_accuracy_study()
    write_csv(out/"stability_accuracy.csv", stability)
    fig, ax = plt.subplots(figsize=(7, 4))
    for method in ["euler", "heun", "rk4"]:
        selected = [r for r in stability if r["method"] == method and r["apogee_error_m"] is not None]
        ax.loglog([r["dt_s"] for r in selected], [r["apogee_error_m"] for r in selected], "o-", label=method)
    ax.axhline(.05, color="black", linestyle="--", lw=1, label="0.05 m target")
    ax.set(xlabel="Time step (s)", ylabel="Apogee absolute error (m)", title="Drag case vs independent DOP853; rejected runs in CSV")
    ax.legend(); ax.grid(which="both", alpha=.2)
    fig.tight_layout(); fig.savefig(figures/"accuracy.png"); plt.close(fig)
    peaks = peak_study()
    write_csv(out/"peak_acceleration.csv", peaks)
    print("Performance and accuracy studies generated.", flush=True)
    exact = no_drag_quantities(Parameters())
    published = [match(k, exact[k], value, atol=tol, unit=unit).to_dict()
                 for k,value,tol,unit in [("v_burnout",235.8,.05,"m/s"), ("h_burnout",214.1,.05,"m"), ("apogee",3048,.5,"m")]]
    dataset = generate_local_dataset(out/"local_dataset_200.npz", dataset_n)
    environment = {"python": platform.python_version(), "platform": platform.platform(),
                   "packages": {name: importlib.metadata.version(name) for name in ["numpy","scipy","matplotlib","pytest","PyYAML","reportlab","wmlab"]}}
    (ROOT/"requirements-tested.txt").write_text("# Exact top-level versions used; wmlab comes ONLY from the supplied archive.\n"+"\n".join(f"{k}=={v}" for k,v in environment["packages"].items() if k != "wmlab")+"\n./vendor/starter_kit/wmlab\n", encoding="utf-8")
    summary = {"format": "c5-local-report-v1", "official_wmlab": False, "consent_physeval": False,
               "parameters": asdict(Parameters()), "baseline": baseline, "analytic_no_drag": exact,
               "published_reference_comparison": published, "scipy_drag": scipy_reference(Parameters(c=.002)),
               "convergence": convergence, "scenarios": scenarios, "burn_rate": rates,
               "trajectory_verification": trajectory_verification,
               "stability": stability, "peak_refinement": peaks, "local_dataset": dataset,
               "environment": environment}
    write_json(out/"summary.json", summary)
    print(f"Local dataset: {dataset['count']} trajectories. Summary: {out/'summary.json'}", flush=True)
    if (not all(r["passed"] for r in convergence.values())
            or not all(r["demonstration_pass"] for r in scenarios)
            or not trajectory_verification["passed"]):
        raise RuntimeError("Verification failed: inspect generated reports.")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT/"outputs")
    args = parser.parse_args()
    generate(args.output)
