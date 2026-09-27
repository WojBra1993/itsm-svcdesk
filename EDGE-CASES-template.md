---
lab2_edge_cases:
  E1: {rule: R-08, count: 0}
  E2: {rule: R-06, count: 0}
  E3: {rule: R-09, count: 0}
  E4: {rule: R-10, count: 0}
  E5: {rule: R-12, count: 0}
  E6: {rule: R-13, count: 0}
---
<!-- ai-generated: ??% - TODO replace ?? with a number and say in one line how this file was written -->

# Edge cases in the practice event log

Replace every `count` above with what **your own service** reports for the practice fixture. The checker
compares the six numbers with the service's answer, so a guess fails (`L2-CORE-4.07` to `L2-CORE-4.09`):

| declare here | your service's field |
|---|---|
| E1 | `anomalies.negative_lead_time_pairs` |
| E2 | `anomalies.revert_chains_collapsed` |
| E3 | `anomalies.commits_never_on_main` |
| E4 | `anomalies.deployments_without_commits` |
| E5 | `counts.open_failures` |
| E6 | `anomalies.overlapping_incident_pairs` |

The `rule` values above are already correct and are the only admissible ones; do not change them.

Each of the six sections below needs all three labels, with at least 20 characters after each colon. The final
`## Gaming demonstration` section is read by the lecturer and is not checked mechanically. Delete these
instructions when you write the file.

## E1 - clock skew produces a negative lead time

- What the log contains:
- What a default definition would have done:
- Why the rule is defensible:

## E2 - a revert of a revert

- What the log contains:
- What a default definition would have done:
- Why the rule is defensible:

## E3 - a hotfix that never touched `main`

- What the log contains:
- What a default definition would have done:
- Why the rule is defensible:

## E4 - a deployment with zero linked commits

- What the log contains:
- What a default definition would have done:
- Why the rule is defensible:

## E5 - a deployment that failed and never recovered

- What the log contains:
- What a default definition would have done:
- Why the rule is defensible:

## E6 - overlapping incidents

- What the log contains:
- What a default definition would have done:
- Why the rule is defensible:

## Gaming demonstration

Plain prose, no labels required: which metric you improved and which rule you exploited (the same
`metric` and `rule` as in `gaming.json`), which incentive would produce that change in a real team, and who
would have been rewarded for it.
