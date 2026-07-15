import os
import httpx2
import json
import time
import uuid
import random
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from maia.gateway import GATEWAY_URL, get_gateway_headers
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()


from html import escape


def _sse(event: str, html_fragment: str) -> str:
    # SSE does not allow raw line breaks inside a "data:" field,
    # so each HTML fragment line is prefixed with "data: ".
    lines = html_fragment.split("\n")
    payload = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{payload}\n\n"

# Create an empty session
async def create_session() -> str:
    async with httpx2.AsyncClient(timeout=None) as client:

        headers = get_gateway_headers()

        print(f"creating new session")

        resp = await client.post(
            f"{GATEWAY_URL}/api/sessions",
            headers=headers,
            json={},
        )
        resp.raise_for_status()
        data = resp.json()

        return data["session"]

# Receives the classic htmx form and returns the chat_sse container for streaming the answer.
@router.post("/chat/start")
async def chat_start(request: Request):
    
    data = await request.form()
    user_message = data.get("message")
    session_id = data.get("session_id")

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    #We need to create the session
    session = None
    hx_swap = False
    if not session_id:
        hx_swap = True
        session = await create_session()
        session_id = session["id"]
        session["preview"] = user_message
        if len(session["preview"]) > 63:
            session["preview"] = session["preview"][:60] + "..."

    print(f"session_id is {session_id}")

    #Generate a unique message id
    message_id = uuid.uuid4().hex

    qs = urlencode({"message": user_message, "session_id": session_id })
    sse_url = f"/chat/stream?{qs}"
    
    return templates.TemplateResponse(request=request, name="chat/chat_sse.html", context={
        "sse_url": sse_url, 
        "msg": { "role": "user", "timestamp": time.time(), "content": escape(user_message) },
        "hx_swap": hx_swap, "session": session,
        "thinking_gif": f"static/gif/thinking_funny_{random.randint(0, 11)}.gif",
        "tmp_id": message_id
    })

# Step 2: opened by EventSource (GET only).
@router.get("/chat/stream")
async def chat_stream(request: Request):
    
    user_message = request.query_params.get("message")
    session_id = request.query_params.get("session_id")

    if not user_message or not session_id:
        raise HTTPException(status_code=400, detail="Invalid Parameters")

    headers = get_gateway_headers()

    async def event_generator():
        # Track in-progress function calls so we can reconstruct the name and arguments
        # once the argument stream finishes (they arrive as deltas).
        pending_calls = {}  # index -> {"name": ..., "arguments": "..."}

        try:
            async with httpx2.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{GATEWAY_URL}/api/sessions/{session_id}/chat/stream",
                    json={"input": user_message},
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
                    tool_index = 0
                    started = False
                    message_id = 0
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip("\n")

                        #print(f"{raw_line}")  # Debugging line

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

                        #if current_event == "run.started":
                        if current_event == "message.started":
                            #Started received
                            print("stream started")
                            started = True
                            print(event_data);
                            continue

                        #Send first_event after message.started received
                        if (started):
                            yield _sse("first_event", "<span class='spinner'></span>")
                            started = False

                        if current_event == "tool.started":
                            yield _sse(
                                "tool_call",
                                templates.get_template("chat/parts/chat_tool_call.html").render({
                                    "call": {
                                        "name": event_data.get("tool_name"),
                                        "arguments": event_data.get("args") or "",
                                        "output": "",
                                    },
                                    "sse_swap": f"tool_call_{tool_index}",
                                })
                            )
                            tool_index += 1

                        #TODO: no output until run.completed
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
                            #store the timestamp as id
                            message_id = int(event_data.get("ts"))

                        elif current_event == "run.completed":
                            timestamp = event_data.get('ts')
                            yield _sse(
                                "timestamp", 
                                f"<span class='timestamp'>{timestamp}</span>"
                            )

                            #TODO
                            print(event_data.get('usage'))

                            #TODO: no output or reasoning until run.completed
                            #Parse the tools outputs
                            tool_index = 0
                            reasoning = ""
                            for item in event_data.get('messages'):
                                msg_reasonning = item.get('reasoning')
                                if (msg_reasonning and msg_reasonning.lstrip()):
                                    if (reasoning == ""):
                                        reasoning = msg_reasonning
                                        yield _sse(
                                            "reasoning",
                                            templates.get_template("chat/parts/chat_reasoning.html").render({
                                                "msg": {
                                                    "reasoning": reasoning,
                                                }
                                            })
                                        )
                                    else:
                                        print(f"additionnal reasonning: {msg_reasonning}")
                                if (item.get('role') == "tool"):
                                    yield _sse(
                                        f"tool_call_{tool_index}",
                                        templates.get_template("chat/parts/chat_tool_call_output.html").render({
                                            "call": {
                                                "output": str(item.get("content") or ''),
                                            }
                                        })
                                    )
                                    tool_index += 1

                        elif current_event == "done":
                            print("stream done")
                            break

                    #yield real message_id
                    yield _sse("message_id", f"<input type='hidden' id='real_message_id' value='{message_id}'>")

                    #yield audio container with message_id
                    yield _sse(
                        "audio",
                        templates.get_template("chat/parts/chat_audio.html").render({
                            "msg": { "id": message_id }
                        })
                    )

                    #DONE
                    yield _sse(
                        "done",
                        "",
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
            "X-Accel-Buffering": "no",  # prevent buffering for nginx
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

            #print(f"Fetched chat session data: {result}")  # Debugging line

            print(f"Loaded chat session messages: {len(result.get('data', []))}")  # Debugging line

            # Reformat the messages to include tool calls and results in a structured way.
            messages = []
            last_ai_message = None
            for msg in result.get("data", []):
                if msg.get("role") == "user":
                    if last_ai_message is not None:
                        messages.append(last_ai_message)
                        last_ai_message = None
                    messages.append({"id": int(msg.get("timestamp")), "role": "user", "content": escape(msg.get("content")), "timestamp": msg.get("timestamp")})
                elif msg.get("role") == "assistant":
                    if last_ai_message is None:
                        last_ai_message = {
                            "id": int(msg.get("timestamp")),
                            "role": "assistant",
                            "reasoning": escape(msg.get("reasoning")),
                            "content": escape(msg.get("content")),
                            "tool_steps": [],
                            "timestamp": msg.get("timestamp")
                        }
                    else:
                        if msg.get("reasoning") and msg.get("reasoning").lstrip():
                            last_ai_message["reasoning"] += escape(msg.get("reasoning"))
                        if msg.get("content") is not None:
                            last_ai_message["content"] += escape(msg.get("content"))
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
                else:
                    print(f"unknown role:{msg.get('role')}")

            if last_ai_message is not None:
                messages.append(last_ai_message)

            #print(f"Formatted chat session messages: {messages}")  # Debugging line

            return templates.TemplateResponse(request=request, name="chat/chat_messages.html", context={"messages": messages, "session_id": session_id})

        except Exception as e:
            logger.error(f"Unexpected error in get_chat_session: {str(e)}", exc_info=True)
            return templates.TemplateResponse(request=request, name="chat/chat_messages.html", context={"messages": [] })