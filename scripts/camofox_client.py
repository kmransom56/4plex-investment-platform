import requests, time, json
from typing import List, Dict

BASE_URL = "http://localhost:9377"


def _request(method: str, path: str, **kwargs) -> Dict:
    url = f"{BASE_URL}{path}"
    r = requests.request(method, url, **kwargs)
    r.raise_for_status()
    if r.headers.get("content-type", "").startswith("application/json"):
        return r.json()
    return {}


def start_browser():
    _request("POST", "/start")


def create_tab(user_id: str, session_key: str = "default", url: str | None = None) -> str:
    payload = {"userId": user_id, "sessionKey": session_key}
    if url:
        payload["url"] = url
    res = _request("POST", "/tabs", json=payload)
    return res["tabId"]


def navigate(tab_id: str, user_id: str, url: str):
    _request(
        "POST",
        f"/tabs/{tab_id}/navigate",
        json={"userId": user_id, "url": url},
    )
    time.sleep(2)


def snapshot(tab_id: str, user_id: str) -> Dict:
    return _request(
        "GET",
        f"/tabs/{tab_id}/snapshot",
        params={"userId": user_id, "format": "text"},
    )


def click(tab_id: str, user_id: str, ref: str | None = None, selector: str | None = None):
    """Click an element either by its snapshot ``ref`` or by a CSS ``selector``.

    The original Camofox API accepts both fields; the thin wrapper previously only
    supported ``ref``. Adding ``selector`` lets us click inputs directly without
    having to parse the snapshot for a ref ID.
    """
    payload: Dict[str, str] = {"userId": user_id}
    if ref:
        payload["ref"] = ref
    if selector:
        payload["selector"] = selector
    _request(
        "POST",
        f"/tabs/{tab_id}/click",
        json=payload,
    )
    time.sleep(1)


def type_text(tab_id: str, user_id: str, text: str, selector: str | None = None):
    payload = {"userId": user_id, "text": text}
    if selector:
        payload["selector"] = selector
    _request("POST", f"/tabs/{tab_id}/type", json=payload)
    time.sleep(1)


def press(tab_id: str, user_id: str, key: str):
    _request("POST", f"/tabs/{tab_id}/press", json={"userId": user_id, "key": key})
    time.sleep(1)


def extract_links(tab_id: str, user_id: str) -> List[Dict]:
    return _request(
        "GET",
        f"/tabs/{tab_id}/links",
        params={"userId": user_id},
    )["links"]

def wait_for(tab_id: str, user_id: str, selector: str, timeout: int = 5000) -> None:
    """Wait until an element matching ``selector`` appears (or timeout).

    ``timeout`` is in milliseconds; the Camofox API defaults to 30 000 ms if omitted.
    """
    _request(
        "POST",
        f"/tabs/{tab_id}/wait",
        json={"userId": user_id, "selector": selector, "timeout": timeout},
    )
    time.sleep(0.5)
