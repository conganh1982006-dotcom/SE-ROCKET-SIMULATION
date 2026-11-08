# Member C handoff


## Reading order

1. README and QUICKSTART_EN: run the project and locate outputs.
2. MATHEMATICS_EN: derive h(t), apogee, convergence order and acceleration definitions.
3. verification/checks.py: measurements, units, tolerances and verdicts.
4. verification/scenarios.py and YAML: actual outcomes versus expected demonstration results.
5. verification/convergence.py: log-ratio orders, fitting and INCONCLUSIVE handling.
6. rocket/interface.py and simulator.py: the data contract and event handling.
7. TRAJECTORY_VERIFICATION_EN and verification/trajectory.py: history checks, residual budgets and mutations.
8. WMLAB_INTEGRATION_EN, c5_rocket.py and scripts/wmlab_verify.py: toolkit API, JSON evidence and dataset formats.

## Interpret results

Run `python main.py report` after installing requirements. Test evidence is in outputs/pytest.txt and pytest.xml. After changing a simulator/test, run pytest first, then regenerate reports.

Absolute error has the quantity's units; relative error is dimensionless and becomes a percentage when multiplied by 100. At a zero reference, relative error is null and absolute tolerance applies. The usual acceptance condition is |observed−reference|≤atol+rtol|reference|. Bounds-check observed values can be violation magnitudes rather than raw quantities.

`actual` is the measured scenario verdict; `expected` is declared in advance. The coarse Euler case must have actual=FAIL, with v_burnout failing locally and reference_match failing in the toolkit. `demonstration_pass=true` means the framework detected that intended fault. Do not replace FAIL with PASS or raise its tolerance.

Run `python -m verification.mutations` for two clean baselines and 16 copied trajectories with faults. In the CSV, max_error_ratio≤1 is the acceptance criterion. Dynamics residuals can be nonzero on accurate data because of stencil error. A near-zero reference can make relative error large; do not use that ratio alone.

An acceleration-only mutation leaves h/v/m reference checks unaffected, but must fail dynamics_acceleration. A velocity mutation with a recalculated from the RHS can pass acceleration consistency while failing reference v and the v-prime residual.

## Calculate convergence yourself

In outputs/convergence.csv, choose one method and metric, such as Euler/h_burnout. Compute p=ln(E_0.1/E_0.05)/ln(2), then repeat for other adjacent steps. Orders close to 1,2,4 support the expected behavior within the studied range. Do not force a fit through roundoff-level errors.

## 13. Running the project, interpreting errors and integrating Member B

### 13.1. WSL workflow

From the directory containing main.py and requirements.txt:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

If multiple Python installations are available, select Python 3.13 when creating the environment. requirements.txt installs wmlab from the bundled vendor directory. In later terminal sessions, enter the project directory and activate .venv; dependencies do not need to be reinstalled for every run.

Typical commands are:

```bash
python main.py no-drag --method euler --dt 0.02
python main.py with-drag --method rk4 --dt 0.02 --c 0.002
python main.py compare --method rk4 --dt 0.02 --c 0.002
python main.py verify
python main.py report
```

The first three commands create separate simulation outputs. verify runs the standard verification suite; report reproduces the studies, evidence and standard V3 report. report does not automatically create a report for the latest quick run. This English technical report is stored separately in outputs/full_report_en/, so the automatic reporting workflow does not overwrite it. The earlier source-language report remains outside this English distribution.

### 13.2. Responding to common errors

| Symptom | What to check |
|---|---|
| main.py cannot be found | Confirm that the current directory is the project root |
| ModuleNotFoundError | Activate the correct environment and install requirements.txt |
| Unknown system c5_rocket | Check the --module c5_rocket.py option |
| Invalid physical parameters | Check m0 > mf > 0, q/ve/g > 0, h0/v0 ≥ 0 and q·ve > m0·g |
| NumericalError | Read the diagnostic, reduce dt if appropriate and check the parameter domain |
| A report contains FAIL | Read name, value, threshold, note/details and the scenario's expected outcome |
| Unexpected dataset shape | Check output_mode, horizon, dt and stride |
| A manual run differs from the standard report | Compare all parameters and methods, not just c |

A tolerance should not be increased merely to make a result pass. First determine whether the cause is a simulation error, adapter error, unit mismatch, time-alignment mistake or a deliberately inaccurate configuration.

### 13.3. Supplying Member B's simulator to the verifier

The local verification framework accepts an adapter(params, dt, method) function returning a Trajectory. The adapter must map the actual output of Member B's simulator into t, correctly ordered h/v/m values, SI units, a, burnout and apogee. It can be supplied through simulator=adapter to run_scenario or convergence_study.

If Member B's simulator does not yet provide events or acceleration, the data contract must be extended or the unverified portion must be stated explicitly. The adapter must not fill events from reference solutions, rerun the reference simulator to replace observations, or recompute a and then claim that Member B's original acceleration was verified. Independent solutions belong on the comparison side only.

This design keeps the same checks available when the simulator changes. Faults detected in mutated reference trajectories should remain detectable when equivalent data arrive through the group's adapter.


## Full Member B contract

The adapter accepts (params,dt,method) and returns Trajectory with:

- strictly increasing t in seconds, starting at zero and ending at apogee;
- y shaped N×3 with h (m), v (m/s), m (kg), positive upward;
- independently exported coordinate acceleration a (m/s²), coast-side at burnout;
- actual burnout/apogee Event objects with time, state and both acceleration limits;
- samples at both events and at least two intervals within each phase;
- the requested parameters and numerical method actually used.

Nonuniform time grids are accepted. Do not reconstruct missing candidate events from the reference, discard difficult samples or silently replace Euler/Heun with RK4. The adapter example in chapter 13 marks a connection point for the real team API, not an unfinished part of this reference simulator.

Call `verify_trajectory(result, params=parameters_requested)` for one trajectory. The reference and dynamics check functions can also be used separately; run_scenario passes scenario inputs as the independent source of parameters. Dynamics calibrates stencil bias using the reference, so the two layers are complementary rather than completely independent oracles.

## Submission preparation

The starter kit templates, schema, CLI and checks have been integrated. This edition localizes text while preserving numerical logic; see LOCALIZATION_EN for provenance. Use `python -m scripts.wmlab_verify` for toolkit evidence or `python main.py report` for the full pipeline. Read JSON passed_all/checks, not exit code alone.

Fill group names/student IDs, choose unique scenario IDs if needed and record individual contributions. If a separate answer template is issued later, transfer the report content without hand-editing numerical results. The supplied starter archive had no such template.

Explain why the official dataset contains common-time 0–4 s segments while the local dataset contains full ascents, and why official convergence uses a smooth 1.5 s horizon. Neither finite tests nor 16 mutations guarantee detection of every sub-tolerance or unexported error.

## Appendix B. Questions to be prepared to explain

### Why not use RK4 for everything?

RK4 is a convenient default, but Euler and Heun are needed to compare errors, measure convergence order and show how the method affects the result. Having several methods also supports a deliberate inaccuracy case with a coarse Euler step.

### Why does DOP853 not replace RK4?

RK4 is one of the algorithms being studied and is implemented directly in the project. DOP853 is used as an independent reference. Substituting DOP853 results for RK4 output would invalidate that comparison.

### Why are both pytest and wmlab used?

pytest checks specific code behavior, including invalid input, mutations, adapters and the CLI. wmlab follows the course's shared scenario contract and produces toolkit-format reports and datasets. These layers address complementary requirements.

### Does the DE kit run the rocket simulation by itself?

The kit's worked examples can run when invoked correctly. However, a set of templates does not automatically become the C5 model. The C5 module must provide the relevant equations, states, parameters and system-specific checks.

### Does a zero custom-check value mean zero numerical error?

No. For the three C5 custom checks, value is the number of failed subchecks. Actual errors appear in details. The meaning of value must be read separately for each check.

### Can the 200 dataset segments be treated as 200 apogee results?

No. The wmlab dataset stores only t from 0 to 4 s, and many flights have not reached apogee by 4 s. Apogee requires a full ascent or the local dataset with complete events.

### Does negative acceleration mean that the rocket is falling?

No. If v is positive and a is negative, the rocket is still rising but slowing down. It reaches the apex when v becomes zero. This is why the velocity and acceleration plots should be read together.

### Do three expected scenario outcomes mean three PASS verdicts?

No. The scenario set deliberately includes a coarse Euler case with excessive error. The demonstration succeeds when the two accurate cases pass and the inaccurate case fails the intended check.


Keep the required ai_use disclosure. Metadata default to consent_physeval=false.
