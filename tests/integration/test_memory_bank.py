# Copyright 2026 Google LLC
#
# Integration tests verifying Vertex AI Memory Bank integration.

import asyncio
import time
import uuid
import pytest
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from app.agent import root_agent

PROJECT_ID = "qwiklabs-gcp-04-cbd6b324d319"
LOCATION = "us-central1"
AGENT_ENGINE_ID = "8481341875838517248"


async def wait_for_memory(
    memory_service: VertexAiMemoryBankService,
    app_name: str,
    user_id: str,
    query: str,
    timeout_seconds: int = 30,
    poll_interval: int = 3,
):
    """Poll Memory Bank until the background LLM extraction finishes and returns results."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        res = await memory_service.search_memory(
            app_name=app_name,
            user_id=user_id,
            query=query,
        )
        if res and res.memories:
            return res
        await asyncio.sleep(poll_interval)
    return None


@pytest.mark.asyncio
async def test_agent_runner_memory_persists_and_preloads() -> None:
    """End-to-end test: Runner saves facts to Memory Bank and recalls them in a new session."""
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    app_name = "app"

    session_service = InMemorySessionService()
    memory_service = VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=AGENT_ENGINE_ID,
    )

    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        memory_service=memory_service,
        app_name=app_name,
    )

    # --- SESSION 1: User introduces themselves with their name and patron saint ---
    session1 = await session_service.create_session(app_name=app_name, user_id=test_user_id)
    msg1 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Hello, my name is Brother Francis and my patron saint is Saint Francis of Assisi.")],
    )

    events1 = []
    async for event in runner.run_async(
        new_message=msg1,
        user_id=test_user_id,
        session_id=session1.id,
    ):
        events1.append(event)

    assert len(events1) > 0, "Expected runner to produce events in session 1"

    # Poll until Memory Bank completes background extraction (typically ~10-15s)
    memory_res = await wait_for_memory(
        memory_service=memory_service,
        app_name=app_name,
        user_id=test_user_id,
        query="Francis Assisi",
        timeout_seconds=40,
    )

    assert memory_res is not None, f"Expected Memory Bank to extract memories for user {test_user_id}"
    assert len(memory_res.memories) > 0, "Expected at least 1 extracted memory"

    memory_text = " ".join(
        part.text
        for m in memory_res.memories
        if m.content and m.content.parts
        for part in m.content.parts
        if part.text
    )
    assert "Francis" in memory_text, f"Expected 'Francis' in stored memory: {memory_text}"

    # --- SESSION 2: Brand new session, PreloadMemoryTool should preload the name ---
    session2 = await session_service.create_session(app_name=app_name, user_id=test_user_id)
    msg2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Do you remember my name?")],
    )

    events2 = []
    async for event in runner.run_async(
        new_message=msg2,
        user_id=test_user_id,
        session_id=session2.id,
    ):
        events2.append(event)

    session2_text = " ".join(
        part.text
        for e in events2
        if e.content and e.content.parts
        for part in e.content.parts
        if part.text
    )
    assert "Francis" in session2_text, (
        f"Expected agent to recall 'Francis' in session 2 without being told, got: {session2_text}"
    )
