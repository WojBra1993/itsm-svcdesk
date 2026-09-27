# ai-generated: 100% - Gemini drafted the service; Codex corrected Lab 2 metrics, validation and event ordering.
import os, uuid, datetime, zoneinfo
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Optional
from .dora import MetricsError, compute_metrics, parse_instant

app = FastAPI()
WARSAW = zoneinfo.ZoneInfo("Europe/Warsaw")
db = {}

@app.exception_handler(RequestValidationError)
async def val_err(r, exc):
    return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": "bad request"}})

@app.exception_handler(404)
async def not_found(r, exc):
    return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "not found"}})

def get_now(r: Request):
    if os.getenv("SVCDESK_TEST_CLOCK") in ("1", "true"):
        tc = r.headers.get("X-Test-Clock")
        if tc:
            try:
                return datetime.datetime.fromisoformat(tc.replace("Z", "+00:00"))
            except:
                raise HTTPException(400, {"error": {"code": "bad_request"}})
    return datetime.datetime.now(datetime.timezone.utc)

def add_biz(start, hours):
    dt = start.astimezone(WARSAW)
    if dt.weekday() >= 5:
        dt = dt.replace(hour=8, minute=0, second=0, microsecond=0) + datetime.timedelta(days=7 - dt.weekday())
    elif dt.hour >= 16:
        dt = dt.replace(hour=8, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        if dt.weekday() >= 5: dt += datetime.timedelta(days=2)
    elif dt.hour < 8:
        dt = dt.replace(hour=8, minute=0, second=0, microsecond=0)
    rem = hours * 3600
    while rem > 0:
        eod = dt.replace(hour=16, minute=0, second=0, microsecond=0)
        sec = int((eod - dt).total_seconds())
        if rem <= sec:
            dt += datetime.timedelta(seconds=rem)
            break
        else:
            rem -= sec
            dt = eod + datetime.timedelta(hours=16)
            if dt.weekday() >= 5: dt += datetime.timedelta(days=2)
    return dt.astimezone(datetime.timezone.utc)

class Reporter(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    vip: bool = False

class TicketIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=4000)
    reporter: Reporter
    impact: int = Field(..., ge=1, le=3)
    urgency: int = Field(..., ge=1, le=3)
    related_to: Optional[str] = None

@app.get("/health")
def health(): return {"status": "ok", "service": "svcdesk"}

@app.post("/tickets", status_code=201)
async def create(t: TicketIn, req: Request):
    now = get_now(req)
    m = {(1,1):"P1",(1,2):"P2",(1,3):"P3",(2,1):"P2",(2,2):"P3",(2,3):"P4",(3,1):"P3",(3,2):"P4",(3,3):"P4"}
    pri = m[(t.impact, t.urgency)]
    if t.reporter.vip and pri in ("P3", "P4"): pri = "P2"
    
    if pri == "P1":
        ack_due = now + datetime.timedelta(minutes=15)
        res_due = now + datetime.timedelta(hours=4)
    else:
        ack_t = {"P2":1, "P3":4, "P4":8}
        res_t = {"P2":8, "P3":24, "P4":72}
        ack_due = add_biz(now, ack_t[pri])
        res_due = add_biz(now, res_t[pri])
        
    tid = str(uuid.uuid4())
    doc = {
        "id": tid, "title": t.title, "description": t.description, "reporter": t.reporter.model_dump(),
        "impact": t.impact, "urgency": t.urgency, "priority": pri, "state": "new",
        "created_at": now.isoformat().replace("+00:00", "Z"), "acknowledged_at": None,
        "resolved_at": None, "closed_at": None, "related_to": t.related_to,
        "sla": {"ack_due_at": ack_due.isoformat().replace("+00:00", "Z"), "resolve_due_at": res_due.isoformat().replace("+00:00", "Z")}
    }
    db[tid] = doc
    return doc

@app.get("/tickets")
def list_t(state: Optional[str]=None, priority: Optional[str]=None):
    return [v for v in db.values() if (not state or v["state"]==state) and (not priority or v["priority"]==priority)]

@app.get("/tickets/{tid}")
def get_t(tid: str):
    if tid not in db: raise HTTPException(404, {"error": {"code": "not_found"}})
    return db[tid]

@app.get("/tickets/{tid}/sla")
def get_sla(tid: str, req: Request):
    if tid not in db: raise HTTPException(404, {"error": {"code": "not_found"}})
    t = db[tid]
    now = get_now(req)
    ack_due = datetime.datetime.fromisoformat(t["sla"]["ack_due_at"].replace("Z","+00:00"))
    res_due = datetime.datetime.fromisoformat(t["sla"]["resolve_due_at"].replace("Z","+00:00"))
    
    ack_at = datetime.datetime.fromisoformat(t["acknowledged_at"].replace("Z","+00:00")) if t["acknowledged_at"] else None
    res_at = datetime.datetime.fromisoformat(t["resolved_at"].replace("Z","+00:00")) if t["resolved_at"] else None
    
    ack_b = (ack_at and ack_at > ack_due) or (not ack_at and now > ack_due)
    res_b = (res_at and res_at > res_due) or (not res_at and now > res_due)
    
    paused = False
    if t["state"] not in ("resolved", "closed") and t["priority"] != "P1":
        local_now = now.astimezone(WARSAW)
        if local_now.weekday() >= 5 or local_now.hour < 8 or local_now.hour >= 16:
            paused = True
            
    return {"priority": t["priority"], "ack_due_at": t["sla"]["ack_due_at"], "resolve_due_at": t["sla"]["resolve_due_at"], "ack_breached": ack_b, "resolve_breached": res_b, "paused": paused}

@app.post("/tickets/{tid}/{action}")
def do_action(tid: str, action: str, req: Request):
    if tid not in db: raise HTTPException(404, {"error": {"code": "not_found"}})
    t = db[tid]
    now = get_now(req)
    now_str = now.isoformat().replace("+00:00", "Z")
    
    if action == "ack":
        if t["state"] != "new": raise HTTPException(409, {"error": {"code": "err"}})
        t["state"] = "acknowledged"
        t["acknowledged_at"] = now_str
    elif action == "start":
        if t["state"] != "acknowledged": raise HTTPException(409, {"error": {"code": "err"}})
        t["state"] = "in_progress"
    elif action == "resolve":
        if t["state"] != "in_progress": raise HTTPException(409, {"error": {"code": "err"}})
        t["state"] = "resolved"
        t["resolved_at"] = now_str
    elif action == "close":
        if t["state"] != "resolved": raise HTTPException(409, {"error": {"code": "err"}})
        t["state"] = "closed"
        t["closed_at"] = now_str
    elif action == "reopen":
        if t["state"] != "resolved": raise HTTPException(409, {"error": {"code": "err"}})
        res_at = datetime.datetime.fromisoformat(t["resolved_at"].replace("Z","+00:00"))
        if (now - res_at).total_seconds() > 7*86400: raise HTTPException(409, {"error": {"code": "err"}})
        t["state"] = "in_progress"
        t["resolved_at"] = None
        t["closed_at"] = None
    else:
        raise HTTPException(404, {"error": {"code": "not_found"}})
    return t


# --- LAB 2: DORA METRICS & TICKET EVENTS ---

@app.post("/dora/metrics")
async def calculate_dora_metrics(request: Request):
    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": "Invalid JSON"}})
    try:
        return compute_metrics(payload)
    except MetricsError as exc:
        return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": str(exc)}})


@app.get("/dora/ticket-events")
async def export_ticket_events():
    ticket_events = []
    for tid, t in db.items():
        priority = t.get("priority", "P4")
        
        if t.get("created_at"):
            ticket_events.append({"ticket_id": tid, "phase": "created", "priority": priority, "state": "new", "at": t["created_at"]})
        if t.get("acknowledged_at"):
            ticket_events.append({"ticket_id": tid, "phase": "acknowledged", "priority": priority, "state": "acknowledged", "at": t["acknowledged_at"]})
        if t.get("resolved_at"):
            ticket_events.append({"ticket_id": tid, "phase": "resolved", "priority": priority, "state": "resolved", "at": t["resolved_at"]})
        if t.get("closed_at"):
            ticket_events.append({"ticket_id": tid, "phase": "closed", "priority": priority, "state": "closed", "at": t["closed_at"]})
            
    ticket_events.sort(key=lambda x: (parse_instant(x["at"]), x["ticket_id"]))
    return JSONResponse(content=ticket_events)