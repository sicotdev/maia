import json
import random
import time
import uuid
from html import escape
from itertools import islice
from typing import Any
from urllib.parse import urlencode

import httpx2
from fastapi import APIRouter, Depends, Form, Path, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from maia.config.gateway import get_custom_gateway, get_gateway_params
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
async def create_session(gateway_params: dict[str, Any]) -> dict[str, Any]:
    async with httpx2.AsyncClient(timeout=None) as client:
        headers = gateway_params["headers"]

        print("creating new session")

        resp = await client.post(
            f"{gateway_params['url']}/api/sessions",
            headers=headers,
            json={},
        )
        resp.raise_for_status()
        data = resp.json()

        return data["session"]


# Create a run
async def create_run(
    gateway_params: dict[str, Any],
    message: str,
    session_id: str,
) -> dict[str, Any]:
    async with httpx2.AsyncClient(timeout=None) as client:
        headers = gateway_params["headers"]

        # Get conversation history for the run
        # Test
        # TODO: doesn't work, tool_calls and "role": "tool" disappears
        # conversation_history = [
        #     {"role": "user", "content": "On va effectuer un test."},
        #     {
        #         "role": "assistant",
        #         "content": "J'utilise l'outil",
        #         "tool_calls": [
        #             {
        #                 "id": "5V4Agj2HAcWJh8zpvrxPQMzSNH78aTIg",
        #                 "call_id": "5V4Agj2HAcWJh8zpvrxPQMzSNH78aTIg",
        #                 "type": "function",
        #                 "function": {
        #                     "name": "skill_view",
        #                     "arguments": '{"name":"project-discovery"}',
        #                 },
        #             }
        #         ],
        #     },
        #     {
        #         "role": "tool",
        #         "tool_call_id": "5V4Agj2HAcWJh8zpvrxPQMzSNH78aTIg",
        #         "content": "Projet trouvé: Maia",
        #     },
        #     {"role": "assistant", "content": "C'est fait."},
        # ]
        # conversation_history = await get_session_messages(gateway_params, session_id)

        print("creating run")

        resp = await client.post(
            f"{gateway_params['url']}/v1/runs",
            headers=headers,
            json={
                "input": message,
                "session_id": session_id,  # TODO: should work when PR 62750 is accepted
                # "conversation_history": conversation_history,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data


# Get session messages
async def get_session_messages(gateway_params: dict[str, Any], session_id: str):

    async with httpx2.AsyncClient(timeout=None) as client:
        try:
            response = await client.get(
                f"{gateway_params['url']}/api/sessions/{session_id}/messages",
                headers=gateway_params["headers"],
            )
            response.raise_for_status()
            result = response.json()

            # print(f"Fetched chat session data: {result}")  # Debugging line

            print(
                f"Loaded chat session messages: {len(result.get('data', []))}"
            )  # Debugging line

            messages = result.get("data", [])
            return messages

        except Exception as e:
            logger.error(
                f"Unexpected error in get_session_messages: {str(e)}", exc_info=True
            )
            return []


# Receives the classic htmx form and returns the chat_sse container for streaming the answer.
@router.post("/start")
async def chat_start(
    request: Request,
    gateway_params: str = Depends(get_gateway_params),
    message: str = Form(..., min_length=1),
    session_id: str = Form(None),
    previous_response_id: str = Form(None),
    is_voicecall: bool = Form(False),
):

    session = None
    hx_swap = False

    # We need to create the session
    if not session_id and not gateway_params["is_custom"]:
        hx_swap = True
        session = await create_session(gateway_params)
        session_id = session["id"]
        session["preview"] = message
        session["last_active"] = session["started_at"]
        if len(session["preview"]) > 63:
            session["preview"] = session["preview"][:60] + "..."

    # print(f"new session: {session}")

    # Create a run
    # TODO: doesn't work for now as the session history is lost (see https://github.com/NousResearch/hermes-agent/pull/62750)
    # run = await create_run(gateway_params, message, session_id)
    # print(run)
    # run_id = run.get("run_id")
    # qs = urlencode({"run_id": run_id})
    # sse_url = f"/chat/run?{qs}"

    # # Test
    # async with httpx2.AsyncClient(timeout=None) as client:
    #     resp = await client.get(
    #         f"{gateway_params['url']}/v1/runs/{run_id}",
    #         headers=gateway_params["headers"],
    #     )
    #     resp.raise_for_status()
    #     data = resp.json()
    #     print(data)

    params = {
        "message": message,
        "is_voicecall": is_voicecall,
    }
    if previous_response_id:
        params["previous_response_id"] = previous_response_id
    if session_id:
        params["session_id"] = session_id

    qs = urlencode(params)
    sse_url = f"/chat/stream?{qs}"

    # Generate a tmp unique message id for audio chunks
    message_id = uuid.uuid4().hex

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


# Stream ai response
@router.get("/stream")
async def chat_stream(
    gateway_params: str = Depends(get_gateway_params),
    message: str = Query(..., min_length=1),
    session_id: str = Query(None),
    previous_response_id: str = Query(None),
    is_voicecall: bool = Query(False),
):
    payload = {
        "model": "hermes-llm",
        "input": message,
        "store": True,  # request to keep the conversation history with previous_response_id
        "stream": True,
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    # Phone call instructions
    if is_voicecall:
        payload["instructions"] = (
            "This is a phone call in french, keep your response short and casual. You're a woman, User is a man."
        )
        payload["reasoning"] = {"effort": "none"}

    # Call normal v1/response with previous_response_id, with no session save
    if gateway_params["is_custom"]:
        url = "v1/responses"
    else:
        url = f"api/sessions/{session_id}/chat/stream"

    async def event_generator():

        try:
            async with httpx2.AsyncClient(timeout=None) as client:
                startTime = time.time()
                async with client.stream(
                    "POST",
                    f"{gateway_params['url']}/{url}",
                    json=payload,
                    headers=gateway_params["headers"],
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
                    first_event = False
                    message_id = 0
                    response_id = None
                    delta_received = False
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

                        # TODO: do we want this? (hermes not giving it for now)
                        # Could use the same logic as answer_raw
                        # response.reasoning_text.delta

                        # if current_event == "run.started":
                        if current_event == "message.started":
                            # Started received
                            print("stream started")
                            # print(event_data);
                            continue

                        # First event received
                        if not started:
                            print("first_event")
                            # response.created or run.started
                            print(f"{current_event} : {event_data}")
                            started = True
                            continue

                        # Fire first event only after really started
                        if not first_event:
                            if current_event == "response.in_progress":
                                continue
                            first_event = True
                            print(f"{current_event} : {event_data}")
                            yield _sse("first_event", "<span class='spinner'></span>")

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

                        elif (
                            current_event == "assistant.delta"
                            or current_event == "response.output_text.delta"
                        ):
                            delta = event_data.get("delta", "")
                            if delta:
                                delta_received = True
                                yield _sse("text_delta", escape(delta))

                        elif current_event == "assistant.completed":
                            # No delta means it's an error message
                            if not delta_received:
                                print(escape(event_data.get("content")))

                        elif current_event == "response.reasoning_text.done":
                            reasoning = event_data.get("text")
                            yield _sse(
                                "reasoning",
                                templates.get_template(
                                    "chat/parts/chat_reasoning.html"
                                ).render({"msg": {"reasoning": reasoning}}),
                            )

                        elif (
                            current_event == "run.completed"
                            or current_event == "response.completed"
                        ):
                            if current_event == "response.completed":
                                response = event_data.get("response")
                                timestamp = response.get("completed_at")
                                usage = response.get("usage")
                                response_id = response.get("id")
                            else:
                                timestamp = event_data.get("ts")
                                usage = event_data.get("usage")
                            # store the timestamp as id
                            message_id = int(timestamp)

                            yield _sse(
                                "message-header",
                                f"""<span class='timestamp'>{timestamp}</span>
                                <span class='elapsed-time'>{int(timestamp - startTime)} s</span>
                                <span class='token-count'>{usage["output_tokens"]} tokens</span>""",
                            )

                            yield _sse(
                                "context_tokens",
                                f"<input type='hidden' id='context_tokens' value='{usage['input_tokens']}'>",
                            )

                            # TODO: no tool outputs or reasoning until run.completed
                            # Parse the tools outputs
                            tool_index = 0
                            reasoning = ""
                            for item in event_data.get("messages", []):
                                msg_reasoning = item.get("reasoning")
                                if msg_reasoning and msg_reasoning.lstrip():
                                    # TODO: sometimes contains reasoning of previous turns
                                    # print(msg_reasoning)
                                    reasoning += msg_reasoning
                                    yield _sse(
                                        "reasoning",
                                        templates.get_template(
                                            "chat/parts/chat_reasoning.html"
                                        ).render({"msg": {"reasoning": reasoning}}),
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

                            print("stream done")
                            break

                        elif current_event == "done":
                            print("stream done")
                            break

                    # yield real message_id
                    yield _sse(
                        "message_id",
                        f"<input type='hidden' id='real_message_id' value='{message_id}'>",
                    )

                    if response_id:
                        yield _sse(
                            "response_id",
                            f"<input type='hidden' id='response_id' value='{response_id}'>",
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # prevent buffering for nginx
        },
    )


# Stream using /v1/runs/
@router.get("/run")
async def chat_run(
    gateway_params: str = Depends(get_gateway_params),
    run_id: str = Query(..., min_length=1),
):

    async def event_generator():

        try:
            async with httpx2.AsyncClient(timeout=None) as client:
                startTime = time.time()
                async with client.stream(
                    "GET",
                    f"{gateway_params['url']}/v1/runs/{run_id}/events",
                    headers=gateway_params["headers"],
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
                    delta_received = False
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip("\n")

                        print(f"{raw_line}")  # Debugging line

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

                        if not started:
                            yield _sse("first_event", "<span class='spinner'></span>")
                            started = True

                        current_event = event_data.get("event")

                        # if current_event == "run.started":
                        if current_event == "message.started":
                            # Started received
                            print("stream started")
                            started = True
                            # print(event_data);
                            continue

                        # Send first_event after message.delta received
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
                                            "name": event_data.get("tool"),
                                            "arguments": event_data.get("preview")
                                            or "",
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

                        elif current_event == "message.delta":
                            delta = event_data.get("delta", "")
                            if delta:
                                delta_received = True
                                yield _sse("text_delta", escape(delta))

                        elif current_event == "run.completed":
                            timestamp = event_data.get("timestamp")
                            message_id = timestamp
                            usage = event_data.get("usage")
                            yield _sse(
                                "message-header",
                                f"""<span class='timestamp'>{timestamp}</span>
                                <span class='elapsed-time'>{int(timestamp - startTime)} s</span>
                                <span class='token-count'>{usage["output_tokens"]} tokens</span>""",
                            )

                            print(f"context : {usage['input_tokens']}")

                            yield _sse(
                                "context_tokens",
                                f"<input type='hidden' id='context_tokens' value='{usage['input_tokens']}'>",
                            )

                            # No delta means it's an error message
                            if not delta_received:
                                print(escape(event_data.get("output")))

                            # TODO: no tool outputs or reasoning AT ALL
                            # Parse the tools outputs
                            # tool_index = 0
                            # reasoning = ""
                            # for item in event_data.get("messages"):
                            #     msg_reasoning = item.get("reasoning")
                            #     if msg_reasoning and msg_reasoning.lstrip():
                            #         reasoning += msg_reasoning
                            #         yield _sse(
                            #             "reasoning",
                            #             templates.get_template(
                            #                 "chat/parts/chat_reasoning.html"
                            #             ).render(
                            #                 {
                            #                     "msg": {
                            #                         "reasoning": reasoning,
                            #                     }
                            #                 }
                            #             ),
                            #         )

                            #     if item.get("role") == "tool":
                            #         yield _sse(
                            #             f"tool_call_{tool_index}",
                            #             templates.get_template(
                            #                 "chat/parts/chat_tool_call_output.html"
                            #             ).render(
                            #                 {
                            #                     "call": {
                            #                         "output": str(
                            #                             item.get("content") or ""
                            #                         ),
                            #                     }
                            #                 }
                            #             ),
                            #         )
                            #         tool_index += 1

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
                    # TODO: need to get the full message with api/session again LOL
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
# Used to call LMStudio directly or any openAPI compatible (we don't use it for hermes anymore)
# use previous_response_id to chain, but conversions are not saved
# @router.post("/response")
async def get_response(
    request: Request,
    gateway_params: dict[str, Any],
    message: str,
    previous_response_id: str,
    is_voicecall: bool,
):

    payload = {
        "model": "hermes-llm",
        "input": message,
        "store": True,  # request to keep the conversation history with previous_response_id
        # "stream": True, TODO stream
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    # Phone call instructions
    if is_voicecall:
        payload["instructions"] = (
            "This is a phone call in french, keep your response short and casual. You're a woman, User is a man."
        )
        payload["reasoning"] = {"effort": "none"}

    async with httpx2.AsyncClient(timeout=None) as client:
        error_message = (
            "Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée."
        )

        try:
            response = await client.post(
                f"{gateway_params['url']}/v1/responses",
                headers=gateway_params["headers"],
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            print(f"Chat response received: {result}")  # Debugging line

            output = result.get("output", [])

            tool_steps = []
            ai_response = ""
            reasoning = ""

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
                if item_type == "reasoning":
                    for content_part in item.get("content", []):
                        if content_part.get("type") == "reasoning_text":
                            reasoning += content_part.get("text", "")

            return templates.TemplateResponse(
                request=request,
                name="chat/chat_messages.html",
                context={
                    "previous_response_id": result.get("id"),
                    "messages": [
                        {
                            "role": "user",
                            "timestamp": time.time(),
                            "content": escape(message),
                        },
                        {
                            "id": result.get("completed_at"),
                            "role": "assistant",
                            "timestamp": result.get("completed_at"),
                            "reasoning": reasoning,
                            "tool_steps": tool_steps,
                            "content": ai_response,
                            "context_tokens": result.get("usage").get("input_tokens"),
                        },
                    ],
                },
            )

        # TODO: no JSON
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
    gateway_params: str = Depends(get_gateway_params),
    session_id: str = Path(..., min_length=1),
):

    print(f"Fetching chat session for session_id: {session_id}")  # Debugging line

    messages_raw = await get_session_messages(gateway_params, session_id)
    messages = get_formated_messages(messages_raw)

    # print(f"Formatted chat session messages: {messages}")  # Debugging line

    return templates.TemplateResponse(
        request=request,
        name="chat/chat_messages.html",
        context={"messages": messages, "session_id": session_id},
    )


async def generate_summary_title(
    gateway_params: dict[str, Any],
    session_id: str,
):

    print(f"Generating session title for session_id: {session_id}")  # Debugging line

    messages_raw = await get_session_messages(gateway_params, session_id)
    messages = get_formated_messages(messages_raw)

    # Construct input
    input = []
    for msg in islice(messages, 10):
        input.append({"role": msg["role"], "content": msg["content"]})

    input.append(
        {
            "role": "user",
            "content": "Génère un titre pour cette conversation de 64 caractères maximum (ton message ne doit contenir que le titre)",
        }
    )

    payload = {"model": "hermes-llm", "input": input, "reasoning": {"effort": "none"}}

    custom_gateway = get_custom_gateway()

    async with httpx2.AsyncClient(timeout=None) as client:
        response = await client.post(
            f"{custom_gateway['url']}/v1/responses",
            headers=custom_gateway["headers"],
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

        print(f"Chat response received: {result}")  # Debugging line

        output = result.get("output", [])

        ai_response = ""
        for item in output:
            item_type = item.get("type")
            if item_type == "message":
                for content_part in item.get("content", []):
                    if content_part.get("type") == "output_text":
                        ai_response += content_part.get("text", "")

        print(f"Title: {ai_response}")  # Debugging line

        return ai_response


# Reformat the messages to include tool calls and results in a structured way.
def get_formated_messages(messages_list: list):
    messages = []
    last_ai_message = None
    for msg in messages_list:
        # print(msg)
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
            # TODO: msg.get('token_count') is None
            if last_ai_message is None:
                last_ai_message = {
                    "id": int(msg.get("timestamp")),
                    "role": "assistant",
                    "reasoning": msg.get("reasoning") or "",
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
                            "arguments": tool_call.get("function", {}).get("arguments"),
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

    return messages
