# ai-generated: 100% - Codex wrote HTTP regression tests for the Lab 2 endpoints.
import copy
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.main import app, db
from tests.test_dora import WINDOW, commit, deploy, incident


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.previous = copy.deepcopy(db)
        db.clear()

    def tearDown(self):
        self.client.close()
        db.clear()
        db.update(self.previous)

    def test_metrics_success_and_order_independence(self):
        events = [commit(), deploy(), deploy("later", at="2026-09-03T00:00:00Z")]
        a = self.client.post("/dora/metrics", json={"window": WINDOW, "events": events})
        b = self.client.post("/dora/metrics", json={"window": WINDOW, "events": events[::-1]})
        self.assertEqual(a.status_code, 200)
        self.assertEqual(a.json()["change_lead_time_seconds_p50"], 86400)
        self.assertEqual(a.json(), b.json())

    def test_invalid_json_has_top_level_error_object(self):
        response = self.client.post("/dora/metrics", content="{broken", headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["error"], dict)

    def test_invalid_incident_returns_422(self):
        response = self.client.post("/dora/metrics", json={"window": WINDOW, "events": [incident(phase="resolved", deployments=[])]})
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["error"], dict)

    def test_empty_metrics_response(self):
        response = self.client.post("/dora/metrics", json={"window": WINDOW, "events": []})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["ground_truth"]["true_change_lead_time_seconds_p50"])

    def test_ticket_lifecycle_includes_only_recorded_phases(self):
        with patch.dict("os.environ", {"SVCDESK_TEST_CLOCK": "1"}):
            response = self.client.post("/tickets", json={"title": "Test", "reporter": {"name": "Test"}, "impact": 1, "urgency": 1},
                                        headers={"X-Test-Clock": "2026-09-01T10:00:00Z"})
            self.assertEqual(response.status_code, 201)
            tid = response.json()["id"]
            for action, at in [("ack", "10:01:00"), ("start", "10:02:00"), ("resolve", "10:03:00"), ("close", "10:04:00")]:
                response = self.client.post(f"/tickets/{tid}/{action}", headers={"X-Test-Clock": f"2026-09-01T{at}Z"})
                self.assertEqual(response.status_code, 200)
        events = self.client.get("/dora/ticket-events").json()
        self.assertEqual([event["phase"] for event in events], ["created", "acknowledged", "resolved", "closed"])
        self.assertEqual([event["state"] for event in events], ["new", "acknowledged", "resolved", "closed"])

    def test_ticket_stream_orders_instants_not_timezone_strings(self):
        db.update({"later": {"created_at": "2026-09-01T00:30:00Z", "priority": "P2"},
                   "earlier": {"created_at": "2026-09-01T01:00:00+02:00", "priority": "P1"}})
        events = self.client.get("/dora/ticket-events").json()
        self.assertEqual([event["ticket_id"] for event in events], ["earlier", "later"])
