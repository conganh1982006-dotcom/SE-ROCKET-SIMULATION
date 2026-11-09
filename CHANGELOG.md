# Release changes

## Submission cleanup — 9 November 2026

- Populated all five authors in the current and historical reports, including PDF/Word Author properties and historical cover details.
- Updated experiments/report.py to read authors from system_card.yaml. Removed stale name-entry text and corrected the remaining mixed-language heading.
- Removed the scenario-level AI declaration fields from the 11 group YAML configurations at the team’s request. Reports retain the assistance disclosure; original vendor templates and toolkit files are unchanged. See README for the distinction from the catalogue’s per-scenario declaration format.
- Corrected report/guide paths, stale metadata reminders and editing-process wording in current documentation.
- Included reports/final/ with the six-page main report, complete report with appendices, and editable Word source.
- Regenerated the standard reports and scientific evidence through the full reproduction command. Physics, solver algorithms, public APIs and numerical tolerances are unchanged.
- Validation: 172 pytest tests passed; expected scenario outcomes PASS/PASS/FAIL; three convergence reports passed; 16 local and 12 toolkit mutations detected; all 200 toolkit segments checked. Scientific CSVs and datasets match the input package within the recorded numerical comparison.
- Detailed file list and validation: outputs/release_validation/FILE_CHANGES.json and VALIDATION.json.

# Changelog

## V3.1 English edition — 2026-11-08

Created as a separate project copy. The original project and ZIP are retained.

- Translated `main.py`, `experiments/quick_runs.py` and `experiments/report.py`: menu, help, errors, tables, plot labels, JSON notes and generated reports use English.
- Updated `scripts/reproduce.py` to point to `report_en.pdf`. Legacy `report_vi.pdf/.md` remain English compatibility copies.
- Added English guides (`QUICKSTART_EN.md`, `docs/*_EN.md`), translated legacy `_VI.md` files and README, and retained the full English Word/PDF report as dated V3.1 reference material.
- Translated author placeholders in the six official-schema scenario/convergence YAML files and `system_card.yaml`; numerical inputs, checks, IDs and tolerances are preserved.
- Localized wmlab comments, docstrings, messages, README and example descriptions. Both legacy language selectors display English; the default language is English. Numerical algorithms and verification thresholds are preserved. DE kit source templates are unchanged.
- Retained `vendor/STARTER_KIT_PROVENANCE.json` and added `vendor/ENGLISH_LOCALIZATION.json`. Updated `scripts/wmlab_verify.py` to check both bundled and installed localized hashes while explicitly reporting that the toolkit is text-localized.
- Updated language assertions in `tests/test_cli.py` and the integration-test description. Added `tests/test_english_edition.py` for English toolkit messages and rejection of modified provenance, bundled files or active installed code.
- Recreated English plots for historical quick runs from their original CSV/event data. Numerical CSVs, run IDs and timestamps are retained; translated historical logs are labeled as translations.
- Regenerated `requirements-tested.txt` with the actual versions used in this run; application dependency ranges are unchanged.
- Reran tests, experiments, the actual toolkit, dataset checks and report generation. Current evidence is in `outputs/english_validation/`; historical validation documents remain dated.
- Updated `scripts/package.py` to produce `c5_rocket_v3_1_english.zip` and exclude temporary Word lock files.

No new runtime dependency, rocket physics, numerical integration method, reference algorithm, scientific tolerance or public simulator API is introduced. Detailed file hashes and comparison results are in `outputs/english_validation/`.

## V3.1 — CLI and usability (2026-10-28)

Added `main.py` with a menu and five subcommands: no-drag, with-drag, compare, verify and report. Input validation and nonzero failure codes delegate to the V3 model and workflows.

Added `experiments/quick_runs.py`: a separate directory for every manual run, event/peak tables, four plots with event/extremum markers, parameter CSV/JSON and UTC timestamps. Acceleration plots retain both burnout limits. Quick runs do not assign themselves a verification PASS.

Added `tests/test_cli.py` and `tests/fixtures/v3_baseline.json`: actual CLI/menu runs, invalid inputs, exported data, evidence isolation, workflow failures and six Euler/Heun/RK4 × drag/no-drag comparisons against V3. Added Quickstart and example guides, quick-run examples and usability validation logs.

Updated README links, package destination and changelog. Verify/Report regenerated outputs, convergence and datasets. The V3.1 upgrade preserved rocket/, verification/, c5_rocket.py, existing tests, requirements, official scenario YAML and the original toolkit. It added no dependency. Verify checks standard V3 configurations; Report reproduces the standard report rather than substituting the latest quick run. Historical evidence: outputs/usability/VALIDATION_V3_1.md.

## V3 — official starter-kit integration (2026-10-27)

Added c5_rocket.py using the actual DE kit API while preserving rocket/. It supports full ascent and fixed-horizon/grid observations through fractional steps. Added the original vendor/starter_kit source, provenance manifest and requirements-wmlab.txt; requirements install the supplied package rather than a similarly named PyPI package.

Added three official-schema scenarios and three convergence YAML/report pairs. Filled system_card.yaml from the supplied template and updated measured orders from actual JSON. Added scripts/wmlab_verify.py to run the actual CLI, read JSON verdicts, reject nonfinite orders, demonstrate 12 mutations and generate/independently verify all 200 common-time dataset segments.

Added integration tests and documentation while retaining V2 regressions/mutations. Updated reproduction, experiments, report generation, requirements, README, Member C/requirements documentation, legacy card and ignore rules. Reports distinguish local/toolkit evidence and explain real toolkit limitations and dataset definitions. Packaging created c5_rocket_complete_v3.zip while retaining earlier ZIPs.

At that release, toolkit source, physics and baseline definitions were unchanged. Names/IDs were left for the group. No separate answer template was supplied. VALIDATION_V2 remained a historical snapshot.

## V2 — trajectory verification (2026-10-24)

Fixed an endpoint-only verification gap: a velocity spike inside a trajectory could preserve burnout/apogee and pass the old checks. An adapter regression reproduced this before the fix.

Added verification/trajectory.py for whole-history h/v/m references, phase-specific ODE residuals, algebraic acceleration, propagated tolerance budgets, coverage and maximum-error reports. Added verification/mutations.py for two clean baselines and 16 copied faulty trajectories, with JSON/CSV evidence and real exit verdicts. Added regression tests covering all four fields, both phases/drag values, burnout neighbors, nonuniform grids, coverage, reference refinement and adapters. Added trajectory-verification documentation and outputs.

Updated independent.py with split-phase DOP853 dense history while retaining endpoint references. Updated scenarios.py to require trajectory checks, accept local tolerance overrides and retain expected-FAIL semantics. Integrated mutation evidence into experiments and reports. Updated packaging, local system card, README and handoff/requirements guides. Generated outputs and dependency pins came from the actual V2 run.

The entire rocket/ directory, three local scenarios and three existing regression-test files were unchanged from V1. No dependency or public simulator interface changed. Member B adapters remained supported. V2 evidence was local; official wmlab integration came in V3.
