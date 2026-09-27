# ai-generated: 100% - Codex wrote regression tests against METRIC-SPEC.md.
import copy
import json
from pathlib import Path
import random
import unittest

from src.dora import MetricsError, compute_metrics

ROOT = Path(__file__).resolve().parents[1]
WINDOW = {"from": "2026-09-01T00:00:00Z", "to": "2026-09-22T00:00:00Z"}


def commit(sha="a", at="2026-09-01T00:00:00Z", change="A", branch="main", reverts=None):
    return {"event_id": "c-" + sha, "type": "commit", "at": at, "sha": sha,
            "branch": branch, "change_id": change, "reverts": reverts}


def deploy(identifier="D1", at="2026-09-02T00:00:00Z", shas=None, outcome="success", environment="production"):
    return {"event_id": "d-" + identifier, "type": "deployment", "at": at,
            "deployment_id": identifier, "environment": environment, "outcome": outcome,
            "commits": ["a"] if shas is None else shas, "unplanned": False, "caused_by": None}


def incident(identifier="I1", phase="opened", at="2026-09-02T00:00:00Z", deployments=None):
    return {"event_id": "i-" + identifier + "-" + phase, "type": "incident", "at": at,
            "incident_id": identifier, "phase": phase, "deployments": ["D1"] if deployments is None else deployments}


def score(events, window=None):
    return compute_metrics({"window": WINDOW if window is None else window, "events": events})


class DoraTests(unittest.TestCase):
    def test_published_practice_values_and_shuffled_inputs(self):
        events = [json.loads(line) for line in (ROOT / "fixtures/events-practice.jsonl").read_text().splitlines() if line.strip()]
        expected = json.loads((ROOT / "fixtures/metrics-practice.json").read_text())
        original = copy.deepcopy(events)
        self.assertEqual(score(events), expected)
        self.assertEqual(events, original)
        for seed in range(5):
            random.Random(seed).shuffle(events)
            self.assertEqual(score(events), expected)

    def test_redeployment_uses_earliest_success_for_any_order(self):
        events = [commit(), deploy(), deploy("D2", at="2026-09-03T00:00:00Z")]
        self.assertEqual(score(events)["change_lead_time_seconds_p50"], 86400)
        self.assertEqual(score(events), score(list(reversed(events))))
        self.assertEqual(score(events)["counts"]["lead_time_pairs"], 1)

    def test_failed_deployment_does_not_deliver_a_commit(self):
        result = score([commit(), deploy(outcome="failure"), deploy("D2", at="2026-09-03T00:00:00Z")])
        self.assertEqual(result["change_lead_time_seconds_p50"], 172800)
        self.assertEqual(result["counts"]["open_failures"], 1)

    def test_empty_log_has_null_medians_and_ratios(self):
        result = score([])
        for field in ("change_lead_time_seconds_p50", "failed_deployment_recovery_time_seconds_p50", "change_fail_rate", "deployment_rework_rate"):
            self.assertIsNone(result[field])
        self.assertIsNone(result["ground_truth"]["true_change_lead_time_seconds_p50"])
        self.assertEqual(result["deployment_frequency_per_day"], 0)
        self.assertTrue(all(value == 0 for value in result["counts"].values()))

    def test_negative_fractional_lead_time_is_counted_and_clamped(self):
        result = score([commit(at="2026-09-02T00:00:00.100000Z"), deploy()])
        self.assertEqual(result["anomalies"]["negative_lead_time_pairs"], 1)
        self.assertEqual(result["change_lead_time_seconds_p50"], 0)

    def test_half_up_rounding_of_duration(self):
        result = score([commit(), deploy(at="2026-09-01T00:00:02.500000Z")])
        self.assertEqual(result["change_lead_time_seconds_p50"], 3)

    def test_even_median_half_up(self):
        result = score([commit(), commit("b", change="B"), deploy(at="2026-09-01T00:00:02Z"),
                        deploy("D2", at="2026-09-01T00:00:03Z", shas=["b"])])
        self.assertEqual(result["change_lead_time_seconds_p50"], 3)

    def test_rate_rounding_half_up(self):
        result = score([deploy(shas=[])], {"from": WINDOW["from"], "to": "2027-01-07T00:00:00Z"})
        # Exactly 128 days: 1/128 = 0.0078125, rounded up at the sixth place.
        self.assertEqual(result["deployment_frequency_per_day"], 0.007813)

    def test_window_is_half_open_and_staging_is_ignored(self):
        result = score([commit(at="2026-08-31T23:00:00Z"), deploy(at=WINDOW["from"]),
                        deploy("end", at=WINDOW["to"]), deploy("staging", environment="staging")])
        self.assertEqual(result["counts"]["deployments"], 1)
        self.assertEqual(result["change_lead_time_seconds_p50"], 3600)

    def test_timezone_offsets_are_compared_as_instants(self):
        result = score([commit(at="2026-09-01T01:00:00+02:00"), deploy(at="2026-09-01T02:00:00+02:00")])
        self.assertEqual(result["change_lead_time_seconds_p50"], 3600)

    def test_duplicate_event_first_occurrence_wins(self):
        first = deploy()
        self.assertEqual(score([commit(), first, dict(first, at="2026-09-20T00:00:00Z")]), score([commit(), first]))
        self.assertEqual(score([commit(), first, {"event_id": first["event_id"]}]), score([commit(), first]))

    def test_revert_of_revert_is_one_change(self):
        result = score([commit(), commit("b", change=None, reverts="a"), commit("c", change=None, reverts="b"), deploy(shas=["a", "b", "c"])])
        self.assertEqual(result["counts"]["changes"], 1)
        self.assertEqual(result["ground_truth"]["changes_delivered"], 1)
        self.assertEqual(result["anomalies"]["revert_chains_collapsed"], 2)

    def test_change_clock_starts_at_earliest_commit_anywhere(self):
        result = score([commit(at="2026-08-31T00:00:00Z"), commit("b", at="2026-09-01T00:00:00Z"), deploy(shas=["b"])])
        self.assertEqual(result["change_lead_time_seconds_p50"], 86400)
        self.assertEqual(result["ground_truth"]["true_change_lead_time_seconds_p50"], 172800)

    def test_hotfix_in_failed_deployment_counts_as_off_main(self):
        result = score([commit(branch="hotfix"), deploy(outcome="failure")])
        self.assertEqual(result["anomalies"]["commits_never_on_main"], 1)
        self.assertIsNone(result["change_lead_time_seconds_p50"])

    def test_empty_deployment_still_counts(self):
        result = score([deploy(shas=[], outcome="failure")])
        self.assertEqual(result["counts"]["deployments"], 1)
        self.assertEqual(result["change_fail_rate"], 1)
        self.assertEqual(result["anomalies"]["deployments_without_commits"], 1)

    def test_open_failure_is_not_given_an_invented_recovery_time(self):
        result = score([commit(), deploy(outcome="failure"), incident()])
        self.assertIsNone(result["failed_deployment_recovery_time_seconds_p50"])
        self.assertEqual(result["counts"]["open_failures"], 1)
        self.assertEqual(result["change_fail_rate"], 1)

    def test_recovery_after_window_is_included(self):
        result = score([commit(), deploy(outcome="failure"), incident(), incident(phase="resolved", at="2026-09-23T00:00:00Z")])
        self.assertEqual(result["failed_deployment_recovery_time_seconds_p50"], 21 * 86400)

    def test_earliest_covering_incident_wins_even_if_open(self):
        result = score([commit(), deploy(outcome="failure"), incident("early"),
                        incident("later", at="2026-09-03T00:00:00Z"), incident("later", phase="resolved", at="2026-09-04T00:00:00Z")])
        self.assertEqual(result["counts"]["open_failures"], 1)

    def test_covering_incident_tie_uses_identifier(self):
        result = score([commit(), deploy(outcome="failure"), incident("B"), incident("A"),
                        incident("B", phase="resolved", at="2026-09-04T00:00:00Z"), incident("A", phase="resolved", at="2026-09-03T00:00:00Z")])
        self.assertEqual(result["failed_deployment_recovery_time_seconds_p50"], 86400)

    def test_one_incident_recovers_two_deployments_separately(self):
        result = score([commit(), deploy(outcome="failure"), deploy("D2", at="2026-09-03T00:00:00Z", outcome="failure"),
                        incident(deployments=["D1", "D2"]), incident(phase="resolved", at="2026-09-04T00:00:00Z", deployments=["D1", "D2"])])
        self.assertEqual(result["counts"]["recovered_failures"], 2)
        self.assertEqual(result["failed_deployment_recovery_time_seconds_p50"], 129600)

    def test_touching_incident_intervals_do_not_overlap(self):
        events = [incident("A", deployments=[]), incident("A", phase="resolved", at="2026-09-03T00:00:00Z", deployments=[]),
                  incident("B", at="2026-09-03T00:00:00Z", deployments=[]), incident("B", phase="resolved", at="2026-09-04T00:00:00Z", deployments=[])]
        self.assertEqual(score(events)["anomalies"]["overlapping_incident_pairs"], 0)

    def test_rework_requires_both_unplanned_and_cause(self):
        events = [deploy("a", shas=[]), deploy("b", shas=[]), deploy("c", shas=[]), incident(deployments=[])]
        events[0]["unplanned"] = True
        events[1]["caused_by"] = "I1"
        events[2].update(unplanned=True, caused_by="I1")
        self.assertEqual(score(events)["counts"]["rework_deployments"], 1)
        self.assertEqual(score(events)["deployment_rework_rate"], 0.333333)

    def test_invalid_timestamps_are_rejected(self):
        for value in [None, "2026-09-01", "2026-09-01T00:00:00", "2026-02-30T00:00:00Z", "2026-09-01T00:00:00+00:60", "bad"]:
            with self.subTest(value=value), self.assertRaises(MetricsError):
                score([commit(at=value)])

    def test_invalid_requests_are_rejected(self):
        for payload in [None, [], {}, {"window": WINDOW}, {"window": WINDOW, "events": {}},
                        {"window": {"from": WINDOW["from"], "to": WINDOW["from"]}, "events": []}]:
            with self.subTest(payload=payload), self.assertRaises(MetricsError):
                compute_metrics(payload)

    def test_invalid_references_are_rejected(self):
        cases = [[commit(change=None, reverts="unknown")], [deploy()],
                 [dict(deploy(shas=[]), caused_by="missing")], [incident(deployments=["missing"])]]
        for events in cases:
            with self.subTest(events=events), self.assertRaises(MetricsError):
                score(events)

    def test_resolved_incident_without_open_is_rejected(self):
        with self.assertRaises(MetricsError):
            score([incident(phase="resolved", deployments=[])])

    def test_duplicate_incident_phase_and_duplicate_sha_are_rejected(self):
        for events in [[incident(deployments=[]), dict(incident(deployments=[]), event_id="different")],
                       [commit(), dict(commit(), event_id="different")]]:
            with self.subTest(events=events), self.assertRaises(MetricsError):
                score(events)

    def test_revert_cycles_are_rejected(self):
        with self.assertRaises(MetricsError):
            score([commit("a", change=None, reverts="b"), commit("b", change=None, reverts="a")])

    def test_malformed_event_fields_are_rejected(self):
        cases = [dict(deploy(shas=[]), outcome="unknown"), dict(deploy(shas=[]), unplanned=1),
                 dict(deploy(shas=[]), commits="abc"), dict(commit(), event_id=[]),
                 dict(commit(), type="unknown"), dict(commit(), event_id="a" * 65)]
        for event in cases:
            with self.subTest(event=event), self.assertRaises(MetricsError):
                score([event])


if __name__ == "__main__":
    unittest.main()
