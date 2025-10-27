#!/usr/bin/env python3
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, PageBreak
from git import Repo, GitCommandError

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {"py"}
PDF_LINE_LIMIT = 1400

# Tool commands (base). For multi-file analysis we pass directory or file paths.
TOOL_COMMANDS = {
    "pylint": ["pylint", "--output-format=text"],
    "flake8": ["flake8"],
    "bandit": ["bandit", "-r"],
    "mypy": ["mypy"],
    "radon_cc": ["radon", "cc", "-s", "-n", "B"],
    "radon_raw": ["radon", "raw"],
    "black_check": ["black", "--check", "--diff"],
}

CHECK_ORDER = ["pylint", "flake8", "bandit", "mypy", "radon_cc", "radon_raw", "black_check"]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_tool_available(cmd):
    return shutil.which(cmd[0]) is not None


def run_cmd(cmd_list, target_paths, timeout=120):
    """
    cmd_list: list (base command)
    target_paths: list of paths (files or single directory) to append
    returns (rc, output)
    """
    # Some tools accept a directory directly; if single dir given, pass it once.
    full_cmd = cmd_list + target_paths
    try:
        proc = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return -1, f"Execution timed-out after {timeout}s for command: {' '.join(full_cmd)}"
    except FileNotFoundError:
        return 127, f"Tool not found: {cmd_list[0]}"
    except Exception as e:
        return 1, f"Error running {' '.join(full_cmd)}: {e}"


def collect_py_files(root_dir):
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if fn.endswith(".py"):
                py_files.append(os.path.join(dirpath, fn))
    return py_files


def shorten_text(text, limit=PDF_LINE_LIMIT):
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    head = lines[: limit // 2]
    tail = lines[- limit // 2 :]
    return "\n".join(head + ["\n... (truncated) ...\n"] + tail)


def gather_reports(targets, selected_tools):
    """
    targets: list of file paths OR a single directory path (list ok)
    selected_tools: list of keys from TOOL_COMMANDS or friendly names like 'pylint'
    """
    reports = {}
    # If many files and a tool accepts directory, sometimes passing a directory is better.
    # We'll pass the list of file paths (some tools accept multiple files).
    for key in CHECK_ORDER:
        friendly = key if key in selected_tools else None
        if not friendly:
            continue
        cmd = TOOL_COMMANDS[key]
        available = is_tool_available(cmd)
        if not available:
            reports[key] = {
                "available": False,
                "note": f"Tool '{cmd[0]}' not found on PATH. Install with 'pip install {cmd[0]}'",
                "returncode": None,
                "output": ""
            }
            continue

        # run the tool
        rc, out = run_cmd(cmd, targets)
        reports[key] = {"available": True, "returncode": rc, "output": out}
    return reports


def make_pdf_report(target_name, reports, output_pdf):
    doc = SimpleDocTemplate(output_pdf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading1"]
    subheading = styles["Heading2"]
    pre_style = ParagraphStyle("pre", fontName="Courier", fontSize=8, leading=10)

    elems = []
    elems.append(Paragraph(f"Static Analysis Report: {target_name}", heading))
    elems.append(Spacer(1, 0.1 * 72))
    elems.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()} UTC", normal))
    elems.append(Spacer(1, 0.1 * 72))

    elems.append(Paragraph("Summary", subheading))
    for tool_name, data in reports.items():
        status = "Available" if data.get("available") else "Missing"
        rc = data.get("returncode")
        rc_text = str(rc) if rc is not None else "-"
        note = data.get("note") or ""
        elems.append(Paragraph(f"<b>{tool_name}</b> — {status} — return code: {rc_text}. {note}", normal))
    elems.append(PageBreak())

    for tool_name, data in reports.items():
        elems.append(Paragraph(f"{tool_name} Output", subheading))
        if not data.get("available"):
            elems.append(Paragraph(data.get("note", "Missing"), normal))
            elems.append(Spacer(1, 0.1 * 72))
            continue
        out = data.get("output", "")
        if not out.strip():
            elems.append(Paragraph("No output.", normal))
        else:
            elems.append(Preformatted(shorten_text(out), pre_style))
        elems.append(PageBreak())

    doc.build(elems)


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # Which tools selected? form checkboxes like 'pylint', 'flake8', ...
    selected_tools = request.form.getlist("tools")
    if not selected_tools:
        flash("Select at least one analysis tool.", "warning")
        return redirect(url_for("index"))

    target_dir = None
    cleanup_dir = None
    uploaded_file_path = None
    repo_url = request.form.get("git_url", "").strip()

    try:
        if "upload" in request.files and request.files["upload"].filename:
            f = request.files["upload"]
            if not allowed_file(f.filename):
                flash("Only .py files are allowed for upload.", "danger")
                return redirect(url_for("index"))
            filename = f"{uuid.uuid4().hex}_{f.filename}"
            uploaded_file_path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(uploaded_file_path)
            target_paths = [uploaded_file_path]
            target_name = os.path.basename(uploaded_file_path)
        elif repo_url:
            # Clone git repo into tempdir
            tmpdir = tempfile.mkdtemp(prefix="sa_repo_")
            cleanup_dir = tmpdir
            try:
                Repo.clone_from(repo_url, tmpdir)
            except GitCommandError as e:
                flash(f"Failed to clone repo: {e}", "danger")
                shutil.rmtree(tmpdir, ignore_errors=True)
                return redirect(url_for("index"))
            py_files = collect_py_files(tmpdir)
            if not py_files:
                flash("No Python (.py) files found in the repository.", "warning")
                shutil.rmtree(tmpdir, ignore_errors=True)
                return redirect(url_for("index"))
            # For many tools, passing the root directory is okay, but to be safe pass all files.
            target_paths = py_files
            target_name = f"repo_{os.path.basename(repo_url) or 'cloned'}"
            target_dir = tmpdir
        else:
            flash("Upload a .py file or provide a Git repo URL.", "warning")
            return redirect(url_for("index"))

        # Gather chosen tool reports
        reports = gather_reports(target_paths, selected_tools)

        # Create result PDF
        out_pdf = os.path.join(tempfile.gettempdir(), f"static_report_{uuid.uuid4().hex}.pdf")
        make_pdf_report(target_name, reports, out_pdf)

        # Render results as HTML with download link
        # Pass a small preview (first 2000 chars) per tool for the page to be responsive
        preview_reports = {}
        for k, v in reports.items():
            preview_reports[k] = {
                "available": v.get("available", False),
                "returncode": v.get("returncode"),
                "preview": (v.get("output") or "")[:5000]  # small slice
            }

        # Save paths for download from server (we will send the PDF file directly)
        return render_template("results.html", reports=preview_reports, pdf_path=os.path.basename(out_pdf), pdf_fullpath=out_pdf, target_name=target_name)

    finally:
        # cleanup uploaded file if any - we keep the PDF
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
            except Exception:
                pass
        # Do NOT delete cloned repo here because user might want re-run — but we created cleanup_dir variable.
        # To be safe, delete it now to avoid disk growth:
        if cleanup_dir:
            try:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            except Exception:
                pass


@app.route("/download_pdf")
def download_pdf():
    # pdf_fullpath query param is passed? (we used pdf_fullpath when rendering results page)
    pdf_fullpath = request.args.get("path")
    if not pdf_fullpath or not os.path.exists(pdf_fullpath):
        flash("PDF not found or expired.", "danger")
        return redirect(url_for("index"))
    return send_file(pdf_fullpath, as_attachment=True, download_name=os.path.basename(pdf_fullpath))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
