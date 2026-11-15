"""Offline agent-loop tests; generated-code probes execute only in the sandbox."""

import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bakeoff import agent, practice, sandbox
from bakeoff.config import SAMPLE
from bakeoff.practice import PracticeFeedback


class Item(SimpleNamespace):
    def model_dump(self, **kwargs):
        return vars(self)


def reply(name, arguments, *, status="completed", usage=True):
    return SimpleNamespace(
        status=status,
        usage=SimpleNamespace(input_tokens=20, output_tokens=30) if usage else None,
        output=[Item(type="function_call", name=name, arguments=json.dumps(arguments), call_id="call-test")],
    )


def write(code="def parse_inr(text): return 50000", **kwargs):
    return reply("write_code", {"lines": code.splitlines(), "explanation": "A test draft."}, **kwargs)


def feedback(passed):
    return PracticeFeedback(passed, 4, passed == 4, "finished" if passed == 4 else "failed",
                            0 if passed == 4 else 1, f"{passed} practice tests passed")


@pytest.fixture
def folder(tmp_path):
    folder = tmp_path.resolve()
    shutil.copytree(SAMPLE, folder / "candidate")
    (folder / "drafts").mkdir()
    return folder


def test_failed_draft_is_revised_using_feedback_and_both_are_saved(folder):
    client = Mock()
    client.responses.create.side_effect = [write("# first"), write("# revised"), reply("submit", {"summary": "Fixed it."})]
    checker = Mock(side_effect=[feedback(0), feedback(2), feedback(4)])
    report = agent.run_agent(client, folder, checker=checker)
    assert report["status"] == "submitted_practice_passed"
    assert [d["practice"]["passed"] for d in report["drafts"]] == [2, 4]
    assert (folder / "drafts/draft-01.py").read_text() == "# first\n"
    assert (folder / "candidate/money.py").read_text() == "# revised\n"
    assert report["input_tokens"] == 60 and report["output_tokens"] == 90
    inputs = client.responses.create.call_args.kwargs["input"]
    assert any("2 practice tests passed" in item.get("output", "") for item in inputs if isinstance(item, dict))
    assert "hidden_tests" not in inputs[0]["content"]
    assert json.loads((folder / "report.json").read_text())["hidden_tests_run"] is False


def test_agent_cannot_choose_a_path_or_edit_tests(folder):
    client = Mock()
    client.responses.create.return_value = reply("write_code", {
        "lines": ["bad"], "explanation": "bad", "path": "../outside.py"})
    report = agent.run_agent(client, folder, max_rounds=1, checker=Mock(return_value=feedback(0)))
    assert report["drafts"] == []
    assert "NotImplementedError" in (folder / "candidate/money.py").read_text()
    assert report["protected_files_unchanged"]


def test_submit_without_passing_draft_is_refused_and_calls_are_bounded(folder):
    client = Mock()
    client.responses.create.return_value = reply("submit", {"summary": "Trust me"})
    report = agent.run_agent(client, folder, checker=Mock(return_value=feedback(0)))
    assert report["status"] == "out_of_rounds"
    assert client.responses.create.call_count == 4


def test_second_draft_checker_error_cannot_reuse_first_draft_success(folder):
    client = Mock()
    client.responses.create.side_effect = [write("# good"), write("# unchecked"), reply("submit", {"summary": "done"})]
    checker = Mock(side_effect=[feedback(0), feedback(4), ValueError("test runner unavailable")])
    report = agent.run_agent(client, folder, max_rounds=3, checker=checker)
    assert report["status"] == "out_of_rounds"
    assert report["drafts"][-1]["practice"] is None


@pytest.mark.parametrize("options, expected", [
    ({"status": "incomplete"}, "incomplete_response"),
    ({"usage": False}, "usage_missing"),
])
def test_incomplete_responses_are_not_saved_or_retried(folder, options, expected):
    client = Mock()
    client.responses.create.return_value = write(**options)
    report = agent.run_agent(client, folder, checker=Mock(return_value=feedback(0)))
    assert report["status"] == expected
    assert not report["drafts"]
    assert client.responses.create.call_count == 1


def test_changed_candidate_cannot_be_submitted(folder):
    client = Mock()
    replies = iter([write(), reply("submit", {"summary": "done"})])
    def next_reply(**kwargs):
        answer = next(replies)
        if answer.output[0].name == "submit":
            (folder / "candidate/money.py").write_text("# changed after testing")
        return answer
    client.responses.create.side_effect = next_reply
    report = agent.run_agent(client, folder, checker=Mock(side_effect=[feedback(0), feedback(4)]))
    assert report["status"] == "files_changed_after_testing"


def test_payload_limit_stops_before_api_request(folder, monkeypatch):
    monkeypatch.setattr(agent, "MAX_REQUEST_BYTES", 1)
    client = Mock()
    report = agent.run_agent(client, folder, checker=Mock(return_value=feedback(0)))
    assert report["status"] == "context_limit"
    client.responses.create.assert_not_called()


@pytest.mark.skipif(sys.platform != "darwin", reason="Real macOS sandbox required")
def test_fake_success_line_without_completed_test_reports_is_not_a_pass(folder):
    (folder / "candidate/money.py").write_text("import os\nprint('4 passed', flush=True)\nos._exit(0)\n")
    result = practice.check_practice(folder / "candidate")
    assert not result.all_passed


@pytest.mark.parametrize("status, returncode, record", [
    ("finished", 0, {"exitcode": 0, "collected": [], "reports": []}),
    ("timeout", -9, {"exitcode": 0, "collected": list(practice.EXPECTED_TESTS), "reports": []}),
])
def test_empty_or_interrupted_runs_do_not_qualify(monkeypatch, status, returncode, record):
    monkeypatch.setattr(practice, "run_python", lambda *a, **k: sandbox.SandboxResult(
        status, returncode, practice.MARKER + json.dumps(record), 0.1))
    assert not practice.check_practice(Path("unused")).all_passed
