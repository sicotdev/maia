import os
import httpx2
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from maia.gateway import GATEWAY_APIKEY, GATEWAY_URL, get_gateway_headers
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()


from html import escape


def _sse(event: str, html_fragment: str) -> str:
    # SSE does not allow raw line breaks inside a "data:" field,
    # so each HTML fragment line is prefixed with "data: ".
    lines = html_fragment.splitlines() or [""]
    payload = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{payload}\n\n"


@router.post("/chat/start")
async def chat_start(request: Request):
    """Step 1: receives the classic htmx form and returns the fragment
    containing the SSE container with the message encoded in the URL."""
    data = await request.form()
    user_message = data.get("message")
    previous_response_id = data.get("previous_response_id") or ""

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    from urllib.parse import urlencode

    qs = urlencode({"message": user_message, "previous_response_id": previous_response_id})

    html = f"""
    <div hx-ext="sse" sse-connect="/chat/stream?{qs}" sse-close="done">
      <div id="tools"></div>
      <div sse-swap="tool_call" hx-target="#tools" hx-swap="beforeend"></div>
      <div sse-swap="tool_result" hx-target="#tools" hx-swap="beforeend"></div>
      <div id="answer-raw"
           sse-swap="text_delta"
           hx-swap="beforeend"
           style="display:none"
           hx-on::after-swap="document.getElementById('answer').innerHTML = DOMPurify.sanitize(marked.parse(this.textContent, {{ breaks: true, gfm: true }}))"
      ></div>
      <div id="answer"></div>
      <div sse-swap="answer_error" hx-swap="beforeend" hx-target="#answer"></div>
      <div sse-swap="done" hx-swap="none"></div>
    </div>
    """
    return HTMLResponse(html)


@router.get("/chat/stream")
async def chat_stream(request: Request):
    """Step 2: opened by EventSource (GET only, no body)."""
    user_message = request.query_params.get("message")
    previous_response_id = request.query_params.get("previous_response_id") or None

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    headers = {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    payload = {
        "model": "hermes-llm",
        "input": user_message,
        "stream": True,
        "store": True,
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    async def event_generator():
        # Track in-progress function calls so we can reconstruct the name and arguments
        # once the argument stream finishes (they arrive as deltas).
        pending_calls = {}  # index -> {"name": ..., "arguments": "..."}
        response_id = None

        try:
            async with httpx2.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{GATEWAY_URL}/v1/responses",
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        logger.error(
                            f"Gateway HTTP Error: {response.status_code} - {body.decode(errors='replace')}"
                        )
                        yield _sse(
                            "answer_error",
                            "<div class='error'>Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée.</div>",
                        )
                        yield _sse("done", "")
                        return

                    current_event = None
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip("\n")

                        print(f"{raw_line}")  # Debugging line

                        if line.startswith("event:"):
                            current_event = line[len("event:"):].strip()
                            continue

                        if not line.startswith("data:"):
                            continue

                        raw_data = line[len("data:"):].strip()
                        if not raw_data:
                            continue

                        try:
                            event_data = json.loads(raw_data)
                        except json.JSONDecodeError:
                            # Payload is truncated or too long (see known issue with
                            # response.completed), so we ignore it; everything has already
                            # been reconstructed from the progressive events.
                            continue

                        if current_event == "response.created":
                            response_id = event_data.get("response", {}).get("id") or event_data.get("id")

                        elif current_event == "response.output_item.added":
                            item = event_data.get("item", {})
                            index = event_data.get("index")
                            if item.get("type") == "function_call":
                                yield _sse(
                                    "tool_call",
                                    f"<div class='tool-badge tool-running'>🔧 {escape(item.get('name') or '')}({escape(item.get('arguments') or '')})</div>",
                                )
                            elif item.get("type") == "function_call_output":
                                yield _sse(
                                    "tool_result",
                                    f"<div class='tool-badge tool-running'>output: {escape(str(item.get('output') or ''))}</div>",
                                )

                        elif current_event == "response.output_text.delta":
                            delta = event_data.get("delta", "")
                            if delta:
                                yield _sse("text_delta", escape(delta))

                        elif current_event == "response.completed":
                            # End-of-stream signal only: we do not read
                            # event_data["response"]["output"] (which may be very large or truncated),
                            # because everything has already been streamed.
                            break

                    # Out-of-band swap: update the hidden field in the main form so the next round
                    # sends the previous_response_id.
                    yield _sse(
                        "done",
                        f"<input type='hidden' id='previous_response_id' name='previous_response_id' "
                        f"value='{escape(response_id or '')}' hx-swap-oob='true'>",
                    )

        except httpx2.HTTPStatusError as e:
            logger.error(
                f"Gateway HTTP Error: {e.response.status_code} - {e.response.text}",
                exc_info=True,
            )
            yield _sse(
                "answer_error",
                "<div class='error'>Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée.</div>",
            )
            yield _sse("done", "")
        except Exception as e:
            logger.error(f"Unexpected error in chat_stream router: {str(e)}", exc_info=True)
            yield _sse(
                "answer_error",
                "<div class='error'>Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée.</div>",
            )
            yield _sse("done", "")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # évite le buffering si tu es derrière nginx
        },
    )


# Classic chat endpoint; returns the whole response at once.
@router.post("/chat")
async def chat(request: Request):
    data = await request.form()
    user_message = data.get("message")
    
    # Get the previous_response_id from the form data if it exists
    previous_response_id = data.get("previous_response_id")
 
    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")
 
    payload = {
        "model": "hermes-llm",
        "input": user_message,
        "store": True,  # request to keep the conversation history with previous_response_id
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id
 
    async with httpx2.AsyncClient(timeout=None) as client:
        error_message = "Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée."
 
        try:
            response = await client.post(
                f"{GATEWAY_URL}/v1/responses",
                headers=get_gateway_headers(),
                json=payload
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
                            #"call_id": item.get("call_id"),
                        }
                    )
                elif item_type == "function_call_output":
                    tool_steps.append(
                        {
                            "type": "tool_result",
                            #"call_id": item.get("call_id"),
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
                    "response_id": result.get("id"),  # to send back next turn as previous_response_id
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

@router.get("/chat/{session_id}")
async def get_chat_session(request: Request, session_id: str):

    print(f"Fetching chat session for session_id: {session_id}")  # Debugging line

    async with httpx2.AsyncClient(timeout=None) as client:
        
        try:
            response = await client.get(
                f"{GATEWAY_URL}/api/sessions/{session_id}/messages",
                headers=get_gateway_headers()
            )
            response.raise_for_status() 
            result = response.json()

            print(f"Fetched chat session data: {result}")  # Debugging line

            print(f"Loaded chat session messages: {len(result.get('data', []))}")  # Debugging line

            # Reformat the messages to include tool calls and results in a structured way.
            messages = []
            last_ai_message = None
            for msg in result.get("data", []):
                if msg.get("role") == "user":
                    if last_ai_message is not None:
                        messages.append(last_ai_message)
                        last_ai_message = None
                    messages.append({"role": "user", "content": msg.get("content"), "timestamp": msg.get("timestamp")})
                elif msg.get("role") == "assistant":
                    if last_ai_message is None:
                        last_ai_message = {
                            "role": "assistant",
                            "reasoning": msg.get("reasoning"),
                            "content": msg.get("content"),
                            "tool_steps": [],
                            "timestamp": msg.get("timestamp")
                        }
                    elif msg.get("content") is not None:
                        last_ai_message["content"] += msg.get("content")
                    if msg.get("tool_calls") is not None:
                        for tool_call in msg.get("tool_calls"):
                            last_ai_message["tool_steps"].append({
                                "type": "tool_call",
                                "name": tool_call.get("function", {}).get("name"),
                                "arguments": tool_call.get("function", {}).get("arguments"),
                            })
                    
                elif msg.get("role") == "tool":
                    # Set the output of the last tool call in the last AI message.
                    last_ai_message["tool_steps"][-1]["output"] = msg.get("content")

            if last_ai_message is not None:
                messages.append(last_ai_message)

            print(f"Formatted chat session messages: {messages}")  # Debugging line

            # TODO: we need the last message's response_id to send back as previous_response_id for the next turn.

            return templates.TemplateResponse(request=request, name="parts/chat_messages.html", context={"messages": messages})
        except Exception as e:
            logger.error(f"Unexpected error in get_chat_session: {str(e)}", exc_info=True)
            return templates.TemplateResponse(request=request, name="parts/chat_messages.html", context={"messages": [] })