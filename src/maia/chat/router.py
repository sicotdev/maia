import os
import httpx2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from maia.gateway import GATEWAY_URL, get_gateway_headers
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()

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

            #TODO: no reasonning?
            #TODO: use stream: true
            
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
 
            #TODO: return html using the same template

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

            #Reformat the messages to include tool calls and results in a structured way
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
                    #Set output of the last tool call in the last AI message
                    last_ai_message["tool_steps"][-1]["output"] = msg.get("content")

            if last_ai_message is not None:
                messages.append(last_ai_message)

            print(f"Formatted chat session messages: {messages}")  # Debugging line

            #TODO: we need the last message's response_id to send back as previous_response_id for the next turn

            return templates.TemplateResponse(request=request, name="parts/chat_messages.html", context={"messages": messages})
        except Exception as e:
            logger.error(f"Unexpected error in get_chat_session: {str(e)}", exc_info=True)
            return templates.TemplateResponse(request=request, name="parts/chat_messages.html", context={"messages": [] })