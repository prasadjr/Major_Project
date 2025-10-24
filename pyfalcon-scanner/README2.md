Pyfalcon - Python Dependency & Vulnerability Scanner
Project Overview

Pyfalcon is a Python-based tool that scans GitHub repositories for Python files, analyzes dependencies, checks for the latest PyPI versions, and detects security vulnerabilities using pip-audit. It generates a structured report in HTML, PDF, and JSON formats and shows a scan workflow with stages in the browser.

Features

Clone any public GitHub repository

Recursively scan all Python files

Parse import statements and dependencies

Fetch latest PyPI versions of dependencies

Run vulnerability scan with pip-audit

Generate report in HTML, PDF, JSON

Visualize scan workflow and file structure in UI

Highlight outdated packages and known vulnerabilities

Workflow
flowchart TD
    A[Enter GitHub Repository URL] --> B[Clone Repository]
    B --> C[Scan Python Files & requirements.txt]
    C --> D[Parse Imports & Dependencies]
    D --> E[Fetch Latest Versions from PyPI]
    E --> F[Run pip-audit Vulnerability Scan]
    F --> G[Build Report (HTML / PDF / JSON)]
    G --> H[View Scan Workflow & Report in Browser]


Crisp Working:

Enter Repo URL – User provides GitHub repository link.

Clone Repo – Repository is cloned locally under /scans.

Scan Files – Python files and requirements.txt are collected recursively.

Parse Dependencies – Imports are aggregated to map dependencies.

Check Latest Versions – Queries PyPI for latest package versions.

Vulnerability Scan – Runs pip-audit to detect security issues.

Build Report – Generates structured HTML, PDF, and JSON reports.

View Workflow – UI displays scan stages, file structure, and report.

Setup & Installation
# 1. Clone your project
git clone https://github.com/prasadjr/Major_Project.git
cd Major_Project/webapp

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt
pip install pdfkit Flask requests pip-audit


Note: For PDF generation, ensure wkhtmltopdf is installed on your system.

Running the Application
# Start Flask server
python app.py


Open browser and visit: http://127.0.0.1:5000

Enter the GitHub repository URL to scan.

The workflow view shows each stage of the scan.

Generated reports (HTML, PDF, JSON) can be downloaded.

Folder Structure
Major_Project/
├─ webapp/
│  ├─ app.py
│  ├─ templates/
│  │  ├─ report.html
│  │  └─ scan_workflow.html
│  ├─ static/
│  │  └─ css.css
│  ├─ scans/           # Cloned repos and generated reports
│  ├─ clone_repo.py
│  ├─ file_finder.py
│  ├─ import_parser.py
│  ├─ requirement_parser.py
│  ├─ pypi_checker.py
│  ├─ vulnerability_tools.py
│  └─ report_builder.py
├─ README.md
└─ requirements.txt

Commands Summary
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Start scanning server
python app.py

# Open browser
http://127.0.0.1:5000

Screenshots