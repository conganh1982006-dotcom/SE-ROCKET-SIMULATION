# C5 Rocket V3.1 — Full Technical Report (English)

- **C5_FULL_REPORT_EN.docx**: editable historical Word report; group details are populated.
- **C5_FULL_REPORT_EN.pdf**: checked reading/printing copy, 29 pages.
- **C5_FULL_REPORT_EN.md**: text source; keep the assets directory beside it.
- **assets/**: two English flow diagrams and five scientific figures. The four
  trajectory plots use the same saved CSV and event data as the Vietnamese edition.
- **DATA_SOURCES.json**: source-file hashes and provenance.
- **LAYOUT_CHECKS.json**: PDF, Word structure and translation consistency checks.

The report contains an abstract, 14 chapters and three appendices, with 21 tables
and seven figures. Chapters 8–11 cover DE kit, wmlab, the c5_rocket.py adapter,
scenario execution, JSON reports and NPZ datasets.

Report date: 2 November 2026. Numerical evidence is from the stored V3.1 run of
28 October 2026. The translation and figure relabelling do not represent a new
simulation or verification run. The original Vietnamese report, source code and
scientific outputs have been preserved.

Function names, commands, paths, numerical values and the distinction between
expected failures and passing tests are retained. Decimal points are used in
English numerical tables. Word pagination may differ with the installed fonts
and application settings; the supplied PDF is the fixed-layout copy.

In the English project edition, python main.py report generates outputs/report_en.pdf
and an English compatibility copy at outputs/report_vi.pdf. It does not overwrite
this separate historical full report. Descriptions of the unchanged original toolkit
in this report refer to the October V3.1 release; see ../../docs/LOCALIZATION_EN.md
for the subsequent English text localization and separate hash checks.

Editorial update (9 November 2026): team names, IDs, instructor and document Author properties are populated, and the assistance disclosure is retained in the report. The historical scientific results and original report date remain unchanged. Use ../../reports/final/ for the concise submission report.
The DATA_SOURCES.json and LAYOUT_CHECKS.json files describe the original historical build; current release checks, including the updated cover, are in ../release_validation/.
