# C5 Model Rocket — English edition

Start with **`python main.py`**. The menu runs simulations, comparisons, verification and report generation from one entry point. See [QUICKSTART_EN.md](QUICKSTART_EN.md) for WSL installation, parameters, methods and plots.

This is the English edition of C5 Rocket V3.1. Physics, Euler/Heun/RK4, event handling, numerical tolerances and the Member B adapter contract are preserved. All project-facing text, documentation, comments and generated presentation outputs use English. Preferred documentation names end in `_EN`. This cleaned submission ZIP omits unused duplicate `_VI` guides. Three old `_VI` guides remain solely to preserve references from Python documentation strings and the legacy local system card; their contents are English.

The bundled wmlab 0.1.1 contains translated comments, documentation and messages. It is a **text-localized copy**, not a byte-identical upstream release. Original hashes remain in `vendor/STARTER_KIT_PROVENANCE.json`; localized hashes are recorded separately in `vendor/ENGLISH_LOCALIZATION.json`. The runner checks the bundled and active installed copies against this English-edition manifest. DE kit templates and numerical algorithms remain unchanged. See [LOCALIZATION_EN.md](docs/LOCALIZATION_EN.md) and [CHANGELOG.md](CHANGELOG.md).

## Install and run

Run these commands from the directory containing `main.py`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Use Python 3.13 to match the tested environment. The local requirements install the supplied wmlab package; do not install an unrelated package with the same name from PyPI. No new application dependencies are required.

```bash
python main.py compare --method rk4 --dt 0.02 --c 0.002
python main.py verify
python main.py report
python -m scripts.package
```

`verify` runs pytest, local scenarios, convergence, mutations and the actual wmlab CLI. `report` reproduces all experiments, both datasets, tests and the short English PDF/Markdown report. Both commands update standard evidence. Manual simulations write only to new directories in `outputs/quick_runs/`.

The deliberate coarse Euler case must remain **FAIL**: `v_burnout` must fail locally and `reference_match` must fail through wmlab with a finite numerical error. An exception is not a successful demonstration. wmlab 0.1.1 can exit with code 0 even when checks fail, so the runner reads JSON verdicts.

## Results and evidence

| File or directory | Contents |
|---|---|
| `outputs/report_en.pdf`, `.md` | Reproducible short English report |
| `outputs/report_vi.pdf`, `.md` | Exact English compatibility duplicates omitted from this cleaned ZIP; running `python main.py report` regenerates them automatically (the report-generation code is unchanged) |
| `outputs/full_report_en/` | Full English report, Word/PDF/Markdown, based on the recorded V3.1 run of 28 October 2026; retained as a historical explanation |
| `outputs/summary.json` | Numerical results, environment and metadata |
| `outputs/pytest.txt`, `.xml` | Actual regression-test output |
| `outputs/wmlab/*_report.json`, `logs/` | Actual toolkit verdicts and command logs |
| `convergence/wmlab/` | Official-schema convergence YAML and raw reports at a 1.5 s horizon |
| `outputs/wmlab/summary.json`, `mutations.json`, `dataset_validation.json` | Toolkit summary, 12 mutations, independent checks of all 200 segments |
| `system_card.yaml` | Supplied-template metadata and measured convergence orders |
| `c5_rocket.npz` | Toolkit dataset: 200 common-time ascent segments, shape (200,201,3), t=0–4 s, stride=1 |
| `outputs/scenarios/` | Local checks with units, tolerances and absolute/relative errors |
| `outputs/trajectory_verification.json`, `.csv` | Whole-trajectory errors, ODE residuals, budgets and mutation results |
| `convergence/{euler,heun,rk4}.json`, `outputs/convergence.csv` | Local errors and observed orders |
| `outputs/history_*.csv`, `outputs/figures/` | t,h,v,m,a histories and scientific figures |
| `outputs/local_dataset_200.npz` | Additional 200 variable-length full ascents to apogee, in the local format |
| `outputs/english_validation/` | English-edition run logs, preservation comparisons and localization checks |

Historical V2/V3/V3.1 evidence remains labeled by its original date. Translated historical logs are identified as translations; current English-edition logs are kept separately. The full report describes the original V3.1 implementation; consult the localization notes for the later text-only toolkit changes.

## Simulator and verification API

```python
from rocket import Parameters, simulate, quantities
from verification.trajectory import verify_trajectory

p = Parameters(c=0.002, q=0.2)
r = simulate(p, dt=0.02, method="rk4")
print(quantities(r))
print(r.burnout.t, r.apogee.t)
# r.t: (N,), r.y: (N,3) = h,v,m, r.a: (N,)
checks = verify_trajectory(r, params=p)
assert all(check.passed for check in checks)
```

`q` is positive propellant consumption rate. `c` is measured in kg/m, not a dimensionless aerodynamic coefficient. `dt` is the requested maximum step; steps shorten at burnout and apogee. The solver does not silently refine poor results into passing ones.

`max_acceleration_g = max |dv/dt|/g`, while `max_proper_acceleration_g = max |dv/dt+g|/g`. Both burnout limits are included. Extrema between samples remain estimates; see `peak_acceleration.csv`. With drag, post-burnout deceleration can have a larger magnitude than upward acceleration.

For Member B, pass `simulator=adapter` to `run_scenario` or `convergence_study`. Supply the requested parameters explicitly to `verify_trajectory`; do not use parameters silently changed by an adapter as the reference. Local YAML can specify `trajectory_tolerances` with h_atol, v_atol, m_atol, state_rtol, a_atol and a_rtol. Agree tolerances before looking at results.

Reference checks use every exported time. Dynamics checks use phase-specific intervals, with coast-side stored acceleration at burnout. Missing burnout or insufficient within-phase coverage fails verification. These checks detect exported errors above tolerance; they do not prove continuous-time correctness or experimental validity.

## Code map and reading order

- `rocket/`: parameters, ODE, integration steps, event handling, analytical references and Trajectory contract.
- `verification/`: independent DOP853, endpoint/trajectory/dynamics checks, mutations, scenarios and convergence.
- `experiments/`: studies, dataset generation, quick-run presentation and reports.
- `c5_rocket.py`: adapter implementing the supplied toolkit API.
- `scripts/`: reproduction, wmlab execution and packaging.
- `scenarios/`: local YAML; `scenarios/wmlab/`: official-schema YAML.
- `tests/`: regression, verifier, adapter, dataset and CLI tests.
- `vendor/`: supplied DE kit and text-localized wmlab, with provenance.

Read [Member C handoff](docs/MEMBER_C_HANDOFF_EN.md), [wmlab integration](docs/WMLAB_INTEGRATION_EN.md), [mathematics](docs/MATHEMATICS_EN.md), [trajectory verification](docs/TRAJECTORY_VERIFICATION_EN.md), then [requirements and limitations](docs/REQUIREMENTS_AND_LIMITS_EN.md).

Enter names/student IDs in the six toolkit scenario/convergence YAML files, `system_card.yaml` and report author fields. Update scenario IDs if needed and rerun reproduction so generated metadata match.

## Sources and disclosure

The supplied Quang Nguyen, *Differential Equations – Simulation Projects*, v1.0, October 2026, sections 1–5 and C5 pages 10–11 defines the course context. The original PDF is not redistributed here. See also the [official SciPy solve_ivp documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).

OpenAI Codex assisted with code, reasoning, testing, figures, documentation and translation. Students should review and explain the work before using it in a group submission. Metadata retain `consent_physeval: false`; the project has not been published to a shared course collection.
