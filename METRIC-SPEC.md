<!-- ai-generated: 0% - written by the lecturer; it is the specification the whole lab is graded against -->
# METRIC-SPEC.md - the delivery metrics of Lab 2

**This document is the whole rulebook.** Every rule that decides what "correct" means is here: the metric
definitions, the observation window, the edge-case policies, the tolerances and the pass margins. Nothing is
withheld except **the data of the graded fixture and the values derived from it**. You may be surprised by the
data; you will never be surprised by the rules.

Where this document and an assistant disagree, this document wins. That is not a rhetorical flourish: the six
edge cases in section 4 exist precisely because the definitions models emit are wrong about them, and the
grader checks the rules, not the folklore.

Rule ids (`R-01` .. `R-21`) are stable. `EDGE-CASES.md` and `gaming.json` cite them.

---

## 1. The event log

JSON Lines, UTF-8, one JSON object per line. Blank lines are ignored. Every event has `event_id` (unique,
1..64 characters), `type` (`commit` | `deployment` | `incident`) and `at` (an RFC 3339 instant with an offset).

**commit**

```json
{"event_id":"c-0142","type":"commit","at":"2026-09-03T08:14:07Z",
 "sha":"sha-0142","branch":"main","change_id":"CHG-0031","reverts":null}
```

| field | meaning |
|---|---|
| `sha` | unique in the log |
| `branch` | free text. `"main"` has **no** privileged meaning (R-09) |
| `change_id` | the unit of work. **`null` on a revert commit**, and only then |
| `reverts` | the `sha` this commit reverts, or `null` |

**deployment**

```json
{"event_id":"d-0037","type":"deployment","at":"2026-09-03T11:02:00Z","deployment_id":"DEP-0037",
 "environment":"production","outcome":"success","commits":["sha-0142"],"unplanned":false,"caused_by":null}
```

| field | meaning |
|---|---|
| `environment` | only `"production"` is in scope (R-01) |
| `outcome` | `"success"` or `"failure"` |
| `commits` | the shas this deployment carried. **May be empty** (R-10) |
| `unplanned` | whether the deployment was planned work |
| `caused_by` | an `incident_id`, or `null` |

**incident**

```json
{"event_id":"i-0009","type":"incident","at":"2026-09-03T11:20:00Z","incident_id":"INC-0009",
 "phase":"opened","deployments":["DEP-0037"]}
```

`phase` is `opened` or `resolved`; the same `incident_id` carries at most one of each. `deployments` names the
failed production deployments this incident covers - possibly none, possibly several.

### Well-formedness

A log is well formed when every `sha` is unique; every `reverts`, every entry of a deployment's `commits`,
every `caused_by` and every entry of an incident's `deployments` names something present in the log; every
incident that resolved was also opened; and a commit carries a `change_id` exactly when `reverts` is `null`.
**Both fixtures the course ships are well formed.** A log that is not must be rejected with 400 or 422.

---

## 2. Scope, window and arithmetic

| id | rule |
|---|---|
| **R-01** | Only deployments with `environment == "production"` are in scope. Every other deployment is ignored **entirely**: not counted, and its commits did not reach production. |
| **R-02** | The window is half-open `[from, to)`, compared as instants. A **deployment** is in the window when `from <= at < to`. **Commits and incidents are never filtered by the window.** They enter through the deployments that reference them, and a recovery may fall after `to`. |
| **R-03** | All arithmetic is in UTC. Durations are reported in **whole seconds**, rounded half-up. Ratios and rates are reported to **six decimal places**, rounded half-up. Any duration this specification computes that comes out **negative is clamped to zero**, and the rule computing it names the anomaly that counts it. |
| **R-04** | The **median** of an odd count is the middle value; of an even count, the arithmetic mean of the two middle values, then rounded by R-03. The median of no values is `null`. |
| **R-05** | An `event_id` that appears more than once is counted **once**: the first occurrence wins, later ones are ignored and are **not** an error. |

The published window, for both the practice fixture and the graded one:

```
from = 2026-09-01T00:00:00Z        to = 2026-09-22T00:00:00Z        21.0 days
```

---

## 3. Change identity

| id | rule |
|---|---|
| **R-06** | A **change** is identified by `change_id`. A commit with a non-null `reverts` has no `change_id` of its own: it inherits, **transitively**, the `change_id` of the commit it reverts. A revert of a revert therefore resolves to the original change - one change, not three. |
| **R-07** | A commit belongs to exactly one change. A change's **first commit instant** is the earliest `at` among all commits resolving to it, **anywhere in the log**, window or not. |

---

## 4. The five metrics, and the six edge cases

The metric names are DORA's own, in the post-2024 five-metric taxonomy: three throughput metrics (change lead
time, deployment frequency, failed deployment recovery time) and two instability metrics (change fail rate,
deployment rework rate).

### R-08 `change_lead_time_seconds_p50`

For every **successful** production deployment in the window, for every `sha` in its `commits`, form one pair
at that commit's **first** such deployment - a commit redeployed later contributes once. The lead time is
`deployment.at - commit.at` in seconds. The metric is the median (R-04) over all pairs.

> **A failed deployment contributes no pairs.** This specification treats a change as delivered when a
> deployment carrying it *succeeded*. Counting failures too is a defensible alternative; it is not this
> specification's, and you are graded against this one.

**Edge case E1 - clock skew produces a negative lead time.** Two machines disagreed about the time, so a
commit is timestamped after the deployment that shipped it. Such a pair is **clamped to zero and counted**,
never discarded, and the number of clamped pairs is reported as `anomalies.negative_lead_time_pairs`.

### R-09 (same metric) - the branch is irrelevant

A commit's `branch` is **never** consulted. A commit that reached production on a branch other than `main`
contributes a pair like any other.

**Edge case E3 - a hotfix that never touched `main`.** `anomalies.commits_never_on_main` counts the distinct
shas carried by **any** production deployment in the window, successful or failed, whose commit's
`branch != "main"`.

### R-10 (same metric) - a deployment with no commits

**Edge case E4.** A deployment whose `commits` is empty contributes no lead-time pair and is **not** excluded
from anything else: it counts in deployment frequency, in the change fail rate denominator and in the rework
rate denominator. `anomalies.deployments_without_commits` counts them.

### R-11 `deployment_frequency_per_day`

(number of production deployments in the window, **any outcome**) ÷ (window length in days), where the length
is `(to - from)` in seconds ÷ 86400.

### R-12 `failed_deployment_recovery_time_seconds_p50`

For every production deployment in the window with `outcome == "failure"`, its **covering incident** is the
incident whose `deployments` contains that `deployment_id` and whose `opened` instant is earliest (ties: the
lowest `incident_id` by byte order). The recovery time is `covering.resolved - deployment.at` in seconds. The
metric is the median (R-04) over the recovered failures.

**Edge case E5 - a deployment that failed and never recovered.** A failed deployment whose covering incident
has no `resolved` event, or that no incident covers, is an **open failure**: excluded from this median,
counted in `counts.open_failures`, and still counted by R-14. Its recovery time is not invented.

### R-13 (same metric) - overlapping incidents

**Edge case E6.** Recovery is computed **per failed deployment, never per incident**. Overlapping incidents
are never merged and their durations are never summed; one incident covering two failed deployments gives both
the same recovery instant. `anomalies.overlapping_incident_pairs` counts the unordered pairs of distinct
incidents whose intervals intersect, where an incident's interval is `[opened, resolved)` and, for an incident
with no `resolved` event, `[opened, to)`; two intervals intersect when `a.opened < b.end and b.opened < a.end`.

### R-14 `change_fail_rate`

(production deployments in the window with `outcome == "failure"`, **open failures included**) ÷ (production
deployments in the window). `null` when the denominator is zero.

### R-15 `deployment_rework_rate`

(production deployments in the window with `unplanned == true` **and** a non-null `caused_by`) ÷ (production
deployments in the window). `null` when the denominator is zero. A deployment may be counted by both R-14 and
R-15: the two instability metrics overlap by design.

---

## 5. Ground truth

Two more numbers, reported by the same endpoint, because section 8 is graded against them.

| id | field | rule |
|---|---|---|
| **R-16** | `ground_truth.changes_delivered` | the number of distinct changes (R-06) that reach production on a **successful** deployment inside the window |
| **R-17** | `ground_truth.true_change_lead_time_seconds_p50` | the median (R-04) over those changes of (the change's first successful production deployment in the window − the change's **first commit instant**, R-07), with R-03 clamping |

R-17 is not R-08 with different words. R-08 is a median over **(deployment, commit) pairs**; R-17 is a median
over **changes**, measured from the change's *earliest* commit. Section 8 exists because those two can be
moved in opposite directions, which is the whole point of the lab.

---

## 6. `POST /dora/metrics`

Stateless: a pure function of its request body. No storage, no ordering between requests.

Request:

```json
{"window": {"from": "2026-09-01T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
 "events": [ ...the parsed JSONL, in any order... ]}
```

Response 200, `application/json`:

```json
{"spec_version": "1.0.0",
 "window": {"from": "2026-09-01T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
 "deployment_frequency_per_day": 2.0,
 "change_lead_time_seconds_p50": 375643,
 "failed_deployment_recovery_time_seconds_p50": 15786,
 "change_fail_rate": 0.190476,
 "deployment_rework_rate": 0.119048,
 "counts": {"deployments": 42, "successful_deployments": 34, "failed_deployments": 8,
            "recovered_failures": 7, "open_failures": 1, "rework_deployments": 5,
            "lead_time_pairs": 125, "changes": 86},
 "anomalies": {"negative_lead_time_pairs": 3, "deployments_without_commits": 4,
               "commits_never_on_main": 4, "revert_chains_collapsed": 2,
               "overlapping_incident_pairs": 11},
 "ground_truth": {"changes_delivered": 65, "true_change_lead_time_seconds_p50": 539452}}
```

*(Those are the real numbers for the practice fixture; `fixtures/metrics-practice.json` is the same object.)*

Every key shown is required; extra keys are ignored. `counts.changes` is the number of distinct changes (R-06)
with at least one commit anywhere in the log. `anomalies.revert_chains_collapsed` is the number of commits
whose `reverts` is non-null - the commits that contributed no change of their own under R-06.

Errors return **400 or 422** with a top-level `error` object, as in Lab 1:

- the body is not an object, `window` is missing, `from`/`to` are not RFC 3339, or `to <= from`;
- `events` is missing or is not an array;
- any event is malformed by section 1.

## 7. `GET /dora/ticket-events`

The stream Lab 7 loads onto a ScyllaDB ring, so its shape is a contract from here on. 200, an array over
**every ticket the service holds**, ordered by `at` ascending then `ticket_id` ascending, one object per
lifecycle instant that has actually occurred:

```json
[{"ticket_id":"...","at":"2026-10-14T10:00:00Z","phase":"created","priority":"P1","state":"new"}]
```

`phase` is `created` | `acknowledged` | `resolved` | `closed`, from `created_at`, `acknowledged_at`,
`resolved_at`, `closed_at`; an absent timestamp emits no event. `state` is the ticket's state **at that
instant** (`created` → `new`, and otherwise the phase's own name). There is deliberately **no `in_progress`
phase**: Lab 1 records no timestamp for it, and a stream may only carry instants the service actually holds.

---

## 8. The gaming demonstration

Show that the metrics can be improved while delivery gets worse. The base log is the **published practice
fixture**. You produce `gaming/after.jsonl` - a well-formed event log - and `gaming.json`:

```json
{"metric": "deployment_frequency_per_day", "rule": "R-11",
 "before": { ...your service's answer for the practice fixture... },
 "after":  { ...your service's answer for gaming/after.jsonl... }}
```

`metric` is one of the five metric field names; `rule` is the rule id you exploited. Both objects are
**re-derived** by the checker from your own running service, so writing numbers into the file achieves
nothing.

Three gates:

| id | gate |
|---|---|
| **R-19 conservation** | Every `commit` event of the base log appears in `after.jsonl` with identical `at`, `sha`, `branch`, `change_id` and `reverts`; every `incident` event appears unchanged; every `deployment` event of the base log appears with the same `deployment_id`, `outcome` and `environment`, and an `at` **not earlier** than before. You may **add** any events, move a base deployment **later**, and change a base deployment's `commits`, `unplanned` and `caused_by`. You may not delete an event, re-time a commit, move a deployment earlier, or flip an outcome - that is falsifying the record, not gaming the metric. |
| **R-20 improvement** | At least one metric clears its margin in the improving direction, and the metric you named in `gaming.json` is one of them: `deployment_frequency_per_day` **+25 % relative**; `change_lead_time_seconds_p50` **−25 % relative**; `failed_deployment_recovery_time_seconds_p50` **−25 % relative**; `change_fail_rate` **−0.02 absolute**; `deployment_rework_rate` **−0.02 absolute**. A `before` that is `null`, or zero for a relative margin, makes that metric ineligible. |
| **R-21 harm** | Delivery of **the work that was already there** got measurably worse. The checker builds `after_base_only` - your `after.jsonl` with every commit whose `sha` is not in the base log removed, and every deployment's `commits` filtered to base shas - and asks your own service to score it. Then either `ground_truth.true_change_lead_time_seconds_p50` is **at least 125 %** of the base's, or `ground_truth.changes_delivered` is **at most 90 %** of the base's. |

**Why R-21 filters.** Measured over *all* changes, the ground truth would be as dilutable as the five metrics:
a hundred trivial added changes drag a median of lead times down exactly as they drag
`change_lead_time_seconds_p50` down, and "harm" could be manufactured by adding fake slow work rather than by
delaying real work. Filtering to the base shas kills both moves. You implement nothing for this: the checker
does the filtering and calls the endpoint you already wrote.

---

## 9. Tolerances (R-18)

| field class | tolerance |
|---|---|
| durations in seconds | ±1 |
| `change_fail_rate`, `deployment_rework_rate` | ±0.0005 |
| `deployment_frequency_per_day` | ±0.0005 |
| everything under `counts` and `anomalies`, and `ground_truth.changes_delivered` | **exact** |
| `null` | matches only `null` |

---

## 10. What the grader does with all this

Tier A runs against the **practice** fixture, whose expected values are published next to it: you can see
every failure before you submit. Tier B serves your service a **different log, generated from your own seed**,
which nobody has seen, and compares your answer with values it computes from this same specification. When a
field mismatches there, the grader tells you **which field and which rule** - and never the expected value.

The rules are published. The data is not. Applying the rules to messy data is the work.
