"""A small command menu for the current learning milestone."""

import argparse
import importlib.util
import shutil
import sys

from .config import LANES, MAX_OUTPUT_TOKENS, MAX_ROUNDS


def lesson() -> int:
    print("STEP 1: Write the assignment before inviting the contestants.\n")
    print("1. Read sample/SPEC.md. It defines a correct answer.")
    print("2. Open sample/money.py. This is the unfinished answer sheet.")
    print("3. Read sample/tests/test_visible.py. These are four practice checks.")
    print("4. Run: .venv/bin/python -m bakeoff practice")
    print("   Four failures are expected: the answer is not implemented yet.\n")
    print("Example: 'INR 99.50' goes in; 9950 paise should come out.")
    print("Question: what should '0.29' produce? Answer: 29 paise.\n")
    print("Step 2 is available: .venv/bin/python -m bakeoff connect")
    print("No OpenAI requests or charges occur in this learning step.")
    return 0


def models() -> int:
    print("Planned lanes (account access not verified):\n")
    for lane in LANES:
        print(f"  {lane.name:<8} {lane.model:<18} reasoning={lane.reasoning_effort}")
    print(f"\nInitial limits: {MAX_ROUNDS} calls per lane, "
          f"{MAX_OUTPUT_TOKENS} output tokens per call.")
    print("All five solve the whole assignment. No API calls were made.")
    return 0


def doctor() -> int:
    from .credentials import load_credentials

    try:
        credentials = load_credentials()
        configured = True
        source = credentials.source
    except ValueError:
        configured = False
        source = "not configured"
    checks = {
        "Python 3.12 or newer": sys.version_info >= (3, 12),
        "Git installed": shutil.which("git") is not None,
        "pytest installed": importlib.util.find_spec("pytest") is not None,
        "OpenAI client installed": importlib.util.find_spec("openai") is not None,
        "Five distinct GPT models": len(LANES) == len({x.model for x in LANES}) == 5,
        "OpenAI key present locally": configured,
    }
    for label, passed in checks.items():
        print(f"{'READY' if passed else 'TODO ':5}  {label}")
    print(f"\nKey source: {source}.")
    print("\nKey values are never displayed. This does not verify authentication,")
    print("billing, or model access. No network requests were made.")
    if not configured:
        print("\nRun doctor in the terminal where OPENAI_API_KEY was exported,")
        print("or set it in a local .env file. Step 1 works without a key.")
    return 0 if all(checks.values()) else 1


def practice() -> int:
    from .sandbox import SandboxUnavailable, VISIBLE_TEST_PROGRAM, run_python

    print("Checking the unfinished answer sheet.", flush=True)
    print("Expected today: 4 failures because parse_inr is not implemented.\n", flush=True)
    try:
        result = run_python(VISIBLE_TEST_PROGRAM)
    except (SandboxUnavailable, ValueError, OSError) as error:
        print(f"Practice was not run: {error}")
        return 1
    print(result.output, end="")
    print(f"\nRestricted process: {result.status}; exit code {result.returncode}.")
    print("This is practice feedback, not a trusted final judge score.")
    return 0 if result.status == "finished" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("lesson", "models", "doctor", "practice", "connect", "sandbox-check", "agent", "race", "judge", "keep"))
    parser.add_argument("--race", help="Saved race folder to judge; required for judge")
    parser.add_argument("--judge", help="Exact judge.json record for keep")
    parser.add_argument("--lane", help="Reviewed winning lane for keep")
    parser.add_argument("--destination", help="New solution folder for keep; defaults to solution")
    args = parser.parse_args()
    if args.command == "keep":
        from .selection import keep_command
        return keep_command(args.race, args.judge, args.lane, args.destination)
    if args.command == "judge":
        from .judge import judge_command
        return judge_command(args.race)
    if args.command == "connect":
        from .connection import connect
        return connect()
    if args.command == "sandbox-check":
        from .sandbox_check import sandbox_check
        return sandbox_check()
    if args.command == "agent":
        from .agent import agent
        return agent()
    if args.command == "race":
        from .race import race_command
        return race_command()
    commands = {"lesson": lesson, "models": models, "doctor": doctor, "practice": practice}
    return commands[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
