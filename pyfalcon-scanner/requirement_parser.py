# scanner/requirement_parser.py
import re

REQ_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+)(?:\s*(?:==|>=|<=|~=|!=)\s*([0-9a-zA-Z\.\-]+))?')

def parse_requirements_txt(path):
    deps = {}
    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = REQ_LINE.match(line)
            if m:
                name = m.group(1)
                version = m.group(2) or None
                deps[name.lower()] = version
    return deps
