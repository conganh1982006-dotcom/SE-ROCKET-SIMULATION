# V3 integration — historical recorded results

English translation. Date: 27 October 2026. Environment: Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43, Python 3.13.18.

- Pytest: 122/122 PASS; failures=0, errors=0, skipped=0.
- At the original V3 release, wmlab 0.1.1 source and installed package hashes matched the supplied archive unchanged. The later English localization is described separately in docs/LOCALIZATION_EN.md.
- Local mutations: 16/16 detected; toolkit EXTRA_CHECKS mutations: 12/12 detected.

| Official scenario | Actual | Expected | Demonstration |
|---|---|---|---|
| c5_baseline_drag | PASS | PASS | PASS |
| c5_analytic_no_drag | PASS | PASS | PASS |
| c5_euler_coarse_fail | FAIL | FAIL | PASS |

| Method | Order measured by wmlab |
|---|---|
| euler | 0.988516160 |
| heun | 1.999868455 |
| rk4 | 3.999388473 |

The actual CLI generated c5_rocket.npz: shape (200,201,3), 200 ascent segments, t=0–4 s, dt=0.02 s, seed=20261027, stride=1. All 200 segments were independently checked.

| Quantity | Max absolute error | Unit |
|---|---|---|
| h | 2.690388e-07 | m |
| v | 1.759337e-07 | m/s |
| m | 1.398881e-14 | kg |

All rocket/ files and tests present in V2 were preserved. Baseline quantities matched V2 with maximum difference 0. Integration tests also compared full-flight arrays with the original engine using exact array equality.

Reproduction command: python -m scripts.reproduce. Actual CLI logs are in outputs/wmlab/logs/; raw reports are in outputs/wmlab/ and convergence/wmlab/. Expected FAIL is not rewritten as PASS. These canonical paths may be refreshed by later runs; this document records the original V3 snapshot.

Group names/IDs remain to be entered. No separate answer template was included in the supplied ZIP; a short PDF report was prepared. Full ascents remain in outputs/local_dataset_200.npz. The 0–4 s official-format segments are not complete flights.

The toolkit exports no independent acceleration channel; checking Member B acceleration still requires the local Trajectory adapter. There is no experimental validation or guarantee of detecting every below-tolerance deviation.

Metadata note (9 November 2026): the author-entry reminder above describes the original V3 release. All five members are now recorded in the current project metadata. The original numerical validation record is unchanged.
