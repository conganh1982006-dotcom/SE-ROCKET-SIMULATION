from pathlib import Path
import pytest
from rocket import simulate
from verification.convergence import convergence_study
from verification.scenarios import run_scenario

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def convergence():
    return convergence_study()


@pytest.mark.parametrize("method", ["euler", "heun", "rk4"])
def test_measured_convergence_order(convergence, method):
    assert convergence[method]["passed"], convergence[method]


@pytest.mark.parametrize("filename", ["01_baseline_drag.yaml", "02_analytic_no_drag.yaml", "03_euler_coarse_fail.yaml"])
def test_scenario_expected_outcome(filename):
    r = run_scenario(ROOT/"scenarios"/filename)
    assert r["demonstration_pass"]
    if r["expected"] == "FAIL":
        assert "v_burnout" in r["failed_checks"]
        assert r["actual"] == "FAIL"


def test_adapter_injection_uses_contract():
    calls = []
    def teammate_adapter(params, dt, method):
        calls.append((dt, method))
        return simulate(params, dt, method)
    result = run_scenario(ROOT/"scenarios/02_analytic_no_drag.yaml", simulator=teammate_adapter)
    assert result["demonstration_pass"] and len(calls) == 1


def test_crash_does_not_count_as_expected_failure():
    def crashed(params, dt, method):
        raise RuntimeError("unexpected engine crash")
    with pytest.raises(RuntimeError, match="unexpected engine crash"):
        run_scenario(ROOT/"scenarios/03_euler_coarse_fail.yaml", simulator=crashed)
