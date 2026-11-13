# ai-generated: 100% - Codex implemented the published CI-SPEC P-14 to P-24 rules and checked the practice data.
"""Compute per-scanner confusion matrices from SARIF using the course contract."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

CWE = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}


def obj(value):
    return value if isinstance(value, dict) else {}


def array(value):
    return value if isinstance(value, list) else []


def tool_id(driver):
    name = driver.get("name")
    if not isinstance(name, str):
        return "unknown"
    name = name.strip().lower()
    if name in {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}:
        return "semgrep"
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-") or "unknown"


def tags(value):
    return [tag for tag in array(obj(value.get("properties")).get("tags")) if isinstance(tag, str)]


def classes(result, driver, tool):
    explicit = obj(result.get("properties")).get("class")
    if isinstance(explicit, str) and explicit in CWE:
        return {explicit}
    if tool == "gitleaks":
        return {"secret"}
    if tool in {"grype", "osv-scanner"}:
        return {"vulnerable-dependency"}
    rule = next((entry for entry in array(driver.get("rules"))
                 if isinstance(entry, dict) and entry.get("id") == result.get("ruleId")), {})
    rule_tags = tags(rule)
    if tool == "trivy":
        mapping = {"vulnerability": "vulnerable-dependency", "secret": "secret", "misconfiguration": "misconfiguration"}
        found = {mapping[tag.lower()] for tag in rule_tags if tag.lower() in mapping}
        if found:
            return found
    numbers = {int(match) for tag in tags(result) + rule_tags
               for match in re.findall(r"(?<![A-Za-z0-9])(?i:CWE)-([0-9]+)", tag)}
    return {name for name, values in CWE.items() if values & numbers} or {"other"}


def location(result, root):
    locations = array(result.get("locations"))
    physical = obj(obj(locations[0]).get("physicalLocation")) if locations else {}
    uri = obj(physical.get("artifactLocation")).get("uri")
    if not isinstance(uri, str) or not uri:
        return None
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    parts = path.split("/")
    indices = [i for i, part in enumerate(parts) if part == root]
    if not indices:
        return None
    file = "/".join(parts[indices[-1]:])
    region = obj(physical.get("region"))
    start = region.get("startLine")
    if type(start) is not int or start < 1:
        return file, None, None
    end = region.get("endLine")
    end = max(start, end) if type(end) is int else start
    return file, start, end


def package_name(value):
    return re.sub(r"[-_.]+", "-", value.lower())


def matrix(labels, documents):
    defects = labels["defects"]
    state = {}
    for document in documents:
        for run in array(obj(document).get("runs")):
            if not isinstance(run, dict):
                continue
            driver = obj(obj(run.get("tool")).get("driver"))
            tool = tool_id(driver)
            found, false_positives = state.setdefault(tool, (set(), set()))
            for result in array(run.get("results")):
                if not isinstance(result, dict) or result.get("kind") not in (None, "fail") or result.get("suppressions"):
                    continue
                loc = location(result, labels["set"])
                if loc is None:
                    continue
                file, start, end = loc
                result_classes = classes(result, driver, tool)
                message = obj(result.get("message")).get("text")
                packages = {package_name(token.strip("._-")) for token in re.findall(r"[A-Za-z0-9._-]+", message)} if isinstance(message, str) else set()
                matched = set()
                for defect in defects:
                    if defect["file"] != file or defect["class"] not in result_classes:
                        continue
                    if defect["class"] == "vulnerable-dependency":
                        match = package_name(defect["package"]) in packages
                    else:
                        match = start is not None and start <= defect["end_line"] and defect["start_line"] <= end
                    if match:
                        matched.add(defect["id"])
                if matched:
                    found.update(matched)
                else:
                    rule = result.get("ruleId")
                    false_positives.add((rule if isinstance(rule, str) else None, file, start, end))
    tools = {}
    for tool, (found, false_positives) in sorted(state.items()):
        tp, fp, fn = len(found), len(false_positives), len(defects) - len(found)
        tools[tool] = {"tp": tp, "fp": fp, "fn": fn,
                       "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                       "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                       "f1": round(2 * tp / (2 * tp + fp + fn), 4) if 2 * tp + fp + fn else None}
    return {"set": labels["set"], "defects": len(defects), "tools": tools}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("sarif", nargs="+", type=Path)
    args = parser.parse_args()
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in args.sarif]
    print(json.dumps(matrix(labels, documents), indent=2))


if __name__ == "__main__":
    main()
