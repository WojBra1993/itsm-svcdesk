# ai-generated: 100% - Claude Code (Opus 5.5) wrote this file from the course's Lab 5 design (CI-SPEC.md is its public part); the lecturer reviews it
"""Convert an AI reviewer's findings (the course's JSON) into SARIF 2.1.0 with driver `ai-reviewer` (CI-SPEC.md P-30).

Standard library only. The output is deterministic: rules and results keep the order of the input.
Run `python3 tools/ai-to-sarif.py --help` for the input shape.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DRIVER = "ai-reviewer"
INFORMATION_URI = "https://github.com/swasik/itsm-2026-template"
ROUTES = ("action", "local")

# The course's weakness classes (CI-SPEC.md P-19) and their CWEs.
CLASSES = {
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

SHAPE = """\
input (UTF-8 JSON; a Markdown ```json fence around it is tolerated):

  {"model": "<the model that reviewed, e.g. its id>",  (optional with --model, which replaces it)
   "findings": [
     {"file": "lab5-canary/app/x.py",    path from the repository root, starting at lab5-canary/
      "start_line": 3,                   first line of the defective statement, 1-based
      "end_line": 5,                     last line, inclusive (optional, default start_line)
      "class": "injection",              one of the classes below
      "cwe": "CWE-89",                   optional, CWE-<number>
      "rule": "sql-fstring",             optional short name of the kind of defect (default: the class)
      "message": "..."}]}                what is wrong; for vulnerable-dependency it must name the package

classes: """ + ", ".join(CLASSES) + """

output: SARIF 2.1.0, one run, tool.driver.name "ai-reviewer", one rule per distinct rule (its CWEs in
properties.tags), one result per finding (level warning, one location, properties.class), and the model and the
route (action = claude-code-action in a workflow, local = an assistant on your machine) in run.properties.
A model often misnames itself: --model NAME records the model you actually ran (and keeps the answer's own claim,
when it differs, as run.properties.model_self_reported).

exit status: 0 written, 2 the input breaks the shape (the message names the finding)."""


class InputError(Exception):
    pass


def _load(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as first:
        fence = re.search(r"```(?:json)?[ \t]*\n(.*?)\n[ \t]*```", text, re.S)
        if fence:
            try:
                return json.loads(fence.group(1))
            except json.JSONDecodeError as exc:
                raise InputError(f"the fenced block is not JSON: {exc}") from None
        raise InputError(f"not JSON: {first}") from None


def _line(value: object, where: str, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InputError(f"{where}: '{field}' must be an integer of at least 1, not {value!r}")
    return value


def _text(value: object, where: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where}: '{field}' must be a non-empty string")
    return value.strip()


def convert(data: object, route: str, model_override: str | None = None) -> dict:
    """The SARIF document for the parsed input; raises InputError naming the first problem. `model_override`
    (`--model`) is the model that actually ran; the answer's own `model` is then optional."""
    if not isinstance(data, dict):
        raise InputError("the top level must be an object with 'model' and 'findings'")
    claimed = data.get("model")
    if model_override is not None:
        model = _text(model_override, "--model", "model")
        claimed = claimed.strip() if isinstance(claimed, str) and claimed.strip() else None
    else:
        model = claimed = _text(claimed, "top level", "model")
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise InputError("top level: 'findings' must be a list (it may be empty)")
    rules: dict[str, list[str]] = {}
    results = []
    for index, finding in enumerate(findings):
        where = f"finding {index}"
        if not isinstance(finding, dict):
            raise InputError(f"{where}: must be an object")
        path = _text(finding.get("file"), where, "file").replace("\\", "/")
        start = _line(finding.get("start_line"), where, "start_line")
        end = _line(finding.get("end_line", start), where, "end_line")
        if end < start:
            raise InputError(f"{where}: end_line {end} is before start_line {start}")
        cls = finding.get("class")
        if cls not in CLASSES:
            raise InputError(f"{where}: class {cls!r} is not one of: {', '.join(CLASSES)}")
        cwe = finding.get("cwe")
        if cwe is not None:
            cwe = _text(cwe, where, "cwe").upper()
            if not re.fullmatch(r"CWE-\d+", cwe):
                raise InputError(f"{where}: cwe {cwe!r} is not CWE-<number>")
        rule = _text(finding.get("rule", cls), where, "rule")
        message = _text(finding.get("message"), where, "message")
        tags = rules.setdefault(rule, [])
        if cwe and cwe not in tags:
            tags.append(cwe)
        results.append({
            "ruleId": rule,
            "level": "warning",
            "message": {"text": message},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": path},
                "region": {"startLine": start, "endLine": end},
            }}],
            "properties": {"class": cls},
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": DRIVER,
                "informationUri": INFORMATION_URI,
                "rules": [{"id": rule, "name": rule, "shortDescription": {"text": rule},
                           "properties": {"tags": tags}} for rule, tags in rules.items()],
            }},
            "results": results,
            "properties": {"model": model, "route": route,
                           **({"model_self_reported": claimed} if claimed and claimed != model else {})},
        }],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai-to-sarif.py",
        description="Convert an AI reviewer's findings (the course's JSON) into SARIF with driver 'ai-reviewer'.",
        epilog=SHAPE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="the findings JSON (the model's answer), or - for standard input")
    parser.add_argument("-o", "--output", help="the SARIF file to write (default: standard output)")
    parser.add_argument("--route", choices=ROUTES, default="local",
                        help="how the review ran: action (claude-code-action in a workflow) or local (default)")
    parser.add_argument("--model", default=None, metavar="NAME",
                        help="the model you ran (e.g. qwen3:4b-instruct); replaces the answer's own 'model', which a "
                             "model often gets wrong")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read() if args.input == "-" else Path(args.input).read_bytes()
        text = raw.decode("utf-8-sig")
        sarif = convert(_load(text), args.route, args.model)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ai-to-sarif.py: cannot read {args.input}: {exc}", file=sys.stderr)
        return 2
    except InputError as exc:
        print(f"ai-to-sarif.py: {args.input}: {exc}", file=sys.stderr)
        return 2
    out = json.dumps(sarif, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"ai-to-sarif.py: {len(sarif['runs'][0]['results'])} results -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
