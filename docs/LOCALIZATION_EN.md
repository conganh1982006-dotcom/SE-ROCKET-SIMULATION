# English localization and provenance

Edition date: 8 November 2026. Source: c5_rocket_v3_1_cli.zip. The original project/ZIP remain separate. This copy provides English text throughout the CLI, plots, report generator, documentation, comments, author placeholders and example descriptions.

## Preserved contracts

The rocket/ and verification/ modules, c5_rocket.py, scientific studies and numerical scenario/convergence inputs retain their original behavior. Tests compare six method/drag configurations and saved scientific arrays against the original V3.1 release. Human-readable fields do not determine scientific PASS/FAIL.

The cleaned submission ZIP removes four unneeded duplicate _VI guides and retains three legacy _VI guides referenced by Python documentation strings or the local system card. All remaining _VI documents contain English, and preferred guides end in _EN. Report generation still writes report_en.pdf/.md and identical English compatibility copies at report_vi.pdf/.md, although the duplicate report_vi files are omitted from the cleaned submission ZIP; no report-generation code was changed. Historical full English reports describe the original October V3.1 run; they are not claimed to be newly rerun November reports.

## Why the toolkit is also localized

The supplied wmlab includes text in its README, comments, docstrings, examples and a bilingual message helper. An entirely English distribution therefore requires translating those text fields. Existing English message alternatives are reused in both language slots. The default is en; the legacy vi selector remains accepted and also produces English. No numerical formula, threshold or check verdict is replaced.

`vendor/STARTER_KIT_PROVENANCE.json` remains the original archive/file hash record. It is not rewritten to pretend that translated files are byte-identical. `vendor/ENGLISH_LOCALIZATION.json` records the original manifest hash, archive identity, translated filenames and expected English file hashes. The runner verifies manifest coverage, every bundled file and each active installed wmlab Python source file. Modified files or an older installed toolkit cause a failure; the checks are not bypassed. The runner reports original_toolkit_unchanged=false and localized_toolkit_hashes_verified=true after success.

The DE kit template/worked-example files were already English and remain byte-identical. The wmlab algorithm comparison removes documentation and message text from syntax trees, then checks the remaining executable structure and numerical constants. Runtime tests and the actual toolkit pipeline provide additional evidence; a text comparison alone is not treated as a complete behavioral proof.

## Historical and fresh outputs

Historical quick-run CSV values, IDs and timestamps are preserved. Their PNG labels and descriptive JSON notes are translated using the saved data, including both burnout acceleration limits. Historical terminal logs are identified as English translations. Historical V2/V3/V3.1 validation statements retain their original dates and counts.

Fresh report generation runs pytest, the scientific studies, local verification, actual wmlab checks and both datasets. Current logs and comparison results are stored in outputs/english_validation/. The full English Word/PDF/Markdown report is included as a separately dated reference, with its original evidence dates and provenance.

No new runtime dependencies, GUI, web framework, deployment or external publication are introduced.
