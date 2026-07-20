import os
from fastapi import Cookie
from maia.config.settings import PROFILES

GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL")
GATEWAY_APIKEY = os.getenv("HERMES_GATEWAY_APIKEY")

#Port depends of profile choice
def get_gateway_url(hermesProfile: int = Cookie(0, ge=0, lt=len(PROFILES))) -> str:
    port = PROFILES[hermesProfile]['port']
    return f"{GATEWAY_URL}:{port}"

def get_gateway_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json",
    }
