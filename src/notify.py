"""WhatsApp outbound via CallMeBot."""
from __future__ import annotations

import urllib.parse
import requests

from .config import CALLMEBOT_API_KEY, WHATSAPP_PHONE, require


def send_whatsapp(text: str, timeout: int = 30) -> dict:
    """Send a WhatsApp message. Returns {"ok": bool, "status": int, "body": str}."""
    api = require("CALLMEBOT_API_KEY", CALLMEBOT_API_KEY)
    phone = require("WHATSAPP_PHONE", WHATSAPP_PHONE)
    # CallMeBot has a soft ~1000-char practical limit; longer messages 503.
    if len(text) > 950:
        text = text[:940] + "…[…]"
    url = (
        "https://api.callmebot.com/whatsapp.php"
        f"?phone={urllib.parse.quote(phone)}"
        f"&text={urllib.parse.quote(text)}"
        f"&apikey={urllib.parse.quote(api)}"
    )
    try:
        r = requests.get(url, timeout=timeout)
        return {"ok": r.ok, "status": r.status_code, "body": r.text[:300]}
    except Exception as exc:
        return {"ok": False, "status": 0, "body": str(exc)}
