import requests
import os
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "")
TIMEOUT = 120  # seconds — MCP server may be sleeping on free tier


def get_mcp_url() -> str:
    """Get MCP server URL from environment"""
    url = MCP_SERVER_URL.rstrip("/")
    if not url:
        raise RuntimeError(
            "MCP_SERVER_URL not set in .env. "
            "Set it to your deployed MCP server URL."
        )
    return url


def wake_up_server() -> bool:
    """
    Ping MCP server to wake it up (Render free tier sleeps).
    Returns True if server is alive.
    """
    url = get_mcp_url()
    try:
        print(f"  Connecting to MCP server at {url}...")
        response = requests.get(f"{url}/", timeout=TIMEOUT)
        if response.status_code == 200:
            print(f"  ✓ MCP server is alive")
            return True
        return False
    except requests.exceptions.Timeout:
        print(f"  ⚠ MCP server timed out — it may be waking up")
        return False
    except Exception as e:
        raise RuntimeError(f"Cannot connect to MCP server: {e}")


def call_mcp(endpoint: str, payload: dict) -> dict:
    """
    Call an MCP server endpoint with retry on timeout.
    Returns the response JSON.
    """
    url = get_mcp_url()
    full_url = f"{url}/{endpoint.lstrip('/')}"

    for attempt in range(2):
        try:
            response = requests.post(
                full_url,
                json=payload,
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise RuntimeError(
                    f"Google Doc not found. Check GOOGLE_DOC_ID in .env"
                )
            elif response.status_code == 403:
                raise RuntimeError(
                    f"No edit access to Google Doc. "
                    f"Make sure you own the doc."
                )
            elif response.status_code == 401:
                raise RuntimeError(
                    f"Google auth token expired. "
                    f"Re-run auth.py and update GOOGLE_TOKEN_JSON on Render."
                )
            else:
                raise RuntimeError(
                    f"MCP server error {response.status_code}: "
                    f"{response.text[:200]}"
                )

        except requests.exceptions.Timeout:
            if attempt == 0:
                print(f"  ⚠ Request timed out, retrying...")
            else:
                raise RuntimeError(
                    "MCP server timed out after 2 attempts. "
                    "Try again in a few minutes."
                )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"MCP call failed: {e}")