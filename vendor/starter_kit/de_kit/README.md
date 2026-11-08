# Differential Equations — Project Starter Kit

## Setup (once)
```bash
pip install numpy pyyaml
pip install ./wmlab            # the verification toolkit, shipped next to this folder
export WMLAB_LANG=en           # English messages (Windows PowerShell: $env:WMLAB_LANG="en")
```
No installation? Run everything on Google Colab: upload the two folders and prefix commands with `!`.

## Files
| File | What it is |
|---|---|
| `example_cooling.py` | **Worked example.** A complete project module (Newton + radiative cooling). Read it first. |
| `scenarios/cooling_*.yaml` | Three example scenarios: baseline (passes), nonlinear (passes), deliberately failing (Euler too large a step). |
| `example_system_card.yaml` | Example datasheet for the cooling model. |
| `template_system.py` | **Copy this** to `<your_system>.py` and fill in every `TODO`. |
| `scenario_template.yaml` | Copy for each scenario you submit (at least 3). |
| `system_card_template.yaml` | Copy to `system_card.yaml` and fill in. |

## Try the worked example
```bash
python -m wmlab check scenarios/cooling_newton.yaml        --module example_cooling.py
python -m wmlab check scenarios/cooling_radiative.yaml     --module example_cooling.py
python -m wmlab check scenarios/cooling_euler_bigstep.yaml --module example_cooling.py   # FAILS on purpose
python -m wmlab dataset --system cooling --module example_cooling.py --n 200 -o cooling.npz
```

## Your workflow
1. `cp template_system.py pendulum.py` (use your system's name) and implement `rhs`, `analytic`,
   `quantities`, `sample` (+ `energy` / `invariant` / `bounds` / `reference_quantities` when they apply).
2. Write 3+ scenarios, run `python -m wmlab check <scenario>.yaml --module pendulum.py`.
3. Convergence study: run the same scenario with `method: euler`, `heun`, `rk4` and record the observed orders.
4. Generate the dataset: `python -m wmlab dataset --system pendulum --module pendulum.py --n 200 -o pendulum.npz`.
5. Fill `system_card.yaml` and the report template.

## Available checks
`analytic_match` · `convergence_order` (`expected: 1|2|4`, `mode: analytic|self`) · `energy_conserved` ·
`energy_nonincreasing` · `invariant_conserved` · `within_bounds` (`tol`) · `reference_match` · `answer_matches`
— plus any project-specific check you add in `EXTRA_CHECKS` (see `example_cooling.py`).

## Tips that save hours
- A second-order ODE becomes a first-order system: `y = [x, v]`, `y' = [v, a(t, x, v)]`.
- `sqrt`, `log`, division: guard against invalid values (e.g. `max(h, 0.0)` for a draining tank).
- Convergence orders are only meaningful when the step is small enough **and** the right-hand side is smooth.
  If yours is not (switches, impacts, a rope going slack), say so — that is a finding, not a failure.
- Every `sample()` draw must use the same `t_span` and `dt`, and must stay physically sensible.
