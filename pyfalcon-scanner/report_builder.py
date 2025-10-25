
# scanner/report_builder.py
import json
import os
from datetime import datetime

def build_report(dependency_map, req_versions, latest_versions, pip_audit_results=None):
    """
    Build a structured scan report.

    dependency_map: dict {package_name: [files]} or list of package names
    req_versions: {package_name_lower: pinned_version_or_None}
    latest_versions: {package_name_lower: latest_version_or_None}
    pip_audit_results: list of dicts or strings (optional)
        dict format: {"name": package_name, "vulns": [...]}
        string format: package_name with no vulnerability info
    """
    rows = []

    # Convert list to dict if needed
    if isinstance(dependency_map, list):
        dependency_map = {pkg: [] for pkg in dependency_map}

    # Build vulnerability map
    vuln_map = {}
    if pip_audit_results:
        for item in pip_audit_results:
            if isinstance(item, dict):
                name = item.get("name")
                vulns = item.get("vulns", [])
                if name:
                    vuln_map[name.lower()] = vulns
            elif isinstance(item, str):
                vuln_map[item.lower()] = []

    # Iterate over dependencies
    for pkg, files in sorted(dependency_map.items(), key=lambda x: x[0].lower()):
        pkg_lower = pkg.lower()
        local_ver = req_versions.get(pkg_lower)
        latest = latest_versions.get(pkg_lower)
        vulnerabilities = vuln_map.get(pkg_lower, [])

        pros = "Widely used"
        cons = ""
        suggestions = ""

        if local_ver and latest:
            if local_ver != latest:
                suggestions = f"Consider upgrading from {local_ver} → {latest}"
        elif not local_ver:
            suggestions = f"No pinned version found; consider pinning or checking compatibility with {latest or 'latest'}"

        if vulnerabilities:
            cons = f"{len(vulnerabilities)} known vulnerabilities"

        rows.append({
            "dependency": pkg,
            "files": files,
            "current_version": local_ver,
            "latest_version": latest,
            "pros": pros,
            "cons": cons,
            "vulnerabilities": vulnerabilities,
            "suggestions": suggestions
        })

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rows": rows
    }


def save_report_json(report, outpath):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
