# ai-generated: 100% - Codex implemented and tested the published Lab 2 rules.
"""Pure delivery-metric calculations following METRIC-SPEC.md R-01 to R-17."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
import re


class MetricsError(ValueError):
    """The supplied request or event log is not well formed."""


_RFC3339 = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt](?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d"
    r"(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z"
)


def parse_instant(value):
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        raise MetricsError("Timestamps must be RFC 3339 instants with a timezone offset")
    try:
        return datetime.fromisoformat(value.upper().replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise MetricsError("Invalid timestamp") from exc


def _seconds(delta):
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / 1000000


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    value = ordered[midpoint] if len(ordered) % 2 else (ordered[midpoint - 1] + ordered[midpoint]) / 2
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _ratio(numerator, denominator):
    if denominator == 0:
        return None
    return float((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _text(event, key, allow_empty=False):
    value = event.get(key)
    if not isinstance(value, str) or (not allow_empty and not value):
        raise MetricsError(f"{key} must be a string" + ("" if allow_empty else " that is not empty"))
    return value


def _references(event, key):
    value = event.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise MetricsError(f"{key} must be an array of identifiers")
    return value


def _read_log(raw_events):
    if not isinstance(raw_events, list):
        raise MetricsError("events must be an array")
    events, seen = [], set()
    for event in raw_events:
        if not isinstance(event, dict):
            raise MetricsError("Every event must be an object")
        event_id = _text(event, "event_id")
        if len(event_id) > 64:
            raise MetricsError("event_id must contain 1 to 64 characters")
        # R-05: later occurrences have no effect, including their other fields.
        if event_id in seen:
            continue
        seen.add(event_id)
        if event.get("type") not in ("commit", "deployment", "incident"):
            raise MetricsError("Unknown event type")
        events.append((event, parse_instant(event.get("at"))))

    commits, deployments, incidents = {}, {}, {}
    for event, instant in events:
        kind = event["type"]
        if kind == "commit":
            sha = _text(event, "sha")
            if sha in commits:
                raise MetricsError("Duplicate commit sha")
            _text(event, "branch", allow_empty=True)
            if "change_id" not in event or "reverts" not in event:
                raise MetricsError("A commit requires change_id and reverts")
            if event["reverts"] is None:
                _text(event, "change_id")
            elif event["change_id"] is not None:
                raise MetricsError("A revert must have a null change_id")
            else:
                _text(event, "reverts")
            commits[sha] = (event, instant)
        elif kind == "deployment":
            deployment_id = _text(event, "deployment_id")
            if deployment_id in deployments:
                raise MetricsError("Duplicate deployment_id")
            _text(event, "environment")
            if event.get("outcome") not in ("success", "failure"):
                raise MetricsError("Invalid deployment outcome")
            _references(event, "commits")
            if not isinstance(event.get("unplanned"), bool):
                raise MetricsError("unplanned must be a boolean")
            if "caused_by" not in event:
                raise MetricsError("A deployment requires caused_by")
            if event["caused_by"] is not None:
                _text(event, "caused_by")
            deployments[deployment_id] = (event, instant)
        else:
            incident_id = _text(event, "incident_id")
            phase = event.get("phase")
            if phase not in ("opened", "resolved"):
                raise MetricsError("Invalid incident phase")
            _references(event, "deployments")
            phases = incidents.setdefault(incident_id, {})
            if phase in phases:
                raise MetricsError("An incident may have only one event of each phase")
            phases[phase] = (event, instant)

    for event, _ in commits.values():
        if event["reverts"] is not None and event["reverts"] not in commits:
            raise MetricsError("reverts references an unknown commit")
    for event, _ in deployments.values():
        if any(sha not in commits for sha in event["commits"]):
            raise MetricsError("Deployment references an unknown commit")
        if event["caused_by"] is not None and event["caused_by"] not in incidents:
            raise MetricsError("Deployment references an unknown incident")
    for phases in incidents.values():
        if "opened" not in phases:
            raise MetricsError("A resolved incident must also have an opened event")
        for event, _ in phases.values():
            for deployment_id in event["deployments"]:
                if deployment_id not in deployments:
                    raise MetricsError("Incident references an unknown deployment")
                deployment = deployments[deployment_id][0]
                if deployment["environment"] != "production" or deployment["outcome"] != "failure":
                    raise MetricsError("Incidents must reference failed production deployments")
    return commits, deployments, incidents


def compute_metrics(payload):
    """Validate a request and return its metric object without mutating inputs."""
    if not isinstance(payload, dict) or not isinstance(payload.get("window"), dict):
        raise MetricsError("The request must contain a window object")
    window = payload["window"]
    start, end = parse_instant(window.get("from")), parse_instant(window.get("to"))
    if end <= start:
        raise MetricsError("window.to must be strictly after window.from")
    commits, deployments, incidents = _read_log(payload.get("events"))

    # R-06: iteratively resolve revert chains, rejecting cycles without recursion.
    change_for_sha = {}
    for sha in commits:
        cursor, chain, visited = sha, [], set()
        while cursor not in change_for_sha:
            if cursor in visited:
                raise MetricsError("A revert chain cannot contain a cycle")
            visited.add(cursor)
            chain.append(cursor)
            event = commits[cursor][0]
            if event["reverts"] is None:
                change_for_sha[cursor] = event["change_id"]
                break
            cursor = event["reverts"]
        for item in chain:
            change_for_sha[item] = change_for_sha[cursor]

    first_commit = {}
    for sha, (_, instant) in commits.items():
        change = change_for_sha[sha]
        first_commit[change] = min(first_commit.get(change, instant), instant)

    production = [
        (event, instant) for event, instant in deployments.values()
        if event["environment"] == "production" and start <= instant < end
    ]
    successes = [(event, instant) for event, instant in production if event["outcome"] == "success"]
    failures = [(event, instant) for event, instant in production if event["outcome"] == "failure"]
    first_deployment, first_change_delivery = {}, {}
    for event, instant in successes:
        for sha in event["commits"]:
            first_deployment[sha] = min(first_deployment.get(sha, instant), instant)
            change = change_for_sha[sha]
            first_change_delivery[change] = min(first_change_delivery.get(change, instant), instant)

    raw_lead_times = [_seconds(instant - commits[sha][1]) for sha, instant in first_deployment.items()]
    lead_times = [max(Decimal(0), value) for value in raw_lead_times]
    true_lead_times = [max(Decimal(0), _seconds(instant - first_commit[change]))
                       for change, instant in first_change_delivery.items()]

    recovery_times, open_failures = [], 0
    for deployment, deployed_at in failures:
        covering = [
            (phases["opened"][1], incident_id.encode("utf-8"), phases)
            for incident_id, phases in incidents.items()
            if any(deployment["deployment_id"] in event["deployments"] for event, _ in phases.values())
        ]
        if not covering:
            open_failures += 1
            continue
        phases = min(covering, key=lambda item: (item[0], item[1]))[2]
        if "resolved" not in phases:
            open_failures += 1
        else:
            recovery_times.append(max(Decimal(0), _seconds(phases["resolved"][1] - deployed_at)))

    intervals = [(phases["opened"][1], phases["resolved"][1] if "resolved" in phases else end)
                 for phases in incidents.values()]
    overlaps = sum(a_start < b_end and b_start < a_end
                   for (a_start, a_end), (b_start, b_end) in combinations(intervals, 2))
    production_shas = {sha for event, _ in production for sha in event["commits"]}
    rework_count = sum(event["unplanned"] and event["caused_by"] is not None for event, _ in production)
    deployment_count = len(production)
    return {
        "spec_version": "1.0.0",
        "window": {"from": window["from"], "to": window["to"]},
        "deployment_frequency_per_day": _ratio(deployment_count * 86400, _seconds(end - start)),
        "change_lead_time_seconds_p50": _median(lead_times),
        "failed_deployment_recovery_time_seconds_p50": _median(recovery_times),
        "change_fail_rate": _ratio(len(failures), deployment_count),
        "deployment_rework_rate": _ratio(rework_count, deployment_count),
        "counts": {
            "deployments": deployment_count,
            "successful_deployments": len(successes),
            "failed_deployments": len(failures),
            "recovered_failures": len(recovery_times),
            "open_failures": open_failures,
            "rework_deployments": rework_count,
            "lead_time_pairs": len(first_deployment),
            "changes": len(first_commit),
        },
        "anomalies": {
            "negative_lead_time_pairs": sum(value < 0 for value in raw_lead_times),
            "deployments_without_commits": sum(not event["commits"] for event, _ in production),
            "commits_never_on_main": sum(commits[sha][0]["branch"] != "main" for sha in production_shas),
            "revert_chains_collapsed": sum(event["reverts"] is not None for event, _ in commits.values()),
            "overlapping_incident_pairs": overlaps,
        },
        "ground_truth": {
            "changes_delivered": len(first_change_delivery),
            "true_change_lead_time_seconds_p50": _median(true_lead_times),
        },
    }
