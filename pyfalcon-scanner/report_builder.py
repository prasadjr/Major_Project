# scanner/report_builder.py
import json
import os
from datetime import datetime

def build_report(dependency_map, req_versions, latest_versions, pip_audit_results=None):
    """
    Builds a structured, file-wise scan report.

    dependency_map: dict {package_name: [files]} or list of package names
    req_versions: {package_name_lower: pinned_version_or_None}
    latest_versions: {package_name_lower: latest_version_or_None}
    pip_audit_results: list of dicts or strings
    """
    file_wise = {}

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

    # Group dependencies per file
    for pkg, files in dependency_map.items():
        pkg_lower = pkg.lower()
        local_ver = req_versions.get(pkg_lower)
        latest = latest_versions.get(pkg_lower)
        vulnerabilities = vuln_map.get(pkg_lower, [])

        dep_info = {
            "name": pkg,
            "current_version": local_ver,
            "latest_version": latest,
            "up_to_date": local_ver == latest if local_ver and latest else None,
            "pip_audit": vulnerabilities,
            "suggestions": None
        }

        if local_ver and latest and local_ver != latest:
            dep_info["suggestions"] = f"Consider upgrading from {local_ver} → {latest}"
        elif not local_ver:
            dep_info["suggestions"] = f"No pinned version found; consider pinning or checking compatibility with {latest or 'latest'}"

        for f in files or ["<unknown>"]:
            file_wise.setdefault(f, {"filename": f, "imports": [], "dependencies": []})
            if pkg not in file_wise[f]["imports"]:
                file_wise[f]["imports"].append(pkg)
            file_wise[f]["dependencies"].append(dep_info)

    # Return as a list sorted by filename
    return sorted(file_wise.values(), key=lambda x: x["filename"])


def save_report_json(report, outpath):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
