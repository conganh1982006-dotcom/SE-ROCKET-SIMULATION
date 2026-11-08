# wmlab — physics-based World Models (teaching edition 0.1)

A shared toolkit for four courses. Assignments and projects submit one YAML/JSON scenario using a common data contract, then run simulation and automated checks based on physical laws.

This copy is text-localized into English. Numerical algorithms are preserved; the parent project's vendor manifests distinguish original and localized hashes.

## Installation

```bash
pip install .  # Run in this directory, or use the parent project requirements.
```

## Commands

| Command | Purpose |
|---|---|
| `python -m wmlab systems` | List available systems |
| `python -m wmlab validate example.yaml` | Check the scenario schema |
| `python -m wmlab check example.yaml -o out/` | Simulate/check and save out/<id>_report.json |
| `python -m wmlab dataset --system oscillator --n 500 -o data.npz` | Generate a random dataset for a neural-model project |
| `python -m wmlab collect out/ -o registry.csv` | Collect reports and mark pool eligibility |

Both legacy language selectors remain accepted; this edition displays English for either.

## Built-in systems

`projectile_drag`: projectile motion with drag; `oscillator`: forced damped oscillations with an analytical solution; `heat1d`: FTCS/Crank–Nicolson heat equation; `lorenz`: chaos and Lyapunov exponent; `langevin`: thermal-bath oscillator, equipartition and fluctuation-dissipation; `lorentz`: charged particles in E/B fields, Larmor radius and E×B drift, Boris versus RK4; `heat2d`: sourced heat equation with insulated boundaries and simulated thermal sensor images.

## Checks

analytic_match, convergence_order, energy_conserved, energy_nonincreasing, invariant_conserved, within_bounds, reference_match, max_principle, stability, heat_balance, lyapunov_reference, equipartition, fdt and answer_matches are available as implemented in checks.py. Modules can add EXTRA_CHECKS.

## Scenario data contract

```yaml
id: phy1-proj-range-demo          # Unique identifier.
author: "Name (student ID)"
course: PHY1                     # PHY1 | PHY2 | PHY3 | DE | AMCS | RS
system: projectile_drag
law: "Describe the applicable physical law"
params: {...}
initial: {...}
t_span: [0.0, 4.0]
dt: 0.001
question:                        # Optional; required for Physics 1–3 assignments.
  text: "..."
  quantity: range                # Quantity produced by the simulation.
  answer: 38.31                  # Computed independently by the student.
  unit: m
  tolerance: 0.005               # Relative tolerance.
misconceptions: ["..."]          # Optional common misconceptions.
checks: [answer_matches, energy_conserved, {name: analytic_match, tol: 1.0e-6}]
license: CC-BY-4.0                # CC-BY-4.0 | CC0-1.0 | MIT | ALL-RIGHTS-RESERVED
consent_physeval: true            # Voluntary; does not affect grades.
```

## Add a system

Implement simulate, analytic (or return None), quantities and sample, plus energy if applicable. Modules in wmlab/sims can be registered in REGISTRY. Version 0.1.1 also supports `--module path/to/system.py`, used by C5 without editing the built-in registry.

## Examples

examples/ contains 11 scenarios, some designed to fail (such as unstable FTCS), plus amcs_surrogate_starter.py. The example MLP can have a small one-step loss (about 3e-5) yet large long-rollout energy drift (over 300% after 100 s), motivating physical verification rather than loss alone. These are example descriptions, not results of the C5 localization validation.
