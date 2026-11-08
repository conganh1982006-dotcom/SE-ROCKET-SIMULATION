"""Integration against the text-localized supplied wmlab, including its real CLI."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
import yaml
import c5_rocket as module
from rocket import Parameters, simulate, quantities
from verification.trajectory import reference_history
from wmlab import schema
from wmlab.checks import run_checks

ROOT = Path(__file__).resolve().parents[1]
BASE = dict(m0=1.0,mf=0.6,q=0.2,ve=500.0,g=9.81,c=0.0,method="rk4")
INIT = dict(h0=0.0,v0=0.0)


@pytest.mark.parametrize("c", [0,0.002])
def test_official_bridge_preserves_full_ascent_exactly(c):
    p = {**BASE,"c":c}
    t,y = module.simulate(p,INIT,[0,40],0.02)
    r = simulate(Parameters(c=c))
    np.testing.assert_array_equal(t,r.t)
    np.testing.assert_array_equal(y,r.y)
    assert module.quantities(p,INIT,t,y) == quantities(r)


@pytest.mark.parametrize("method", ["euler","heun","rk4"])
@pytest.mark.parametrize("end", [1.5,2.0,2.003])
def test_fixed_horizon_stops_at_requested_time(method,end):
    p={**BASE,"method":method}
    t,y=module.simulate(p,INIT,[0,end],0.07)
    assert t[-1] == end
    assert y.shape==(len(t),3)
    assert np.all(np.diff(t)>0)
    if end>=2: assert np.any(t==2)
    if method=="rk4":
        np.testing.assert_allclose(y,module.analytic(p,INIT,t),atol=1e-5,rtol=0)


@pytest.mark.parametrize("filename,expected", [
    ("c5_baseline_drag.yaml",True),("c5_analytic_no_drag.yaml",True),("c5_euler_coarse_fail.yaml",False)])
def test_real_schema_and_checks(filename,expected):
    sc=yaml.safe_load((ROOT/"scenarios/wmlab"/filename).read_text(encoding="utf-8"))
    assert not schema.validate(sc,{module.NAME:module})
    t,y=module.simulate(sc['params'],sc['initial'],sc['t_span'],sc['dt'])
    checks=run_checks(sc,module,t,y)
    assert all(x['passed'] for x in checks) == expected
    if not expected:
        c=next(x for x in checks if x['name']=='reference_match')
        assert not c['passed'] and c['value']>c['threshold']


@pytest.mark.parametrize("field,index,delta,named", [
    ("h",0,1.0,"trajectory_reference"),("v",1,25.0,"trajectory_reference"),("m",2,0.02,"dynamics_consistency")])
def test_official_extra_checks_catch_mutated_supplied_arrays(field,index,delta,named):
    sc=yaml.safe_load((ROOT/"scenarios/wmlab/c5_baseline_drag.yaml").read_text(encoding="utf-8"))
    t,y=module.simulate(sc['params'],sc['initial'],sc['t_span'],sc['dt'])
    bad=y.copy(); i=np.argmin(abs(t-3)); bad[i,index]+=delta
    checks=run_checks(sc,module,t,bad)
    assert not next(x for x in checks if x['name']==named)['passed']
    np.testing.assert_array_equal(y[[0,-1]],bad[[0,-1]])
    assert y[i,index]!=bad[i,index]


def test_quantities_use_supplied_arrays_after_other_convergence_runs():
    t,y=module.simulate(BASE,INIT,[0,40],0.02)
    expected=module.quantities(BASE,INIT,t,y)
    module.simulate({**BASE,'q':.23},INIT,[0,1.5],0.1)
    assert module.quantities(BASE,INIT,t,y)==expected
    bad=y.copy(); bad[-1,0]+=1
    assert module.quantities(BASE,INIT,t,bad)['apogee']==expected['apogee']+1


def test_three_column_output_does_not_claim_independent_acceleration_check():
    sc=yaml.safe_load((ROOT/"scenarios/wmlab/c5_baseline_drag.yaml").read_text(encoding='utf-8'))
    t,y=module.simulate(sc['params'],sc['initial'],sc['t_span'],sc['dt'])
    result=module.dynamics_consistency(sc,module,t,y)
    assert result['passed']
    assert 'dynamics_acceleration' not in {x['name'] for x in result['details']}


def test_official_dataset_observations_share_grid_and_match_independent_reference():
    rng=np.random.default_rng(20261027)
    common=None
    for _ in range(5):
        p,init,ts,dt=module.sample(rng)
        t,y=module.simulate(p,init,ts,dt)
        if common is None: common=t
        np.testing.assert_array_equal(t,common)
        assert y.shape==(201,3)
        ref=reference_history(module.parameters(p,init),t)
        np.testing.assert_allclose(y,ref,atol=2e-4,rtol=0)


def test_real_cli_expected_fail_is_reported_even_when_exit_code_is_zero(tmp_path):
    command=[sys.executable,'-m','wmlab','--lang','en','check',
             'scenarios/wmlab/c5_euler_coarse_fail.yaml','--module','c5_rocket.py','-o',str(tmp_path)]
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    assert run.returncode==0,run.stderr  # documented behavior of supplied 0.1.1
    report=json.loads(next(tmp_path.glob('*_report.json')).read_text(encoding='utf-8'))
    assert report['passed_all'] is False
    assert not next(c for c in report['checks'] if c['name']=='reference_match')['passed']
