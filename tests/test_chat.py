import pytest
from fastapi.testclient import TestClient
from maia.app import app
import os
from unittest.mock import patch, Mock, AsyncMock

client = TestClient(app)

# Environment variable configuration for testing
@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(os.environ, {
        "HERMES_GATEWAY_URL": "http://fake-gateway.com",
        "HERMES_GATEWAY_APIKEY": "fake-key"
    }):
        yield

@patch("maia.chat.router.httpx2.AsyncClient.post")
def test_chat_success(mock_post):
    """Simulate a successful response from the Hermes gateway."""
    # Create a regular Mock for the response object
    # We use Mock because .json() is a synchronous method in httpx
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "Hello! I am the Maia AI."}}
        ]
    }
    # The mock_post (AsyncMock) returns this mock_response
    mock_post.return_value = mock_response

    response = client.post("/chat", data={"message": "Hello"})
    assert response.status_code == 200
    assert "Hello! I am the Maia AI." in response.text

@patch("maia.chat.router.httpx2.AsyncClient.post")
def test_chat_error(mock_post):
    """Simulate a 500 error from the Hermes gateway."""
    from httpx2 import HTTPStatusError
    
    # Create a regular Mock for the error response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    # Simulate the raise_for_status exception
    mock_response.raise_for_status.side_effect = HTTPStatusError(
        "Error", request=None, response=mock_response
    )
    
    mock_post.return_value = mock_response

    response = client.post("/chat", data={"message": "Hello"})
    assert response.status_code == 200
    assert "Error: 500" in response.text
