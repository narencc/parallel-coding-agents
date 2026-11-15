# Help us find what the tests missed

You do not need to understand the whole project to help. The most useful small
contribution is a clear example of something that does not work as specified.

## Can you break the kept answer?

Read the [assignment rules](sample/SPEC.md), then report:

1. **Input:** exactly what you tried, including spaces and punctuation.
2. **Expected answer:** the exact paise value, or why the input should be rejected.
3. **Observed answer:** what happened, or “not run yet” if this is a proposed case.
4. **Rule:** the assignment rule supporting your expectation.
5. **Where you tried it:** model/lane or kept solution; operating system and Python
   version if you ran it. Do not include keys or personal file paths.

Use the “Challenge the answer” issue template. An issue is a public report or
discussion on GitHub. If you have only a question, say which explanation confused
you and what you expected it to mean.

A passing test suite does not prove every possible input works. Report failures
as failed cases; several failed cases may share one underlying bug.

## Explore first, without credentials

```sh
python3 -m bakeoff replay
python3 -m bakeoff replay --lane lane-4
```

These read saved records only. You can also browse [the example](examples/money-converter/README.md)
on GitHub. No API key or paid run is needed to participate.

## If you change code or tests

Use Python 3.12+ and install `requirements.txt` in a virtual environment. Follow
the [README](README.md) for setup. Run `.venv/bin/python -m pytest -q` to check the
coordinator. Run `.venv/bin/python -m bakeoff recheck` on supported macOS to
reproduce the saved candidates' results. It expects the same known failures.

Keep execution of generated code inside the sandbox. Do not directly import
candidate files or run their tests with unrestricted pytest. On other operating
systems, use the replay and documentation; do not bypass the missing sandbox.

Do not rewrite the archived example to make an improvement look like the original
result. Add new evidence separately. For a proposed fix, explain the old behavior,
the new behavior, and how you checked it. Preserve the exact recorded winner.

## Suggest another assignment

Choose a useful, different task with rules we can check objectively. Include a
few examples, invalid inputs, and why the task tests different skills. Do not
choose tasks just because they might make a particular model fail. See the
[second-experiment proposal](docs/NEXT_EXPERIMENT.md).

## Improve an explanation

Tell us the sentence you found confusing and suggest a simpler version. You do
not need coding experience to make the project easier to understand.

Be respectful, focus criticism on behavior and evidence, and never post API keys
or someone else's private data. If this project helps you, a star is welcome but
is never required for help or participation.
