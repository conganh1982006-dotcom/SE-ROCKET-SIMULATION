# Requirements, extensions and remaining limitations

Source: the supplied Quang Nguyen catalogue, v1.0, October 2026. The catalogue defines the course context and technical requirements.

| Source | Requirement | Implementation |
|---|---|---|
| Sections 1–2, p.2 | Python/NumPy; implement Euler/Heun/RK4; SciPy for cross-checking; disclose AI | Implemented/tested; assistance disclosed in reports. Scenario-level disclosure fields are omitted at the team’s request |
| Section 3, p.3 | Milestones in weeks 1/2/4/6/7/8 | Course administration; students arrange registration/submission |
| Section 4 | System module based on template_system.py | c5_rocket.py implements the actual API using the existing NumPy engine |
| Section 4 | At least three scenarios, including an intentional FAIL | Three official-schema YAML files and actual toolkit reports; expected outcomes checked |
| Section 4 | Euler/Heun/RK4 convergence reports | Three toolkit reports plus the local four-step study |
| Section 4 | Template-based system_card.yaml | Supplied template filled; measured orders from reports; all five authors recorded |
| Section 4 | 200 samples from wmlab dataset | c5_rocket.npz: 200 common-time ascent segments, shape (200,201,3), all independently checked |
| Section 4 | 4–6 page report plus appendix using the answer template | Six-page main report plus appendices in reports/final/; automatic numerical report in outputs/report_en.pdf. The historical full report is additional material |
| Sections 4–5 | Reproducible README; model, convergence, verification, applications, limits | Source, tests, reproduction pipeline and documentation |
| C5, pp.10–11 | Variable-mass equations, baseline and vb/hb/ha derivation | Independent formulas and separate rounded-landmark comparisons |
| C5, p.11 | Drag/no-drag comparison, q study with fixed propellant, peak acceleration | Tables/plots, declared search bounds, refinement and sensitivity checks |
| C5, p.11 | reference_match, within_bounds, convergence_order | Actual supplied wmlab 0.1.1 algorithms and additional EXTRA_CHECKS |
| C5, p.11 | v_burnout, h_burnout, apogee, max_acceleration_g | All keys provided with explicit acceleration conventions |
| C5, p.11 | Burnout as an event | Exact final burn step and separate phase RHS |

Additional verification features include apogee root finding, explicit tolerances, full-history and dynamics checks, analytical drag coast, independent DOP853, regression tests, adapter injection, zero-drag and roundoff checks, optimization-domain sensitivity, multiple acceleration definitions, local datasets and generated reports. Project tolerance/step/domain choices are not presented as instructor requirements.

## Validity domain

- Newtonian 1D ascent with constant g,q,ve,c and quadratic drag. No atmospheric density variation, wind, attitude, lift, rail/contact or descent.
- m0>mf>0; q,ve,g>0; c≥0; h0,v0≥0; qve>m0g. Launch-pad waiting is excluded. Rejected invalid inputs are outside the model, not a simulated flight verdict.
- No measured parameter uncertainties or flight data are supplied. Verification is not experimental validation.
- Peaks include time-grid samples and both burnout limits; extrema between samples are not guaranteed. Refinement tables assess baseline sensitivity.
- Apogee bracketing assumes a sufficiently resolved coast. Guards catch some large-step failures; finite output still needs reference/convergence checks.
- Convergence roundoff filtering is heuristic; four tested steps do not establish accuracy over every parameter domain.
- Burn-rate optimization is one-dimensional on assumed domains without motor/material/load constraints. It is not a hardware design recommendation. No-drag maxima occur at the search boundary rather than at a finite global optimum.
- The 200 local full ascents pass physical checks; the separate 200 official-format segments are all compared with independent references. Sampling domains are numerical examples, not real rocket population distributions.
- Group names and student IDs are populated in the project metadata. Local legacy outputs are not mislabeled as raw wmlab outputs.

## Local dataset

Seed 20261024. Sample m0 uniformly on [0.8,1.2] kg, propellant fraction [0.25,0.45], ve [400,550] m/s, initial thrust/weight [1.2,15], c [0,0.003] kg/m. Derive q from thrust/weight to ensure immediate liftoff. These are declared test assumptions.

Load with `np.load(path, allow_pickle=False)`. Concatenated t,y,a are sliced with offsets[i]:offsets[i+1]. parameters/parameter_names store inputs; quantities/quantity_names store outputs including event times. Burnout also appears in the history. format and official_wmlab identify the local source; consent_physeval=false.

## Toolkit dataset

The actual CLI produces t,Y,meta,system,state in c5_rocket.npz, using [0,4] s, dt=0.02, stride=1 and seed=20261027. No padding or continuation after apogee is used. Internal steps respect burnout, but draw-dependent event times are not inserted into the common output grid. Fractional steps use the selected method. See WMLAB_INTEGRATION_EN for horizon choices and JSON verdict handling.

## English-edition scope

Only language/presentation and localization integrity bookkeeping change. Original V3.1 evidence is preserved separately; current verification is rerun in this English copy. The toolkit comments, examples and messages are translated, and the localization is explicitly disclosed rather than claimed to be byte-identical to the supplied archive. Original DE kit templates, rocket physics and verification tolerances are retained.
