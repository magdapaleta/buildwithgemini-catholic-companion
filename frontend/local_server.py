"""Local development server and proxy for the Catholic Companion Agent.

Directly bridges the mobile-first senior-friendly UI to the local ADK Runner
so you have zero network latency and seamless stateful conversation.
"""

import os
import uuid
import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

from app.agent import app as adk_app, root_agent
from app.companion_tools import (
    get_daily_liturgical_readings,
    get_daily_mass,
    save_prayer_intention,
    get_user_prayer_intentions,
    get_traditional_prayer,
    get_saint_of_the_day,
    generate_custom_prayer_card_image,
)

app = FastAPI(title="Catholic Companion Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.app_utils import services

session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

runner = Runner(
    app=adk_app,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=services.get_memory_service(),
    auto_create_session=True,
)

# In-memory session tracking per browser client
_user_sessions = {}

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        user_id = body.get("user_id") or "default_user"

        if user_id not in _user_sessions:
            session = await session_service.create_session(
                app_name=adk_app.name,
                user_id=user_id
            )
            _user_sessions[user_id] = session.id
        
        session_id = _user_sessions[user_id]

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        )

        response_text = ""
        # Run turn through ADK runner
        async for event in runner.run_async(
            session_id=session_id,
            user_id=user_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

        if not response_text.strip():
            response_text = "May the Lord bless you and keep you. How may I accompany you in prayer today?"

        return JSONResponse(
            status_code=200,
            content={
                "parts": [
                    {"kind": "text", "text": response_text}
                ]
            }
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=200,
            content={
                "parts": [
                    {"kind": "text", "text": f"Peace be with you. (Error: {str(exc)})"}
                ]
            }
        )

# Direct helper endpoints for one-touch actions to minimize typing for older users
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

# Mount frontend static directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
