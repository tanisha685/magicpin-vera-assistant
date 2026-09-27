"""
magicpin AI Challenge — Vera Bot Server
=======================================
High-performance FastAPI server exposing the 5 required challenge endpoints:
- GET  /v1/healthz
- GET  /v1/metadata
- POST /v1/context
- POST /v1/tick
- POST /v1/reply

Plus interactive dashboard routes for visualization, real-time testing, and simulation.

Usage:
    uvicorn bot:app --host 0.0.0.0 --port 8080 --reload
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import (
    ContextPushRequest, ContextPushResponse,
    TickRequest, TickResponse, ComposedAction,
    ReplyRequest, ReplyResponse,
    HealthzResponse, MetadataResponse
)
from context_store import ContextStore
from composer import composer, compose
from conversation_handlers import ConversationManager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vera.bot")

# App Initialization
app = FastAPI(
    title="magicpin Vera Assistant",
    description="Intelligent Merchant WhatsApp AI Assistant for magicpin AI Challenge",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
DATASET_DIR = Path(__file__).parent / "dataset"
context_store = ContextStore(DATASET_DIR)
conversation_manager = ConversationManager(context_store)


# =============================================================================
# CHALLENGE API ENDPOINTS (TECHNICAL CONTRACT)
# =============================================================================

@app.get("/v1/healthz", response_model=HealthzResponse)
async def healthz():
    """Liveness probe reporting uptime and counts of all loaded contexts."""
    uptime = int(time.time() - START_TIME)
    counts = context_store.counts()
    return HealthzResponse(
        status="ok",
        uptime_seconds=uptime,
        contexts_loaded=counts
    )


@app.get("/v1/metadata", response_model=MetadataResponse)
async def metadata():
    """Returns bot metadata, architecture, model identity, and submission info."""
    return MetadataResponse(
        team_name="Team Vera Pro",
        team_members=["Candidate"],
        model=composer.model or "Hybrid Frontier LLM + Expert Deterministic Engine",
        approach="4-Context Composer with Intent-Action State Machine, Taboo Guardrails & Canned Auto-Reply Backoff",
        contact_email="challenge@magicpin.in",
        version="1.0.0",
        submitted_at="2026-04-26T12:00:00Z"
    )


@app.post("/v1/context", response_model=ContextPushResponse)
async def push_context(req: ContextPushRequest):
    """
    Ingests category, merchant, customer, or trigger contexts.
    Guarantees idempotency and handles version conflicts.
    """
    accepted, reason_or_ack, cur_ver = context_store.set(
        scope=req.scope,
        context_id=req.context_id,
        version=req.version,
        payload=req.payload
    )

    if not accepted:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "accepted": False,
                "reason": reason_or_ack,
                "current_version": cur_ver
            }
        )

    return ContextPushResponse(
        accepted=True,
        ack_id=reason_or_ack,
        stored_at=datetime.utcnow().isoformat() + "Z"
    )


@app.post("/v1/tick", response_model=TickResponse)
async def tick(req: TickRequest):
    """
    Periodic wake-up endpoint. Bot inspects available triggers and emits proactive actions.
    """
    actions: List[ComposedAction] = []

    for trg_id in req.available_triggers:
        trigger = context_store.get("trigger", trg_id)
        if not trigger:
            logger.warning("Trigger context %s not found in store", trg_id)
            continue

        merchant_id = trigger.get("merchant_id")
        customer_id = trigger.get("customer_id")

        merchant = context_store.get("merchant", merchant_id) if merchant_id else None
        if not merchant:
            logger.warning("Merchant %s for trigger %s not found", merchant_id, trg_id)
            continue

        cat_slug = merchant.get("category_slug", "")
        category = context_store.get("category", cat_slug) or {}

        customer = context_store.get("customer", customer_id) if customer_id else None

        # Compose message
        composed = compose(category, merchant, trigger, customer)

        conv_id = f"conv_{merchant_id}_{trg_id}"
        if customer_id:
            conv_id = f"conv_{customer_id}_{trg_id}"

        # Initialize conversation state
        conversation_manager.get_or_create(conv_id, merchant_id, customer_id).add_turn(
            role=composed.get("send_as", "vera"),
            message=composed.get("body", "")
        )

        actions.append(ComposedAction(
            conversation_id=conv_id,
            merchant_id=merchant_id,
            customer_id=customer_id,
            send_as=composed.get("send_as", "vera"),
            trigger_id=trg_id,
            template_name=composed.get("template_name", "vera_generic_v1"),
            template_params=composed.get("template_params", [merchant.get("identity", {}).get("name", "Merchant")]),
            body=composed.get("body", ""),
            cta=composed.get("cta", "open_ended"),
            suppression_key=composed.get("suppression_key", f"suppress:{trg_id}"),
            rationale=composed.get("rationale", "Composed from 4-context framework.")
        ))

    return TickResponse(actions=actions)


@app.post("/v1/reply", response_model=ReplyResponse)
async def reply(req: ReplyRequest):
    """
    Multi-turn conversation reply endpoint. Handles merchant/customer responses synchronously.
    """
    res = conversation_manager.respond(
        conv_id=req.conversation_id,
        merchant_id=req.merchant_id,
        customer_id=req.customer_id,
        from_role=req.from_role,
        message=req.message,
        turn_number=req.turn_number
    )

    return ReplyResponse(
        action=res.get("action", "send"),
        body=res.get("body"),
        cta=res.get("cta"),
        wait_seconds=res.get("wait_seconds"),
        rationale=res.get("rationale", "Turn handled successfully.")
    )


@app.post("/v1/teardown")
async def teardown():
    """Optional teardown hook to wipe memory at test completion."""
    context_store.clear()
    return {"status": "cleared"}


# =============================================================================
# INTERACTIVE UI & DASHBOARD APIS
# =============================================================================

@app.get("/api/dashboard_stats")
async def dashboard_stats():
    """Returns overview stats for the UI."""
    return {
        "counts": context_store.counts(),
        "uptime": int(time.time() - START_TIME),
        "categories": list(context_store.get_all("category").keys()),
        "merchants": list(context_store.get_all("merchant").keys()),
        "triggers": list(context_store.get_all("trigger").keys()),
        "customers": list(context_store.get_all("customer").keys()),
        "active_conversations": len(conversation_manager.conversations)
    }


@app.get("/api/context/{scope}/{context_id}")
async def get_context_detail(scope: str, context_id: str):
    data = context_store.get(scope, context_id)
    if not data:
        raise HTTPException(status_code=404, detail="Context not found")
    return {"scope": scope, "context_id": context_id, "payload": data}


@app.post("/api/compose_custom")
async def compose_custom(req: Request):
    """Live composition endpoint for the interactive playground."""
    data = await req.json()
    cat_id = data.get("category_id")
    m_id = data.get("merchant_id")
    t_id = data.get("trigger_id")
    c_id = data.get("customer_id")

    trigger = context_store.get("trigger", t_id) if t_id else None
    if not trigger:
        trigger = {
            "id": "trg_custom",
            "scope": "merchant" if not c_id else "customer",
            "kind": data.get("kind", "curious_ask_due"),
            "source": "internal",
            "payload": data.get("payload", {})
        }

    merchant = context_store.get("merchant", m_id) if m_id else None
    if not merchant:
        merchant = {
            "merchant_id": "m_custom",
            "category_slug": cat_id or "restaurants",
            "identity": {"name": data.get("merchant_name", "Dr. Meera's Clinic"), "locality": "Lajpat Nagar", "city": "Delhi"},
            "performance": {"views": 2400, "calls": 25, "ctr": 0.032},
            "offers": [{"title": "Special Offer @ ₹299", "status": "active"}]
        }

    cat_slug = cat_id or merchant.get("category_slug", "dentists")
    category = context_store.get("category", cat_slug) or {"slug": cat_slug, "voice": {"tone": "peer_clinical"}}
    customer = context_store.get("customer", c_id) if c_id else None

    result = compose(category, merchant, trigger, customer)
    return {
        "inputs": {"category": category, "merchant": merchant, "trigger": trigger, "customer": customer},
        "composed": result
    }


@app.get("/api/test_pairs")
async def get_test_pairs():
    """Retrieve test pairs from dataset/test_pairs.json."""
    tp_file = DATASET_DIR / "test_pairs.json"
    if tp_file.exists():
        with open(tp_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pairs": []}


@app.post("/api/generate_submission_jsonl")
async def generate_submission_jsonl():
    """Run batch composition on all 30 test pairs and save to submission.jsonl."""
    tp_file = DATASET_DIR / "test_pairs.json"
    if not tp_file.exists():
        raise HTTPException(status_code=400, detail="test_pairs.json not found")

    with open(tp_file, "r", encoding="utf-8") as f:
        pairs = json.load(f).get("pairs", [])

    submission_lines = []
    out_file = Path(__file__).parent / "submission.jsonl"

    with open(out_file, "w", encoding="utf-8") as out_fp:
        for pair in pairs:
            t_id = pair.get("trigger_id")
            m_id = pair.get("merchant_id")
            c_id = pair.get("customer_id")
            test_id = pair.get("test_id")

            trigger = context_store.get("trigger", t_id) or {"id": t_id, "kind": "generic", "scope": "merchant"}
            merchant = context_store.get("merchant", m_id) or {"merchant_id": m_id, "category_slug": "restaurants", "identity": {"name": m_id}}
            cat_slug = merchant.get("category_slug", "restaurants")
            category = context_store.get("category", cat_slug) or {"slug": cat_slug}
            customer = context_store.get("customer", c_id) if c_id else None

            res = compose(category, merchant, trigger, customer)
            entry = {
                "test_id": test_id,
                "trigger_id": t_id,
                "merchant_id": m_id,
                "customer_id": c_id,
                "body": res.get("body"),
                "cta": res.get("cta"),
                "send_as": res.get("send_as"),
                "suppression_key": res.get("suppression_key"),
                "rationale": res.get("rationale")
            }
            submission_lines.append(entry)
            out_fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "count": len(submission_lines),
        "file": str(out_file),
        "items": submission_lines
    }


# =============================================================================
# DASHBOARD HTML INTERFACE
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard_view():
    """Serves the rich modern Vera Command Center UI."""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return HTMLResponse(content=open(html_file, "r", encoding="utf-8").read())
    return HTMLResponse(content="<h1>Vera Bot Running</h1><p>Check /v1/healthz</p>")


# Mount static directory if exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=8080, reload=True)
