

# Pyfalcon - Python Project Dependency & Vulnerability Scanner

## Overview

Pyfalcon scans a GitHub repository for Python files, parses their dependencies, fetches the latest versions from PyPI, checks for known vulnerabilities, and generates a report in HTML, PDF, and JSON formats.

It also provides a **Scan Workflow** view showing the stages of scanning and the list of Python files found.

## Workflow

1. **Clone Repository**
   The repo is cloned locally into `webapp/scans/`.

2. **Scan Python Files**
   Recursively scan all `.py` files and `requirements.txt` in the repo.

3. **Parse Imports & Dependencies**
   Extract imported packages from Python files and `requirements.txt`.

4. **Fetch Latest Versions**
   Check PyPI for the latest versions of each dependency.

5. **Run Vulnerability Scan**
   Use `pip-audit` to detect known security vulnerabilities.

6. **Generate Report**
   Produce a report showing:

   * Dependency
   * Current Version
   * Latest Version
   * Status (Up-to-date / Outdated)
   * Vulnerabilities / Suggestions

   Reports are saved as:

   * JSON: `scans/<repo>/report.json`
   * PDF: `scans/<repo>/report.pdf`
   * HTML: rendered in browser

7. **Scan Workflow UI**
   Interactive UI showing each scan stage and the list of Python files scanned.

---

## Setup & Installation

```bash
# 1. Clone the project
git clone https://github.com/prasadjr/Major_Project.git
cd Major_Project/webapp

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate     # Linux / macOS
venv\Scripts\activate        # Windows

# 3. Install required packages
pip install -r requirements.txt
```

> **Note:** `requirements.txt` should include:
>
> ```
> Flask
> pdfkit
> pip-audit
> requests
> ```

* Install **wkhtmltopdf** for PDF generation if not installed:

  * Linux: `sudo apt install wkhtmltopdf`
  * Mac: `brew install wkhtmltopdf`
  * Windows: download installer from [wkhtmltopdf.org](https://wkhtmltopdf.org/)

---

## Running the Application

```bash
# Start the Flask app
python app.py
```

* Open your browser at: `http://127.0.0.1:5000/`
* Enter a **GitHub repository URL** in the input box.
* Click **Start Scan** to view:

  * Scan workflow stages
  * Python files found
  * Dependencies and vulnerabilities
  * Downloadable PDF/JSON reports

---

## API Endpoints

| Endpoint                      | Method | Description                                       |
| ----------------------------- | ------ | ------------------------------------------------- |
| `/api/scan`                   | POST   | Scan a repo. Send JSON: `{ "repo_url": "<URL>" }` |
| `/reports/<repo>/report.json` | GET    | Download JSON report                              |
| `/reports/<repo>/report.pdf`  | GET    | Download PDF report                               |

---

## Example

```bash
# Scan a repo via curl
curl -X POST http://127.0.0.1:5000/api/scan \
    -H "Content-Type: application/json" \
    -d '{"repo_url": "https://github.com/prasadjr/Major_Project.git"}'
```

* The response contains URLs for JSON, PDF, and HTML report previews.

---

## Folder Structure

```
webapp/
├─ app.py
├─ templates/
│  ├─ report.html
│  └─ scan_workflow.html
├─ static/
│  └─ css.css
├─ scans/
│  └─ <cloned_repos>/
└─ modules/ (clone_repo, file_finder, import_parser, etc.)
```

---



# Pyfalcon Workflow Diagram (Sanner)

         ┌────────────────────┐
         │ Enter GitHub Repo  │
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ Clone Repository   │
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ Scan Python Files  │
         │ & requirements.txt │
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ Parse Imports &    │
         │ Dependencies       │
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ Fetch Latest Versions│
         │ from PyPI           │
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ Run pip-audit      │
         │ Vulnerability Scan │
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ Build Report       │
         │ (HTML / PDF / JSON)│
         └─────────┬──────────┘
                   │
                   ▼
         ┌────────────────────┐
         │ View Scan Workflow │
         │ & Report in Browser│
         └────────────────────┘
