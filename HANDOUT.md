<!-- ai-generated: 0% - written by the course team -->
# Lab 2 - Measure your own delivery, and prove the metrics are gameable

Saturday 26 September 2026, 150 minutes, fully online. AI Assessment Scale level 3 (AI-assisted). Peak container
RAM about 0.5 GB.

Disclosure: reasoning artifacts are pre-screened by an AI model; all grades are assigned by the lecturer.

## Goal

Add two endpoints to the `svcdesk` you built in Lab 1: one that computes DORA's five delivery metrics from a
supplied event log, and one that exports your own tickets as a lifecycle stream. Then demonstrate Goodhart's law
with arithmetic attached - a change to the event log that **improves** at least one of the five metrics while
making delivery **measurably worse**.

The rules are published in full. The data is not. An assistant will give you five metric definitions in one
prompt, and they will be right about the easy cases and wrong about six specific ones that are in the log on
purpose. Applying the specification to messy data is the work of this lab.

Read, in this order: [METRIC-SPEC.md](METRIC-SPEC.md) (the whole rulebook - metrics, edge cases, tolerances,
margins), [CHECKS.md](CHECKS.md) (every check the checker runs), and the two templates,
[EDGE-CASES-template.md](EDGE-CASES-template.md) and [gaming-template.json](gaming-template.json).
`./itsmlab.sh checks 2` (Windows: `.\itsmlab.ps1 checks 2`) prints the same catalogue from the checker itself; it runs
nothing, so it is safe at any
point in the lab. The course [README](../README.md) explains the checker, the receipts and the deadlines.

## If you have not finished Lab 1

Finish it first. Lab 2 adds two endpoints to the `svcdesk` you built in Lab 1, so you need that service
running before any of this lab makes sense; there is no checkpoint to adopt for Lab 2.

This costs you nothing, because **Lab 1's correction window now closes on Sunday 27 September at 23:59:59**,
not at the start of today's session. So: finish Lab 1 today, receipt it by Sunday evening and collect its
marks, then do Lab 2 against your own service. Lab 2's own attempt 1 is due the same Sunday, and its
correction window runs until **Saturday 10 October at 08:00**, which is the room you have for it.

Leave `baselines:` in `itsmlab.yaml` as `{}`, or declare `lab1: student`; nothing in Lab 2 reads it yet.

## Before you start

Pull the current checker image and check its version:

    docker pull ghcr.io/swasik/itsmlab:2026
    ./itsmlab.sh --version                  # Linux, macOS
    .\itsmlab.ps1 --version                 # Windows PowerShell

It must print `itsmlab 0.3.2` or newer. An image pulled before 25 September does not know Lab 2, so
`checks 2` and `verify 2` fail with it. Your repository itself does not change.

## Minute budget

Core items sum to 110 minutes; the remaining 40 are slack. If an item overruns by more than its budget, stop, run
the checker, and ask on the forum with the check id.

**Before item 1**, copy this folder's `fixtures/` directory into your repository root. You need the practice
log locally to compute `metrics.json` and to build `gaming/after.jsonl`; the checker uses its own copy, so
editing yours changes nothing it checks.

| # | Core item | minutes | at |
|---|---|---|---|
| 1 | Read `METRIC-SPEC.md`; open `fixtures/events-practice.jsonl` and find the six edge cases by eye | 10 | 10 |
| 2 | `POST /dora/metrics`: parse and validate the log, apply the window, compute the five metrics | 30 | 40 |
| 3 | The six edge-case rules, until `metrics-practice.json` matches field for field | 25 | 65 |
| 4 | `GET /dora/ticket-events` | 10 | 75 |
| 5 | `EDGE-CASES.md`: six sections, and the counts your own service reports | 15 | 90 |
| 6 | The gaming demonstration: `gaming/after.jsonl`, `gaming.json` and the `## Gaming demonstration` section of `EDGE-CASES.md` | 15 | 105 |
| 7 | Write `metrics.json`, run `./itsmlab.sh verify 2` (Windows: `.\itsmlab.ps1 verify 2`), tag, submit | 5 | 110 |
| | slack | 40 | 150 |

Item 3 is the one that overruns. When it does, run `./itsmlab.sh verify 2` (Windows: `.\itsmlab.ps1 verify 2`) and read
which check fails: each of
`L2-CORE-3.12` to `L2-CORE-3.14` names the anomaly and the rule, and that is usually enough to find which edge
case you got wrong.

## The six edge cases

They are the reason this lab is not a one-prompt lab. Each one is covered by a published rule, and each one
defeats a definition that models reliably emit:

| id | what the log contains | the default that fails | the rule |
|---|---|---|---|
| E1 | a commit timestamped **after** the deployment that shipped it (clock skew) | drop the pair, or report a negative median | R-08 |
| E2 | a commit that reverts a commit that is itself a revert | three commits, three changes | R-06 |
| E3 | a hotfix deployed straight to production, never on `main` | filter commits on `branch == "main"` | R-09 |
| E4 | a production deployment with **no** linked commits | drop the deployment, or divide by zero | R-10 |
| E5 | a deployment that failed and never recovered | close it at the window's end, or drop it | R-12 |
| E6 | incidents whose intervals overlap | merge them, or sum their wall-clock | R-13 |

All six are in the practice fixture **and** in the graded one. What differs between the two is the data, never
the rules.

A useful way to spend ten minutes: ask your assistant for the five DORA metric definitions **before** you read
`METRIC-SPEC.md`, keep its answer, and then mark it up against the six rules. It is the cheapest possible
demonstration of the point Lecture 2 makes about where AI helps and where it confidently does not, and it costs
you nothing if the answer turns out to be right.

## Core specs (all must pass; no partial credit inside the bundle)

| spec | what it checks |
|---|---|
| `L2-CORE-1` `compose-up` | your service still builds and answers `GET /health` |
| `L2-CORE-2` `dora-api` | the endpoint contract: shape, purity, order independence, duplicate events, empty log, four rejections, and `GET /dora/ticket-events` |
| `L2-CORE-3` `metrics-practice` | the five metrics, every count and every anomaly for the practice fixture, plus `metrics.json` |
| `L2-CORE-4` `edge-cases` | `EDGE-CASES.md`, and **the consistency gate**: the counts you declared must equal what your own service reports |
| `L2-CORE-5` `gaming` | conservation, both re-derived metric objects, and the two margins |
| `L2-CORE-6` `prediction-order` | Tier B only; passes vacuously if you do not attempt the METR stretch. A prediction the grader cannot confirm from its receipt costs `L2-STRETCH-1`, not Core; deleting `PREDICTION.md` withdraws it |

**The consistency gate is the heart of the lab**, as `DECISIONS.md` was in Lab 1: you may not declare one thing
and ship another. If your service says three negative-lead-time pairs, `EDGE-CASES.md` says three.

## Stretch (any two of three; each lifts the grade band equally)

| spec | what it is |
|---|---|
| `L2-STRETCH-1` `metr-n1` | An n=1 METR self-replication. Predict, in `PREDICTION.md`, how long a named feature will take - then **receipt the prediction before the feature's first commit** - build it, and record the outcome in `METR.md` with the ratio actual/predicted to two decimals. **Direction-neutral**: a speedup and a slowdown score identically. What is graded is that the prediction came first and was measured honestly. |
| `L2-STRETCH-2` `rework-class` | Compute the deployment rework rate over the class's shared repository history with `gh api`. That repository is the submissions repository, <https://github.com/swasik/itsm-2026-submissions>: every receipted lab submission is an issue there with the labels `receipted` and `kind:submission`. Count each one as a deployment, and every later attempt at the same lab (`lab<N>/v2` onwards) as rework - for example `gh api --paginate "repos/swasik/itsm-2026-submissions/issues?state=all&labels=receipted,kind:submission&per_page=100"`. Commit the captured payload, and record `source`, `captured_at`, `capture_path`, `sha256`, `deployments`, `rework_deployments` and `deployment_rework_rate` in `rework-class.json`. The checker re-derives the rate from your two counts and checks the payload's digest. |
| `L2-STRETCH-3` `own-tests` | Your own pytest suite behind the compose `tests` profile, as in Lab 1: exit 0 within 300 s and a last line `ITSMLAB-TESTS: passed=<n> failed=0` with n at least 10. |

There is no Kubernetes track in this lab.

## AI usage

Free choice of tool; this is AIAS level 3. Claude Pro is **not** required and is never on the Core path: Gemini
CLI (free tier, no card), GitHub Copilot Free, a local Ollama model or no AI at all all reach the same grade
bands.

The interesting result of this lab is that an assistant confidently produces metric definitions that fail on the
six traps. You are not graded on whether your assistant got them right or wrong - only on whether your service
follows `METRIC-SPEC.md`.

## Deliverables

At the repository root, on the tag you submit:

| path | what |
|---|---|
| `fixtures/` | the practice log and its published expectations, copied from this folder |
| `metrics/` (or wherever your code lives) | the metric computation |
| `metrics.json` | the metric object for the practice fixture, as **your** service returns it |
| `EDGE-CASES.md` | six sections, six declared counts, front matter as the template shows, and a final `## Gaming demonstration` section (your gaming write-up) |
| `gaming/after.jsonl` | the transformed event log |
| `gaming.json` | `metric`, `rule`, `before`, `after` |
| `PREDICTION.md`, `METR.md` | Stretch 1 only |
| `rework-class.json` + the captured payload | Stretch 2 only |

## Submission, receipts and attempts

Same path as Lab 1; every command runs in your repository root (PowerShell users: `.\itsmlab.ps1`, `;` instead of
`&&`).

1. **If you attempt Stretch 1**, do this *first*: write `PREDICTION.md`, commit and push it, then
   `./itsmlab.sh submit 2 --kind prediction` (Windows: `.\itsmlab.ps1 submit 2 --kind prediction`), open the printed
   issue-form URL, submit the issue, and wait for
   the bot's receipt. With no `--text` the command files the contents of `PREDICTION.md`, and the receipt binds
   the sha256 of exactly that, which is what the grader re-hashes: edit the file afterwards, or type a text of
   your own into the form, and the receipt no longer matches it. Only then write the first line of that feature;
   the command warns you if commits already touch `feature_path`, because such a prediction can never be confirmed. The receipt binds the
   hash of your prediction to the `main` SHA at that moment, and Tier B requires the feature's commits to descend
   from it. Git author dates are never used, so back-dating a commit achieves nothing.
   Push nothing between running the command and the bot's receipt: the bot refuses a prediction whose commit is no
   longer the head of `main` (if you did, run the command again and open the new URL).
2. **Implement**, running `./itsmlab.sh verify 2` (Windows: `.\itsmlab.ps1 verify 2`) as often as you like. Tier A runs
   are unlimited and never count.
3. **Commit and push**: `git add -A && git commit -m "Lab 2 attempt 1" && git push origin main` (Windows:
   `git add -A; git commit -m "Lab 2 attempt 1"; git push origin main`).
4. **Verify the committed tree**: `./itsmlab.sh verify 2` (Windows: `.\itsmlab.ps1 verify 2`) exits 0 and its `commit`
   line does not say `(dirty)`.
5. **Tag and push the tag**: `git tag -a lab2/v1 -m "Lab 2 attempt 1"` and `git push origin lab2/v1`. Tier B
   grades the tag's files, never your working directory.
6. **Submission receipt**: `./itsmlab.sh submit 2 --kind submission --tag lab2/v1` (Windows:
   `.\itsmlab.ps1 submit 2 --kind submission --tag lab2/v1`). Open the URL, submit the
   issue, keep the receipt.
7. Three attempts. Attempt 1 is due Sunday 27 September 2026, 23:59:59 (Europe/Warsaw); that deadline is
   advisory - a receipt after it is marked `after_attempt1_due` and still counts. Attempts 2 and 3 are the
   correction window and close **Saturday 10 October 2026 at 08:00:00 Europe/Warsaw**, when session 3 starts; a
   receipt after that instant is `late` and does not count. The best attempt counts.
8. The grade arrives as a comment `itsmlab grade` on the same issue, usually within 20 minutes.

## What the grader does that the checker cannot

Tier A checks you against the **practice** fixture, whose expected values are published next to it - so you can
see every failure before you submit. Tier B serves your service a **different log, generated from your own
seed**, that nobody has ever seen, and compares your answer with values it computes from `METRIC-SPEC.md`
itself. When a field mismatches there, the grade report names **the field and the rule** and never the expected
value.

A classmate's `metrics.json` is worthless to you: their log is not yours.

## The AI-disclosure header

Every file under `src/`, `specs/` and `metrics/` with extension `.py .go .ts .js .java .cs .rb .rs .kt .md`, plus
`DECISIONS.md` and `EDGE-CASES.md`, carries in its first ten lines a comment matching
`ai-generated: <0-100>% - <one line on how>`:

    # ai-generated: 70% - Gemini CLI wrote the parser, I wrote the six rules     (Python, Ruby)
    // ai-generated: 0% - by hand                                                (Go, TypeScript, Java, ...)
    <!-- ai-generated: 30% - outline by an assistant, text mine -->              (Markdown)

In `EDGE-CASES.md` put it on the line right after the closing `---` of the front matter, as the template does:
the front matter must be the first thing in the file. The checker lists files without the header as an advisory;
the course rules require it on every checked file.

## Style of the written artifacts

Plain prose. `EDGE-CASES.md`, including its final `## Gaming demonstration` section (your gaming write-up), is
read by the lecturer (after an AI pre-screen, see the disclosure line above) and graded on whether you understood
**why** the rule is the way it is - not on whether you can restate it. For each edge case, say what a default
definition would have done and what that would have cost the person reading the dashboard. For the gaming
demonstration, say which metric you improved and which rule you exploited (the same `metric` and `rule` as in
`gaming.json`), which incentive would produce that change in a real team, and who would have been rewarded for
it.
