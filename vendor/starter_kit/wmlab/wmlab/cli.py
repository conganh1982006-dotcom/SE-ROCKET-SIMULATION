"""Command line:
  python -m wmlab validate scenario.yaml [--module my_system.py]
  python -m wmlab check scenario.yaml [-o out/] [--module my_system.py]
  python -m wmlab dataset --system NAME --n 500 --seed 0 -o data.npz [--module my_system.py]
  python -m wmlab collect out/ -o registry.csv
  python -m wmlab systems [--module my_system.py]
Use --lang en (or WMLAB_LANG=en) to select English messages."""
import argparse
import importlib.util
import json
import os
import sys

import numpy as np

from . import schema
from .checks import run_checks
from .i18n import tr
from .sims import REGISTRY

REQUIRED_FUNCS = ("simulate", "analytic", "quantities", "sample")


def load_module(path):
    """Load a student system module and register it under NAME (or its filename)."""
    spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [f for f in REQUIRED_FUNCS if not hasattr(mod, f)]
    if missing:
        sys.exit(tr(f"Module is missing required functions: {missing}", f"Module is missing required functions: {missing}"))
    name = getattr(mod, "NAME", spec.name)
    REGISTRY[name] = mod
    return name


def _load_extra(a):
    for path in getattr(a, "module", None) or []:
        load_module(path)


def cmd_validate(a):
    _load_extra(a)
    sc = schema.load(a.scenario)
    err = schema.validate(sc, REGISTRY)
    if err:
        print(tr("INVALID:", "INVALID:"))
        for e in err:
            print("  -", e)
        sys.exit(1)
    print(tr(f"Valid: {sc['id']} ({sc['system']}, {sc['course']})", f"Valid: {sc['id']} ({sc['system']}, {sc['course']})"))


def cmd_check(a):
    _load_extra(a)
    sc = schema.load(a.scenario)
    err = schema.validate(sc, REGISTRY)
    if err:
        print(tr("INVALID — fix before running checks:", "INVALID — fix before running checks:"))
        for e in err:
            print("  -", e)
        sys.exit(1)
    mod = REGISTRY[sc["system"]]
    t, Y = mod.simulate(sc["params"], sc["initial"], sc["t_span"], sc["dt"])
    Y = np.asarray(Y, float)
    if Y.ndim == 1:
        Y = Y[:, None]
    results = run_checks(sc, mod, t, Y)
    q = mod.quantities(sc["params"], sc["initial"], t, Y)
    traj_path, rep_path = schema.out_paths(sc, a.out)
    np.savez_compressed(traj_path, t=t, Y=Y)
    report = {"id": sc["id"], "author": sc["author"], "course": sc["course"], "system": sc["system"],
              "passed_all": all(r["passed"] for r in results), "checks": results, "quantities": q,
              "consent_physeval": sc["consent_physeval"], "license": sc["license"]}
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    ok, ko = tr("PASS", "PASS"), tr("FAIL", "FAIL")
    print(f"# {sc['id']} — {sc['system']}")
    for r in results:
        v = "—" if r["value"] is None else f"{r['value']:.4g}"
        print(f"  [{ok if r['passed'] else ko}] {r['name']:<22} {tr('value', 'value')}={v:<12} "
              f"{tr('threshold', 'threshold')}={r['threshold']}  {r['note']}")
    print(tr("  Quantities: ", "  Quantities: ") + ", ".join(f"{k}={v:.5g}" for k, v in q.items()))
    verdict = tr("ALL PASSED", "ALL PASSED") if report["passed_all"] else tr("SOME CHECKS FAILED", "SOME CHECKS FAILED")
    print(f"  => {verdict} · {tr('report', 'report')}: {rep_path}")


def cmd_dataset(a):
    _load_extra(a)
    if a.system not in REGISTRY:
        sys.exit(tr(f"Unknown system '{a.system}'; available: {sorted(REGISTRY)}", f"Unknown system '{a.system}'; available: {sorted(REGISTRY)}"))
    mod = REGISTRY[a.system]
    rng = np.random.default_rng(a.seed)
    Ys, meta = [], []
    t = None
    for _ in range(a.n):
        p, init, ts, dt = mod.sample(rng)
        t, Y = mod.simulate(p, init, ts, dt)
        Y = np.asarray(Y, float)
        Ys.append((Y[:, None] if Y.ndim == 1 else Y)[::a.stride])
        meta.append({"params": p, "initial": init})
    shapes = {y.shape for y in Ys}
    if len(shapes) > 1:
        sys.exit(tr("sample() must return the same t_span and dt for every draw (equal-length trajectories)",
                    "sample() must return the same t_span and dt for every draw (equal-length trajectories)"))
    Yarr = np.stack(Ys)
    if not np.all(np.isfinite(Yarr)):
        sys.exit(tr("Dataset contains NaN/inf: check the parameter ranges in sample() or the step dt",
                    "Dataset contains NaN/inf: check the parameter ranges in sample() or the step dt"))
    np.savez_compressed(a.out, t=t[::a.stride], Y=Yarr, meta=np.array(json.dumps(meta, ensure_ascii=False)),
                        system=np.array(a.system), state=np.array(json.dumps(getattr(mod, "STATE", []))))
    print(tr(f"Generated {a.n} trajectories of '{a.system}' -> {a.out}  (Y shape {Yarr.shape})",
             f"Generated {a.n} trajectories of '{a.system}' -> {a.out}  (Y shape {Yarr.shape})"))


def cmd_collect(a):
    import csv
    import glob
    rows = []
    for path in sorted(glob.glob(os.path.join(a.folder, "*_report.json"))):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        eligible = r["passed_all"] and r["consent_physeval"] and r["license"] != "ALL-RIGHTS-RESERVED"
        rows.append({"id": r["id"], "author": r["author"], "course": r["course"], "system": r["system"],
                     "passed_all": r["passed_all"], "consent": r["consent_physeval"], "license": r["license"],
                     "eligible_physeval": eligible,
                     "failed_checks": ";".join(c["name"] for c in r["checks"] if not c["passed"])})
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)
    n_ok = sum(r["eligible_physeval"] for r in rows)
    print(tr(f"{len(rows)} reports · {n_ok} eligible for the pool (all checks passed + voluntary consent + open license) -> {a.out}",
             f"{len(rows)} reports · {n_ok} eligible for the pool (all checks passed + voluntary consent + open license) -> {a.out}"))


def cmd_systems(a):
    _load_extra(a)
    for k, m in sorted(REGISTRY.items()):
        print(f"{k:<18} {(m.__doc__ or '').strip().splitlines()[0] if m.__doc__ else ''}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="wmlab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", choices=["vi", "en"], help="message language (both selectors use English in this edition)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_module(p):
        p.add_argument("--module", action="append", help="student system .py file (can be repeated)")

    v = sub.add_parser("validate"); v.add_argument("scenario"); add_module(v); v.set_defaults(f=cmd_validate)
    c = sub.add_parser("check"); c.add_argument("scenario"); c.add_argument("-o", "--out", default="out")
    add_module(c); c.set_defaults(f=cmd_check)
    d = sub.add_parser("dataset"); d.add_argument("--system", required=True)
    d.add_argument("--n", type=int, default=200); d.add_argument("--seed", type=int, default=0)
    d.add_argument("--stride", type=int, default=10); d.add_argument("-o", "--out", default="dataset.npz")
    add_module(d); d.set_defaults(f=cmd_dataset)
    k = sub.add_parser("collect"); k.add_argument("folder"); k.add_argument("-o", "--out", default="registry.csv")
    k.set_defaults(f=cmd_collect)
    s = sub.add_parser("systems"); add_module(s); s.set_defaults(f=cmd_systems)
    a = ap.parse_args(argv)
    if a.lang:
        os.environ["WMLAB_LANG"] = a.lang
    a.f(a)
