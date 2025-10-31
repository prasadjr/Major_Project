import os
import re
import tempfile
import shutil
import subprocess
import requests
import stat
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

app = Flask(__name__)
app.secret_key = "your_secret_key"

OSV_API_URL = "https://api.osv.dev/v1/query"


# ---------------------------
# Helper: Remove readonly files (for Windows)
# ---------------------------
def handle_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


# ---------------------------
# Helper: Parse dependency files
# ---------------------------
def parse_dependencies(file_path):
    deps = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Matches `pkg==version`
            match = re.match(r"([a-zA-Z0-9_\-]+)==([\d\.]+)", line)
            if match:
                deps.append((match.group(1), match.group(2)))
    return deps


# ---------------------------
# Helper: Query OSV API
# ---------------------------
def query_osv(package, version):
    payload = {
        "package": {"name": package, "ecosystem": "PyPI"},
        "version": version,
    }
    try:
        r = requests.post(OSV_API_URL, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("vulns", [])
        return []
    except Exception as e:
        print(f"[Error] OSV query failed for {package}: {e}")
        return []


# ---------------------------
# Generate PDF Report
# ---------------------------
def generate_pdf_buffer(git_url, results):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Python Vulnerability Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Scanned Repository: <b>{git_url}</b>", styles["Normal"]))
    story.append(Spacer(1, 12))

    for dep, vulns in results.items():
        if not vulns:
            continue
        story.append(Paragraph(f"<b>{dep}</b>", styles["Heading2"]))
        data = [["CVE ID", "Severity", "Description"]]

        for vuln in vulns:
            cve = vuln.get("id", "N/A")
            severity = vuln.get("database_specific", {}).get("severity", "Unknown")
            summary = vuln.get("summary", "No description available.")
            summary = summary[:400] + "..." if len(summary) > 400 else summary
            data.append([cve, severity, summary])

        table = Table(data, colWidths=[100, 80, 300])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))

    if not any(results.values()):
        story.append(Paragraph("✅ No known vulnerabilities found.", styles["Normal"]))

    doc.build(story)
    buf.seek(0)
    return buf


# ---------------------------
# Main route
# ---------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        git_url = request.form.get("git_url")
        if not git_url:
            flash("Please enter a GitHub repository URL.", "warning")
            return redirect(url_for("index"))

        tmp_dir = None
        results = {}

        try:
            tmp_dir = tempfile.mkdtemp()
            subprocess.run(["git", "clone", "--depth", "1", git_url, tmp_dir], check=True)

            dep_files = []
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    if f in ["requirements.txt", "pyproject.toml"]:
                        dep_files.append(os.path.join(root, f))

            if not dep_files:
                flash("No dependency files found in the repository.", "warning")
                return redirect(url_for("index"))

            all_deps = []
            for dep_file in dep_files:
                all_deps.extend(parse_dependencies(dep_file))

            for pkg, ver in all_deps:
                vulns = query_osv(pkg, ver)
                results[f"{pkg}=={ver}"] = vulns

            pdf_buf = generate_pdf_buffer(git_url, results)
            return send_file(
                pdf_buf,
                as_attachment=True,
                download_name="vulnerability_report.pdf",
                mimetype="application/pdf",
            )

        except subprocess.CalledProcessError:
            flash("Failed to clone the repository. Check the URL.", "danger")
            return redirect(url_for("index"))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("index"))

        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir, onerror=handle_remove_readonly)
                except Exception as cleanup_error:
                    print(f"Warning: could not delete temp dir {tmp_dir}: {cleanup_error}")

    return render_template("index.html")


# ---------------------------
# Run the app
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
