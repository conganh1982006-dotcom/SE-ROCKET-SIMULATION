"""Shared data contract: each assignment/project submits one YAML or JSON scenario
using this structure, so work from four courses can share one scenario collection."""
import json
import os

from .i18n import tr

REQUIRED = ["id", "author", "course", "system", "params", "initial", "t_span", "dt",
            "checks", "license", "consent_physeval"]
COURSES = {"PHY1", "PHY2", "PHY3", "DE", "AMCS", "RS"}
LICENSES = {"CC-BY-4.0", "CC0-1.0", "MIT", "ALL-RIGHTS-RESERVED"}


def load(path):
    with open(path, encoding="utf-8") as f:
        if path.endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(f)
        return json.load(f)


def validate(sc, registry):
    """Return a list of errors (empty means valid)."""
    err = []
    for k in REQUIRED:
        if k not in sc:
            err.append(tr(f"missing required field '{k}'", f"missing required field '{k}'"))
    if err:
        return err
    if sc["course"] not in COURSES:
        err.append(tr(f"course must be one of {sorted(COURSES)}", f"course must be one of {sorted(COURSES)}"))
    if sc["system"] not in registry:
        err.append(tr(f"unknown system '{sc['system']}'; available: {sorted(registry)} (did you pass --module?)", f"unknown system '{sc['system']}'; available: {sorted(registry)} (did you pass --module?)"))
    t0, t1 = sc["t_span"]
    if not t1 > t0:
        err.append(tr("t_span must have t1 > t0", "t_span must have t1 > t0"))
    if not 0 < sc["dt"] < (t1 - t0):
        err.append(tr("dt must be positive and smaller than the t_span length", "dt must be positive and smaller than the t_span length"))
    if sc["license"] not in LICENSES:
        err.append(tr(f"license must be one of {sorted(LICENSES)}", f"license must be one of {sorted(LICENSES)}"))
    if not isinstance(sc["consent_physeval"], bool):
        err.append(tr("consent_physeval must be true/false (voluntary, does not affect grades)", "consent_physeval must be true/false (voluntary, does not affect grades)"))
    if sc["consent_physeval"] and sc["license"] == "ALL-RIGHTS-RESERVED":
        err.append(tr("contributing to the scenario pool requires an open license (CC-BY-4.0, CC0-1.0 or MIT)", "contributing to the scenario pool requires an open license (CC-BY-4.0, CC0-1.0 or MIT)"))
    q = sc.get("question")
    if q is not None:
        for k in ("text", "quantity", "answer", "tolerance"):
            if k not in q:
                err.append(tr(f"question is missing '{k}'", f"question is missing '{k}'"))
    if not sc["checks"]:
        err.append(tr("at least one entry is required in 'checks'", "at least one entry is required in 'checks'"))
    return err


def slug(sc):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in sc["id"])


def out_paths(sc, outdir):
    os.makedirs(outdir, exist_ok=True)
    s = slug(sc)
    return os.path.join(outdir, f"{s}_traj.npz"), os.path.join(outdir, f"{s}_report.json")
