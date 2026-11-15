"""Trusted entry point copied into each workspace; runs before candidate code."""

import os
from pathlib import Path
import resource
import runpy
import sys

# Hard limits cannot be raised again by candidate code running as this user.
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

workspace = Path(__file__).resolve().parent
os.chdir(workspace / "scratch")
# -I -S skips Python startup customization. Add only our trusted packages and
# the candidate snapshot; never add the host project, home, or current directory.
sys.path.append(sys.argv[1])
sys.path.append(str(workspace / "source"))
runpy.run_path(str(workspace / "program.py"), run_name="__main__")
