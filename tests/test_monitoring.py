# ai-generated: 100% - Codex wrote contract, timing, concurrency and cardinality tests for Lab 3.
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from src import monitoring
from src.main import app


HITS = [{"id": "article-1", "title": "VPN recovery", "score": 0.75}]
NAME = "http_server_request_duration_seconds"


@pytest.fixture
def kb(monkeypatch):
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"query": "upstream echo", "hits": HITS})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(monitoring, "create_kb_client", lambda: httpx.AsyncClient(
        base_url="http://kb-index:8080/", transport=transport, timeout=3.0))
    with TestClient(app) as client:
        yield client, calls


def samples(client):
    response = client.get("/metrics", headers={"Accept": "text/plain;version=0.0.4"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    return {(s.name, tuple(sorted(s.labels.items()))): s.value
            for family in text_string_to_metric_families(response.text)
            for s in family.samples}


def count(client, route, status, suffix="_count"):
    labels = tuple(sorted({"http_request_method": "GET", "http_route": route,
                           "http_response_status_code": str(status)}.items()))
    return samples(client).get((NAME + suffix, labels), 0)


def test_search_preserves_hits_and_encodes_query_without_caching(kb):
    client, calls = kb
    query = "vpn drops & logowanie + zażółć?"
    before = count(client, "/kb/search", 200)
    for _ in range(2):
        response = client.get("/kb/search", params={"q": query})
        assert response.status_code == 200
        assert response.json() == {"query": query, "hits": HITS}
    assert len(calls) == 2
    assert all(r.method == "GET" and r.url.path == "/search" for r in calls)
    assert all(list(r.url.params.items()) == [("q", query)] for r in calls)
    assert count(client, "/kb/search", 200) - before == 2


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "x" * 201}])
def test_invalid_query_is_counted_but_never_calls_index(kb, params):
    client, calls = kb
    before = count(client, "/kb/search", 422)
    response = client.get("/kb/search", params=params)
    assert response.status_code == 422
    assert isinstance(response.json()["error"], dict)
    assert calls == []
    assert count(client, "/kb/search", 422) - before == 1


@pytest.mark.parametrize("length", [1, 200])
def test_query_length_boundaries_are_accepted(kb, length):
    client, calls = kb
    assert client.get("/kb/search", params={"q": "x" * length}).status_code == 200
    assert len(calls) == 1


@pytest.mark.parametrize("failure", [503, 301, 404, "timeout", "connection"])
def test_upstream_failures_are_counted_502_without_retry(monkeypatch, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("mock timeout", request=request)
        if failure == "connection":
            raise httpx.ConnectError("mock connection failure", request=request)
        return httpx.Response(failure, headers={"Location": "http://kb-index:8080/other"})

    monkeypatch.setattr(monitoring, "create_kb_client", lambda: httpx.AsyncClient(
        base_url="http://kb-index:8080/", transport=httpx.MockTransport(handler)))
    with TestClient(app) as client:
        before = count(client, "/kb/search", 502)
        response = client.get("/kb/search", params={"q": "force-error-itsmlab"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "upstream_unavailable"
        assert len(calls) == 1
        assert count(client, "/kb/search", 502) - before == 1


def test_histogram_labels_and_scrapes_do_not_create_observations(kb):
    client, _ = kb
    client.get("/health")
    before = samples(client)
    after = samples(client)
    assert after == before
    for (name, labels), value in after.items():
        if not name.startswith(NAME):
            continue
        expected = {"http_request_method", "http_route", "http_response_status_code"}
        if name.endswith("_bucket"):
            expected.add("le")
        assert set(dict(labels)) == expected


def test_thousand_unique_probe_requests_add_no_series(kb):
    client, _ = kb
    for path in ("/itsmlab-probe/warmup", "/tickets/warmup", "/health?itsmlab-probe=warmup"):
        client.get(path)
    before = set(samples(client))
    for _ in range(250):
        client.get(f"/itsmlab-probe/{uuid4()}")
        client.get(f"/tickets/{uuid4()}")
    for _ in range(500):
        client.get(f"/health?itsmlab-probe={uuid4()}")
    after = samples(client)
    assert set(after) - before == set()
    routes = {dict(labels)["http_route"] for name, labels in after if name == NAME + "_count"}
    assert "/tickets/{tid}" in routes
    assert "unmatched" in routes
    assert all("?" not in route and "itsmlab-probe" not in route for route in routes)


def test_timer_includes_final_stream_chunk_in_seconds(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(monitoring, "perf_counter", lambda: clock[0])
    observed = []
    fake_histogram = SimpleNamespace(labels=lambda **kwargs: SimpleNamespace(observe=observed.append))
    monkeypatch.setattr(monitoring, "REQUEST_DURATION", fake_histogram)

    async def streaming(scope, receive, send):
        scope["route"] = SimpleNamespace(path="/stream/{id}")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        clock[0] += 0.25
        await send({"type": "http.response.body", "body": b"a", "more_body": True})
        assert observed == []
        clock[0] += 0.5
        await send({"type": "http.response.body", "body": b"b", "more_body": False})

    async def no_op(*args):
        pass

    asyncio.run(monitoring.RequestDurationMiddleware(streaming)(
        {"type": "http", "path": "/stream/example", "method": "GET"}, no_op, no_op))
    assert observed == [0.75]


def test_parallel_searches_wait_for_upstream_without_serializing(monkeypatch):
    async def scenario():
        started = 0
        all_started = asyncio.Event()

        async def handler(request):
            nonlocal started
            started += 1
            if started == 16:
                all_started.set()
            await asyncio.wait_for(all_started.wait(), timeout=3)
            return httpx.Response(200, json={"hits": HITS})

        monkeypatch.setattr(monitoring, "create_kb_client", lambda: httpx.AsyncClient(
            base_url="http://kb-index:8080/", transport=httpx.MockTransport(handler)))
        async with monitoring.lifespan(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://svcdesk") as client:
                responses = await asyncio.gather(*[
                    client.get("/kb/search", params={"q": f"parallel {i}"}) for i in range(16)])
        assert started == 16
        assert all(response.status_code == 200 for response in responses)

    asyncio.run(scenario())


def test_configured_index_client_uses_required_timeout_and_url(monkeypatch):
    monkeypatch.setenv("KB_INDEX_URL", "http://alternate-index:8081")

    async def scenario():
        async with monitoring.create_kb_client() as client:
            assert str(client.base_url) == "http://alternate-index:8081/"
            assert min(client.timeout.as_dict().values()) >= 2
            assert client.follow_redirects is False

    asyncio.run(scenario())


def test_buckets_resolve_a_band_around_the_measured_profile():
    # Real first load 3 result, not the synthetic latency of the unit tests.
    measured_q = 0.1592
    boundaries = monitoring.BUCKETS
    assert len(boundaries) <= 30
    assert list(boundaries) == sorted(set(boundaries))
    assert min(boundaries) > 0
    assert 0.2 in boundaries  # The latency SLI must count at an exact boundary.
    lower = measured_q * 0.8
    upper = measured_q * 1.2
    for lo, hi in zip((0, *boundaries), boundaries):
        if hi < lower or lo >= upper:
            continue
        assert hi - lo <= 0.2 * lower
