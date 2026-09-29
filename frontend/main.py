"""FastAPI proxy for Catholic Companion Agent talking to deployed Agent Runtime over A2A.

Bridges the senior-friendly Catholic Companion Web UI with the deployed
Agent Engine instance, providing Application Default Credentials authentication,
A2A JSON-RPC protocol communication, context reuse, and rich UI rendering.
"""

import os
import uuid
import json
import logging
import google.auth
import google.auth.transport.requests
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load deployment metadata
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
meta_path = os.path.join(AGENT_DIR, "deployment_metadata.json")
meta = {}
if os.path.exists(meta_path):
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        pass

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    meta.get(
        "remote_agent_runtime_id",
        "projects/602596533885/locations/us-central1/reasoningEngines/7099862690142617600",
    ),
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", meta.get("agent_directory", "app"))
AGENT_APP_NAME = os.environ.get("AGENT_APP_NAME", "oiramen_app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# Try both oiramen_app and AGENT_DIRECTORY
A2A_URL = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_APP_NAME}"
)
DEFAULT_PORT = 8080
_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI(title="Catholic Companion Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    logger.exception("Error processing request")
    return JSONResponse(
        status_code=200,
        content={
            "parts": [
                {
                    "kind": "text",
                    "text": f"Peace be with you. (Notice: {type(exc).__name__}: {exc})",
                }
            ]
        },
    )


# Map user_id to active A2A contextId
_user_contexts: dict[str, str] = {}


def _extract_parts(raw_parts: list) -> list[dict]:
    out: list[dict] = []
    for p in raw_parts:
        if not isinstance(p, dict):
            continue
        kind = p.get("kind")
        text = p.get("text")
        data = p.get("data")
        metadata = p.get("metadata") or {}

        if text:
            out.append({"kind": "text", "text": text})
        elif data is not None and metadata.get("mimeType") == _A2UI_MIME:
            out.append({"kind": "a2ui", "data": data})
        elif kind == "text" and text:
            out.append({"kind": "text", "text": text})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "").strip()
    user_id = body.get("user_id") or "default_user"
    parts: list[dict] = []

    message_payload = {
        "messageId": str(uuid.uuid4()),
        "role": "user",
        "parts": [{"kind": "text", "text": message}],
    }
    if context_id := _user_contexts.get(user_id):
        message_payload["contextId"] = context_id

    rpc_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": message_payload
        },
    }

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        resp = await client.post(A2A_URL, json=rpc_payload)
        resp.raise_for_status()
        res_json = resp.json()

        result = res_json.get("result") or {}
        new_context = result.get("contextId")
        if new_context:
            _user_contexts[user_id] = new_context

        # Extract from artifacts
        for artifact in result.get("artifacts") or []:
            parts.extend(_extract_parts(artifact.get("parts") or []))

        # If empty, check history messages from agent
        if not parts:
            for item in result.get("history") or []:
                if item.get("role") == "agent":
                    parts.extend(_extract_parts(item.get("parts") or []))

    if not parts:
        parts = [
            {
                "kind": "text",
                "text": "May the Lord bless you and keep you. How may I accompany you in prayer today?",
            }
        ]

    return JSONResponse({"parts": parts})


# Direct helper tool endpoints
try:
    from app.companion_tools import (
        get_daily_liturgical_readings,
        get_daily_mass,
        get_user_prayer_intentions,
        get_traditional_prayer,
        get_saint_of_the_day,
    )

    @app.get("/api/gospel")
    async def api_gospel(lang: str = "en"):
        return get_daily_liturgical_readings(language=lang)

    @app.get("/api/mass")
    async def api_mass(lang: str = "en"):
        return get_daily_mass(language=lang)

    @app.get("/api/intentions")
    async def api_intentions(user_name: str = ""):
        return get_user_prayer_intentions(user_name=user_name)

    @app.get("/api/traditional_prayer")
    async def api_traditional_prayer(prayer: str = "our_father", lang: str = "en"):
        return get_traditional_prayer(prayer_name=prayer, language=lang)

    @app.get("/api/saint")
    async def api_saint(query: str = "", lang: str = "en"):
        return get_saint_of_the_day(saint_query=query, language=lang)
except Exception as e:
    logger.warning(f"Could not load direct helper tool endpoints: {e}")

# Mount static directory for Catholic Companion UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
