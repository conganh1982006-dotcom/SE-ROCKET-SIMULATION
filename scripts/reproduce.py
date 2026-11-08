"""One command: regression, local studies, real wmlab checks/dataset, reports."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    (root/"outputs").mkdir(exist_ok=True)
    test = subprocess.run([sys.executable, "-m", "pytest", "-q", "--junitxml=outputs/pytest.xml"],
                          capture_output=True, text=True, encoding="utf-8")
    log = test.stdout+test.stderr
    (root/"outputs/pytest.txt").write_text(log, encoding="utf-8")
    print(log, flush=True)
    if test.returncode:
        return test.returncode
    from experiments.run import generate
    from experiments.report import make_reports
    from scripts.wmlab_verify import run_official
    summary = generate()
    summary["wmlab"] = run_official()
    summary["format"] = "c5-project-report-v3"
    summary["official_wmlab"] = True
    make_reports(summary, root/"outputs")
    print("Complete. Open outputs/report_en.pdf and docs/MEMBER_C_HANDOFF_EN.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
