# C5 Rocket V3.1 — start with main.py

Use `python main.py` for the interactive menu, or choose one command:

```bash
python main.py no-drag
python main.py with-drag
python main.py compare
python main.py verify
python main.py report
```

The CLI delegates to the existing C5 simulation and verification framework. The English edition changes presentation text without changing the rocket equations, numerical methods or adapter contract.

## 1. Install on WSL Ubuntu

Extract the ZIP, open Ubuntu and enter the directory containing `main.py` and `requirements.txt`. For example:

```bash
cd /path/to/SE-ROCKET-SIMULATION-main
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Replace the path with your extraction location. Python 3.13 matches the tested environment; use `python3.13 -m venv .venv` if you have several installations. If venv is missing, install the venv package for your Python version. Do not copy a Windows virtual environment into WSL.

Requirements install wmlab from `vendor/starter_kit/wmlab`. This English edition needs no new runtime dependencies. Create a fresh environment for this copy so an older installed wmlab does not fail the localization hash check.

For subsequent sessions:

```bash
cd /path/to/c5_rocket_english
source .venv/bin/activate
python main.py
```

Plots are saved as PNG files without a Linux desktop or graphical window. Run `explorer.exe .` in WSL to open the directory in Windows Explorer.

## 2. Interactive menu

| Choice | Purpose |
|---|---|
| 1. No Drag Simulation | Use c=0 |
| 2. With Drag Simulation | Use a positive drag coefficient |
| 3. Compare No Drag vs With Drag | Keep all inputs identical except c |
| 4. Run Verification | Run pytest, local checks and the actual toolkit |
| 5. Generate Report | Reproduce experiments and create English PDF/Markdown |
| 0. Exit | Close the menu |

For modes 1–3, choose the numerical method, dt and, where relevant, c. Press Enter for defaults. Enter `y` to edit other physical parameters or `n` to retain them. After export, the menu returns. Ctrl+C interrupts with exit code 130.

An easy first run: select 3, then press Enter for RK4, dt=0.02, c=0.002 and default parameters. The program prints a comparison table and the new output directory.

## 3. Repeatable command-line runs

```bash
# Compare the two models with the same method and time step.
python main.py compare --method rk4 --dt 0.02 --c 0.002
# Try other methods.
python main.py no-drag --method euler --dt 0.02
python main.py with-drag --method heun --dt 0.01 --c 0.002
# Change drag and propellant consumption rate.
python main.py with-drag --method rk4 --dt 0.02 --c 0.003 --q 0.15
# Inspect all options.
python main.py --help
python main.py compare --help
```

`no-drag` always uses c=0 and rejects `--c`. `with-drag` and `compare` require c>0, default 0.002 kg/m. Compare changes only c; each trajectory ends at its own apogee and may contain a different number of samples.

| Option | Meaning | Default |
|---|---|---:|
| `--method` | euler, heun or rk4 | rk4 |
| `--dt` | Time step (s) | 0.02 |
| `--m0` | Initial mass (kg) | 1.0 |
| `--mf` | Dry mass (kg) | 0.6 |
| `--q` | Propellant consumption rate (kg/s) | 0.2 |
| `--ve` | Exhaust velocity (m/s) | 500 |
| `--g` | Gravitational acceleration (m/s²) | 9.81 |
| `--h0` | Initial altitude (m) | 0 |
| `--v0` | Initial velocity (m/s) | 0 |

All values must be finite. Conditions are m0>mf>0; q,ve,g>0; h0,v0≥0; q*ve>m0*g; dt>0. The model covers immediate-liftoff ascent, not launch-pad waiting or descent. Valid physical parameters can still require a smaller numerical step. The CLI reports errors without silently changing your inputs.

**Method choice:** RK4 is the default for exploration and usually has smaller error at the same dt. Euler is useful for learning first-order error. Heun is second order. Compare the same configuration at dt=0.02 and 0.01 to assess sensitivity. Smaller steps cost more computation; excessively small steps can encounter step-count or floating-point resolution limits. The CLI uses the selected method directly.

## 4. Locate and interpret outputs

Each manual simulation creates:

```text
outputs/quick_runs/<UTC_timestamp>_<mode>_<unique_id>/
    results.json
    summary.csv
    no_drag.csv       # No Drag or Compare
    with_drag.csv     # With Drag or Compare
    altitude.png
    velocity.png
    acceleration.png
    mass.png
```

Timestamps use UTC and include timezone information in JSON. Convert to your local timezone if needed. Unique IDs prevent overwriting concurrent runs.

The terminal table and `summary.csv` list burnout time/altitude/velocity, apogee altitude, time to apogee and peak acceleration. Summary CSV also records parameters, method, dt and creation time. `results.json` contains units, each case, event states, both burnout acceleration limits and output filenames. It is written last: a failed export can leave an incomplete directory without this completion record.

Trajectory CSV columns are `t_s,h_m,v_m_s,m_kg,a_m_s2`. Open them in Excel or Python. To change results, change inputs and run again rather than editing numerical evidence.

- **Altitude vs Time:** altitude rises to apogee, where the simulation ends.
- **Velocity vs Time:** upward velocity approaches zero at apogee; peak speed need not coincide with burnout when drag is present.
- **Acceleration vs Time:** signed coordinate acceleration in m/s². A negative value means upward velocity is decreasing, not necessarily that descent has started.
- **Mass vs Time:** mass decreases during burn and stays at mf during coast.

Circles mark burnout, diamonds apogee, and vertical dashed lines their times. Stars and horizontal dotted lines mark sampled extrema, with values on the Y axis. Closely spaced Y labels may be merged for readability; CSV/JSON retain each value.

For acceleration, the star marks the greatest **magnitude**, which may be negative. The plot preserves the burnout jump: an open circle is the left limit and a filled circle the right limit. CSV stores the right limit; JSON stores both. Do not differentiate across this discontinuity.

`Peak |a|/g` is the largest sampled coordinate acceleration magnitude divided by g, including both burnout limits. It is not proper acceleration. Within-phase peaks are estimates; refine dt to assess them. The plot uses m/s² while the peak table uses g units.

A completed quick run is **not a verification PASS**. Its JSON sets `verification_performed=false`. Verify checks the standard V3 configurations, not every manually chosen parameter set. To verify a custom run, use the functions in `verification/` with those parameters; see [trajectory verification](docs/TRAJECTORY_VERIFICATION_EN.md).

## 5. Verification and report generation

```bash
python main.py verify
python main.py report
```

Verify runs pytest → local scenarios → local convergence → mutations → `scripts.wmlab_verify`. The last step checks three scenarios, three convergence reports, mutations and all 200 regenerated dataset segments. It reads JSON because wmlab 0.1.1 exit code 0 alone does not prove the checks passed.

Expected scenario outcomes are PASS, PASS and a deliberate coarse-Euler FAIL. The test confirming that failure passes. Any unexpected outcome stops the workflow with a nonzero exit code.

Report calls `scripts.reproduce` and creates `outputs/report_en.pdf`, `report_en.md` and `summary.json`. Compatibility files `report_vi.pdf/.md` contain the same English output. There is no need to run Verify first. This is the standard scientific report, not a custom report of the latest quick run. The full English Word/PDF report in `outputs/full_report_en/` remains a separate historical document.

Verify and Report update standard evidence and datasets. Only manual simulation modes are isolated in new quick-run directories. Existing quick runs are retained.

Command-line subcommands never prompt for extra input. Exit 0 means completion; 2 commonly indicates invalid input/operation; subprocess failures propagate. Ctrl+C/EOF returns 130.

## 6. Files worth understanding

| File or directory | Role |
|---|---|
| `main.py` | Menu, arguments and workflow dispatch |
| `experiments/quick_runs.py` | Tables, CSV/JSON and four plots |
| `rocket/model.py` | Parameters, validity checks and ODE |
| `rocket/methods.py`, `rocket/simulator.py` | Numerical steps and events |
| `rocket/interface.py` | Trajectory contract for Member B |
| `verification/`, `tests/` | Independent checks, regression and mutations |
| `scenarios/`, `convergence/` | Standard verification configurations and evidence |
| `c5_rocket.py` | Toolkit adapter |
| `scripts/`, remaining `experiments/` | Internal orchestration called by the CLI |
| `vendor/starter_kit/` | DE kit and localized toolkit; do not change algorithms |
| `outputs/` | Generated evidence |

Simulation flow: `main.py` → `quick_runs.calculate` → `rocket.simulate` → `Trajectory` → `quantities` → tables/plots/CSV/JSON. There is no duplicate ODE in the CLI.

Continue with [README](README.md), [Member C handoff](docs/MEMBER_C_HANDOFF_EN.md), [wmlab integration](docs/WMLAB_INTEGRATION_EN.md), [example](docs/EXAMPLE_CLI_EN.md) and [CHANGELOG](CHANGELOG.md).
