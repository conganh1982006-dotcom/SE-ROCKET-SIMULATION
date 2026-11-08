"""Present existing simulator results; write only to a fresh quick_runs folder."""
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
from uuid import uuid4

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from rocket import Parameters, simulate, quantities


ROOT = Path(__file__).resolve().parents[1]
LABELS = {"no_drag": "No drag", "with_drag": "With drag"}
COLORS = {"no_drag": "#1864ab", "with_drag": "#c65316"}
PLOTS = (
    ("altitude", "h", "Altitude", "m"),
    ("velocity", "v", "Velocity", "m/s"),
    ("acceleration", "a", "Coordinate acceleration", "m/s²"),
    ("mass", "m", "Mass", "kg"),
)
NOTES = [
    "Manual simulation; this is not a verification certificate. Run main.py verify to check V3.",
    "The ascent model stops at apogee; descent to the ground is not simulated.",
    "Peak acceleration = max |dv/dt| / g, including samples and both limits at burnout.",
    "Within-phase extrema are grid estimates; reduce dt to assess sensitivity.",
    "The trajectory CSV uses post-shutdown acceleration at burnout; JSON retains both limits.",
]


def calculate(mode, params, dt, method):
    """Both comparison cases have identical inputs except for drag coefficient."""
    if mode not in ("no-drag", "with-drag", "compare"):
        raise ValueError(f"Unknown simulation mode: {mode}")
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and > 0.")
    if mode == "no-drag" and params.c != 0:
        raise ValueError("No Drag requires c = 0.")
    if mode != "no-drag" and params.c <= 0:
        raise ValueError("With Drag / Compare requires c > 0.")
    cases = [("no_drag", replace(params, c=0.0))] if mode == "compare" else []
    cases.append(("no_drag" if mode == "no-drag" else "with_drag", params))
    return {name: simulate(p, dt=dt, method=method) for name, p in cases}


def event_data(event):
    return {"time_s": float(event.t), "h_m": float(event.state[0]),
            "v_m_s": float(event.state[1]), "m_kg": float(event.state[2]),
            "a_before_m_s2": float(event.a_before), "a_after_m_s2": float(event.a_after)}


def plot_series(result, field):
    """Show the acceleration jump with duplicate t, never interpolate across it."""
    if field != "a":
        return result.t, getattr(result, field)
    index = int(np.searchsorted(result.t, result.burnout.t))
    return (np.insert(result.t, index, result.burnout.t),
            np.insert(result.a, index, result.burnout.a_before))


def make_plot(histories, field, title, unit):
    figure = Figure(figsize=(9.4, 5.6), layout="constrained")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    extremes = []
    for name, result in histories.items():
        color = COLORS[name]
        t, values = plot_series(result, field)
        ax.plot(t, values, color=color, linewidth=1.7,
                label=f"{LABELS[name]} · c={result.params.c:g} kg/m")
        for event, marker in [(result.burnout, "o"), (result.apogee, "D")]:
            value = event.a_after if field == "a" else event.state[{"h": 0, "v": 1, "m": 2}[field]]
            ax.axvline(event.t, color=color, alpha=0.3, linestyle="--", linewidth=0.9)
            ax.scatter([event.t], [value], marker=marker, color=color, s=36, zorder=4)
        if field == "a":
            ax.scatter([result.burnout.t], [result.burnout.a_before], marker="o",
                       facecolors="white", edgecolors=color, s=36, zorder=4)
        extreme_index = int(np.argmax(np.abs(values) if field == "a" else values))
        extreme = float(values[extreme_index])
        extremes.append(extreme)
        ax.scatter([t[extreme_index]], [extreme], color=color, marker="*", s=80, zorder=5)
        ax.axhline(extreme, color=color, alpha=0.35, linestyle=":", linewidth=0.8)
    # Label actual extrema on the Y axis. Drop nearby ordinary ticks to avoid overlap.
    low, high = ax.get_ylim()
    gap = max((high-low)*0.035, 1e-12)
    marked = []
    for value in sorted(extremes):
        if not marked or value-marked[-1] > gap:
            marked.append(value)
    regular = [float(x) for x in ax.get_yticks() if low <= x <= high
               and all(abs(x-value) > gap for value in marked)]
    ticks = sorted(regular+marked)
    ax.set_yticks(ticks, [f"{x:.6g} ★" if x in marked else f"{x:g}" for x in ticks])
    ax.set_ylim(low, high)
    handles, labels = ax.get_legend_handles_labels()
    for marker, label in [("o", "Burnout"), ("D", "Apogee"), ("*", "Sampled extremum")]:
        handles.append(Line2D([], [], marker=marker, color="#52606d", linestyle="None"))
        labels.append(label)
    first = next(iter(histories.values()))
    ax.set(title=f"{title} vs time — {first.method.upper()}, dt={first.dt:g} s",
           xlabel="Time (s)", ylabel=f"{title} ({unit})")
    ax.grid(alpha=0.18)
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9)
    if field == "a":
        figure.supxlabel("Signed acceleration; ★ marks max |a|. Open circle: immediately before burnout.", fontsize=9)
    return figure


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def print_summary(report, destination):
    cases = report["cases"]
    print("\n" + f"{'Quantity':<32}" + "".join(f"{LABELS[name]:>20}" for name in cases))
    for label, key in [
        ("Burnout: time (s)", "t_burnout"),
        ("Burnout: altitude (m)", "h_burnout"),
        ("Burnout: velocity (m/s)", "v_burnout"),
        ("Apogee: altitude (m)", "apogee"),
        ("Time to apogee (s)", "t_apogee"),
        ("Peak |a| / g", "max_acceleration_g"),
    ]:
        print(f"{label:<32}" + "".join(f"{case['quantities'][key]:>20.6f}" for case in cases.values()))
    print(f"\nSaved: {destination}\n"
          "See the 4 PNG plots, summary.csv, results.json and trajectory CSV files.\n"
          "Peaks include samples and both burnout limits; reduce dt to assess sensitivity.\n"
          "This is a quick run. Run python main.py verify to check V3.")


def run_quick(mode, params: Parameters, dt=0.02, method="rk4", *, project_root=ROOT):
    histories = calculate(mode, params, dt, method)
    created = datetime.now(timezone.utc)
    run_id = f"{created:%Y%m%dT%H%M%S_%fZ}_{mode}_{uuid4().hex[:8]}"
    parent = Path(project_root)/"outputs"/"quick_runs"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent/run_id
    destination.mkdir()  # Exclusive creation: never reuse another run's files.
    report = {"format": "c5-quick-run-v1", "run_id": run_id,
              "created_at_utc": created.isoformat(), "mode": mode,
              "python": platform.python_version(), "method": method, "dt_s": dt,
              "verification_performed": False, "notes": NOTES,
              "parameter_units": {"m0": "kg", "mf": "kg", "q": "kg/s", "ve": "m/s",
                                  "g": "m/s^2", "c": "kg/m", "h0": "m", "v0": "m/s"},
              "quantity_units": {"t_burnout": "s", "h_burnout": "m", "v_burnout": "m/s",
                                 "apogee": "m", "t_apogee": "s", "max_acceleration_g": "g",
                                 "max_upward_acceleration_g": "g", "max_proper_acceleration_g": "g"},
              "cases": {}, "plots": [f"{name}.png" for name, *_ in PLOTS]}
    rows = []
    for name, result in histories.items():
        metrics = quantities(result)
        parameters = asdict(result.params)
        report["cases"][name] = {"parameters": parameters, "quantities": metrics,
                                  "burnout": event_data(result.burnout), "apogee": event_data(result.apogee),
                                  "sample_count": len(result.t), "trajectory_csv": f"{name}.csv"}
        rows.append({"run_id": run_id, "created_at_utc": report["created_at_utc"], "case": name,
                     "method": method, "dt_s": dt, **parameters, **metrics})
        np.savetxt(destination/f"{name}.csv", np.column_stack([result.t, result.h, result.v, result.m, result.a]),
                   delimiter=",", header="t_s,h_m,v_m_s,m_kg,a_m_s2", comments="", fmt="%.17g")
    write_csv(destination/"summary.csv", rows)
    for filename, field, title, unit in PLOTS:
        figure = make_plot(histories, field, title, unit)
        try:
            figure.savefig(destination/f"{filename}.png", dpi=160)
        finally:
            figure.clear()
    # This file is the completion record; it is only written after all exports succeed.
    (destination/"results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print_summary(report, destination)
    return destination
