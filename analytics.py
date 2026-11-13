import threading
import uuid

import requests
import streamlit as st


def _cfg():
    try:
        s = st.secrets["supabase"]
        return s["url"].rstrip("/"), s["key"]
    except Exception:
        return None, None


def _send(url, key, row):
    try:
        requests.post(f"{url}/rest/v1/events", json=row, timeout=5,
                      headers={"apikey": key, "Content-Type": "application/json",
                               "Prefer": "return=minimal"})
    except Exception:
        pass  # analytics must never break the app


def track(event: str, detail: str = ""):
    url, key = _cfg()
    if not url:
        return
    sid = st.session_state.setdefault("_sid", uuid.uuid4().hex[:12])
    row = {"event": event, "session_id": sid, "detail": str(detail)}
    threading.Thread(target=_send, args=(url, key, row), daemon=True).start()


def fetch_events(limit: int = 20000):
    url, key = _cfg()
    r = requests.get(f"{url}/rest/v1/events", timeout=15, headers={"apikey": key},
                     params={"select": "created_at,event,session_id,detail",
                             "order": "created_at.desc", "limit": limit})
    r.raise_for_status()
    return r.json()
