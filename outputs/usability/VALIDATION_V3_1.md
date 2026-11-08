# V3.1 usability validation — historical recorded results

English translation of the 28 October 2026 record. WSL Ubuntu, Python 3.13.14, platform Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43.

## Results

- python main.py verify: exit 0; pytest, local checks and actual wmlab completed.
- python main.py report: exit 0; evidence and PDF regenerated.
- 166/166 tests PASS: 122 original V3 regressions plus 44 CLI tests; no skips, failures or errors.
- Three expected scenario outcomes: two PASS and the designated coarse-Euler FAIL. Raw toolkit verdicts were retained.
- Three official convergence reports PASS: Euler 0.988516160, Heun 1.999868455, RK4 3.999388473.
- 200/200 independently checked dataset segments, shape (200,201,3).
- 16/16 local and 12/12 toolkit mutations detected.

## Preservation of V3

Six Euler/Heun/RK4 × c=0/c=0.002 configurations were run with rocket/ extracted from the original V3 ZIP in the same environment. Every t/h/v/m/a array and quantity matched the new call path exactly: maximum difference 0.

After Report, baseline/history CSV numbers and all arrays in both datasets matched V3. NPZ container hashes can differ despite identical arrays. Seventy protected files retained their hashes, including rocket, verification, adapter, existing tests, official YAML, requirements and original kit.

All three manual modes were actually run. Each wrote a fresh directory; all 150 previously existing files remained unchanged. Subprocess tests exercised the real menu and commands from another directory, including paths with spaces, and inspected actual CSV contents. Four PNGs were visually checked for labels, events, extrema and the acceleration jump.

## Evidence and limits

Historical logs: [Verify](verify.log), [Report](report.log), [manual runs](example_runs.log). These log copies are labeled English translations. JSON evidence: validation_v3_1.json, baseline_comparison.json, scientific_outputs_comparison.json, quick_runs_validation.json and file_changes.json.

The first Verify used pytest 9.2.0; the final Report used pytest 9.1.1 according to requirements-tested.txt. Both had 166 passing tests. Final top-level dependency versions matched the V3 pins; requirements were unchanged.

Quick runs do not claim verification PASS. Verify/Report use standard V3 configurations and do not certify every manually chosen input. Within-phase extrema are sampled estimates. This is the original V3.1 record; see ../english_validation/ for the later English-edition run.
