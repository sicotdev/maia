import httpx2
import json
import time
import uuid
import random
from typing import Any
from html import escape
from urllib.parse import urlencode
from fastapi import APIRouter, Form, Query, Path, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from maia.config.gateway import get_gateway_url, get_gateway_headers
from maia.config.logging_config import logger
from maia.config.templating import templates

MAX_GIF_NUMBER = 17

router = APIRouter()


def _sse(event: str, html_fragment: str) -> str:
    # SSE does not allow raw line breaks inside a "data:" field,
    # so each HTML fragment line is prefixed with "data: ".
    lines = html_fragment.split("\n")
    payload = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{payload}\n\n"


def _sse_error():
    # Make sure we're always sending the first event and done event
    return (
        _sse("first_event", "<span class='spinner'></span>")
        + _sse(
            "answer_error",
            "<div class='error'>Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée.</div>",
        )
        + _sse("done", "")
    )


# Create an empty session
async def create_session(gateway_url: str) -> dict[str, Any]:
    async with httpx2.AsyncClient(timeout=None) as client:
        headers = get_gateway_headers()

        print("creating new session")
        print(f"{gateway_url}")

        resp = await client.post(
            f"{gateway_url}/api/sessions",
            headers=headers,
            json={},
        )
        resp.raise_for_status()
        data = resp.json()

        return data["session"]


# Receives the classic htmx form and returns the chat_sse container for streaming the answer.
@router.post("/start")
async def chat_start(
    request: Request,
    gateway_url: str = Depends(get_gateway_url),
    message: str = Form(..., min_length=1),
    session_id: str = Form(None),
):

    # We need to create the session
    session = None
    hx_swap = False
    if not session_id:
        hx_swap = True
        session = await create_session(gateway_url)
        session_id = session["id"]
        session["preview"] = message
        if len(session["preview"]) > 63:
            session["preview"] = session["preview"][:60] + "..."

    print(f"session_id is {session_id}")

    # Generate a unique message id
    message_id = uuid.uuid4().hex

    qs = urlencode({"message": message, "session_id": session_id})
    sse_url = f"/chat/stream?{qs}"

    return templates.TemplateResponse(
        request=request,
        name="chat/chat_sse.html",
        context={
            "sse_url": sse_url,
            "msg": {
                "role": "user",
                "timestamp": time.time(),
                "content": escape(message),
            },
            "hx_swap": hx_swap,
            "session": session,
            "thinking_gif": f"static/gif/thinking_funny_{random.randint(0, MAX_GIF_NUMBER)}.gif",
            "tmp_id": message_id,
        },
    )


# Step 2: opened by EventSource (GET only).
@router.get("/stream")
async def chat_stream(
    gateway_url: str = Depends(get_gateway_url),
    message: str = Query(..., min_length=1),
    session_id: str = Query(..., min_length=1),
):

    headers = get_gateway_headers()

    async def event_generator():

        try:
            async with httpx2.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{gateway_url}/api/sessions/{session_id}/chat/stream",
                    json={"input": message},
                    headers=headers,
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        logger.error(
                            f"Gateway HTTP Error: {response.status_code} - {body.decode(errors='replace')}"
                        )
                        yield _sse_error()
                        return

                    current_event = None
                    tool_index = 0
                    started = False
                    message_id = 0
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip("\n")

                        # print(f"{raw_line}")  # Debugging line

                        if line.startswith("event:"):
                            current_event = line[len("event:") :].strip()
                            continue

                        if not line.startswith("data:"):
                            continue

                        raw_data = line[len("data:") :].strip()
                        if not raw_data:
                            continue

                        try:
                            event_data = json.loads(raw_data)
                        except json.JSONDecodeError:
                            # Payload is truncated or too long (see known issue with
                            # response.completed), so we ignore it; everything has already
                            # been reconstructed from the progressive events.
                            continue

                        # if current_event == "run.started":
                        if current_event == "message.started":
                            # Started received
                            print("stream started")
                            started = True
                            # print(event_data);
                            continue

                        # Send first_event after message.started received
                        if started:
                            yield _sse("first_event", "<span class='spinner'></span>")
                            started = False

                        if current_event == "tool.started":
                            yield _sse(
                                "tool_call",
                                templates.get_template(
                                    "chat/parts/chat_tool_call.html"
                                ).render(
                                    {
                                        "call": {
                                            "name": event_data.get("tool_name"),
                                            "arguments": event_data.get("args") or "",
                                            "output": "",
                                        },
                                        "sse_swap": f"tool_call_{tool_index}",
                                    }
                                ),
                            )
                            tool_index += 1

                        # TODO: no output until run.completed
                        # elif current_event == "tool.completed":

                        #     yield _sse(
                        #         f"tool_call_{tool_index}",
                        #         templates.get_template("chat/parts/chat_tool_call_output.html").render({
                        #             "call": {
                        #                 "output": str(event_data.get("output") or ''),
                        #             }
                        #         })
                        #     )

                        elif current_event == "assistant.delta":
                            delta = event_data.get("delta", "")
                            if delta:
                                yield _sse("text_delta", escape(delta))

                        elif current_event == "assistant.completed":
                            # store the timestamp as id
                            message_id = int(event_data.get("ts"))

                        elif current_event == "run.completed":
                            timestamp = event_data.get("ts")
                            yield _sse(
                                "timestamp",
                                f"<span class='timestamp'>{timestamp}</span>",
                            )

                            # TODO
                            print(event_data.get("usage"))

                            # TODO: no output or reasoning until run.completed
                            # Parse the tools outputs
                            tool_index = 0
                            reasoning = ""
                            for item in event_data.get("messages"):
                                msg_reasonning = item.get("reasoning")
                                if msg_reasonning and msg_reasonning.lstrip():
                                    reasoning += msg_reasonning
                                    yield _sse(
                                        "reasoning",
                                        templates.get_template(
                                            "chat/parts/chat_reasoning.html"
                                        ).render(
                                            {
                                                "msg": {
                                                    "reasoning": reasoning,
                                                }
                                            }
                                        ),
                                    )

                                if item.get("role") == "tool":
                                    yield _sse(
                                        f"tool_call_{tool_index}",
                                        templates.get_template(
                                            "chat/parts/chat_tool_call_output.html"
                                        ).render(
                                            {
                                                "call": {
                                                    "output": str(
                                                        item.get("content") or ""
                                                    ),
                                                }
                                            }
                                        ),
                                    )
                                    tool_index += 1

                        elif current_event == "done":
                            print("stream done")
                            break

                    # yield real message_id
                    yield _sse(
                        "message_id",
                        f"<input type='hidden' id='real_message_id' value='{message_id}'>",
                    )

                    # yield audio container with message_id
                    yield _sse(
                        "audio",
                        templates.get_template("chat/parts/chat_audio.html").render(
                            {"msg": {"id": message_id}}
                        ),
                    )

                    # DONE
                    yield _sse(
                        "done",
                        "",
                    )

        except httpx2.HTTPStatusError as e:
            logger.error(
                f"Gateway HTTP Error: {e.response.status_code} - {e.response.text}",
                exc_info=True,
            )
            yield _sse_error()
        except Exception as e:
            logger.error(
                f"Unexpected error in chat_stream router: {str(e)}", exc_info=True
            )
            yield _sse_error()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # prevent buffering for nginx
        },
    )


# Classic chat endpoint; returns the whole response at once.
# TODO: check this to call LMStudio directly or any openAPI compatible (we won't use it for hermes anymore)
# I think we will need the whole context, not just previous_response_id
@router.post("/response")
async def chat(
    gateway_url: str = Depends(get_gateway_url),
    message: str = Form(..., min_length=1),
    previous_response_id: str = Form(...),
):

    payload = {
        "model": "hermes-llm",
        "input": message,
        "store": True,  # request to keep the conversation history with previous_response_id
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    async with httpx2.AsyncClient(timeout=None) as client:
        error_message = (
            "Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée."
        )

        try:
            response = await client.post(
                f"{gateway_url}/v1/responses",
                headers=get_gateway_headers(),
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            print(f"Chat response received: {result}")  # Debugging line

            # TODO: no reasoning?
            # TODO: use stream: true

            output = result.get("output", [])

            tool_steps = []
            ai_response = ""

            for item in output:
                item_type = item.get("type")

                if item_type == "function_call":
                    tool_steps.append(
                        {
                            "type": "tool_call",
                            "name": item.get("name"),
                            "arguments": item.get("arguments"),
                            # "call_id": item.get("call_id"),
                        }
                    )
                elif item_type == "function_call_output":
                    tool_steps.append(
                        {
                            "type": "tool_result",
                            # "call_id": item.get("call_id"),
                            "output": item.get("output"),
                        }
                    )
                elif item_type == "message":
                    for content_part in item.get("content", []):
                        if content_part.get("type") == "output_text":
                            ai_response += content_part.get("text", "")

            # TODO: return HTML using the same template.

            return JSONResponse(
                {
                    "role": "assistant",
                    "content": ai_response,
                    "tool_steps": tool_steps,  # to display on the frontend as "cards" of progress
                    "response_id": result.get(
                        "id"
                    ),  # to send back next turn as previous_response_id
                    "usage": result.get("usage", {}),
                    "error": False,
                }
            )

        except httpx2.HTTPStatusError as e:
            logger.error(
                f"Gateway HTTP Error: {e.response.status_code} - {e.response.text}",
                exc_info=True,
            )
            return JSONResponse(
                {
                    "role": "assistant",
                    "content": error_message,
                    "error": True,
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in chat router: {str(e)}", exc_info=True)
            return JSONResponse(
                {
                    "role": "assistant",
                    "content": error_message,
                    "error": True,
                }
            )


@router.get("/{session_id}")
async def get_chat_session(
    request: Request,
    gateway_url: str = Depends(get_gateway_url),
    session_id: str = Path(..., min_length=1),
):

    print(f"Fetching chat session for session_id: {session_id}")  # Debugging line

    async with httpx2.AsyncClient(timeout=None) as client:
        try:
            response = await client.get(
                f"{gateway_url}/api/sessions/{session_id}/messages",
                headers=get_gateway_headers(),
            )
            response.raise_for_status()
            result = response.json()

            # print(f"Fetched chat session data: {result}")  # Debugging line

            print(
                f"Loaded chat session messages: {len(result.get('data', []))}"
            )  # Debugging line

            # Reformat the messages to include tool calls and results in a structured way.
            messages = []
            last_ai_message = None
            for msg in result.get("data", []):
                if msg.get("role") == "user":
                    if last_ai_message is not None:
                        messages.append(last_ai_message)
                        last_ai_message = None
                    messages.append(
                        {
                            "id": int(msg.get("timestamp")),
                            "role": "user",
                            "content": msg.get("content"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )
                elif msg.get("role") == "assistant":
                    if last_ai_message is None:
                        last_ai_message = {
                            "id": int(msg.get("timestamp")),
                            "role": "assistant",
                            "reasoning": msg.get("reasoning"),
                            "content": msg.get("content"),
                            "tool_steps": [],
                            "timestamp": msg.get("timestamp"),
                        }
                    else:
                        if msg.get("reasoning") and msg.get("reasoning").lstrip():
                            last_ai_message["reasoning"] += msg.get("reasoning")
                        if msg.get("content") is not None:
                            last_ai_message["content"] += msg.get("content")
                    if msg.get("tool_calls") is not None:
                        for tool_call in msg.get("tool_calls"):
                            last_ai_message["tool_steps"].append(
                                {
                                    "type": "tool_call",
                                    "name": tool_call.get("function", {}).get("name"),
                                    "arguments": tool_call.get("function", {}).get(
                                        "arguments"
                                    ),
                                }
                            )

                elif msg.get("role") == "tool":
                    # Set the output of the last tool call in the last AI message.
                    if last_ai_message is None:
                        raise Exception("Tool result without previous message")
                    last_ai_message["tool_steps"][-1]["output"] = msg.get("content")
                else:
                    print(f"unknown role:{msg.get('role')}")

            if last_ai_message is not None:
                messages.append(last_ai_message)

            # print(f"Formatted chat session messages: {messages}")  # Debugging line

            return templates.TemplateResponse(
                request=request,
                name="chat/chat_messages.html",
                context={"messages": messages, "session_id": session_id},
            )

        except Exception as e:
            logger.error(
                f"Unexpected error in get_chat_session: {str(e)}", exc_info=True
            )
            return templates.TemplateResponse(
                request=request,
                name="chat/chat_messages.html",
                context={"messages": []},
            )
