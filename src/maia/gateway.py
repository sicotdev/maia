import os

GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL")
GATEWAY_APIKEY = os.getenv("HERMES_GATEWAY_APIKEY")


def get_gateway_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json",
    }
