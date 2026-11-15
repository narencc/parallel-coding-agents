"""Structured practice feedback from the sandbox, never a trusted judge verdict."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .sandbox import run_python, COPY_FILES

EXPECTED_TESTS = {
    "tests/test_visible.py::test_rupee_sign",
    "tests/test_visible.py::test_currency_marker_and_commas",
    "tests/test_visible.py::test_decimal_amount",
    "tests/test_visible.py::test_reject_unknown_word",
}
MARKER = "BAKEOFF_PRACTICE_REPORT="
PROGRAM = '''
import json
from pathlib import Path
import pytest

class Feedback:
    def __init__(self):
        self.collected = []
        self.reports = []
    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]
    def pytest_runtest_logreport(self, report):
        self.reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome})

source = Path(__file__).parent / "source"
feedback = Feedback()
exitcode = pytest.main([
    "-q", "--tb=short", "-c", "/dev/null", "--noconftest",
    "--rootdir", str(source), "--confcutdir", str(source),
    "--import-mode=importlib", "-p", "no:cacheprovider", str(source / "tests"),
], plugins=[feedback])
print("BAKEOFF_PRACTICE_REPORT=" + json.dumps({
    "exitcode": int(exitcode), "collected": feedback.collected, "reports": feedback.reports,
}), flush=True)
raise SystemExit(exitcode)
'''


@dataclass(frozen=True)
class PracticeFeedback:
    passed: int
    total: int
    all_passed: bool
    status: str
    returncode: int
    output: str

    def to_dict(self):
        return asdict(self)


def check_practice(source: Path, *, expected=EXPECTED_TESTS, files=COPY_FILES) -> PracticeFeedback:
    result = run_python(PROGRAM, source=source, files=files)
    total = len(expected)
    lines = result.output.splitlines()
    records = [line[len(MARKER):] for line in lines if line.startswith(MARKER)]
    tail = "\n".join(line for line in lines if not line.startswith(MARKER))[-8000:]
    invalid = PracticeFeedback(0, total, False, result.status, result.returncode, tail)
    if len(records) != 1 or result.status not in ("finished", "failed"):
        return invalid
    try:
        data = json.loads(records[0])
        collected = data["collected"]
        reports = data["reports"]
        if len(collected) != total or set(collected) != expected:
            return invalid
        if data["exitcode"] != result.returncode:
            return invalid
        passed = {r["nodeid"] for r in reports if r["when"] == "call" and r["outcome"] == "passed"}
        clean = all(r["outcome"] == "passed" for r in reports)
        complete = all(
            sum(r["nodeid"] == node and r["when"] == stage and r["outcome"] == "passed"
                for r in reports) == 1
            for node in expected for stage in ("setup", "call", "teardown")
        )
        success = result.status == "finished" and result.returncode == 0 and clean and complete
        return PracticeFeedback(len(passed & expected), total, success,
                                result.status, result.returncode, tail)
    except (ValueError, KeyError, TypeError):
        return invalid
