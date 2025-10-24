# scanner/clone_repo.py
import os
import subprocess
import tempfile
from urllib.parse import urlparse

def is_public_github(url):
    # Very simple heuristic: github.com and not a private SSH
    parsed = urlparse(url)
    return 'github.com' in parsed.netloc or 'gitlab.com' in parsed.netloc

def clone_repo(repo_url, dest_dir=None):
    """
    Clones a public repository to dest_dir (or a temp dir).
    Returns local path on success, raises RuntimeError on failure.
    """
    if not is_public_github(repo_url):
        raise RuntimeError("Repository does not appear to be a public GitHub/GitLab URL.")

    dest = dest_dir or tempfile.mkdtemp(prefix="pyfalcon_repo_")
    cmd = ["git", "clone", "--depth", "1", repo_url, dest]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Git clone failed: {proc.stderr.strip()}")
    return dest
