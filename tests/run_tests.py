# ai-generated: 100% - Codex added the course-required pytest summary.
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Results:
    passed = 0
    failed = 0

    def pytest_runtest_logreport(self, report):
        if report.when == "call" and report.passed:
            self.passed += 1
        if report.failed:
            self.failed += 1

    def pytest_collectreport(self, report):
        if report.failed:
            self.failed += 1


if __name__ == "__main__":
    results = Results()
    exit_code = pytest.main(["-q", "-p", "no:cacheprovider", str(ROOT / "tests")], plugins=[results])
    print(f"ITSMLAB-TESTS: passed={results.passed} failed={results.failed}", flush=True)
    sys.exit(int(exit_code))
