import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from flask import Flask, render_template, request, send_file, flash, redirect, url_for

from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change_this_in_prod")

DEPENDENCY_CHECK_CMD = r"D:\Engineering\7 sem\Major project\project\Major_Project\dependency-check-12.1.0-release\dependency-check\bin\dependency-check.bat"
WORKDIR = Path(tempfile.gettempdir()) / "depcheck_flask"
WORKDIR.mkdir(parents=True, exist_ok=True)
MAX_REPO_SIZE_MB = int(os.environ.get("MAX_REPO_SIZE_MB", "500"))


def run_cmd(cmd, cwd=None, timeout=None):
    try:
        completed = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return completed.returncode, completed.stdout
    except subprocess.TimeoutExpired as e:
        return -1, f"Timeout: {str(e)}"
    except Exception as e:
        return -1, f"Error running command: {str(e)}"


def find_requirements(repo_path: Path):
    for name in ("requirements.txt", "requirements-dev.txt", "dev-requirements.txt"):
        p = repo_path / name
        if p.exists():
            return p
    return None


def repo_size_mb(path: Path):
    total = 0
    for p in path.rglob('*'):
        if p.is_file():
            try:
                total += p.stat().st_size
            except Exception:
                pass
    return total / (1024 * 1024)


def generate_pdf_from_html(html_file, pdf_path, project_name):
    """Extract summary data from OWASP HTML report and write it to a PDF."""
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Extract basic info
    title = soup.find("title").text if soup.find("title") else "Dependency-Check Report"
    summary_table = soup.find("table")

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    elements = []

    elements.append(Paragraph(f"<b>{project_name} - OWASP Dependency-Check Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"<b>Summary Extracted from:</b> {title}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    if summary_table:
        rows = summary_table.find_all("tr")
        for r in rows:
            cols = [c.text.strip() for c in r.find_all(["td", "th"])]
            if cols:
                elements.append(Paragraph(" | ".join(cols), styles["Normal"]))
    else:
        elements.append(Paragraph("No summary table found in the report.", styles["Normal"]))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Full HTML report available separately in generated directory.", styles["Italic"]))

    doc.build(elements)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    repo_url = request.form.get("repo_url", "").strip()
    project_name = request.form.get("project_name", "").strip() or "dependency-check-project"

    if not repo_url:
        flash("Please provide a GitHub repository URL.", "danger")
        return redirect(url_for("index"))

    if not (repo_url.startswith("http://") or repo_url.startswith("https://") or repo_url.startswith("git@")):
        flash("Repository URL must be a valid HTTP(S) or SSH git URL.", "danger")
        return redirect(url_for("index"))

    work_subdir = WORKDIR / uuid.uuid4().hex
    repo_dir = work_subdir / "repo"
    out_dir = work_subdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        work_subdir.mkdir(parents=True, exist_ok=True)

        # Clone repo
        rc, out = run_cmd(["git", "clone", "--depth", "1", repo_url, str(repo_dir)], cwd=str(work_subdir), timeout=300)
        if rc != 0:
            flash(f"Git clone failed: {out[:400]}", "danger")
            shutil.rmtree(work_subdir, ignore_errors=True)
            return redirect(url_for("index"))

        size_mb = repo_size_mb(repo_dir)
        if size_mb > MAX_REPO_SIZE_MB:
            flash(f"Repository too large ({size_mb:.1f} MB), limit is {MAX_REPO_SIZE_MB} MB.", "danger")
            shutil.rmtree(work_subdir, ignore_errors=True)
            return redirect(url_for("index"))

        req_path = find_requirements(repo_dir)

        # Run OWASP Dependency Check
        cmd = [
            DEPENDENCY_CHECK_CMD,
            "--project", project_name,
            "--scan", str(repo_dir),
            "--format", "HTML",
            "--out", str(out_dir)
        ]
        rc, out = run_cmd(cmd, cwd=str(work_subdir), timeout=3600)
        if rc != 0:
            flash("Dependency-Check failed. Check server logs.", "warning")
            (out_dir / "log.txt").write_text(out)

        # Find HTML report
        html_report = None
        for candidate in out_dir.glob("*.html"):
            html_report = candidate
            break

        if not html_report:
            flash("Dependency-Check did not produce an HTML report.", "danger")
            shutil.rmtree(work_subdir, ignore_errors=True)
            return redirect(url_for("index"))

        # Generate PDF summary
        pdf_path = out_dir / f"{project_name}-dependency-report.pdf"
        generate_pdf_from_html(html_report, pdf_path, project_name)

        return send_file(str(pdf_path), as_attachment=True, download_name=pdf_path.name)

    finally:
        try:
            shutil.rmtree(work_subdir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
