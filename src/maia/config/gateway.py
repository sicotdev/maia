import os
from fastapi import Cookie
from maia.config.settings import PROFILES, LLM_ENDPOINTS

GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL")
GATEWAY_APIKEY = os.getenv("HERMES_GATEWAY_APIKEY")
CUSTOM_URL = f"{os.getenv('CUSTOM_GATEWAY_URL')}:{os.getenv('CUSTOM_GATEWAY_PORT')}"
CUSTOM_APIKEY = os.getenv("CUSTOM_GATEWAY_APIKEY")


# Port depends of profile choice
def get_gateway_params(
    hermesProfile: int = Cookie(0, ge=0, lt=len(PROFILES)),
    llmEndpoint: int = Cookie(0, ge=0, lt=len(LLM_ENDPOINTS)),
) -> str:

    if LLM_ENDPOINTS[llmEndpoint]["id"] == "hermes":
        url = f"{GATEWAY_URL}:{PROFILES[hermesProfile]['port']}"
        api_key = GATEWAY_APIKEY
        is_custom = False
    else:
        url = CUSTOM_URL
        api_key = CUSTOM_APIKEY
        is_custom = True
    return {
        "url": url,
        "headers": {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "is_custom": is_custom,
    }
