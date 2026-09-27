# ai-generated: 100% - Codex checked the exported artifacts and gaming constraints.
import json
from pathlib import Path
import unittest

from src.dora import compute_metrics, parse_instant

ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.base = [json.loads(line) for line in (ROOT / "fixtures/events-practice.jsonl").read_text().splitlines() if line.strip()]
        self.after = [json.loads(line) for line in (ROOT / "gaming/after.jsonl").read_text().splitlines() if line.strip()]
        self.gaming = json.loads((ROOT / "gaming.json").read_text())
        self.window = self.gaming["before"]["window"]

    def test_saved_responses_match_the_metric_function(self):
        before = compute_metrics({"window": self.window, "events": self.base})
        after = compute_metrics({"window": self.window, "events": self.after})
        self.assertEqual(self.gaming["before"], before)
        self.assertEqual(self.gaming["after"], after)
        self.assertEqual(json.loads((ROOT / "metrics.json").read_text()), before)

    def test_original_events_are_conserved(self):
        after_by_id = {event["event_id"]: event for event in self.after}
        for event in self.base:
            after = after_by_id[event["event_id"]]
            if event["type"] in ("commit", "incident"):
                self.assertEqual(after, event)
            else:
                for field in ("deployment_id", "environment", "outcome"):
                    self.assertEqual(after[field], event[field])
                self.assertGreaterEqual(parse_instant(after["at"]), parse_instant(event["at"]))

    def test_improvement_and_harm_on_original_work(self):
        metric = self.gaming["metric"]
        self.assertEqual(metric, "deployment_frequency_per_day")
        self.assertEqual(self.gaming["rule"], "R-11")
        self.assertGreaterEqual(self.gaming["after"][metric], self.gaming["before"][metric] * 1.25)
        base_shas = {event["sha"] for event in self.base if event["type"] == "commit"}
        filtered = []
        for event in self.after:
            if event["type"] == "commit" and event["sha"] not in base_shas:
                continue
            if event["type"] == "deployment":
                event = dict(event, commits=[sha for sha in event["commits"] if sha in base_shas])
            filtered.append(event)
        result = compute_metrics({"window": self.window, "events": filtered})
        self.assertEqual(result["counts"]["deployments"], 54)
        self.assertEqual(result["ground_truth"]["changes_delivered"], 50)
        self.assertLessEqual(result["ground_truth"]["changes_delivered"], self.gaming["before"]["ground_truth"]["changes_delivered"] * 0.9)
