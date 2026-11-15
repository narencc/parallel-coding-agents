# The 25-second Brag demo

[Watch the video](../brag-output/brag.mp4) · [How it was made](../brag-output/README.md) · [Back to the project](../README.md)

This is an animated explanation of our recorded money-converter experiment. It includes a synthetic English voice and quiet music.

## What the voice says

Five AI answers. All passed the first tests. But were they all correct?
This project gives five GPT models the same task, in separate workspaces.
Then it checks their saved answers.
In our money converter experiment, closer review found failures in two answers.
Three tied. We kept Astra for readability.
Explore the evidence. Try to break the winner.

## What each part means

1. **Five answers passed the first tests.** Every saved answer passed the original 40 hidden checks and four practice checks.
2. **Each model had a separate workspace.** They solved the same task without sharing their drafts.
3. **Review found more cases to check.** We added 22 checks after reading the answers. Luna and Sol 6 failed five checks each. Five failed checks do not mean five separate bugs.
4. **Three answers tied.** Astra, Sol 6.1, and Terra passed the observed checks. We kept Astra because its code was easy to read. That does not make it the best model for every task.
5. **Readers can challenge the answer.** Inspect the saved files and suggest a valid input that the kept answer handles incorrectly.

The separate booking experiment ended in a five-way tie on all 48 prewritten checks. [Compare both experiments](EXPERIMENT_COMPARISON.md).

## Try the free text replay

```sh
python3 -m bakeoff replay
python3 -m bakeoff replay --task bookings
```

These commands read saved results. They do not need an API key, call GPT, or execute candidate code. The optional `--demo` command is a paced text walkthrough, separate from the video.
