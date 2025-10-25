import requests

def get_latest_pypi_version(package_name):
    """
    Returns the latest version of a package from PyPI.
    Returns None if not found.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return None
        data = response.json()
        return data.get("info", {}).get("version")
    except Exception:
        return None
