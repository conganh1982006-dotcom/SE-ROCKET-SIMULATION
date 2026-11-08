"""CLI acceptance tests: actual exports, isolation, input errors and V3 regression."""
import csv
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

import main as cli
from experiments import quick_runs
from rocket import Parameters, simulate, quantities


ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT/"tests/fixtures/v3_baseline.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", list(BASELINE["cases"].values()),
                         ids=list(BASELINE["cases"]))
def test_all_methods_preserve_original_v3_quantities(case):
    name = "no_drag" if case["c"] == 0 else "with_drag"
    mode = "no-drag" if case["c"] == 0 else "with-drag"
    result = quick_runs.calculate(mode, Parameters(c=case["c"]), case["dt"], case["method"])[name]
    actual = quantities(result)
    for quantity, expected in case["quantities"].items():
        assert actual[quantity] == pytest.approx(expected, rel=1e-11, abs=1e-10)


@pytest.mark.parametrize("mode,method,cases", [
    ("no-drag", "euler", ["no_drag"]),
    ("with-drag", "heun", ["with_drag"]),
    ("compare", "rk4", ["no_drag", "with_drag"]),
])
def test_cli_exports_actual_results_without_touching_evidence(tmp_path, monkeypatch, mode, method, cases):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    protected = ["outputs/report_vi.pdf", "outputs/summary.json", "c5_rocket.npz",
                 "outputs/wmlab/summary.json", "convergence/wmlab/report.json"]
    for name in protected:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"existing official evidence")
    args = [mode, "--method", method, "--dt", "0.03", "--q", "0.15", "--h0", "12"]
    if mode != "no-drag":
        args += ["--c", "0.001"]
    assert cli.main(args) == 0
    run = next((tmp_path/"outputs/quick_runs").iterdir())
    report = json.loads((run/"results.json").read_text(encoding="utf-8"))
    assert datetime.fromisoformat(report["created_at_utc"]).tzinfo is not None
    assert list(report["cases"]) == cases
    assert report["verification_performed"] is False
    assert report["method"] == method and report["dt_s"] == 0.03
    with (run/"summary.csv").open(encoding="utf-8", newline="") as stream:
        summary = list(csv.DictReader(stream))
    assert len(summary) == len(cases)
    for name, row in zip(cases, summary):
        result = report["cases"][name]
        p = Parameters(**result["parameters"])
        assert p.c == (0.0 if name == "no_drag" else 0.001)
        assert p.q == 0.15 and p.h0 == 12
        direct = simulate(p, dt=0.03, method=method)
        actual = np.loadtxt(run/result["trajectory_csv"], delimiter=",", skiprows=1)
        np.testing.assert_array_equal(actual, np.column_stack([direct.t, direct.h, direct.v, direct.m, direct.a]))
        assert result["quantities"] == quantities(direct)
        assert result["burnout"]["a_before_m_s2"] == direct.burnout.a_before
        assert result["burnout"]["a_after_m_s2"] == direct.burnout.a_after
        assert row["created_at_utc"] == report["created_at_utc"]
        assert float(row["apogee"]) == result["quantities"]["apogee"]
        assert float(row["c"]) == p.c
    for plot in ["altitude", "velocity", "acceleration", "mass"]:
        assert (run/f"{plot}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    for name in protected:
        assert (tmp_path/name).read_bytes() == b"existing official evidence"
    assert set(p for p in tmp_path.rglob("*") if p.is_file() and run not in p.parents) == {
        tmp_path/name for name in protected}


def test_repeated_runs_are_isolated_even_at_identical_timestamp(tmp_path, monkeypatch):
    class FixedClock:
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 28, 12, 0, tzinfo=tz)
    monkeypatch.setattr(quick_runs, "datetime", FixedClock)
    first = quick_runs.run_quick("no-drag", Parameters(), dt=0.1, project_root=tmp_path)
    saved = {p.name: p.read_bytes() for p in first.iterdir()}
    second = quick_runs.run_quick("no-drag", Parameters(), dt=0.1, project_root=tmp_path)
    assert first != second
    assert {p.name: p.read_bytes() for p in first.iterdir()} == saved


@pytest.mark.parametrize("args", [
    ["no-drag", "--dt", "0"], ["no-drag", "--dt", "-1"],
    ["no-drag", "--dt", "nan"], ["no-drag", "--dt", "inf"],
    ["with-drag", "--c", "-0.1"], ["compare", "--c", "0"],
    ["with-drag", "--c", "nan"], ["no-drag", "--ve", "inf"],
    ["no-drag", "--method", "dop853"], ["no-drag", "--c", "0.002"],
    ["verify", "--dt", "0.2"], ["report", "--method", "euler"],
])
def test_invalid_arguments_exit_nonzero_before_writing(tmp_path, monkeypatch, args):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as error:
        cli.main(args)
    assert error.value.code == 2
    assert not (tmp_path/"outputs").exists()


@pytest.mark.parametrize("options", [
    ["--m0", "0.5", "--mf", "0.6"], ["--mf", "0"],
    ["--q", "0"], ["--q", "0.001"], ["--g", "-1"],
    ["--ve", "-1"], ["--h0", "-1"], ["--v0", "-1"],
])
def test_invalid_physics_is_explained_without_partial_output(tmp_path, monkeypatch, capsys, options):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["no-drag", *options]) == 2
    assert "Unable to complete" in capsys.readouterr().err
    assert not (tmp_path/"outputs").exists()


def test_comparison_changes_only_drag():
    p = Parameters(m0=1.2, mf=0.7, q=0.15, ve=450, g=9.7, c=0.001, h0=5, v0=2)
    cases = quick_runs.calculate("compare", p, 0.03, "heun")
    no_drag = asdict(cases["no_drag"].params)
    with_drag = asdict(cases["with_drag"].params)
    assert no_drag.pop("c") == 0
    assert with_drag.pop("c") == p.c
    assert no_drag == with_drag
    assert p.c == 0.001


def test_acceleration_plot_preserves_jump_and_signed_absolute_peak():
    result = simulate(Parameters(c=0.002))
    t, a = quick_runs.plot_series(result, "a")
    indices = np.flatnonzero(t == result.burnout.t)
    assert len(indices) == 2
    np.testing.assert_array_equal(a[indices], [result.burnout.a_before, result.burnout.a_after])
    result.a[10] = -1000.0  # Display-only test: largest magnitude can be negative.
    figure = quick_runs.make_plot({"with_drag": result}, "a", "Acceleration", "m/s²")
    ax = figure.axes[0]
    assert -1000 in ax.get_yticks()
    assert any("-1000" in label.get_text() and "★" in label.get_text() for label in ax.get_yticklabels())
    event_times = [line.get_xdata()[0] for line in ax.lines if line.get_linestyle() == "--"]
    assert result.burnout.t in event_times and result.apogee.t in event_times
    figure.clear()


@pytest.mark.parametrize("mode,expected", [
    ("verify", ["pytest", "verification.scenarios", "verification.convergence", "verification.mutations", "scripts.wmlab_verify"]),
    ("report", ["scripts.reproduce"]),
])
def test_workflows_use_existing_modules_and_current_environment(monkeypatch, mode, expected):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["cwd"] == ROOT
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.main([mode]) == 0
    assert [call[2] for call in calls] == expected
    assert all(call[:2] == [sys.executable, "-m"] for call in calls)


@pytest.mark.parametrize("mode,fail_at", [("verify", 0), ("verify", 4), ("report", 0)])
def test_failed_workflow_propagates_exit_code_and_stops(monkeypatch, capsys, mode, fail_at):
    calls = []
    def run(command, **kwargs):
        index = len(calls)
        calls.append(command)
        return SimpleNamespace(returncode=7 if index == fail_at else 0)
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.main([mode]) == 7
    assert len(calls) == fail_at+1
    assert "Verification complete" not in capsys.readouterr().out


def test_menu_recovers_invalid_choices_and_numbers_then_uses_overrides(monkeypatch):
    replies = iter(["9", "2", "bad-method", "HEUN", "0", "0.05", "nan", "0.003", "y",
                    "1.2", "0.7", "0.15", "450", "9.7", "5", "2", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    calls = []
    monkeypatch.setattr(cli, "execute", lambda args: calls.append(args) or 0)
    assert cli.main([]) == 0
    assert len(calls) == 1
    args = calls[0]
    assert args.mode == "with-drag" and args.method == "heun"
    assert args.dt == 0.05 and args.c == 0.003
    assert (args.m0, args.mf, args.q, args.ve, args.g, args.h0, args.v0) == (1.2, 0.7, 0.15, 450, 9.7, 5, 2)


@pytest.mark.parametrize("choice,mode", [("4", "verify"), ("5", "report")])
def test_menu_dispatches_workflows_without_simulation_prompts(monkeypatch, choice, mode):
    replies = iter([choice, "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    calls = []
    monkeypatch.setattr(cli, "execute", lambda args: calls.append(args.mode) or 0)
    assert cli.main([]) == 0
    assert calls == [mode]


@pytest.mark.parametrize("exception", [EOFError, KeyboardInterrupt])
def test_menu_can_be_cancelled(monkeypatch, exception):
    def cancel(_):
        raise exception
    monkeypatch.setattr("builtins.input", cancel)
    assert cli.main([]) == 130


@pytest.mark.parametrize("arguments,stdin", [
    (["compare", "--method", "RK4", "--dt", "0.02"], None),
    ([], "3\n\n\n\nn\n0\n"),
])
def test_real_command_and_interactive_menu_from_other_directory(tmp_path, arguments, stdin):
    # Copy only the entrypoint so its output root is isolated; import unchanged source via PYTHONPATH.
    project = tmp_path/"project with spaces"
    project.mkdir()
    shutil.copyfile(ROOT/"main.py", project/"main.py")
    outside = tmp_path/"outside"
    outside.mkdir()
    env = {**os.environ, "PYTHONPATH": str(ROOT), "MPLCONFIGDIR": str(tmp_path/"mpl")}
    run = subprocess.run([sys.executable, str(project/"main.py"), *arguments], cwd=outside,
                         input=stdin, capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
    assert run.returncode == 0, run.stdout+run.stderr
    assert "Time to apogee" in run.stdout
    result = next((project/"outputs/quick_runs").glob("*/results.json"))
    assert len(json.loads(result.read_text(encoding="utf-8"))["cases"]) == 2
    assert not (outside/"outputs").exists()
