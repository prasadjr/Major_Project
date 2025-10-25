# webapp/app.py
import os
import traceback
from flask import Flask, render_template, request, send_file, jsonify, url_for
from clone_repo import clone_repo
from file_finder import list_python_files
from import_parser import aggregate_imports
from requirement_parser import parse_requirements_txt
from pypi_checker import get_latest_pypi_version
from vulnerability_tools import run_pip_audit
from report_builder import build_report, save_report_json
import pdfkit

app = Flask(__name__, template_folder="templates", static_folder="static")

SCAN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "scans"))
os.makedirs(SCAN_ROOT, exist_ok=True)

@app.route("/")
def index():
    return render_template("report.html", report=None)

@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.json or {}
    repo_url = data.get("repo_url")
    if not repo_url:
        return jsonify({"error": "repo_url required"}), 400

    try:
        # 1️⃣ Clone repo
        local_path = clone_repo(repo_url)
        if not os.path.exists(local_path):
            return jsonify({"error": "Failed to clone repository"}), 500

        # 2️⃣ List Python and requirement files
        py_files, req_files = list_python_files(local_path)
        if not py_files:
            return jsonify({"error": "No Python files found in repository"}), 400

        # 2a️⃣ Prepare scanned files relative paths
        scanned_files = [os.path.relpath(f, local_path) for f in py_files]

        # 3️⃣ Aggregate imports
        dep_map = aggregate_imports(py_files)
        if not isinstance(dep_map, dict):
            dep_map = {}
        dep_list = [{"name": k, "current_version": v} for k, v in dep_map.items()]

        # 4️⃣ Parse requirements.txt files
        req_versions = {}
        for r in req_files:
            if r.endswith("requirements.txt"):
                req_versions.update(parse_requirements_txt(r))

        # 5️⃣ Fetch latest PyPI versions
        latest_versions = {}
        for dep in dep_list:
            name = dep.get("name")
            try:
                latest_versions[name.lower()] = get_latest_pypi_version(name)
            except Exception:
                latest_versions[name.lower()] = None

        # 6️⃣ Run pip-audit
        pip_audit_results = []
        try:
            pip_audit_results = run_pip_audit()
        except Exception:
            pip_audit_results = []

        # 7️⃣ Build final report
        report = build_report(dep_list, req_versions, latest_versions, pip_audit_results)

        # 8️⃣ Save JSON report
        outdir = os.path.join(SCAN_ROOT, os.path.basename(local_path))
        os.makedirs(outdir, exist_ok=True)
        json_path = os.path.join(outdir, "report.json")
        save_report_json(report, json_path)

        # 9️⃣ Render HTML
        html = render_template("report.html", report=report)

        # 10️⃣ Save PDF
        pdf_path = os.path.join(outdir, "report.pdf")
        try:
            pdfkit.from_string(html, pdf_path)
        except Exception:
            pdf_path = None

        # 11️⃣ Return JSON including scanned files
        return jsonify({
            "report_json": url_for('get_report_json', repo=os.path.basename(local_path)),
            "report_html": html,
            "report_pdf": url_for('get_report_pdf', repo=os.path.basename(local_path)) if pdf_path else None,
            "scanned_files": scanned_files  # <--- added for workflow display
        }), 200

    except Exception as e:
        print("=== Scan Error ===")
        print(traceback.format_exc())
        return jsonify({"error": f"Scan failed: {str(e)}"}), 500

@app.route("/scan_workflow")
def scan_workflow():
    """
    Render the Scan Workflow page.
    """
    return render_template("scan_workflow.html")


@app.route("/reports/<repo>/report.json")
def get_report_json(repo):
    path = os.path.join(SCAN_ROOT, repo, "report.json")
    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404
    return send_file(path, mimetype="application/json")

@app.route("/reports/<repo>/report.pdf")
def get_report_pdf(repo):
    path = os.path.join(SCAN_ROOT, repo, "report.pdf")
    if not os.path.exists(path):
        return jsonify({"error": "PDF not available"}), 404
    return send_file(path, mimetype="application/pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
