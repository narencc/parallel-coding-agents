"""Exercise real OS restrictions using harmless probes and fake private files."""

import json
from pathlib import Path
import tempfile

from .config import ROOT
from .sandbox import MAX_OUTPUT_BYTES, SandboxUnavailable, run_python


def boundary_probe(outside: Path) -> str:
    return '''
import errno
import json
import os
from pathlib import Path
import socket
import subprocess

outside = Path(OUTSIDE_PATH)
source = Path(__file__).parent / "source"
checks = {}

def denied(action):
    try:
        action()
    except OSError as error:
        return error.errno in (errno.EPERM, errno.EACCES)
    return False

checks["read assignment"] = "parse_inr" in (source / "money.py").read_text()
scratch = Path("scratch-note.txt")
scratch.write_text("temporary work")
checks["use scratch folder"] = scratch.read_text() == "temporary work"
checks["no inherited secrets"] = not any(
    key in os.environ for key in ("OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "SANDBOX_TEST_SECRET")
)
for name in ("private.env", "hidden-answer.txt", "other-lane.py", "git-config"):
    checks["block read " + name] = denied(lambda name=name: (outside / name).read_bytes())
checks["block outside writes"] = denied(lambda: (outside / "must-not-exist").write_text("no"))
checks["protect assignment snapshot"] = denied(lambda: (source / "money.py").write_text("no"))

# A path inside the writable folder must not bypass the outside-file policy.
link = Path("private-link")
link.symlink_to(outside / "private.env")
checks["block symlink escape"] = denied(link.read_bytes)

def network():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(0.2)
        client.connect(("127.0.0.1", 9))
checks["block network"] = denied(network)
checks["block child processes"] = denied(
    lambda: subprocess.run(["/bin/sh", "-c", "exit 0"], check=True)
)
print(json.dumps(checks, sort_keys=True))
'''.replace("OUTSIDE_PATH", repr(str(outside)))


def run_checks() -> dict[str, bool]:
    parent = ROOT / "workdir"
    if parent.is_symlink():
        raise ValueError("Workdir must not be a symlink.")
    parent.mkdir(exist_ok=True)
    checks = {}
    with tempfile.TemporaryDirectory(prefix="boundary-probes-", dir=parent) as folder:
        outside = Path(folder).resolve()
        originals = {name: b"fake private data for isolation testing only" for name in (
            "private.env", "hidden-answer.txt", "other-lane.py", "git-config")}
        for name, content in originals.items():
            (outside / name).write_bytes(content)
        result = run_python(boundary_probe(outside))
        if result.status != "finished":
            raise SandboxUnavailable(
                f"Sandbox probe could not finish (exit {result.returncode}). "
                "Do not run candidate code on this configuration."
            )
        try:
            observed = json.loads(result.output)
        except json.JSONDecodeError:
            raise SandboxUnavailable("Sandbox probe returned an invalid report.") from None
        expected = {
            "read assignment", "use scratch folder", "no inherited secrets",
            "block read private.env", "block read hidden-answer.txt", "block read other-lane.py",
            "block read git-config", "block outside writes", "protect assignment snapshot",
            "block symlink escape", "block network", "block child processes",
        }
        if not isinstance(observed, dict) or set(observed) != expected:
            raise SandboxUnavailable("Sandbox probe returned an incomplete report.")
        checks.update({name: value is True for name, value in observed.items()})
        checks["outside files unchanged"] = all(
            (outside / name).read_bytes() == original for name, original in originals.items()
        ) and not (outside / "must-not-exist").exists()
    timeout = run_python("import time; time.sleep(60)", timeout=0.5)
    checks["stop timed-out code"] = timeout.status == "timeout"
    noisy = run_python("import os\nwhile True: os.write(1, b'x' * 8192)")
    checks["stop excessive output"] = noisy.status == "output_limit" and len(noisy.output) <= MAX_OUTPUT_BYTES
    return checks


def sandbox_check() -> int:
    print("STEP 3: Test the locked practice room. No API requests are made.", flush=True)
    print("Private-file probes use dummy files, not your real API key.", flush=True)
    try:
        checks = run_checks()
    except (SandboxUnavailable, OSError, ValueError) as error:
        print(f"NOT READY: {error}")
        return 1
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if all(checks.values()):
        print(f"\nREADY: all {len(checks)} isolation checks passed on this Mac.")
        print("Temporary workspaces were removed. This is a local sandbox, not a VM.")
        return 0
    print("\nNOT READY: at least one boundary failed. Do not run candidate code.")
    return 1
