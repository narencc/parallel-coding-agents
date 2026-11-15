# Beginner guide: building the project step by step

[Back to the project introduction](../README.md) · [Explore the saved example](../examples/money-converter/README.md)

This is the detailed build history. Commands below run from the repository root.
Historical `workdir/` paths belong to the original local experiment and are not
required for the portable replay. See the introduction for fresh-clone instructions.

# Five GPT coding agents

We are building a system that asks five GPT models to solve the same coding task,
checks their answers, and keeps one qualifying answer. All seven learning steps
are now complete. The retained answer and detailed review are in [solution/](../solution/README.md).

## Step 1 is ready

The assignment is a money converter: `₹500` goes in and `50000` paise comes out.
The function is deliberately unfinished. Its tests **should fail** until an agent
fills it in. Step 1 makes no network requests and has no API charges.

Run these commands from the project folder:

```sh
.venv/bin/python -m bakeoff lesson
.venv/bin/python -m bakeoff models
.venv/bin/python -m bakeoff doctor
.venv/bin/python -m bakeoff practice
```

- `lesson` explains the first learning step.
- `models` displays the five lanes without contacting OpenAI.
- `doctor` checks local prerequisites and key presence, never the key value.
- `practice` runs four visible checks. Four failures are expected for the stub.

`.venv/bin/python` is the project's own Python installation. No activation is needed.

## Step 2 is ready: connect one GPT model

We have successfully connected **GPT-6 Luna**, the model assigned to lane-4.
Starting with that lane was a small first experiment. Step 5 below extends the
same loop to all five models.

### 1. Make the key available

Your `.env` file is a private settings file in the project folder. The program
reads `OPENAI_API_KEY` from that file and passes it to the OpenAI client. It does
not print the value or send it as part of the conversation. The key is used to
authenticate the request, like showing an access card at the entrance.

You do not need to restart the desktop app. Each invocation reads the settings
again. An already-exported `OPENAI_API_KEY` takes precedence over `.env`.
This makes the key available to **our Python project**, not globally to every
application on your computer.

```sh
.venv/bin/python -m bakeoff doctor
```

Look for `READY OpenAI key present locally` and `Key source: project .env file`.
This command is local and free. It checks presence, not whether OpenAI accepts the key.

### 2. Make the live connection

```sh
.venv/bin/python -m bakeoff connect
```

This command makes at most two billable Responses API requests to `gpt-6-luna`.
Each has a maximum of 1024 output tokens, including reasoning, and automatic
retries are disabled. It sends a short lesson prompt, not the project files,
hidden tests, or the contents of `.env`.

The first message asks the model to request one allowed action:
`connection_check` with the message `hello`.

### 3. Understand the tool request

The model responds with a structured request, not a program that runs by itself:

```json
{"name": "connection_check", "arguments": {"message": "hello"}}
```

Our Python program checks that both the name and arguments match what we allowed.
It then produces a simple acknowledgment. No generated code is executed and no
project file is edited by the model.

This separation matters: the model **requests** an action; the application
**decides whether and how to perform it**.

### 4. Return the result

The program sends the acknowledgment back to the model, linked to the original
tool call. It preserves the conversation context. The model then replies with a
short confirmation. That is one complete tool round trip.

Later, a coding agent will use a similar loop to request a file save, receive test
results, and revise its answer. Here we are learning that loop with a harmless action.

### 5. Read the outcome

The first successful check on November 15, 2026 reported:

| Request | Input tokens | Output tokens |
| --- | ---: | ---: |
| Ask for a tool request | 165 | 18 |
| Return the tool result | 214 | 13 |
| Total | 379 | 31 |

The model replied: “Success—the app received and handled the request.”
Your next run may use different numbers. `CONNECTED` means that this model
completed the full exchange. It does not mean all five lanes are running.

### If the check fails

| Message | Meaning and next action |
| --- | --- |
| Key missing or placeholder | Check `.env` or the exported environment value |
| Key rejected | Replace the key at the source shown by `doctor` |
| Model unavailable or permission denied | Check project model access; no substitute is chosen silently |
| Rate or quota limit | Check API billing and rate limits |
| Request timed out | Check the network; the command does not automatically retry |
| Response incomplete | The bounded check did not finish; do not count it as success |

Raw API errors and key values are not printed. A failed or timed-out request may
still consume usage, so check the API dashboard if needed.

## Step 3 is ready: a restricted practice room

The main app holds the key and talks to OpenAI. A separate restricted Python
process runs local code. That process receives no API key and has no network
permission. Think of the main app as the teacher and the restricted process as
a student working in a locked practice room.

This implementation uses macOS `sandbox-exec`, which is available on this Mac.
Docker is not installed. Apple's local manual marks `sandbox-exec` deprecated,
so this is a Mac-specific learning backend, not a long-term portable platform.
If it is unavailable or cannot enforce its policy, code does not run. There is
no fallback that quietly runs the code with normal access.

### 1. Prepare a fresh copy

Each execution gets a uniquely named folder under `workdir/sandboxes/`. We copy
only three files: `money.py`, `SPEC.md`, and `tests/test_visible.py`.

The private `.env`, Git metadata, hidden tests, other lanes, and extra pytest
configuration are not copied. Symlinks, hardlinked files, oversized inputs,
and special files are rejected rather than followed into other locations.

The snapshot is read-only during execution. Later, the coordinator will save a
candidate's requested edits, then create another snapshot for the next test run.
The candidate cannot rewrite the snapshot while its tests are running.

### 2. Apply the operating system rules

The policy starts with “deny everything” and adds specific permissions:

| Action | Allowed? |
| --- | --- |
| Read the copied assignment and visible tests | Yes |
| Read the Python runtime, installed packages, required system libraries, and terminal definitions | Yes, read-only |
| Create temporary files in this run's scratch folder | Yes |
| Read private project files or another lane | No |
| Change the copied assignment or host project | No |
| Open network connections, including loopback | No |
| Fork child processes or launch a shell | No |

The runtime also needs to open the filesystem root directory itself. That is a
literal directory permission, not permission to read everything underneath it.
Only the selected Python executable may be executed; it remains subject to the
same sandbox. The runner starts with closed extra file handles and no interactive
input.

### 3. Give the process a clean environment

Instead of passing the parent environment and trying to remove known secrets,
the runner builds a small list of allowed settings. `HOME` and `TMPDIR` point
to the scratch folder. `OPENAI_API_KEY` and other credentials are not included.

Python starts with user startup customization disabled. Pytest plugin discovery
and project configuration loading are disabled for practice runs. The installed
Python runtime and package directory remain trusted dependencies.

### 4. Bound the work

| Limit | What it prevents |
| --- | --- |
| 30 seconds of elapsed time | An indefinitely waiting process |
| 3 seconds of CPU time | A busy infinite loop |
| 64 KiB of captured output | Unbounded terminal output |
| 1 MiB per scratch file | A single very large temporary file |
| 64 open file descriptors | Excessive simultaneously open handles |
| No core dumps | Crash memory being written into a dump file |

CPU and file limits are set before the program starts. On timeout, excess output,
or interruption, the runner kills and reaps its process group. A nonzero exit,
timeout, or output-limit event is reported as unsuccessful, not as a passing run.
The temporary workspace is removed when the execution ends.

There is no hard total-memory or aggregate disk quota in this learning backend.
It shares your Mac's kernel and is not a VM. It has not been audited as a
hostile-code service. A production version should use a maintained isolation
backend with explicit memory and total-disk controls.

### 5. Test the boundaries

```sh
.venv/bin/python -m bakeoff sandbox-check
```

The command uses harmless probes and fake private files, never the real key.
It verifies allowed reads and scratch writes, denied private reads and outside
writes, denied network and child-process creation, a denied symlink escape,
secret-free environment, unchanged outside files, timeouts, and output limits.
All 15 checks passed on this Mac on November 15, 2026.

Additional project tests exercise CPU and file-size limits, cleanup after a crash,
timeout after output is closed, rejected symlink/hardlink inputs, and refusal to
execute when the sandbox backend is missing.

### 6. Run practice inside the room

```sh
.venv/bin/python -m bakeoff practice
```

This command now runs the four visible checks in the restricted process. The
unfinished assignment still produces four expected `NotImplementedError`
failures. That is evidence that pytest ran, not a failure of workspace setup.

The printed output is **practice feedback**, not a trusted judge verdict. Candidate
code can still affect pytest inside its own process or print misleading output.
The trusted final judge and exact-commit checks belong to a later step.

No model-generated code or paid API requests were used to build or verify Step 3.

## Step 4 is ready: one agent writes and improves its answer

The first live coding agent is GPT-6 Luna. It now has two available actions:
`write_code` and `submit`. The coordinator, which is our ordinary Python program,
decides what those requests are allowed to do.

```sh
.venv/bin/python -m bakeoff agent
```

This command uses API credits. It creates a new attempt each time; it does not
overwrite previous attempts or the original sample. It permits at most four
model requests, 4000 output tokens per request, and a 64 KiB serialized prompt,
tool-schema, and conversation payload check before each request. Automatic API
retries are disabled. These are usage limits, not a guaranteed dollar price.

### 1. Check the room and prepare the assignment

Before any paid request, the command checks the sandbox boundaries. It then
creates an attempt folder under `workdir/agents/` with its own candidate copy.
It runs the four practice tests on the initial stub so you can see the starting
point: zero passing tests.

The model receives the written specification, the unfinished `money.py`, and
the four visible tests. It does not receive the hidden tests, the API key, or
other attempts. Each model call has its own bounded response size.

### 2. Ask for the first draft

The model requests `write_code` with the complete file as a list of lines and
a short explanation. There is no path argument: it can only request a change
to this attempt's `money.py`. It cannot use that tool to edit the tests or the
specification.

The coordinator saves the draft, records a copy in `drafts/`, and creates a new
restricted snapshot for practice. The model's code is never imported or executed
by the main app. It only runs in the sandbox from Step 3.

### 3. Return practice feedback

The test runner records which four tests were collected and their setup, test,
and cleanup outcomes. The coordinator checks the expected test identities and
process status. Missing reports, zero tests, timeout, and a plain printed
“4 passed” line do not qualify as a complete practice run.

The model receives those results and the relevant failure output. That gives it
something concrete to correct instead of asking it to guess what went wrong.
This reporting is still inside the candidate's process; it is useful feedback,
not a tamper-proof final judge.

### 4. Review and revise

Even if all four examples pass, the model is asked to review its implementation
against the whole specification. If it finds a real issue, it calls `write_code`
again. The revised file gets a fresh sandbox run. The earlier draft remains
available so we can compare what changed.

The coordinator does not deliberately break the code to manufacture a revision.
Some runs may need several fixes, and some may produce a good first draft.

### 5. Submit the saved answer

The model calls `submit` with a short summary. Submission is refused unless the
latest saved draft has complete passing practice feedback. A previous passing
draft cannot certify a newly saved or externally changed file.

The coordinator records the file's SHA-256 hash, a fingerprint of its contents,
along with the results and usage. It checks that the specification and visible
tests were not changed. Nothing is merged into the main project at this step.

### What our first live run did

On November 15, 2026, the agent used three model requests:

| Stage | Practice results | What happened |
| --- | --- | --- |
| Starting stub | 0 of 4 | No implementation yet |
| First draft | 4 of 4 | Wrote a complete parser |
| Revised draft | 4 of 4 | Fixed spaces before suffixes such as lakh |
| Submission | Latest draft retained | Summarized the completed implementation |

The four practice tests did not expose the suffix-spacing mistake. Luna found it
while reviewing the written rules. After submission, we demonstrated the exact
change with the specification example `1.2 lakh`, running both drafts inside
the sandbox:

| Version | Observed output |
| --- | --- |
| First draft | `ValueError`: rejected an allowed input |
| Revised draft | `12000000`: the correct number of paise |

This is why the written rules matter even when the visible test score is perfect.
No hidden assessment tests were run or sent to the model.

The run reported **5615 input tokens and 1608 output tokens**. Future runs may
produce different code, revisions, and usage. A timeout can leave usage unknown;
the report marks that rather than assuming the failed request was free.

### Inspect the attempt

The command prints its full attempt-folder path. Our first run is stored at
`workdir/agents/luna-20261115T154224Z-6ysiev1q/`. The timestamp in that folder name
is UTC, indicated by `Z`.

| File inside the attempt | What you can learn from it |
| --- | --- |
| `candidate/money.py` | The final submitted code |
| `drafts/draft-01.py` | The first implementation |
| `drafts/draft-02.py` | The revised implementation |
| `report.json` | Practice feedback, explanations, usage, file fingerprint, and stopping reason |
| `improvement-example.json` | The observed before-and-after result for the spacing fix |

The example comparison file was added after the first run for this lesson;
ordinary subsequent runs save the candidate, drafts, and report automatically.
Attempt folders are local and ignored by Git. Encrypted reasoning context stays
in the running conversation and is not written into the learning report.

The final status `submitted_practice_passed` means “the agent submitted a draft
with passing practice feedback.” It does not mean “passed the hidden judge” or
“proven correct for every input.” Five-way competition comes in the next step.

## The files in plain English

| File | Purpose |
| --- | --- |
| `sample/SPEC.md` | The assignment and its exact rules |
| `sample/money.py` | The unfinished answer sheet |
| `sample/tests/test_visible.py` | Four practice questions the agents will see |
| `hidden_tests/test_hidden.py` | Additional assessment cases omitted from future prompts |
| `bakeoff/config.py` | Which model belongs to each lane and its initial limits |
| `bakeoff/__main__.py` | The command menu |
| `bakeoff/credentials.py` | Reads the key privately from the environment or `.env` |
| `bakeoff/connection.py` | Makes the two-request connection check |
| `tests/test_connection.py` | Checks the connection machinery offline, without API calls |
| `bakeoff/sandbox.py` | Creates a snapshot and runs Python under OS restrictions |
| `bakeoff/_sandbox_bootstrap.py` | Applies resource limits before the program runs |
| `bakeoff/sandbox_check.py` | Tries harmless boundary probes and reports the results |
| `tests/test_sandbox.py` | Tests real isolation, limits, cleanup, and refusal paths |
| `bakeoff/agent.py` | Runs one GPT agent and records each draft and its feedback |
| `bakeoff/practice.py` | Collects structured practice results inside the sandbox |
| `tests/test_agent.py` | Checks revision, submission, limits, and incomplete-result handling offline |

Keeping hidden tests out of prompts alone is not a security boundary. The Step 3
sandbox additionally denies the restricted process access to the host project
and does not copy hidden tests. Step 6 now compares candidate outputs in the trusted host program.

## The five lanes

| Lane | Model ID |
| --- | --- |
| lane-1 | `gpt-6-astra` |
| lane-2 | `gpt-6.1-sol` |
| lane-3 | `gpt-6.1-terra` |
| lane-4 | `gpt-6-luna` |
| lane-5 | `gpt-6-sol` |

Each model attempts the entire assignment independently through the Responses API,
with low reasoning effort and no explicit temperature. The `race` command starts
all five lanes concurrently; each has its own client and conversation.

## Step 5: five models working at the same time

Imagine five students receiving the same worksheet. Each has a separate desk,
writes their own answer, checks it, and hands it in. Our coordinator is the
teacher who hands out worksheets and collects answers.

### 1. Make one starting version

The app creates a small, separate Git repository under `workdir/races/`.
Git is a tool that saves named versions of files. A **commit** is one saved
version, identified by a long fingerprint. The first commit contains the same
unfinished function, instructions, and four practice tests for everyone.
Your outer project repository is not staged or committed by this command.

### 2. Give every model a separate desk

A **branch** is a separate line of saved changes. A **worktree** is a folder
where one branch's files are available to edit. We create five branches,
`codex/lane-1` through `codex/lane-5`, and five candidate folders.
All start at exactly the same commit. Editing one candidate does not edit the
others. The coordinator allows the model to replace only `money.py`.

These worktrees belong to the small repository inside that run's `repo` folder.
They do not appear as branches of the outer project repository. Each new race
gets a fresh repository, so previous attempts remain available to inspect.

### 3. Start five independent conversations

The coordinator starts five workers. A worker is a small part of our Python
program that manages one lane. Each sends requests to its assigned GPT model.
While one request waits for OpenAI, the others can be in progress too. This is
**concurrency**. We record the start and end of requests to check actual overlap.

Each model sees the assignment and its own feedback. It does not see another
model's answers. All five solve the whole task; they do not split it into pieces.

### 4. Reuse the write, test, review loop

For each lane, the app first checks that the starting function fails the four
practice tests. The model then calls `write_code` with its proposed file contents.
The app saves that draft and tests a fresh copy in the restricted workspace.
The model receives the results and can revise or call `submit`.

A worktree keeps files organized; it is not a security boundary. The macOS
sandbox from Step 3 provides the execution restrictions. Only the three allowed
assignment files enter the test snapshot. The API key, Git metadata, hidden
tests, and other candidates do not enter it. Existing sandbox limitations still
apply; this is a local learning setup, not a hostile-code hosting service.

### 5. Bound the experiment

Each model gets at most four API requests, with at most 4,000 output tokens per
request. There are at most 20 requests across the race and no automatic retries.
A shared estimate reserves room for each request against a $2 planning limit.
Requests from all lanes use the same locked counter, so simultaneous workers
cannot accidentally reserve the same remaining allowance.

This is **not a guaranteed $2 billing cap**. Token estimates and standard rates
are estimates, and your OpenAI usage dashboard is the billing reference. Missing
usage keeps its full reservation instead of being treated as free. The program
reads the key once and keeps it in the trusted coordinator. A failed lane is
reported separately while the other lanes can finish.

### 6. Save the evidence

After a lane finishes, the coordinator checks the file fingerprint and verifies
that protected files have not changed. It commits that candidate on its branch,
then verifies that the commit contains the same file. A commit is a saved answer,
not proof that the answer is correct.

Every run keeps these files:

| File or folder inside the run | Meaning |
| --- | --- |
| `repo/` | Shared Git history and the unchanged starting branch |
| `lanes/lane-N/candidate/` | That model's worktree and final code |
| `lanes/lane-N/drafts/` | Every draft the model wrote |
| `lanes/lane-N/report.json` | Test feedback, timing, token usage, and commit |
| `race.json` | Combined machine-readable record for all five lanes |
| `SCOREBOARD.md` | Short human-readable results table |

### 7. Run it yourself

From the project folder:

```sh
.venv/bin/python -m bakeoff race
```

This makes a **new paid run**. Reading an existing scoreboard is free. The command
first runs the sandbox checks and refuses to contact models if those checks fail.
The printed prefix, such as `[lane-4 +6.5s]`, tells you which model is speaking
and how many seconds have elapsed since the race started.

Passing four practice tests does not establish full correctness. Step 6 below
judges saved candidates with tests the models have not seen. Step 5 selects no
winner and merges no answer into the original sample.

### Our first real five-model run

Completed November 15, 2026 in **22.34 seconds**, with **five requests in flight
at once**. All five model IDs were accepted by the API and submitted candidates.

| Model | Requests | Drafts | Final practice result |
| --- | ---: | ---: | --- |
| GPT-6 Astra | 2 | 1 | 4/4 passed |
| GPT-6.1 Sol | 2 | 1 | 4/4 passed |
| GPT-6.1 Terra | 3 | 2 | 4/4 passed |
| GPT-6 Luna | 4 | 3 | 4/4 passed |
| GPT-6 Sol | 2 | 1 | 4/4 passed |

Terra's first draft contained a Python syntax error: it wrote
`for pos in range 0, len(digits), 9:`. Python could not read this instruction,
so the tests could not even start. The feedback reported zero passing tests.
Terra corrected the syntax in its second draft, then passed all four tests and
submitted. This demonstrates why the app must execute checks rather than trust
a model's claim that its code works.

The run used **13 requests**, **24,537 input tokens**, and **6,219 output tokens**.
Standard-rate estimated cost was **$0.1153683** (about 12 US cents); actual billing
is available in the OpenAI dashboard. No request usage was missing.

All five saved commits were verified against their candidate files. The starting
branch and original sample stayed unchanged. Hidden tests were not run and no
winner was selected. The project's **39 offline tests passed** before this run,
including overlap, independent worktrees, lane failure containment, and budget
reservation checks.

Read the retained [scoreboard](../examples/money-converter/README.md)
and [detailed run record](../examples/money-converter/run.json).
The links above now point to the portable example included in this repository.
Historical commands using `workdir/races/...` refer to the author’s local run; on
a fresh clone use `python3 -m bakeoff replay` or `.venv/bin/python -m bakeoff recheck`.

## Step 6: mark the five saved answers

All five candidates passed **40 hidden checks and four practice checks** in our
first judging run on November 15, 2026. This step made **zero OpenAI API calls**.
It used the answers already saved in Step 5.

### 1. Choose the exact race

The judge requires an explicit race folder. It does not guess which run you mean.
It reads that run's `race.json`, which identifies the five models, their saved
commits, and the common starting version. A **commit** is Git's saved version of
an answer. A **fingerprint** is a calculated identifier for the file's contents.

### 2. Check the saved answer before marking it

For each candidate, the judge checks that it was submitted, that its commit
comes directly from the common starting version, and that only `money.py` changed.
It then reads `money.py` from the commit and compares its fingerprint with the
race record. A mismatch rejects the candidate before its tests run.

This matters because a working folder is editable. Someone could change a file
after the race. The judge marks the saved version, not whatever happens to be in
the model's folder today. It never imports candidate code into the main program.

### 3. Prepare the marking sheet

The hidden test file contains **19 valid inputs and 21 invalid inputs**. For valid
inputs, the answer must be the exact integer number of paise. For invalid inputs,
the function must raise `ValueError`, Python's way of saying the input is invalid.

Examples include Indian comma grouping, lakh and crore suffixes, negative
amounts, very large exact amounts, malformed commas, and fractional paise.
The four practice examples are checked again too, making **44 checks per answer**.

The judge reads the literal case data from `hidden_tests/test_hidden.py` without
importing that module. It implements its two assertions outside the sandbox:
exact integer equality for valid inputs, and `ValueError` for invalid inputs.
The four practice inputs are also represented explicitly in the judge. If we
change the test structure or add other kinds of assertions later, we must update
this adapter and its tests too. The report records fingerprints of the hidden
file and full case list so we can identify what was used.

### 4. Ask one question in a fresh restricted process

Each case gets a fresh sandbox snapshot of the saved candidate. The process
receives one input and returns a small structured answer. It does not receive
the expected answer, the hidden test file, or the other hidden inputs.

The candidate necessarily sees the input it is being asked to process. “Hidden”
means the models did not receive these tests while writing or revising their
answers. We do not ask a model to revise anything during judging.

The sandbox still blocks access to the API key, other candidates, and host
project files. Each case has a two-second wall-clock limit plus the existing
process and output limits. A new process also prevents one case from leaving
Python variables behind for the next case.

### 5. Mark the answer outside the sandbox

The trusted host program owns the expected answer and makes the comparison.
The candidate cannot award itself a pass by printing `44 passed`. Empty output,
extra output, malformed responses, timeouts, crashes, and wrong results fail.
A floating-point `29.0` or boolean does not count as the required integer `29`.

The output channel is still candidate-controlled: the host treats it as an
answer to check, never as an authoritative test report. This design does not
prove correctness on inputs outside the suite or replace code review. It also
retains the local sandbox limitations described in Step 3.

### 6. Qualify answers without inventing a winner

An answer qualifies only when **all 44 cases pass**. An empty test run cannot
qualify. There is no partial-credit winner and no automatic merge in this step.

| Model | Hidden checks | Practice checks | Verdict |
| --- | --- | --- | --- |
| GPT-6 Astra | 40/40 | 4/4 | Qualified |
| GPT-6.1 Sol | 40/40 | 4/4 | Qualified |
| GPT-6.1 Terra | 40/40 | 4/4 | Qualified |
| GPT-6 Luna | 40/40 | 4/4 | Qualified |
| GPT-6 Sol | 40/40 | 4/4 | Qualified |

That is **220 successful case executions** across five answers. All five qualify;
this suite does not distinguish their quality further. The starting branch and
original sample remain unchanged. Step 7 can review the code and use explicit
tie-breaking criteria to choose among these candidates.

### 7. Read the evidence or repeat the check

The portable [human-readable results](../examples/money-converter/README.md)
and [full case-by-case record](../examples/money-converter/lanes/)
are included in the repository. The detailed records include each input, expected answer,
actual answer, process status, timing, and the candidate commit ID.

To judge this same saved race again:

```sh
.venv/bin/python -m bakeoff judge --race workdir/races/race-20261115T155112Z-rdly1111
```

This reruns local checks and writes a new results folder. It does not contact
OpenAI or overwrite the earlier judging record. There were **51 passing project
tests** before the first live judging run, covering false success claims, wrong
types, incomplete runs, saved-commit selection, and the existing race/sandbox code.

| New or changed file | Job |
| --- | --- |
| `bakeoff/judge.py` | Load saved answers, run isolated cases, and mark results on the host |
| `bakeoff/__main__.py` | Add the `judge --race` command |
| `tests/test_judge.py` | Check that the judge accepts and rejects the right evidence |

## Step 7: review, choose, and keep an answer

**We kept GPT-6 Astra’s answer (lane-1).** Read the [full comparison and beginner’s
walkthrough](../solution/README.md), or open the [retained code](../solution/money.py).

1. **Read every candidate.** Compare its behavior with the written assignment,
   then consider clarity and complexity. All five passed the original 44 cases.
2. **Investigate concrete concerns.** Code review identified possible long-number
   and whitespace problems. We tested 22 additional cases against every candidate
   in the sandbox. Astra, Sol 6.1, and Terra passed all 22; Luna and Sol 6 passed 17.
3. **Make an explicit choice.** The top three tie on tested behavior. Astra wins
   our readability tie-break because its validation and exact conversion follow
   a clear sequence in one function. This is a judgment about this saved answer.
4. **Verify again before keeping it.** The keep command checked the previous
   judging record, matching commit and fingerprints, then reran all 44 original
   cases against the selected commit. All passed.
5. **Keep the exact answer.** The race repository’s `main` branch moved forward
   to Astra’s commit. Its contents were exported to `solution/` without code edits.
6. **Preserve the history.** All five worktrees remain. The original race and
   judging records describe earlier stages; the new selection record describes
   the final choice. The original unfinished sample remains available for lessons.

The kept commit is `46288e9267df9b6ab71df202384a48393c2e6423`. No API requests
were needed for this review, the extra cases, or keeping the winner.

The reusable command is `keep`. It requires an explicit race, judging record,
and lane, and refuses to overwrite an existing solution folder. For a future
reviewed race, use this shape with that race’s real paths and selected lane:

```sh
.venv/bin/python -m bakeoff keep --race PATH_TO_RACE --judge PATH_TO_JUDGE_JSON --lane lane-N
```

`keep` does not decide which code reads best: that is the review step. It checks
and preserves the selected answer. It also refuses a dirty or moved starting
repository, mismatched evidence, or a candidate that fails the final tests.
The outer project is not staged, committed, or published by this command.

The new files are `bakeoff/review.py` (extra review cases), `bakeoff/selection.py`
(verified retention), and `tests/test_selection.py` (merge/export safeguards).
The judge now distinguishes an unchanged starting branch from a branch it did
not modify during judging, so a race can be judged again after its winner is kept.

## Your key

The application reads `OPENAI_API_KEY` from the process environment. A key exported
in another terminal may not be visible to the Codex app. Run `doctor` from the
terminal where you exported the key to check that terminal's environment.

Alternatively, copy `.env.example` to `.env` and edit the key locally:

```sh
cp -n .env.example .env
```

Never paste the real key into chat or commit it. `.env` is ignored by Git. An
existing environment variable takes precedence over the file. `doctor` checks
presence only: it does not verify authentication, billing, or model access.

## Our learning milestones

1. **Assignment and tests — complete.** Understand input, output, and a failing test.
2. **One live GPT connection — complete.** GPT-6 Luna completed a tool round trip.
3. **Restricted workspace — complete.** Real macOS isolation and boundary checks.
4. **One agent loop — complete.** Luna wrote, tested, reviewed, revised, and submitted a draft.
5. **Five worktrees and five lanes — complete.** All five models submitted independently.
6. **Trusted judging — complete.** All five exact commits passed 40 hidden and four practice cases.
7. **Review and keep the winner — complete.** Astra was selected after reviewing all five answers and running 22 extra cases each.

All seven steps are complete. Astra’s exact saved commit is now the race repository’s
main version, and `solution/` contains the retained answer. `sample/` stays unfinished
so new races still start with the same assignment.

## Recreate the environment

Requires Python 3.12 or later and Git:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On this computer, the environment was created with Codex's bundled Python 3.12;
the system Python is 3.9. To run offline tests of the connection and sandbox machinery:

```sh
.venv/bin/python -m pytest -q --tb=short
```

These tests use fake responses, fake keys, and harmless sandbox probes. They make
no API calls and should pass. The real isolation tests require macOS; on other
systems they are skipped, which does not establish isolation there.

To run the four visible assignment checks, use the restricted `practice` command.
The following direct pytest command bypasses the sandbox and is only for the
original, trusted unfinished sample. Do not use it on agent-generated code:

```sh
.venv/bin/python -m pytest sample/tests hidden_tests -q --tb=short
```

All 44 assignment checks are expected to fail until the money function is
implemented. A red assignment suite does not mean the connection machinery failed.

## References

- [Public project introduction](../README.md)
- [OpenAI models](https://developers.openai.com/api/docs/models)
- [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol)
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)

Model documentation checked November 15, 2026. Account access remains a separate check.
