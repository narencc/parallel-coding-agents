"""Real macOS boundary checks. These use probes, never generated model code."""

from pathlib import Path
import shutil
import sys
from unittest.mock import Mock

import pytest

from bakeoff.config import ROOT, SAMPLE
from bakeoff import sandbox
from bakeoff.sandbox_check import run_checks

mac_only = pytest.mark.skipif(
    sys.platform != "darwin" or not sandbox.SANDBOX_EXEC.is_file(),
    reason="Real isolation checks require macOS sandbox-exec",
)


@pytest.fixture
def assignment(tmp_path):
    path = tmp_path.resolve() / "assignment"
    shutil.copytree(SAMPLE, path, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return path


@mac_only
def test_os_boundaries_with_inherited_fake_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-secret-never-sent-to-openai")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "another-fake-secret")
    monkeypatch.setenv("SANDBOX_TEST_SECRET", "fake-sentinel")
    checks = run_checks()
    assert len(checks) == 15
    assert all(checks.values()), checks


@mac_only
def test_only_named_files_are_copied_and_workspace_is_removed(assignment):
    (assignment / ".env").write_text("fake-private-value")
    (assignment / "conftest.py").write_text("raise RuntimeError('must not load')")
    (assignment / "pytest.ini").write_text("[pytest]\naddopts = --collect-only")
    (assignment / ".git").mkdir()
    with sandbox.prepared_workspace("print('ok')", assignment) as workspace:
        copied = {str(p.relative_to(workspace / "source"))
                  for p in (workspace / "source").rglob("*") if p.is_file()}
        assert copied == set(sandbox.COPY_FILES)
    assert not workspace.exists()


@mac_only
def test_symlink_assignment_is_rejected(assignment):
    target = assignment / "money.py"
    target.unlink()
    target.symlink_to(SAMPLE / "money.py")
    with pytest.raises(ValueError, match="symlink"):
        sandbox.run_python("print('must not run')", source=assignment)


@mac_only
def test_hardlinked_assignment_is_rejected(assignment):
    (assignment / "money.py").unlink()
    (assignment / "money.py").hardlink_to(SAMPLE / "money.py")
    try:
        with pytest.raises(ValueError, match="unlinked"):
            sandbox.run_python("print('must not run')", source=assignment)
    finally:
        (assignment / "money.py").unlink()


@mac_only
def test_practice_uses_snapshot_and_does_not_load_extra_config(assignment):
    (assignment / "conftest.py").write_text("raise RuntimeError('unexpected plugin')")
    (assignment / "pytest.ini").write_text("[pytest]\naddopts = --collect-only")
    original = (assignment / "money.py").read_bytes()
    result = sandbox.run_python(sandbox.VISIBLE_TEST_PROGRAM, source=assignment)
    assert result.status == "failed" and result.returncode == 1
    assert "4 failed" in result.output
    assert "NotImplementedError" in result.output
    assert "Cannot read termcap" not in result.output
    assert "unexpected plugin" not in result.output
    assert (assignment / "money.py").read_bytes() == original


@mac_only
def test_crashed_program_is_not_success_and_leaves_no_workspace():
    parent = ROOT / "workdir" / "sandboxes"
    before = set(parent.glob("run-*"))
    result = sandbox.run_python("raise RuntimeError('intentional probe failure')")
    assert result.status == "failed" and result.returncode != 0
    assert set(parent.glob("run-*")) == before


@mac_only
def test_timeout_still_works_after_program_closes_output():
    result = sandbox.run_python(
        "import os,time; os.close(1); os.close(2); time.sleep(60)", timeout=0.3)
    assert result.status == "timeout"
    assert result.seconds < 5


@mac_only
def test_cpu_limit_stops_a_busy_loop():
    result = sandbox.run_python("while True: pass", timeout=8)
    assert result.status == "failed"
    assert result.returncode < 0
    assert result.seconds < 8


@mac_only
def test_file_size_limit_stops_large_scratch_file():
    result = sandbox.run_python("open('too-large', 'wb').write(b'x' * (2 * 1024 * 1024))")
    assert result.status == "failed"
    assert "File too large" in result.output


def test_missing_backend_never_falls_back_to_host_execution(monkeypatch):
    monkeypatch.setattr(sandbox, "SANDBOX_EXEC", Path("/nonexistent/sandbox-exec"))
    process = Mock()
    monkeypatch.setattr(sandbox.subprocess, "Popen", process)
    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.run_python("print('must not run')")
    process.assert_not_called()


@pytest.mark.parametrize("timeout", [0, -1, 31, float("inf"), float("nan")])
def test_invalid_deadlines_are_rejected(timeout):
    with pytest.raises(ValueError, match="Timeout"):
        sandbox.run_python("print('must not run')", timeout=timeout)
