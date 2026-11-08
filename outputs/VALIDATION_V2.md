# V2 validation — historical recorded results

English translation of the V2 evidence, recorded 24 October 2026; this is not the English-edition rerun.

- Environment: Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; Python 3.13.17.
- Pytest: 101/101 PASS; failures=0, errors=0, skipped=0.
- Scenarios: 3/3 expected outcomes; deliberate coarse Euler remains actual FAIL.
- Convergence: 3/3 PASS.
- Clean trajectories: 2/2 PASS.
- Mutations: 16/16 detected by the designated checks; original arrays/events unchanged: True.

## All-sample comparison — baseline RK4, dt=0.02 s

| c (kg/m) | Quantity | N | Max absolute error | Max relative error | Unit | Status |
|---|---|---|---|---|---|---|
| 0.0 | trajectory_h | 1303 | 3.760806e-08 | 1.188120e-09 | m | PASS |
| 0.0 | trajectory_v | 1303 | 1.790681e-09 | 9.994730e-01 | m/s | PASS |
| 0.0 | trajectory_m | 1303 | 1.110223e-16 | 1.476360e-16 | kg | PASS |
| 0.002 | trajectory_h | 451 | 1.588363e-07 | 8.984085e-09 | m | PASS |
| 0.002 | trajectory_v | 451 | 6.681879e-08 | 9.993435e-01 | m/s | PASS |
| 0.002 | trajectory_m | 451 | 1.110223e-16 | 1.476360e-16 | kg | PASS |

Relative errors near zero can be large. Verdicts use atol+rtol*|reference| at each sample; exact-zero references are excluded from the relative maximum.

## Mutations in both phases

| c | t (s) | Field | Change | Detecting dynamics check | Actual |
|---|---|---|---|---|---|
| 0.0 | 1.000 | v | +25.0 m/s | dynamics_v_prime | FAIL |
| 0.0 | 1.000 | h | +1.0 m | dynamics_h_prime | FAIL |
| 0.0 | 1.000 | m | +0.02 kg | dynamics_m_prime_burn | FAIL |
| 0.0 | 1.000 | a | +25.0 m/s^2 | dynamics_acceleration | FAIL |
| 0.0 | 3.000 | v | +25.0 m/s | dynamics_v_prime | FAIL |
| 0.0 | 3.000 | h | +1.0 m | dynamics_h_prime | FAIL |
| 0.0 | 3.000 | m | +0.02 kg | dynamics_m_prime_coast | FAIL |
| 0.0 | 3.000 | a | +25.0 m/s^2 | dynamics_acceleration | FAIL |
| 0.002 | 1.000 | v | +25.0 m/s | dynamics_v_prime | FAIL |
| 0.002 | 1.000 | h | +1.0 m | dynamics_h_prime | FAIL |
| 0.002 | 1.000 | m | +0.02 kg | dynamics_m_prime_burn | FAIL |
| 0.002 | 1.000 | a | +25.0 m/s^2 | dynamics_acceleration | FAIL |
| 0.002 | 3.000 | v | +25.0 m/s | dynamics_v_prime | FAIL |
| 0.002 | 3.000 | h | +1.0 m | dynamics_h_prime | FAIL |
| 0.002 | 3.000 | m | +0.02 kg | dynamics_m_prime_coast | FAIL |
| 0.002 | 3.000 | a | +25.0 m/s^2 | dynamics_acceleration | FAIL |

## Preservation and execution

Twelve files in rocket/, scenarios/ and existing tests were byte-identical to V1. Maximum difference in every baseline quantity: 0.000000e+00 in its corresponding units. See validation_v2.json.

Commands run:

```bash
python -m scripts.reproduce
python -m verification.scenarios
python -m verification.convergence
python -m verification.mutations
```

Recorded logs: pytest.txt/.xml, scenarios_cli.txt, convergence_cli.txt and mutations_cli.txt. Detailed evidence: trajectory_verification.json/.csv, scenario JSON and convergence JSON. Canonical files may be refreshed by later reproduction runs; the counts here are the historical V2 snapshot.

Before the fix, the regression actually failed because a +25 m/s interior velocity mutation near 3 s was still reported PASS by the old verifier. After the fix, the adapter regression passed because the faulty candidate was correctly reported FAIL.

This V2 evidence was local, not official wmlab. Sub-tolerance changes and errors between unexported samples are not guaranteed to be detected.
