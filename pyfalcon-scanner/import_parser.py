# scanner/import_parser.py
import ast
from collections import defaultdict

def extract_imports_from_file(py_path):
    """
    Use ast to extract imported module/package names from a .py file.
    Returns set of top-level module names (example: 'requests', 'flask', 'os').
    """
    imports = set()
    with open(py_path, 'r', encoding='utf-8', errors='ignore') as fh:
        try:
            tree = ast.parse(fh.read(), filename=py_path)
        except Exception:
            return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def aggregate_imports(py_files):
    deps = defaultdict(list)
    for p in py_files:
        names = extract_imports_from_file(p)
        for n in names:
            deps[n].append(p)
    return deps  # {package: [file1, file2, ...]}
