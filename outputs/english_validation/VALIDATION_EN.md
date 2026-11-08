# English-edition validation — 8 November 2026

This record describes actual execution of the localized project under WSL and Python 3.13.14. It is separate from the retained historical V2/V3/V3.1 records.

## Actual runs

| Workflow | Result |
|---|---|
| `python main.py report` | Exit 0; tests, studies, toolkit, datasets and English report completed |
| `python main.py verify` | Exit 0; 172 tests passed, with no failures or skips |
| Local scenarios | Three expected outcomes: PASS, PASS, deliberate coarse-Euler FAIL |
| Toolkit scenarios | Three expected outcomes: PASS, PASS, deliberate coarse-Euler FAIL |
| Local convergence | Euler, Heun and RK4 PASS |
| Toolkit convergence | All three PASS; measured orders approximately 0.988516160, 1.999868455, 3.999388473 |
| Clean trajectory checks | 2/2 PASS |
| Local mutations | 16/16 detected |
| Toolkit mutations | 12/12 detected |
| Official-format dataset | 200/200 segments independently checked; shape (200,201,3) |
| Manual modes | no-drag, with-drag and compare all exited 0 and created separate output folders |
| Interactive menu | Started from another directory and exited normally |

The original 166 tests remain, with English message assertions where necessary. Six additional cases verify localization disclosure, rejection of altered provenance/vendor/installed files, and English messages with either legacy language selector.

## Scientific preservation

- 27 protected source/template/dependency files are byte-identical to the V3.1 ZIP, including all rocket and verification modules, the adapter, scientific studies and DE kit templates.
- Six same-environment Euler/Heun/RK4 × drag/no-drag comparisons have exactly zero differences in t,y,a and identical quantities.
- Every stored array in both c5_rocket.npz and outputs/local_dataset_200.npz matches the original V3.1 release exactly.
- Eight scientific CSVs (baseline, both histories, convergence, peak acceleration, burn-rate optima/sweep and stability/accuracy) match byte for byte.
- Scientific scenario/convergence YAML payloads are unchanged; only descriptive author placeholders were translated.
- All 16 bundled toolkit Python files retain the same executable syntax structure and numerical constants after documentation/message text is excluded. This structural comparison supplements runtime checks; it is not a general proof for all inputs.

The current dependency pins are regenerated from the actual run: numpy 2.5.0, scipy 1.18.0, matplotlib 3.11.0, pytest 9.1.1, PyYAML 6.0.3, reportlab 5.1.0 and local wmlab 0.1.1. They differ from the older run's pins, but the scientific preservation comparisons above were actually performed and passed. Runtime dependency ranges did not change.

## Language and document checks

CLI text, errors, comments, docs, metadata placeholders, plot captions and future generated reports use English. The source-text scan also decodes JSON/YAML/NPZ string metadata. It detects the script-specific accented characters that appeared in the source-language originals; manual translation review complements that scan.

The regenerated English PDF has 6 pages. The retained full English report has 29 pages and an editable Word copy. PDF text extraction and Word XML scans found no source-language characters. The full report remains dated 2 November with numerical evidence from 28 October; it is not relabeled as a November rerun. English-edition changes to toolkit provenance are explained in docs/LOCALIZATION_EN.md.

Historical quick-run plots were redrawn from unchanged CSV/event data with English labels. New manual runs were also executed. The acceleration plot was visually inspected for labels, both burnout limits and signed peak markers. PDF text was checked; the Word file was not rerendered in Microsoft Word during this localization.

## Evidence files

- report.log and verify.log: fresh workflow output.
- example_runs.log: fresh manual-mode output and menu run.
- scientific_preservation.json: source identities, six comparisons, dataset equality, CSV equality, scenario preservation and toolkit structure comparison.
- quick_run_isolation.json: checks that new quick runs preserve all existing project files.
- document_checks.json: PDF page/text and Word archive checks.
- language_audit.json: final text/binary-metadata scan.
- file_changes.json: source-ZIP comparison and hashes for changed/added files.

Quick runs are not automatically certified. Verification retains the original tolerance, sampling and model limitations. No measured flight data are available for experimental validation.
