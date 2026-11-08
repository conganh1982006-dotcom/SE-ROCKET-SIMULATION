"""Run the provided wmlab CLI; validate its JSON verdicts, not just exit codes."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import yaml
import wmlab
import c5_rocket
from wmlab.checks import run_checks
from verification.trajectory import reference_history, TrajectoryTolerances

ROOT=Path(__file__).resolve().parents[1]


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")


def verify_vendor():
    manifest=json.loads((ROOT/"vendor/STARTER_KIT_PROVENANCE.json").read_text())
    localization_path=ROOT/"vendor/ENGLISH_LOCALIZATION.json"
    localization=json.loads(localization_path.read_text())
    original_path=ROOT/"vendor/STARTER_KIT_PROVENANCE.json"
    if hashlib.sha256(original_path.read_bytes()).hexdigest()!=localization['original_manifest_sha256']:
        raise RuntimeError("Original starter-kit provenance manifest was modified.")
    if localization['original_archive_sha256']!=manifest['archive_sha256']:
        raise RuntimeError("Localization does not identify the supplied starter archive.")
    expected=localization['localized_files_sha256']
    if set(expected)!=set(manifest['unmodified_files_sha256']):
        raise RuntimeError("Localization manifest must cover every supplied starter-kit file.")
    installed=Path(wmlab.__file__).parent
    for name,digest in expected.items():
        file=ROOT/"vendor/starter_kit"/name
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
            raise RuntimeError(f"English starter-kit file differs from its recorded hash: {name}")
        prefix="wmlab/wmlab/"
        if name.startswith(prefix):
            active=installed/name[len(prefix):]
            if hashlib.sha256(active.read_bytes()).hexdigest()!=digest:
                raise RuntimeError(f"Active wmlab differs from the English toolkit; reinstall requirements: {active}")
    return {"version":wmlab.__version__,"original_toolkit_unchanged":False,
            "localization":"English text; numerical algorithms preserved",
            "localized_toolkit_hashes_verified":True,
            "original_archive_sha256":manifest['archive_sha256'],
            "localization_manifest_sha256":hashlib.sha256(localization_path.read_bytes()).hexdigest(),
            "module_file":str(installed)}


def command(args,log):
    cmd=[sys.executable,"-m","wmlab","--lang","en",*args]
    env={**os.environ,"PYTHONIOENCODING":"utf-8"}
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",env=env)
    log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text("COMMAND: "+" ".join(cmd)+"\n\n"+run.stdout+run.stderr,encoding="utf-8")
    if run.returncode:
        raise RuntimeError(f"wmlab command error (exit {run.returncode}); see {log}")
    return run


def run_case(path,output,expected_pass=True,must_fail=None):
    sc=yaml.safe_load(path.read_text(encoding="utf-8"))
    logdir=ROOT/"outputs/wmlab/logs"
    command(["validate",str(path),"--module","c5_rocket.py"],logdir/f"{path.stem}_validate.txt")
    command(["check",str(path),"--module","c5_rocket.py","-o",str(output)],logdir/f"{path.stem}_check.txt")
    report_path=output/f"{sc['id']}_report.json"
    report=json.loads(report_path.read_text(encoding="utf-8"))
    failed=[c['name'] for c in report['checks'] if not c['passed']]
    matched=report['passed_all']==expected_pass
    if must_fail:
        target=next(c for c in report['checks'] if c['name']==must_fail)
        # Check errors / missing implementations must not masquerade as expected inaccuracy.
        matched=matched and must_fail in failed and target['value'] is not None and math.isfinite(target['value'])
    for c in report['checks']:
        if c['name']=='convergence_order':
            expected=float(next(x['expected'] for x in sc['checks'] if isinstance(x,dict) and x['name']=='convergence_order'))
            matched=matched and c['value'] is not None and math.isfinite(c['value']) and abs(c['value']-expected)<=0.5
    if not matched:
        raise RuntimeError(f"Unexpected wmlab outcome: {report_path}")
    print(f"wmlab {path.stem}: actual={'PASS' if report['passed_all'] else 'FAIL'}, expected={'PASS' if expected_pass else 'FAIL'}",flush=True)
    return {"scenario":str(path.relative_to(ROOT)),"report":str(report_path.relative_to(ROOT)),
            "expected":"PASS" if expected_pass else "FAIL","actual":"PASS" if report['passed_all'] else "FAIL",
            "demonstration_pass":matched,"failed_checks":failed,"official_report":report}


def official_mutations():
    cases=[]
    for filename in ["c5_baseline_drag.yaml","c5_analytic_no_drag.yaml"]:
        sc=yaml.safe_load((ROOT/"scenarios/wmlab"/filename).read_text(encoding="utf-8"))
        t,y=c5_rocket.simulate(sc['params'],sc['initial'],sc['t_span'],sc['dt'])
        before=y.copy()
        for target in [1.0,3.0]:
            for j,field,delta in [(0,'h',1.0),(1,'v',25.0),(2,'m',0.02)]:
                bad=y.copy(); i=int(np.argmin(abs(t-target))); bad[i,j]+=delta
                checks=run_checks(sc,c5_rocket,t,bad)
                failed=[c['name'] for c in checks if not c['passed']]
                detected={'trajectory_reference','dynamics_consistency'}<=set(failed)
                untouched=np.array_equal(before,y) and np.array_equal(before[[0,-1]],bad[[0,-1]])
                if not detected or not untouched:
                    raise RuntimeError("Official EXTRA_CHECKS mutation demonstration failed.")
                cases.append({'c':sc['params']['c'],'time_s':float(t[i]),'field':field,'delta':delta,
                              'detected':detected,'original_and_endpoints_unchanged':untouched,'failed_checks':failed})
    return {'count':len(cases),'detected':sum(c['detected'] for c in cases),'cases':cases,
            'acceleration_channel':'Not exported in wmlab STATE=[h,v,m]; use the v2 adapter mutation tests for a.'}


def verify_dataset(path):
    with np.load(path,allow_pickle=False) as z:
        t,y,meta=z['t'].copy(),z['Y'].copy(),json.loads(str(z['meta']))
        state=json.loads(str(z['state']))
        system=str(z['system'])
    if state!=c5_rocket.STATE or system!=c5_rocket.NAME or y.shape!=(200,201,3) or len(meta)!=200:
        raise RuntimeError("Official dataset has an unexpected contract/shape.")
    np.testing.assert_array_equal(t,np.linspace(0,4,201))
    tol=TrajectoryTolerances()
    max_error=np.zeros(3); max_ratio=np.zeros(3)
    burnout_times=[]
    for row,metadata in zip(y,meta):
        p=c5_rocket.parameters(metadata['params'],metadata['initial'])
        ref=reference_history(p,t)
        budget=np.column_stack([tol.h_atol+tol.state_rtol*abs(ref[:,0]),
                                tol.v_atol+tol.state_rtol*abs(ref[:,1]),np.full(len(t),tol.m_atol)])
        error=abs(row-ref)
        if not np.all(np.isfinite(row)) or np.any(error>budget):
            raise RuntimeError("Official dataset trajectory failed independent reference comparison.")
        if np.any(row[:,2]<p.mf-1e-10) or np.any(row[:,1]<-1e-8):
            raise RuntimeError("Official dataset violated ascent physical bounds.")
        max_error=np.maximum(max_error,error.max(axis=0)); max_ratio=np.maximum(max_ratio,(error/budget).max(axis=0))
        burnout_times.append(p.burn_time)
    return {'generated_by':'python -m wmlab dataset','official_toolkit':True,'count':200,
            'shape':list(y.shape),'t_span_s':[0,4],'dt_s':0.02,'stride':1,'seed':20261027,
            'scope':'Common-time ascent segments; full variable-duration ascents remain in local_dataset_200.npz.',
            'independent_reference_checked':200,'max_absolute_error_h_v_m':max_error.tolist(),
            'max_error_ratio_h_v_m':max_ratio.tolist(),'burnout_time_range_s':[min(burnout_times),max(burnout_times)],
            'passed':bool(np.all(max_ratio<=1)), 'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def run_official():
    out=ROOT/"outputs/wmlab"
    toolkit=verify_vendor()
    cases=[]
    for name,expected,failed in [("c5_baseline_drag.yaml",True,None),("c5_analytic_no_drag.yaml",True,None),
                                  ("c5_euler_coarse_fail.yaml",False,"reference_match")]:
        cases.append(run_case(ROOT/"scenarios/wmlab"/name,out,expected,failed))
    convergence=[run_case(ROOT/"convergence/wmlab"/f"{method}.yaml",ROOT/"convergence/wmlab")
                 for method in ["euler","heun","rk4"]]
    mutations=official_mutations()
    write_json(out/"mutations.json",mutations)
    command(["dataset","--system","c5_rocket","--module","c5_rocket.py","--n","200",
             "--seed","20261027","--stride","1","-o","c5_rocket.npz"],out/"logs/dataset.txt")
    dataset=verify_dataset(ROOT/"c5_rocket.npz")
    write_json(out/"dataset_validation.json",dataset)
    summary={'official_toolkit':True,'toolkit':toolkit,'scenarios':cases,'convergence':convergence,
             'mutations':mutations,'dataset':dataset,
             'passed':all(x['demonstration_pass'] for x in cases+convergence) and dataset['passed']}
    write_json(out/"summary.json",summary)
    card_path=ROOT/"system_card.yaml"
    if card_path.exists():
        card=yaml.safe_load(card_path.read_text(encoding="utf-8"))
        card['observed_convergence_order']={Path(case['scenario']).stem:
            next(c['value'] for c in case['official_report']['checks'] if c['name']=='convergence_order') for case in convergence}
        card['dataset']['shape']=str(tuple(dataset['shape']))
        card_path.write_text(yaml.safe_dump(card,sort_keys=False,allow_unicode=True),encoding="utf-8")
    print("Official wmlab complete: 3 expected scenario outcomes, 3 convergence reports, 200 verified dataset segments.",flush=True)
    return summary


if __name__=="__main__":
    run_official()
