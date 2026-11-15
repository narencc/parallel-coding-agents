"""macOS learning sandbox: deny by default, copy allowed files, bound execution.

This is a local process sandbox, not a VM or a hardened hostile-code service.
There is deliberately no unsandboxed fallback on unsupported systems.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import sysconfig
import tempfile
import time

from .config import ROOT, SAMPLE, TEST_TIMEOUT_SECONDS

SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")
COPY_FILES = ("SPEC.md", "money.py", "tests/test_visible.py")
MAX_SOURCE_BYTES = 128 * 1024
MAX_OUTPUT_BYTES = 64 * 1024


class SandboxUnavailable(RuntimeError):
    """The requested isolation cannot be enforced; do not run code."""


@dataclass(frozen=True)
class SandboxResult:
    status: str
    returncode: int
    output: str
    seconds: float


def require_backend() -> None:
    if sys.platform != "darwin" or not SANDBOX_EXEC.is_file():
        raise SandboxUnavailable("This step requires macOS sandbox-exec. Code was not run.")


def _quote(path: Path | str) -> str:
    return json.dumps(str(path), ensure_ascii=True)


def make_profile(workspace: Path) -> str:
    """No host project read, no network, no fork, no shell, no arbitrary writes."""
    python = Path(sys.executable).resolve()
    runtime = Path(sys.base_prefix).resolve()
    packages = Path(sysconfig.get_path("purelib")).resolve()
    read_dirs = (runtime, packages, workspace, Path("/System/Library"),
                 Path("/usr/lib"), Path("/usr/share/terminfo"))
    reads = " ".join(f"(subpath {_quote(p)})" for p in read_dirs)
    return "\n".join([
        "(version 1)",
        "(deny default)",
        f"(allow process-exec (literal {_quote(python)}))",
        # The runtime needs to open the filesystem root. This literal does NOT
        # grant recursive access to /Users or to the rest of the filesystem.
        f'(allow file-read* (literal "/") (literal "/dev/null") '
        f'(literal "/dev/urandom") {reads})',
        f"(allow file-write* (subpath {_quote(workspace / 'scratch')}))",
        '(allow file-write-data (literal "/dev/null"))',
    ])


@contextmanager
def prepared_workspace(program: str, source: Path = SAMPLE):
    """Make a fresh snapshot. Symlinks and special files are not assignments."""
    require_backend()
    if len(program.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("Program exceeds the 128 KiB lesson limit.")
    parent = ROOT / "workdir" / "sandboxes"
    if any(p.is_symlink() for p in (ROOT / "workdir", parent)):
        raise ValueError("Workspace parent must not be a symlink.")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    workspace = Path(tempfile.mkdtemp(prefix="run-", dir=parent)).resolve()
    try:
        source = source.absolute()
        if source.is_symlink() or not source.is_dir():
            raise ValueError("Assignment source must be a real directory.")
        for relative in COPY_FILES:
            origin = source / relative
            if any(p.is_symlink() for p in (origin, *origin.parents)):
                raise ValueError(f"Refusing symlink in assignment: {relative}")
            # O_NOFOLLOW and fstat also reject final-component substitution.
            fd = os.open(origin, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError(f"Assignment must be a regular, unlinked file: {relative}")
                data = handle.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError(f"Assignment file is too large: {relative}")
            target = workspace / "source" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o400)
        (workspace / "scratch").mkdir(mode=0o700)
        (workspace / "program.py").write_text(program, encoding="utf-8")
        shutil.copyfile(Path(__file__).with_name("_sandbox_bootstrap.py"), workspace / "bootstrap.py")
        (workspace / "policy.sb").write_text(make_profile(workspace), encoding="utf-8")
        yield workspace
    finally:
        shutil.rmtree(workspace)


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def run_python(program: str, *, source: Path = SAMPLE,
               timeout: float = TEST_TIMEOUT_SECONDS) -> SandboxResult:
    """Execute only inside the sandbox. This result is NOT a trusted judge score."""
    if not math.isfinite(timeout) or not 0 < timeout <= TEST_TIMEOUT_SECONDS:
        raise ValueError(f"Timeout must be between 0 and {TEST_TIMEOUT_SECONDS} seconds.")
    with prepared_workspace(program, source) as workspace:
        # Allowlist environment variables instead of trying to remove every secret.
        env = {
            "PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8",
            "TERM": "dumb",
            "HOME": str(workspace / "scratch"), "TMPDIR": str(workspace / "scratch"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
        command = [str(SANDBOX_EXEC), "-f", str(workspace / "policy.sb"),
                   str(Path(sys.executable).resolve()), "-I", "-S", "-B", "-X", "utf8",
                   str(workspace / "bootstrap.py"), str(Path(sysconfig.get_path("purelib")).resolve())]
        started = time.monotonic()
        process = subprocess.Popen(command, cwd=workspace / "scratch", env=env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
        captured = bytearray()
        status = "finished"
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = timeout - (time.monotonic() - started)
                    if remaining <= 0:
                        status = "timeout"
                        break
                    for key, _ in selector.select(min(remaining, 0.1)):
                        chunk = os.read(key.fileobj.fileno(), 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        available = MAX_OUTPUT_BYTES - len(captured)
                        captured.extend(chunk[:available])
                        if len(chunk) > available:
                            status = "output_limit"
                            break
                    if status == "output_limit":
                        break
                if status == "finished":
                    try:
                        process.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
                    except subprocess.TimeoutExpired:
                        status = "timeout"
        finally:
            # Also reap the process on KeyboardInterrupt or an I/O failure.
            _kill_group(process)
            process.stdout.close()
        if status == "finished" and process.returncode != 0:
            status = "failed"
        return SandboxResult(status, process.returncode,
                             captured.decode("utf-8", errors="replace"), time.monotonic() - started)


VISIBLE_TEST_PROGRAM = '''
from pathlib import Path
import pytest
source = Path(__file__).parent / "source"
raise SystemExit(pytest.main([
    "-q", "--tb=short", "-c", "/dev/null", "--noconftest",
    "--rootdir", str(source), "--confcutdir", str(source),
    "--import-mode=importlib", "-p", "no:cacheprovider", str(source / "tests"),
]))
'''
