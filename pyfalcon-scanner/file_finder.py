# file_finder.py
import os

def list_python_files(repo_path):
    """
    Recursively list all Python files and requirements.txt in the repository.
    Returns two lists: python_files, requirements_files
    """
    py_files = []
    req_files = []

    for root, dirs, files in os.walk(repo_path):
        for file in files:
            full_path = os.path.join(root, file)
            if file.lower().endswith(".py"):
                py_files.append(full_path)
            elif file.lower() == "requirements.txt":
                req_files.append(full_path)

    return py_files, req_files
