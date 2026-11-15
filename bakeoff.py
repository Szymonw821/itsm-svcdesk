# ai-generated: 100% - Claude Code wrote the SARIF parsing and the matching from CI-SPEC.md section 3; checked against the practice set's expected.json
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json

Standard library only: it runs as `python3 -S -E bakeoff.py`. Each rule id below names the paragraph of
CI-SPEC.md section 3 that the code implements.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

# P-19: the course's classes and their CWE numbers.
CLASS_CWES: dict[str, tuple[int, ...]] = {
    "secret": (259, 260, 321, 798),
    "injection": (74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336),
    "deserialization": (502,),
    "weak-crypto": (261, 326, 327, 328, 330, 331, 338, 759, 760, 916),
    "insecure-transport": (295, 297, 319, 322, 757),
    "path-traversal": (22, 23, 35, 36, 73),
    "ssrf": (918,),
    "vulnerable-dependency": (937, 1035, 1104, 1395),
    "misconfiguration": (16, 215, 250, 489, 668, 732, 1188),
    "access-control": (284, 285, 639, 862, 863),
}
CWE_CLASSES: dict[int, set[str]] = {}
for _cls, _cwes in CLASS_CWES.items():
    for _n in _cwes:
        CWE_CLASSES.setdefault(_n, set()).add(_cls)

SEMGREP_NAMES = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}
FIXED_NAMES = {"trivy", "grype", "osv-scanner", "gitleaks"}
TRIVY_TAGS = {"vulnerability": "vulnerable-dependency", "secret": "secret", "misconfiguration": "misconfiguration"}

CWE_RE = re.compile(r"(?<![A-Za-z0-9])[Cc][Ww][Ee]-([0-9]+)")
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")
PEP503_RE = re.compile(r"[-_.]+")
NO_RULE = object()  # P-21: a result without a ruleId string differs from every string


def _get(obj, key):
    """A member of an object; a null member, or a non-object container, counts as absent."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def _list(value) -> list:
    """An array member that is not an array has no entries."""
    return value if isinstance(value, list) else []


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _same(a, b) -> bool:
    """JSON equality: true and 1 are different values."""
    return type(a) is type(b) and a == b


def tool_id(run: dict) -> str:
    """P-15."""
    name = _get(_get(_get(run, "tool"), "driver"), "name")
    if not isinstance(name, str):
        return "unknown"
    key = name.strip().lower()
    if key in FIXED_NAMES:
        return key
    if key in SEMGREP_NAMES:
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return slug or "unknown"


def kept(result: dict) -> bool:
    """P-16: kind absent, null or exactly `fail`; suppressions absent, null or empty."""
    kind = result.get("kind")
    if kind is not None and not _same(kind, "fail"):
        return False
    sup = result.get("suppressions")
    if sup is None or sup is False or _same(sup, ""):
        return True
    if isinstance(sup, (list, dict)) and len(sup) == 0:
        return True
    if isinstance(sup, (int, float)) and not isinstance(sup, bool) and sup == 0:
        return True
    return False


def normalise_path(uri: str) -> str:
    """P-17: decode %XX, drop a file:// prefix (any case), then one leading ./"""
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def set_file(path: str, root: str) -> str | None:
    """P-17: the path from the last component equal to the set root, or None outside the set."""
    parts = path.split("/")
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == root:
            return "/".join(parts[i:])
    return None


def lines_of(physical: dict) -> tuple[int, int] | None:
    """P-18."""
    region = _get(physical, "region")
    start = _get(region, "startLine")
    if not _is_int(start) or start < 1:
        return None
    end = _get(region, "endLine")
    if not _is_int(end) or end < start:
        end = start
    return start, end


def string_tags(obj) -> list[str]:
    return [t for t in _list(_get(_get(obj, "properties"), "tags")) if isinstance(t, str)]


def classes_of(result: dict, rule, tool: str) -> set[str]:
    """P-19: the first of (a) to (d) that gives any class."""
    own = _get(_get(result, "properties"), "class")
    if isinstance(own, str) and own in CLASS_CWES:
        return {own}
    if tool == "gitleaks":
        return {"secret"}
    if tool in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tool == "trivy":
        found = {TRIVY_TAGS[t.lower()] for t in string_tags(rule) if t.lower() in TRIVY_TAGS}
        if found:
            return found
    found = set()
    for tag in string_tags(result) + string_tags(rule):
        for match in CWE_RE.finditer(tag):
            found |= CWE_CLASSES.get(int(match.group(1)), set())
    return found or {"other"}


def pep503(name: str) -> str:
    return PEP503_RE.sub("-", name.lower())


def message_tokens(result: dict) -> set[str]:
    """P-20: the PEP 503 forms of the tokens of message.text."""
    text = _get(_get(result, "message"), "text")
    if not isinstance(text, str):
        return set()
    tokens = set()
    for raw in TOKEN_RE.findall(text):
        token = raw.strip("._-")
        if token:
            tokens.add(pep503(token))
    return tokens


def matches(finding: dict, defect: dict) -> bool:
    """P-20."""
    if finding["file"] != defect.get("file") or defect.get("class") not in finding["classes"]:
        return False
    if defect.get("class") == "vulnerable-dependency":
        package = defect.get("package")
        return isinstance(package, str) and pep503(package) in finding["tokens"]
    lines = finding["lines"]
    if lines is None:
        return False
    start, end = lines
    d_start, d_end = defect.get("start_line"), defect.get("end_line")
    if not _is_int(d_start) or not _is_int(d_end):
        return False
    return start <= d_end and d_start <= end


def collect(sarif_documents: list, root: str) -> dict[str, list[dict]]:
    """Every tool with a run in the inputs, and its kept results in the set (P-15 to P-19)."""
    tools: dict[str, list[dict]] = {}
    for doc in sarif_documents:
        for run in _list(_get(doc, "runs")):
            if not isinstance(run, dict):
                continue
            tool = tool_id(run)
            findings = tools.setdefault(tool, [])
            rules = _list(_get(_get(_get(run, "tool"), "driver"), "rules"))
            for result in _list(run.get("results")):
                if not isinstance(result, dict) or not kept(result):
                    continue
                locations = _list(result.get("locations"))
                if not locations:
                    continue
                physical = _get(locations[0], "physicalLocation")
                uri = _get(_get(physical, "artifactLocation"), "uri")
                if not isinstance(uri, str) or uri == "":
                    continue
                file = set_file(normalise_path(uri), root)
                if file is None:
                    continue  # outside the set: triage material, not the matrix
                rule_id = result.get("ruleId")
                rule = None
                if rule_id is not None:
                    rule = next((r for r in rules if isinstance(r, dict) and _same(r.get("id"), rule_id)), None)
                findings.append({
                    "rule_id": rule_id if isinstance(rule_id, str) else NO_RULE,
                    "file": file,
                    "lines": lines_of(physical),
                    "classes": classes_of(result, rule, tool),
                    "tokens": message_tokens(result),
                })
    return tools


def ratio(num: int, den: int):
    return None if den == 0 else round(num / den, 4)


def confusion_matrix(labels: dict, sarif_documents: list) -> dict:
    """The matrix of P-21 and P-22 for the labels (P-14) and the parsed SARIF documents."""
    defects = [d for d in _list(labels.get("defects")) if isinstance(d, dict)]
    tools: dict[str, dict] = {}
    for tool, findings in collect(sarif_documents, labels["set"]).items():
        found_ids = set()
        unmatched = set()
        for finding in findings:
            hit = False
            for index, defect in enumerate(defects):
                if matches(finding, defect):
                    found_ids.add(index)
                    hit = True
            if not hit:
                start, end = finding["lines"] if finding["lines"] else (None, None)
                rule_key = ("rule", finding["rule_id"]) if finding["rule_id"] is not NO_RULE else ("none",)
                unmatched.add((rule_key, finding["file"], start, end))
        tp = len(found_ids)
        fp = len(unmatched)
        fn = len(defects) - tp
        tools[tool] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, len(defects)),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": labels["set"], "defects": len(defects), "tools": dict(sorted(tools.items()))}


def load_json(path: str):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    labels = load_json(args.labels)
    documents = []
    for path in args.sarif:
        try:
            documents.append(load_json(path))
        except (ValueError, UnicodeDecodeError):
            documents.append(None)  # not JSON: no runs
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
