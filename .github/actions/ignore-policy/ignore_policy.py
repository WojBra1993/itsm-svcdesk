# ai-generated: 100% - Claude Code (Opus 5.5) wrote this file from the course's Lab 5 design (CI-SPEC.md is its public part); the lecturer reviews it
"""The Lab 5 ignore policy (CI-SPEC.md P-06): every ignore expires and says why.

One source, two copies. This file is the checker's `itsmlab/labs/lab5/policy.py` and, byte for byte, the pipeline
skeleton's `.github/actions/ignore-policy/ignore_policy.py`, which the `ignore-policy` job runs with the runner's
`python3` (standard library only, Python 3.10 or newer). A checker test fails when the two copies differ.

The rule, exactly as this module checks it (line numbers are 1-based):

`.trivyignore`
  * A line is blank or a comment when, stripped of surrounding white space, it is empty or starts with `#` - the way
    Trivy 0.74.0 reads the file. Every other line is an entry.
  * An entry, stripped, is exactly two fields separated by white space: `<ID> exp:<YYYY-MM-DD>`. Nothing else may be
    on the line, not even a trailing comment (Trivy takes the first field as the ID and any field starting with
    `exp:` as the expiry; the course keeps the line to those two).
  * ID: `CVE-<4 digits>-<4 or more digits>`, or `GHSA-xxxx-xxxx-xxxx` with every x one of 23456789cfghjmpqrvwx.
  * The expiry is a calendar date after the check date and at most 90 days after it: 0 < exp - check date <= 90
    days. (Trivy stops honouring an entry at 00:00 UTC of its date, so "after" is the right side of the boundary.)
  * Justification: the comment lines directly above the entry - contiguous, so a blank line or another entry ends
    them - each with its leading `#` characters and surrounding white space removed; their texts, concatenated,
    are at least 20 characters long. Two entries in a row: the second one has no justification.
  * No ID appears twice.

`.gitleaksignore`
  * Every line that is neither blank nor a comment has a justification as above. The fingerprint format is
    gitleaks' business, not the policy's.

`.trivyignore.yaml` must not exist next to the checked files: the skeleton passes `--ignorefile .trivyignore`, and
the experimental YAML form would bypass this check.

The check date is a calendar date in UTC, whatever the machine's time zone: the day the pipeline runs, the day of
the submission receipt in Tier B, and today in Tier A. (In Poland, before 01:00 in winter and 02:00 in summer, the
UTC date is still yesterday's.)

Command line (what the `ignore-policy` action runs):

    python3 ignore_policy.py [--date YYYY-MM-DD] [.trivyignore] [.gitleaksignore]

Missing files are fine (nothing to ignore, nothing to check). Exit 0 when the policy holds, 1 with one line per
problem, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

MAX_DAYS = 90
MIN_JUSTIFICATION = 20
TRIVYIGNORE = ".trivyignore"
GITLEAKSIGNORE = ".gitleaksignore"
TRIVYIGNORE_YAML = ".trivyignore.yaml"

_GHSA_CHARS = "[23456789cfghjmpqrvwx]"
ID_RE = re.compile(rf"(?:CVE-\d{{4}}-\d{{4,}}|GHSA-{_GHSA_CHARS}{{4}}-{_GHSA_CHARS}{{4}}-{_GHSA_CHARS}{{4}})")
EXP_RE = re.compile(r"exp:(\d{4})-(\d{2})-(\d{2})")


def _is_skipped(stripped: str) -> bool:
    return stripped == "" or stripped.startswith("#")


def _comment_text(stripped: str) -> str:
    return stripped.lstrip("#").strip()


def _justification(lines: list[str], index: int) -> str:
    """The concatenated text of the contiguous comment lines directly above lines[index]."""
    parts: list[str] = []
    i = index - 1
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped.startswith("#"):
            break
        parts.append(_comment_text(stripped))
        i -= 1
    return "".join(reversed(parts))


def _justification_problem(name: str, number: int, lines: list[str], index: int) -> str | None:
    text = _justification(lines, index)
    if len(text) >= MIN_JUSTIFICATION:
        return None
    return (f"{name} line {number}: no justification - write at least {MIN_JUSTIFICATION} characters of reason in "
            f"'#' comment lines directly above the entry (found {len(text)})")


def _show(stripped: str) -> str:
    return stripped if len(stripped) <= 60 else stripped[:57] + "..."


def trivyignore_ids(text: str) -> list[str]:
    """The ID (first field) of every entry of a `.trivyignore`, in file order, one per entry (a duplicate appears
    twice), whether or not the entry obeys the policy. A leading byte-order mark is dropped (check_trivyignore reports
    it)."""
    ids: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff").strip()
        if not _is_skipped(stripped):
            ids.append(stripped.split()[0])
    return ids


def check_trivyignore(text: str, check_date: date, name: str = TRIVYIGNORE) -> list[str]:
    """P-06 problems of a `.trivyignore`, one message per problem, each naming the line."""
    problems: list[str] = []
    lines = text.splitlines()
    seen: dict[str, int] = {}
    for index, line in enumerate(lines):
        number = index + 1
        stripped = line.strip()
        if _is_skipped(stripped):
            continue
        if stripped.startswith("\ufeff"):
            problems.append(f"{name} line {number}: the file starts with a byte-order mark; save it as UTF-8 "
                            "without BOM")
            continue
        justification = _justification_problem(name, number, lines, index)
        if justification:
            problems.append(justification)
        fields = stripped.split()
        ident = fields[0]
        if not ID_RE.fullmatch(ident):
            problems.append(f"{name} line {number}: '{_show(ident)}' is not a CVE-YYYY-NNNN or GHSA-xxxx-xxxx-xxxx "
                            "identifier")
        elif ident in seen:
            problems.append(f"{name} line {number}: {ident} already appears on line {seen[ident]}")
        else:
            seen[ident] = number
        if len(fields) == 1:
            problems.append(f"{name} line {number}: bare ignore of {_show(ident)} - add an expiry: "
                            "'<ID> exp:<YYYY-MM-DD>'")
            continue
        if len(fields) > 2:
            problems.append(f"{name} line {number}: '{_show(stripped)}' has text after the expiry; the line must be "
                            "exactly '<ID> exp:<YYYY-MM-DD>' (put the reason in '#' lines above it)")
            continue
        match = EXP_RE.fullmatch(fields[1])
        if not match:
            problems.append(f"{name} line {number}: '{_show(fields[1])}' is not 'exp:YYYY-MM-DD'")
            continue
        try:
            expiry = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            problems.append(f"{name} line {number}: {fields[1]} is not a calendar date")
            continue
        days = (expiry - check_date).days
        if days <= 0:
            problems.append(f"{name} line {number}: {fields[1]} is not after the check date {check_date.isoformat()} "
                            "(the ignore has expired)")
        elif days > MAX_DAYS:
            problems.append(f"{name} line {number}: {fields[1]} is {days} days after the check date "
                            f"{check_date.isoformat()}; at most {MAX_DAYS} are allowed")
    return problems


def check_gitleaksignore(text: str, name: str = GITLEAKSIGNORE) -> list[str]:
    """P-06 problems of a `.gitleaksignore`: every entry needs a justification above it."""
    problems: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if _is_skipped(stripped):
            continue
        if stripped.startswith("\ufeff"):
            problems.append(f"{name} line {index + 1}: the file starts with a byte-order mark; save it as UTF-8 "
                            "without BOM")
            continue
        justification = _justification_problem(name, index + 1, lines, index)
        if justification:
            problems.append(justification)
    return problems


def _read(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_bytes().decode("utf-8"), None
    except UnicodeDecodeError:
        return None, f"{path.as_posix()}: not UTF-8 text (save it as UTF-8)"
    except OSError as exc:
        return None, f"{path.as_posix()}: cannot be read ({exc.strerror or exc})"


def check_paths(paths: list[Path], check_date: date, base: Path | None = None) -> list[str]:
    """The whole policy over the given ignore files (missing ones are fine), plus the `.trivyignore.yaml` rule for
    every directory they are in. Relative paths are taken from `base` (default: the working directory) and shown as
    given. Raises ValueError for a file name the policy does not know."""
    problems: list[str] = []
    folders: list[Path] = []
    for path in paths:
        if path.parent not in folders:
            folders.append(path.parent)
        if path.name == TRIVYIGNORE_YAML:
            continue  # reported below, once per directory
        if path.name not in (TRIVYIGNORE, GITLEAKSIGNORE):
            raise ValueError(f"{path.as_posix()}: the policy knows {TRIVYIGNORE} and {GITLEAKSIGNORE} only")
        real = base / path if base is not None else path
        if not real.is_file():
            continue
        text, error = _read(real)
        if error:
            problems.append(error.replace(real.as_posix(), path.as_posix(), 1))
            continue
        if path.name == TRIVYIGNORE:
            problems.extend(check_trivyignore(text or "", check_date, name=path.as_posix()))
        else:
            problems.extend(check_gitleaksignore(text or "", name=path.as_posix()))
    for folder in folders:
        yaml_form = folder / TRIVYIGNORE_YAML
        if ((base / yaml_form) if base is not None else yaml_form).exists():
            problems.append(f"{yaml_form.as_posix()}: must not exist - the pipeline reads {TRIVYIGNORE} only, and "
                            "the YAML form would bypass this policy")
    return problems


def check_repository(root: Path, check_date: date) -> list[str]:
    """The policy on a repository: its `.trivyignore` and `.gitleaksignore` at the root, messages relative to it."""
    return check_paths([Path(TRIVYIGNORE), Path(GITLEAKSIGNORE)], check_date, base=root)


def today_utc() -> date:
    """The check date of the pipeline and of the checker when no date is given: today in UTC (CI-SPEC.md P-06)."""
    return datetime.now(timezone.utc).date()


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a date YYYY-MM-DD: {value!r}") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ignore_policy.py",
        description="Check .trivyignore and .gitleaksignore against the Lab 5 ignore policy (CI-SPEC.md P-06).")
    parser.add_argument("--date", type=_parse_date, default=None,
                        help="the check date, YYYY-MM-DD (default: today in UTC)")
    parser.add_argument("files", nargs="*", default=[TRIVYIGNORE, GITLEAKSIGNORE],
                        help=f"ignore files to check (default: {TRIVYIGNORE} {GITLEAKSIGNORE})")
    args = parser.parse_args(argv)
    check_date = args.date or today_utc()
    try:
        problems = check_paths([Path(f) for f in args.files], check_date)
    except ValueError as exc:
        print(f"ignore_policy.py: {exc}", file=sys.stderr)
        return 2
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"
    for problem in problems:
        print(f"::error title=Ignore policy (P-06)::{problem}" if annotate else problem)
    if problems:
        return 1
    print(f"ignore policy (P-06): OK at {check_date.isoformat()} for {', '.join(args.files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
