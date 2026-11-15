"""A separate teaching repository per race; never stages the user's outer repo."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .config import LANES, ROOT, SAMPLE
from .sandbox import prepared_workspace


def git(cwd: Path, *args: str) -> str:
    # Ignore inherited Git redirection/configuration and disable external hooks.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_") and key != "OPENAI_API_KEY"}
    env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
         "-c", "commit.gpgsign=false", "-c", "core.attributesFile=/dev/null", *args],
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(f"Git {args[0]} failed with exit code {result.returncode}.")
    return result.stdout.decode("utf-8")


def prepare_race(parent: Path | None = None) -> tuple[Path, str]:
    parent = parent or ROOT / "workdir" / "races"
    if any(path.is_symlink() for path in (parent, *parent.parents)):
        raise ValueError("Race directory must not have symlink parents.")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    race = Path(tempfile.mkdtemp(prefix=f"race-{stamp}-", dir=parent)).resolve()
    with prepared_workspace("", SAMPLE) as snapshot:
        shutil.copytree(snapshot / "source", race / "repo")
    repository = race / "repo"
    (repository / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
    git(repository, "init", "-q", "-b", "main")
    git(repository, "config", "user.name", "bakeoff learning project")
    git(repository, "config", "user.email", "bakeoff@localhost")
    git(repository, "add", "--", "money.py", "SPEC.md", "tests/test_visible.py", ".gitignore")
    git(repository, "commit", "-q", "-m", "Starting assignment for all five lanes")
    start = git(repository, "rev-parse", "HEAD").strip()
    for lane in LANES:
        folder = race / "lanes" / lane.name
        folder.mkdir(parents=True)
        (folder / "drafts").mkdir()
        git(repository, "worktree", "add", "-q", "-b", f"codex/{lane.name}",
            str(folder / "candidate"), start)
    return race, start


def record_candidate(folder: Path, report: dict, baseline: str) -> str:
    candidate = folder / "candidate"
    content = (candidate / "money.py").read_bytes()
    if hashlib.sha256(content).hexdigest() != report.get("candidate_sha256"):
        raise RuntimeError("Candidate changed after the agent finished.")
    if not report.get("protected_files_unchanged"):
        raise RuntimeError("Protected assignment files changed.")
    changed = set(git(candidate, "diff", "--name-only", baseline).splitlines())
    untracked = git(candidate, "ls-files", "--others", "--exclude-standard").splitlines()
    if changed - {"money.py"} or untracked:
        raise RuntimeError("Unexpected files changed in candidate worktree.")
    git(candidate, "add", "--", "money.py")
    if git(candidate, "diff", "--cached", "--name-only").strip():
        git(candidate, "commit", "-q", "-m", f"Record {report['lane']} candidate: {report['status']}")
    commit = git(candidate, "rev-parse", "HEAD").strip()
    recorded = git(candidate, "show", f"{commit}:money.py").encode("utf-8")
    if hashlib.sha256(recorded).hexdigest() != report["candidate_sha256"]:
        raise RuntimeError("Recorded commit differs from the tested candidate.")
    if git(candidate, "status", "--porcelain").strip():
        raise RuntimeError("Worktree is not clean after commit.")
    return commit
