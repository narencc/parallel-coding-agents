# Recorded-run walkthrough

[Back to the introduction](../README.md)

This is a reconstruction from saved evidence, not a live race or an original
screen recording. Read it here or run `python3 -m bakeoff replay --demo` from the
repository root for a paced version. No API key, network access, or execution of
candidate code is involved. The pacing is for reading, not the race timing.

## 1. One task, five separate answers

Recorded experiment: 2026-11-15

Read rupee amounts and return exact whole paise.

Example: Rs 500 becomes 50000 paise.

This replay makes no API calls and runs no candidate code.

## 2. Five models worked at the same time

Peak overlapping requests: 5

Recorded race duration: 22.34 seconds

Model requests: 13

Each model had its own folder, conversation, and drafts.

## 3. Practice helped models revise

Terra: first draft had a syntax error; its second passed.

Luna wrote three drafts before submitting.

The final answer from every lane passed all four practice checks.

## 4. All five passed the original assessment

40 hidden cases + four practice cases per saved answer.

Five answers passed all 44 cases.

The coordinator marked outputs outside the restricted process.

## 5. Code review raised new questions

We added 22 checks after reading the answers.

These covered long inputs, whitespace, signs, and precision.

Luna and Sol 6 failed five checks each.

Five failed checks do not mean five independent bugs.

## 6. Results from this one recorded experiment

```text
Model                Original checks   Extra checks   Est. USD
gpt-6-astra          44/44             22/22          $0.07054
gpt-6.1-sol          44/44             22/22          $0.01468
gpt-6.1-terra        44/44             22/22          $0.01364
gpt-6-luna           44/44             17/22          $0.00204
gpt-6-sol            44/44             17/22          $0.01448
```

## 7. Astra was selected after review

Astra, Sol 6.1, and Terra tied on the observed checks.

Readability was the deciding judgment.

One task and one run do not establish a general model ranking.

Can you find a valid input the kept answer handles incorrectly?

[Explore all the evidence](../examples/money-converter/README.md) · [Report a failing case](../CONTRIBUTING.md)
