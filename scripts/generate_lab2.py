# ai-generated: 100% - Codex created a reproducible gaming example and HTTP export.
"""Run with the service up: python scripts/generate_lab2.py --base-url http://localhost:8080"""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
WINDOW = {"from": "2026-09-01T00:00:00Z", "to": "2026-09-22T00:00:00Z"}


def build_demo():
    base = [json.loads(line) for line in (ROOT / "fixtures/events-practice.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    after = copy.deepcopy(base)
    instant = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    candidates = sorted(
        [event for event in after if event["type"] == "deployment"
         and event["environment"] == "production" and event["outcome"] == "success"
         and event["commits"] and instant(WINDOW["from"]) <= instant(event["at"]) < instant(WINDOW["to"])],
        key=lambda event: (instant(event["at"]), event["deployment_id"]),
    )
    # Postpone eight real deliveries beyond the measurement window.
    for event in candidates[-8:]:
        event["at"] = "2026-09-22T12:00:00Z"
    # Twenty additional operational deployments ship none of the pending work.
    for index in range(20):
        after.append({"event_id": f"gaming-empty-{index + 1:02d}", "type": "deployment",
                      "at": f"2026-09-21T12:{index:02d}:00Z", "deployment_id": f"GAMING-EMPTY-{index + 1:02d}",
                      "environment": "production", "outcome": "success", "commits": [],
                      "unplanned": False, "caused_by": None})
    return base, after


def generate(endpoint):
    """endpoint accepts a request body and returns the running API's JSON object."""
    base, after = build_demo()
    before_result = endpoint({"window": WINDOW, "events": base})
    after_result = endpoint({"window": WINDOW, "events": after})
    if after_result["deployment_frequency_per_day"] < before_result["deployment_frequency_per_day"] * 1.25:
        raise RuntimeError("The demonstration failed the R-20 improvement margin")
    if after_result["ground_truth"]["changes_delivered"] > before_result["ground_truth"]["changes_delivered"] * 0.9:
        raise RuntimeError("The demonstration failed the R-21 harm margin")
    (ROOT / "gaming").mkdir(exist_ok=True)
    (ROOT / "gaming/after.jsonl").write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in after), encoding="utf-8")
    (ROOT / "metrics.json").write_text(json.dumps(before_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    gaming = {"metric": "deployment_frequency_per_day", "rule": "R-11", "before": before_result, "after": after_result}
    (ROOT / "gaming.json").write_text(json.dumps(gaming, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return gaming


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    args = parser.parse_args()

    def endpoint(payload):
        request = Request(args.base_url.rstrip("/") + "/dora/metrics", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    result = generate(endpoint)
    print("Saved metrics.json, gaming/after.jsonl and gaming.json from the API responses.")
    print("Frequency:", result["before"]["deployment_frequency_per_day"], "->", result["after"]["deployment_frequency_per_day"])
    print("Changes delivered:", result["before"]["ground_truth"]["changes_delivered"], "->", result["after"]["ground_truth"]["changes_delivered"])
