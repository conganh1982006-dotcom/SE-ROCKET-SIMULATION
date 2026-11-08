"""English reference report generated from saved numerical evidence."""
import json
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

ROOT = Path(__file__).resolve().parents[1]


def make_reports(s, out):
    out = Path(out)
    if "wmlab" not in s:
        raise RuntimeError("Run python -m scripts.reproduce to obtain fresh official wmlab evidence before reporting.")
    official = s["wmlab"]
    xml = out/"pytest.xml"
    if not xml.exists():
        raise RuntimeError("Run pytest --junitxml=outputs/pytest.xml first; do not invent test results.")
    suites = list(ET.parse(xml).getroot().iter("testsuite"))
    counts = {key: sum(int(x.attrib.get(key, 0)) for x in suites) for key in ["tests", "failures", "errors", "skipped"]}
    passed = counts["tests"]-counts["failures"]-counts["errors"]-counts["skipped"]
    s["pytest"] = {**counts, "passed": passed}
    (out/"summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    fonts = Path(matplotlib.get_data_path())/"fonts/ttf"
    pdfmetrics.registerFont(TTFont("DV", str(fonts/"DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DV-Bold", str(fonts/"DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-Bold")
    body = ParagraphStyle("body", fontName="DV", fontSize=9.1, leading=13.4, spaceAfter=6)
    title = ParagraphStyle("title", parent=body, fontName="DV-Bold", fontSize=18, leading=23, textColor=colors.HexColor("#133b56"), spaceAfter=13)
    sub = ParagraphStyle("sub", parent=body, fontName="DV-Bold", fontSize=11, leading=15, spaceBefore=7, spaceAfter=6)
    small = ParagraphStyle("small", parent=body, fontSize=7.6, leading=10.5, spaceAfter=0)
    story, md = [], []

    def heading(text, first=False):
        story.append(Paragraph(escape(text), title if first else sub))
        md.extend([("# " if first else "## ")+text, ""])

    def paragraph(text):
        story.append(Paragraph(escape(text), body))
        md.extend([text, ""])

    def table(headers, rows, widths=None):
        cells = [[Paragraph(escape(str(x)), small) for x in row] for row in [headers]+rows]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#dcebf3")),
                               ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f6f8")]),
                               ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),
                               ("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),
                               ("BOTTOMPADDING",(0,0),(-1,-1),5),
                               ("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor("#5c849b"))]))
        story.extend([t, Spacer(1,8)])
        md.extend(["| "+" | ".join(map(str,headers))+" |", "| "+" | ".join(["---"]*len(headers))+" |"])
        md.extend("| "+" | ".join(map(str,row))+" |" for row in rows); md.append("")

    def figure(filename, width, height, caption):
        story.append(Image(str(out/"figures"/filename), width=width, height=height))
        story.append(Paragraph(escape(caption), small)); story.append(Spacer(1,7))
        md.extend([f"![{caption}](figures/{filename})", ""])

    def new_page(): story.append(PageBreak())

    no, drag = s["baseline"]
    reduction = no["apogee"]-drag["apogee"]
    heading("C5 • Model Rocket", True)
    heading("Reference simulator & verification — Member C")
    paragraph("Independent reference report for Differential Equations, International University – VNUHCM. Requirements source: Quang Nguyen, Simulation Projects v1.0, October 2026, sections 1–5 and C5 on pages 10–11. Enter group names and student IDs before submission.")
    paragraph(f"V3 integrates wmlab {official['toolkit']['version']} from the supplied starter kit, with local verification, actual toolkit JSON reports and an official-format dataset. This English edition translates toolkit text; original and localized hashes are recorded separately. Numerical algorithms are unchanged. The starter ZIP contains no separate report answer template.")
    table(["Parameter", "Value / unit"], [["m0; mf", "1.0; 0.6 kg"], ["q; ve", "0.2 kg/s; 500 m/s"], ["g; c", "9.81 m/s²; 0 then 0.002 kg/m"], ["h0; v0; tb", "0 m; 0 m/s; (m0−mf)/q = 2 s"]], [180,330])
    heading("Model and algorithms")
    paragraph("Powered: h′=v, v′=q ve/m−g−c v|v|/m, m′=−q. Coast: h′=v, v′=−g−c v|v|/mf, m′=0. Euler, Heun and RK4 are implemented directly with NumPy. The last powered step lands exactly on tb; apogee is located by finding the zero of velocity.")
    table(["Quantity", "No drag", "c=0.002 kg/m"], [
        ["v burnout (m/s)", f"{no['v_burnout']:.6f}", f"{drag['v_burnout']:.6f}"],
        ["h burnout (m)", f"{no['h_burnout']:.6f}", f"{drag['h_burnout']:.6f}"],
        ["Apogee (m)", f"{no['apogee']:.6f}", f"{drag['apogee']:.6f}"],
        ["t apogee (s)", f"{no['t_apogee']:.6f}", f"{drag['t_apogee']:.6f}"]], [200,155,155])
    paragraph(f"Baseline: RK4, Δt=0.02 s. Drag reduces apogee by {reduction:.3f} m ({100*reduction/no['apogee']:.2f}%). These are constant-c model results; they have not been validated against measured flight data.")

    new_page(); heading("1 • Analytical solutions and references", True)
    paragraph("During burn: m=m0−qt; v=v0+ve ln(m0/m)−gt. Substituting u=m0−qs in the velocity integral gives ∫ ln[m0/(m0−qs)] ds = t−(m/q)ln(m0/m).")
    paragraph("Hence h=h0+v0t+ve[t−(m/q)ln(m0/m)]−gt²/2. During no-drag coast: v=vb−gτ, h=hb+vbτ−gτ²/2, τa=vb/g, ha=hb+vb²/(2g). Reference values are calculated from these formulas rather than hardcoded as output.")
    table(["Published", "Analytical", "Absolute error", "Error (%)", "Tol / unit"],
          [[str(r["reference"]), f"{r['observed']:.9f}", f"{r['absolute_error']:.6g}", f"{100*r['relative_error']:.6g}", f"{r['atol']} {r['unit']}"] for r in s["published_reference_comparison"]], [80,125,90,100,115])
    paragraph("These differences reflect rounding in the catalogue. Numerical error is measured against full-precision analytical values, not the rounded landmarks 235.8, 214.1 and 3048 treated as arbitrarily precise truth.")
    refs = s["scenarios"][1]["checks"]
    table(["RK4, dt=0.02 s", "Absolute error", "Relative error", "Unit"],
          [[r["name"], f"{r['absolute_error']:.3e}", f"{r['relative_error']:.3e}", r["unit"]] for r in refs if r["name"] in ["v_burnout","h_burnout","apogee"]], [180,120,120,90])
    heading("Independent drag cross-check")
    paragraph("Let k=c/mf. During upward coast: τa=arctan(vb√(k/g))/√(gk); ha−hb=ln(1+k vb²/g)/(2k). The k→0 limit recovers the no-drag formulas. If hb,vb come from the simulator, this check verifies only the coast phase.")
    paragraph("The entire drag trajectory is also compared with SciPy DOP853 using states h,v and algebraic mass. Its RHS is written independently and does not call rocket.rhs or the reference RK4 implementation. rtol=atol=2×10⁻¹². Regression tests also compare a 10⁻¹⁰ tolerance solution to assess reference sensitivity.")
    dr_checks = s["scenarios"][0]["checks"]
    paragraph("RK4 error against DOP853: "+"; ".join(f"{r['name']} = {r['absolute_error']:.3e} {r['unit']}" for r in dr_checks if r["name"] in ["v_burnout","h_burnout","apogee"])+".")

    new_page(); heading("2 • Measured convergence", True)
    paragraph("E(Δt)=|Qnum−Qexact|; p=ln(Ei/Ei+1)/ln(Δti/Δti+1). A log E versus log Δt fit uses four steps: 0.1, 0.05, 0.025 and 0.0125 s for the same no-drag baseline. Local acceptance: |p−p_theory|≤0.35. Errors near roundoff are excluded; insufficient data give INCONCLUSIVE.")
    table(["Method", "p theory", "p(vb)", "p(hb)", "p(apogee)"], [[m, str(r["theoretical_order"]), *[f"{r['metrics'][k]['fitted_order']:.5f}" for k in ["v_burnout","h_burnout","apogee"]]] for m,r in s["convergence"].items()], [100,105,100,100,105])
    table(["Δt (s)", "Euler |ehb| (m)", "Heun |ehb| (m)", "RK4 |ehb| (m)"], [[f"{dt:g}", *[f"{s['convergence'][m]['metrics']['h_burnout']['absolute_errors'][i]:.5e}" for m in ["euler","heun","rk4"]]] for i,dt in enumerate(s["convergence"]["euler"]["dt_s"])], [90,140,140,140])
    figure("convergence.png", 510, 157, "Figure 1. Absolute error against independent formulas on log–log axes.")
    paragraph("Euler/Heun/RK4 have one-step local errors O(Δt²), O(Δt³), O(Δt⁵) and global errors O(Δt), O(Δt²), O(Δt⁴). The measured results test these predictions. Full tables also include pairwise orders and relative errors.")
    paragraph("Separate the phases at the thrust discontinuity: every stage of the last burn step still uses the powered RHS. Apogee bisection recomputes fractional steps from the same left state. Linear event interpolation, missing burnout, large non-asymptotic steps or very small roundoff-limited steps can reduce the measured order.")
    orders = {Path(x['scenario']).stem: next(c['value'] for c in x['official_report']['checks'] if c['name']=='convergence_order') for x in official['convergence']}
    paragraph("wmlab measures at a fixed time of 1.5 s, using h=0.1, 0.05, 0.025 s: "+"; ".join(f"{m}: p={orders[m]:.6f}" for m in ['euler','heun','rk4'])+". This is a smooth interval before burnout. Raw JSON reports are in convergence/wmlab/. The local study also checks burnout/apogee; the two studies use different metrics and horizons.")

    new_page(); heading("3 • PASS/FAIL, bounds and reliability", True)
    table(["Scenario wmlab", "Actual", "Expected", "Demonstration"], [[Path(r['scenario']).stem,r["actual"],r["expected"],"PASS" if r["demonstration_pass"] else "FAIL"] for r in official["scenarios"]], [240,85,85,100])
    paragraph(f"Pytest: {passed}/{counts['tests']} passed; failures={counts['failures']}, errors={counts['errors']}, skipped={counts['skipped']}. Source: outputs/pytest.xml. Tests cover all three methods, non-divisible burnout steps, parameter changes, mass bounds/law, events, formulas, the zero-drag limit, convergence, adapters, datasets and time-rounding regressions.")
    fail = next(r for r in s["scenarios"] if r["expected"] == "FAIL")
    vb_fail = next(c for c in fail["checks"] if c["name"] == "v_burnout")
    paragraph(f"Euler with Δt=0.5 s: vb error={vb_fail['absolute_error']:.6f} m/s, allowed={vb_fail['allowed_error']:.6f} m/s. The named v_burnout check must FAIL. This demonstrates large global error, which does not by itself prove instability. Unexpected exceptions do not count as a successful demonstration.")
    paragraph("Bounds: m≥mf (tolerance 10⁻¹⁰ kg); m=m0−q min(t,tb); constant coast mass; increasing time; nondecreasing ascent altitude; |v_apogee|≤10⁻⁸ m/s; burnout at tb with acceleration jump qve/mf. Positive mass is physical; constant q and stopping at apogee define the model scope.")
    trajectory = s["trajectory_verification"]
    paragraph(f"V2 compares every h,v,m sample with analytical/DOP853 references; checks h′,v′,m′ with phase-specific secants and a with the force equation. "
              f"Clean trajectories passed: {sum(x['passed'] for x in trajectory['clean'])}/{len(trajectory['clean'])}; "
              f"detected {trajectory['detected_count']}/{trajectory['mutation_count']} h/v/m/a mutations during burn and coast, with events preserved. "
              "Derivative tolerances combine reference stencil error, propagated state error and roundoff; intervals next to burnout are retained. "
              "Maximum absolute/relative errors and verdicts: trajectory_verification.csv/json. Tolerance derivation: docs/TRAJECTORY_VERIFICATION_EN.md.")
    heading("Time-step study with drag")
    selected = [r for r in s["stability"] if r["dt_s"] in [4.0,.5,.05]]
    table(["Method / Δt(s)", "Apogee error (m)", "max |R|", "Local verdict"],
          [[f"{r['method']} / {r['dt_s']:g}", "—" if r["apogee_error_m"] is None else f"{r['apogee_error_m']:.5g}", "—" if r["frozen_linear_max_amplification"] is None else f"{r['frozen_linear_max_amplification']:.3g}", "PASS" if r["status"] == "PASS" else "FAIL accuracy/bounds"] for r in selected], [130,130,80,170])
    paragraph("This table requires apogee error≤0.05 m and passing physical bounds. λ=−2c|v|/m, z=λΔt; R is the method stability polynomial. max|R|>1 indicates amplification in a frozen linearization, not a theorem for the full nonlinear system. Guards reject 8 s steps for Heun/RK4; see the CSV.")

    new_page(); heading("4 • Burn rate và peak acceleration", True)
    lower = s["burn_rate"]["search_lower_kg_s"]
    paragraph(f"Fixed propellant: 0.4 kg. Immediate liftoff requires q>m0g/ve={s['burn_rate']['lift_off_threshold_kg_s']:.6f} kg/s. The lower bound is {lower:.6f} kg/s (an assumed 5% thrust margin), with upper bounds 0.5, 1 and 2 kg/s. These are numerical study domains, not supplied motor specifications.")
    table(["c (kg/m)", "q_max", "q* (kg/s)", "Apogee (m)", "Location"], [[f"{r['c_kg_m']:g}", f"{r['upper_q']:g}", f"{r['q_star']:.7f}", f"{r['apogee_m']:.4f}", "upper boundary" if r["location"] == "upper_boundary" else "interior"] for r in s["burn_rate"]["optima"]], [80,75,125,120,110])
    figure("burn_rate.png", 510, 204, "Figure 2. Faster burning reduces gravity losses but can increase drag losses.")
    opt = next(r for r in s["burn_rate"]["optima"] if r["c_kg_m"] == .002 and r["upper_q"] == 1)
    paragraph(f"With drag: candidate q*≈{opt['q_star']:.6f} kg/s gives ha≈{opt['apogee_m']:.3f} m, with little sensitivity to the three upper bounds. Halving dt changes ha by {opt['refinement_difference_m']:.2e} m; DOP853 differs by {opt['dop853_difference_m']:.2e} m. Scan 65 points per domain, refine detected peaks and compare both boundaries; global optimality is not guaranteed. The no-drag maximum is at the upper boundary, not a finite global optimum.")
    table(["Baseline", "max |a|/g", "max a/g", "max |a+g|/g"], [["c=0", *[f"{no[k]:.5f}" for k in ["max_acceleration_g","max_upward_acceleration_g","max_proper_acceleration_g"]]], ["c=0.002", *[f"{drag[k]:.5f}" for k in ["max_acceleration_g","max_upward_acceleration_g","max_proper_acceleration_g"]]]], [130,125,125,130])
    paragraph("a=dv/dt is coordinate acceleration; a+g is proper acceleration. Both burnout limits are included. Within-step extrema are estimates; see peak_acceleration.csv. During no-drag coast, a=−g while proper acceleration is zero.")

    new_page(); heading("5 • wmlab, handoff and limitations", True)
    heading("Using this framework as Member C")
    paragraph("From the project root, run python -m pip install -r requirements.txt; wmlab is installed from vendor/starter_kit/wmlab. Run python main.py report to reproduce tests, local checks, wmlab, both datasets, tables, figures and the PDF. python -m scripts.package creates the English ZIP. Read docs/MEMBER_C_HANDOFF_EN.md and WMLAB_INTEGRATION_EN.md.")
    paragraph("A replacement simulator needs an adapter (params,dt,method)→Trajectory: increasing t; y columns h,v,m; acceleration in SI; actual burnout/apogee events and both acceleration limits. Pass simulator=adapter to run_scenario or convergence_study. Do not fill missing team-simulator events from the reference solution.")
    heading("Toolkit integration and evidence")
    paragraph(f"c5_rocket.py implements simulate(p,init,t_span,dt), analytic, quantities, sample and EXTRA_CHECKS. Two scenarios pass and the deliberate failure is detected; three convergence reports pass. Actual wmlab run_checks detects {official['mutations']['detected']}/{official['mutations']['count']} h/v/m mutations. The toolkit exports only h,v,m, so it cannot independently check an unexported acceleration channel. V2 still checks a through Trajectory.")
    paragraph("wmlab 0.1.1 can exit with code 0 when checks fail; the runner reads passed_all and individual JSON checks. Built-in convergence has only a lower acceptance bound, so the runner also requires finite orders close to theory. Localization changes text, not these checks. system_card.yaml follows the supplied template and receives measured orders from the reports.")
    d = s["local_dataset"]
    ds = official['dataset']
    paragraph(f"wmlab dataset creates c5_rocket.npz: shape={tuple(ds['shape'])}, seed={ds['seed']}, stride=1, dt=0.02 s. These are {ds['count']} common-time ascent segments on [0,4] s, without padding or treating the final time as apogee. All 200 segments were independently checked. Maximum h/v/m errors: "+" / ".join(f"{e:.2e}" for e in ds['max_absolute_error_h_v_m'])+" (m / m/s / kg).")
    paragraph(f"The supplementary local_dataset_200.npz retains {d['count']} full ascents to apogee of differing lengths; {d['physical_checks_passed']} pass physical bounds. Assumed sampling domains: m0=0.8–1.2 kg; fuel fraction=0.25–0.45; ve=400–550 m/s; thrust/weight=1.2–15; c=0–0.003 kg/m. This is not a measured equipment distribution.")
    heading("Limitations and disclosure")
    paragraph("1D ascent with constant g,q,ve,c; no wind, density variation, rail, launch angle or descent. Inputs qve≤m0g are rejected because contact and delayed liftoff are outside scope. Reducing dt can reduce numerical error but cannot remove modeling error. No measured flight data are available for experimental validation.")
    paragraph("AI use: OpenAI Codex assisted with code, mathematical reasoning, tests, analysis and documentation; students must review and explain the work. Metadata retain consent_physeval=false; no shared-pool publication is authorized. This reference report does not replace the group presentation or individual contributions.")
    heading("Sources and runtime environment")
    paragraph("[1] Quang Nguyen, Differential Equations – Simulation Projects v1.0 (October 2026), pages 2–4 and 10–11, supplied PDF. [2] Official SciPy solve_ivp documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html. Mathematical derivations and verification design are in docs/.")
    paragraph("Python "+s["environment"]["python"]+"; "+"; ".join(f"{k} {v}" for k,v in s["environment"]["packages"].items())+". Check details and versions are in summary.json; dependency pins are in requirements-tested.txt.")

    def footer(canvas, doc):
        canvas.setFont("DV", 7.5); canvas.setFillColor(colors.HexColor("#486579"))
        canvas.drawString(42, 24, "C5 English edition • Local + wmlab 0.1.1 • Text-localized toolkit")
        canvas.drawRightString(A4[0]-42, 24, str(doc.page))

    doc = SimpleDocTemplate(str(out/"report_en.pdf"), pagesize=A4,
                            rightMargin=42, leftMargin=42, topMargin=35, bottomMargin=42,
                            title="C5 Model Rocket — Reference Verification", author="Member C reference; AI-assisted",
                            invariant=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    (out/"report_en.md").write_text("\n".join(md), encoding="utf-8")
    # Keep legacy paths usable, with English contents in both copies.
    shutil.copyfile(out/"report_en.pdf", out/"report_vi.pdf")
    shutil.copyfile(out/"report_en.md", out/"report_vi.md")
    print(f"Reports written to {out/'report_en.pdf'}", flush=True)


if __name__ == "__main__":
    output = ROOT/"outputs"
    make_reports(json.loads((output/"summary.json").read_text(encoding="utf-8")), output)
