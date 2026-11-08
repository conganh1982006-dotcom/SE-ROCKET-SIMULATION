"""Verification checks.
Each check returns a dict: name, passed, value, threshold, note.
Khai báo trong scenario:  checks: ["energy_conserved", {"name": "analytic_match", "tol": 1e-6}]
Student modules can define custom checks using EXTRA_CHECKS = {"name": function}."""
import numpy as np

from .i18n import tr


def _r(name, passed, value, threshold, note=""):
    return {"name": name, "passed": bool(passed), "value": None if value is None else float(value),
            "threshold": threshold, "note": note}


def analytic_match(sc, mod, t, Y, tol=1e-4, **_):
    Ya = mod.analytic(sc["params"], sc["initial"], t)
    if Ya is None:
        return _r("analytic_match", False, None, tol, tr("no analytic solution for this system/parameter set",
                                                          "no analytic solution for this system/parameter set"))
    scale = max(np.abs(Ya).max(), 1e-12)
    err = np.abs(Y - Ya).max() / scale
    return _r("analytic_match", err < tol, err, tol, tr("max relative error vs analytic solution",
                                                        "max relative error vs analytic solution"))


def convergence_order(sc, mod, t, Y, expected=4.0, slack=0.5, mode="auto", h=None, horizon=None, **_):
    """Time-step convergence with h, h/2, h/4 (default h = 10*dt).
    mode: analytic | self (Richardson) | auto. horizon: integrate to t0 + horizon (required for chaotic systems)."""
    p, init = sc["params"], sc["initial"]
    t0, t1 = sc["t_span"]
    if horizon is not None:
        t1 = min(t1, t0 + float(horizon))
    h = float(h) if h is not None else 10 * sc["dt"]
    h = (t1 - t0) / max(1, round((t1 - t0) / h))
    finals = [np.asarray(mod.simulate(p, init, [t0, t1], d)[1][-1], float) for d in (h, h / 2, h / 4)]
    if mode == "auto":
        mode = getattr(mod, "CONVERGENCE_MODE", "analytic")
    Ya = mod.analytic(p, init, np.array([t0, t1])) if mode == "analytic" else None
    if Ya is not None:
        errs = [np.abs(f - Ya[-1]).max() for f in finals]
        order = np.log2(errs[0] / errs[1]) if errs[1] > 0 else np.inf
        note = tr(f"vs analytic solution at t={t1:g}, h={h:g}", f"vs analytic solution at t={t1:g}, h={h:g}")
    else:
        d1 = np.abs(finals[0] - finals[1]).max()
        d2 = np.abs(finals[1] - finals[2]).max()
        order = np.log2(d1 / d2) if d2 > 0 else np.inf
        note = tr(f"Richardson (self-convergence) at t={t1:g}, h={h:g}", f"Richardson (self-convergence) at t={t1:g}, h={h:g}")
    return _r("convergence_order", order >= expected - slack, order, expected, note)


def energy_conserved(sc, mod, t, Y, tol=1e-6, **_):
    E = mod.energy(sc["params"], Y)
    drift = np.abs(E - E[0]).max() / max(abs(E[0]), 1e-12)
    return _r("energy_conserved", drift < tol, drift, tol, tr("max relative energy drift",
                                                              "max relative energy drift"))


def energy_nonincreasing(sc, mod, t, Y, tol=1e-9, **_):
    E = mod.energy(sc["params"], Y)
    rise = np.diff(E).max() / max(abs(E[0]), 1e-12)
    return _r("energy_nonincreasing", rise <= tol, rise, tol,
              tr("largest energy increase between steps (must be <= 0 with damping)",
                 "largest energy increase between steps (must be <= 0 with damping)"))


def invariant_conserved(sc, mod, t, Y, tol=1e-6, **_):
    """Module-defined conserved quantity: invariant(p, Y) -> time series."""
    if not hasattr(mod, "invariant"):
        return _r("invariant_conserved", False, None, tol, tr("module does not define invariant(p, Y)",
                                                              "module does not define invariant(p, Y)"))
    I = np.asarray(mod.invariant(sc["params"], Y), float)
    drift = np.abs(I - I[0]).max() / max(abs(I[0]), 1e-12)
    name = getattr(mod, "INVARIANT_NAME", "invariant")
    return _r("invariant_conserved", drift < tol, drift, tol, tr(f"max relative drift of '{name}'",
                                                                 f"max relative drift of '{name}'"))


def within_bounds(sc, mod, t, Y, tol=1e-12, **_):
    """Physical domain: the module defines bounds(p) -> {column index: (min, max)}."""
    if not hasattr(mod, "bounds"):
        return _r("within_bounds", False, None, None, tr("module does not define bounds(p)",
                                                         "module does not define bounds(p)"))
    worst, where = 0.0, ""
    names = getattr(mod, "STATE", None)
    for j, (lo, hi) in mod.bounds(sc["params"]).items():
        col = Y[:, int(j)]
        v = max((lo - col.min()) if lo is not None else 0.0, (col.max() - hi) if hi is not None else 0.0, 0.0)
        if v > worst:
            worst, where = v, names[int(j)] if names else str(j)
    return _r("within_bounds", worst <= tol, worst, tol,
              tr(f"largest excursion outside the physical range {('in ' + where) if where else ''}",
                 f"largest excursion outside the physical range {('in ' + where) if where else ''}"))


def reference_match(sc, mod, t, Y, tol=1e-3, **_):
    """Compare simulated quantities with independent reference_quantities(p, init)."""
    if not hasattr(mod, "reference_quantities"):
        return _r("reference_match", False, None, tol, tr("module does not define reference_quantities()",
                                                          "module does not define reference_quantities()"))
    ref = mod.reference_quantities(sc["params"], sc["initial"])
    if not ref:
        return _r("reference_match", False, None, tol, tr("no reference formula applies to these parameters",
                                                          "no reference formula applies to these parameters"))
    sim = mod.quantities(sc["params"], sc["initial"], t, Y)
    worst, detail = 0.0, []
    for k, rv in ref.items():
        if k not in sim:
            return _r("reference_match", False, None, tol, tr(f"quantities() lacks '{k}'", f"quantities() lacks '{k}'"))
        e = abs(sim[k] - rv) / max(abs(rv), 1e-12)
        worst = max(worst, e)
        detail.append(f"{k}: sim={sim[k]:.6g} ref={rv:.6g}")
    return _r("reference_match", worst < tol, worst, tol, "; ".join(detail))


def max_principle(sc, mod, t, Y, tol=1e-12, **_):
    m = np.abs(Y).max(axis=1)
    rise = np.diff(m).max()
    return _r("max_principle", rise <= tol, rise, tol, tr("max|u| must not increase in time (heat equation)",
                                                          "max|u| must not increase in time (heat equation)"))


def stability(sc, mod, t, Y, limit=None, **_):
    limit = getattr(mod, "STABILITY_LIMIT", 0.5) if limit is None else limit
    if sc["params"].get("scheme", getattr(mod, "DEFAULT_SCHEME", "cn")) != "ftcs":
        return _r("stability", True, None, limit, tr("Crank–Nicolson is unconditionally stable",
                                                     "Crank–Nicolson is unconditionally stable"))
    r = mod.stability_number(sc["params"], sc["dt"])
    return _r("stability", r <= limit, r, limit, tr("FTCS stability number r = alpha dt / dx^2",
                                                    "FTCS stability number r = alpha dt / dx^2"))


def heat_balance(sc, mod, t, Y, tol=1e-9, **_):
    if not hasattr(mod, "heat_balance"):
        return _r("heat_balance", False, None, tol, tr("system does not define a heat balance",
                                                       "system does not define a heat balance"))
    err = mod.heat_balance(sc["params"], sc["initial"], t, Y)
    return _r("heat_balance", err < tol, err, tol, tr("change of total heat vs integrated source (insulated boundary)",
                                                      "change of total heat vs integrated source (insulated boundary)"))


def lyapunov_reference(sc, mod, t, Y, rel_tol=0.05, **_):
    ref = mod.reference_lyapunov(sc["params"])
    lam = mod.max_lyapunov(sc["params"], sc["initial"])
    if ref is None:
        return _r("lyapunov_reference", lam > 0, lam, ">0", tr("no reference value; checks chaos only (lambda > 0)",
                                                               "no reference value; checks chaos only (lambda > 0)"))
    err = abs(lam - ref) / ref
    return _r("lyapunov_reference", err < rel_tol, lam, ref, tr(f"relative deviation {err:.3f}", f"relative deviation {err:.3f}"))


def equipartition(sc, mod, t, Y, tol=0.1, **_):
    q = mod.equipartition(sc["params"], Y)
    dev = max(abs(q["kx2_over_kT"] - 1), abs(q["mv2_over_kT"] - 1))
    return _r("equipartition", dev < tol, dev, tol, f"<kx²>/kT={q['kx2_over_kT']:.3f}, <mv²>/kT={q['mv2_over_kT']:.3f}")


def fdt(sc, mod, t, Y, tol=0.1, expect="satisfied", **_):
    X = mod.fdt_ratio(sc["params"])[0]
    ok = abs(X - 1) < tol
    passed = ok if expect == "satisfied" else not ok
    return _r("fdt", passed, X, f"|X-1|<{tol}" if expect == "satisfied" else f"|X-1|>={tol}",
              tr(f"fluctuation-response ratio X; expected: {expect}",
                 f"fluctuation-response ratio X; expected: {expect}"))


def answer_matches(sc, mod, t, Y, **_):
    q = sc.get("question")
    if q is None:
        return _r("answer_matches", False, None, None, tr("scenario has no 'question'", "scenario has no 'question'"))
    vals = mod.quantities(sc["params"], sc["initial"], t, Y)
    key = q["quantity"]
    if key not in vals:
        return _r("answer_matches", False, None, None, tr(f"cannot compute '{key}'; available: {sorted(vals)}",
                                                          f"cannot compute '{key}'; available: {sorted(vals)}"))
    sim, ans, tol = vals[key], float(q["answer"]), float(q["tolerance"])
    rel = abs(ans - sim) / max(abs(sim), 1e-12)
    return _r("answer_matches", rel <= tol, rel, tol, tr(f"answer {ans:.6g} vs simulation {sim:.6g}",
                                                         f"answer {ans:.6g} vs simulation {sim:.6g}"))


CHECKS = {f.__name__: f for f in [analytic_match, convergence_order, energy_conserved, energy_nonincreasing,
                                  invariant_conserved, within_bounds, reference_match, max_principle, stability,
                                  heat_balance, lyapunov_reference, equipartition, fdt, answer_matches]}


def run_checks(sc, mod, t, Y):
    available = dict(CHECKS)
    available.update(getattr(mod, "EXTRA_CHECKS", {}))
    out = []
    for c in sc["checks"]:
        name, kw = (c, {}) if isinstance(c, str) else (c["name"], {k: v for k, v in c.items() if k != "name"})
        if name not in available:
            out.append(_r(name, False, None, None, tr(f"unknown check; available: {sorted(available)}",
                                                      f"unknown check; available: {sorted(available)}")))
            continue
        try:
            out.append(available[name](sc, mod, t, Y, **kw))
        except Exception as e:  # A check error is a failure, with an explanatory message.
            out.append(_r(name, False, None, None, tr(f"error while running check: {e!r}", f"error while running check: {e!r}")))
    return out
