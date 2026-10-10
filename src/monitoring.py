# ai-generated: 100% - Codex implemented KB search and tuned the histogram to the recorded Lab 3 measurement.
"""KB search and RED metrics, with buckets based on the wojbra1993 profile."""

import os
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated

import httpx
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CollectorRegistry, Histogram, generate_latest
from starlette.types import ASGIApp, Message, Receive, Scope, Send


# 10 October 2026, load 3: p50=0.0193 s, p99=0.1592 s, p99.9=0.1998 s.
# 28 finite boundaries; 10 ms steps cover the slow mode and at least +/-20%
# around measured p99. The latency SLI counts requests <=0.2 s directly.
# The unmodified initial AI ladder is preserved in ai-first-draft.md.
BUCKETS = (0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.06, 0.08, 0.1,
           0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.2, 0.21,
           0.22, 0.23, 0.24, 0.3, 0.5, 1, 2.5, 5)
REGISTRY = CollectorRegistry()
REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "Time from request entry to the final response body, in seconds.",
    ("http_request_method", "http_route", "http_response_status_code"),
    buckets=BUCKETS,
    registry=REGISTRY,
)


def create_kb_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=os.environ.get("KB_INDEX_URL", "http://kb-index:8080").rstrip("/") + "/",
        timeout=httpx.Timeout(3.0),
        limits=httpx.Limits(max_connections=128, max_keepalive_connections=64),
        follow_redirects=False,
        trust_env=False,
    )


@asynccontextmanager
async def lifespan(app):
    # Reuse connections across requests; the async client does not block other
    # searches while kb-index delays a response. HTTPX does not retry by default.
    async with create_kb_client() as client:
        app.state.kb_client = client
        yield


class RequestDurationMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        status_code = 500
        observed = False

        def observe_once():
            nonlocal observed
            if observed:
                return
            observed = True
            # Routing has run by the time the response is sent. Never use
            # scope['path'] here: unmatched paths and ticket IDs are unbounded.
            route = getattr(scope.get("route"), "path", "unmatched")
            REQUEST_DURATION.labels(
                http_request_method=scope["method"],
                http_route=route,
                http_response_status_code=str(status_code),
            ).observe(perf_counter() - started)

        async def send_observed(message: Message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                observe_once()

        try:
            await self.app(scope, receive, send_observed)
        except Exception:
            # The outer ServerErrorMiddleware supplies the 500 response. If a
            # response already finished (e.g. a background task fails), do not
            # add a second observation or replace its original status.
            observe_once()
            raise


router = APIRouter()


def upstream_unavailable():
    return JSONResponse(
        status_code=502,
        content={"error": {"code": "upstream_unavailable", "message": "Knowledge-base index unavailable"}},
    )


@router.get("/kb/search")
async def kb_search(request: Request, q: Annotated[str, Query(min_length=1, max_length=200)]):
    try:
        upstream = await request.app.state.kb_client.get("search", params={"q": q})
        if upstream.status_code != 200:
            return upstream_unavailable()
        hits = upstream.json()["hits"]
    except (httpx.RequestError, ValueError, KeyError, TypeError):
        return upstream_unavailable()
    return {"query": q, "hits": hits}


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(
        content=generate_latest(REGISTRY),
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
    )
