"""Step 5: five independent worktrees and concurrent GPT loops, without judging."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import threading
import time

from openai import OpenAI

from .agent import run_agent
from .tasks import MONEY, get_task
from .budget import RaceBudget
from .config import LANES, MAX_ROUNDS
from .credentials import load_credentials
from .repo import git, prepare_race, record_candidate
from .sandbox_check import run_checks


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def peak_requests(reports) -> int:
    events = []
    for report in reports:
        for request in report.get("requests", []):
            if "ended_seconds" in request:
                events.extend([(request["started_seconds"], 1), (request["ended_seconds"], -1)])
    active = peak = 0
    for _, change in sorted(events):
        active += change
        peak = max(active, peak)
    return peak


def execute_race(race: Path, baseline: str, api_key: str, *, client_factory=OpenAI,
                 runner=run_agent, budget=None, task=MONEY) -> dict:
    budget = budget or RaceBudget()
    start = time.monotonic()
    stop = threading.Event()
    print_lock = threading.Lock()

    def log(lane, message):
        with print_lock:
            print(f"[{lane.name} +{time.monotonic() - start:6.1f}s] {message}", flush=True)

    def worker(lane):
        folder = race / "lanes" / lane.name
        began = time.monotonic() - start
        report = None
        log(lane, f"Starting {lane.model} in its own worktree.")
        try:
            with client_factory(api_key=api_key, base_url="https://api.openai.com/v1",
                                timeout=45.0, max_retries=0) as client:
                report = runner(client, folder, lane=lane, budget=budget, stop_event=stop,
                                clock_start=start, log=lambda message: log(lane, message), task=task)
            report["candidate_commit"] = record_candidate(folder, report, baseline, task=task)
            report["commit_verified"] = True
        except Exception as error:
            # Contain one lane's failure. Never echo provider bodies or credentials.
            if report is None and (folder / "report.json").is_file():
                report = json.loads((folder / "report.json").read_text())
            report = report or {"lane": lane.name, "model": lane.model, "drafts": [],
                                "input_tokens": 0, "output_tokens": 0, "usage_complete": False}
            report["agent_status"] = report.get("status", "not_started")
            report["status"] = "lane_error"
            report["error_type"] = type(error).__name__
            report["commit_verified"] = False
        report.update(baseline_commit=baseline, branch=f"codex/{lane.name}",
                      started_seconds=began, ended_seconds=time.monotonic() - start)
        save_json(folder / "report.json", report)
        log(lane, f"Finished: {report['status']}; commit verified: {report['commit_verified']}.")
        return report

    executor = ThreadPoolExecutor(max_workers=len(LANES), thread_name_prefix="gpt-lane")
    futures = {executor.submit(worker, lane): lane for lane in LANES}
    results = {}
    interrupted = False
    try:
        for future in as_completed(futures):
            lane = futures[future]
            try:
                results[lane.name] = future.result()
            except Exception as error:
                results[lane.name] = {"lane": lane.name, "model": lane.model, "status": "lane_error",
                                      "error_type": type(error).__name__, "commit_verified": False,
                                      "usage_complete": False}
    except KeyboardInterrupt:
        interrupted = True
        stop.set()
        print("\nStopping: in-flight requests finish or time out; no new rounds will start.", flush=True)
        for future in futures:
            future.cancel()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    for future, lane in futures.items():
        if lane.name not in results:
            if future.cancelled():
                results[lane.name] = {"lane": lane.name, "model": lane.model, "status": "cancelled"}
            else:
                try:
                    results[lane.name] = future.result()
                except Exception:
                    results[lane.name] = {"lane": lane.name, "model": lane.model, "status": "lane_error",
                                          "usage_complete": False}
    reports = [results[lane.name] for lane in LANES]
    summary = {
        "task": task.name, "stage": 5, "interrupted": interrupted, "baseline_commit": baseline,
        "seconds": time.monotonic() - start, "lanes": reports,
        "peak_inflight_requests": peak_requests(reports),
        "input_tokens": sum(r.get("input_tokens", 0) for r in reports),
        "output_tokens": sum(r.get("output_tokens", 0) for r in reports),
        "usage_complete": all(r.get("usage_complete", False) for r in reports),
        "budget": budget.snapshot(), "hidden_tests_run": False, "winner": None,
        "main_unchanged": git(race / "repo", "rev-parse", "main").strip() == baseline,
    }
    save_json(race / "race.json", summary)
    lines = ["# Five GPT lane results", "", "Practice results only. No hidden judge or winner yet.", "",
             "| Lane | Model | Practice | Status | Commit |", "| --- | --- | --- | --- | --- |"]
    for report in reports:
        last = report.get("drafts", [])[-1:] or [{}]
        feedback = last[0].get("practice") or {}
        score = f"{feedback.get('passed', '?')}/4"
        lines.append(f"| {report['lane']} | {report['model']} | {score} | {report['status']} | "
                     f"{report.get('candidate_commit', 'not recorded')[:12]} |")
    lines.extend(["", f"Peak simultaneous in-flight requests: {summary['peak_inflight_requests']}.",
                  f"Reported usage: {summary['input_tokens']} input and {summary['output_tokens']} output tokens.",
                  f"Estimated standard-rate cost accounting: ${summary['budget']['accounted_estimated_usd']}.",
                  "This estimate is not the provider's bill; unknown requests retain their reservations.",
                  "", "Worktrees, drafts, and reports are retained for Step 6."])
    (race / "SCOREBOARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def race_command(task_name="money") -> int:
    task = get_task(task_name)
    print("STEP 5: Five GPT models, five separate desks, one shared assignment.", flush=True)
    try:
        credentials = load_credentials()
        print("Verifying the sandbox before model requests...", flush=True)
        if not all(run_checks().values()):
            print("Sandbox checks failed. No model requests were made.")
            return 1
        folder, baseline = prepare_race(task=task)
        if task.name == "bookings":
            from .booking_judge import freeze_assessment
            freeze_assessment(folder, baseline)
        print(f"Race folder: {folder}")
        print(f"All branches start from {baseline[:12]}.")
        print(git(folder / "repo", "worktree", "list"), end="")
        print(f"Starting five lanes: up to {MAX_ROUNDS} calls each, 20 total; "
              "$2 shared estimated-cost reservation guard. API usage is billable.", flush=True)
        result = execute_race(folder, baseline, credentials.key, task=task)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Race setup or reporting failed ({type(error).__name__}). Existing artifacts are retained.")
        return 1
    print("\n" + (folder / "SCOREBOARD.md").read_text())
    print(f"Detailed record: {folder / 'race.json'}")
    print("The starting main branch is unchanged. Hidden judging is Step 6.")
    return 0 if all(r.get("status") == "submitted_practice_passed" and r.get("commit_verified")
                    for r in result["lanes"]) and result["main_unchanged"] else 1
