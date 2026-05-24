"""Notion API thin wrapper for the Pre-Market-Briefs and Trade-Journal DBs."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from .config import NOTION_API_KEY, NOTION_DB_PREMARKET, NOTION_DB_JOURNAL, require

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {require('NOTION_API_KEY', NOTION_API_KEY)}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }


def _title(text: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": text}}]}


def _text_prop(text: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": text[:1900]}}]}


def _number(n: float) -> dict:
    return {"number": n}


def _select(name: str) -> dict:
    return {"select": {"name": name}}


def _date(iso: str) -> dict:
    return {"date": {"start": iso}}


def _paragraph(text: str) -> dict:
    # Notion blocks max 2000 chars per rich-text item
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:1900]}}]},
    }


def create_page(db_id: str, properties: dict, children: list[dict] | None = None) -> dict:
    payload: dict[str, Any] = {"parent": {"database_id": db_id}, "properties": properties}
    if children:
        payload["children"] = children
    r = requests.post(f"{API}/pages", headers=_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def query_db(db_id: str, filter_: dict | None = None, page_size: int = 100) -> list[dict]:
    payload: dict[str, Any] = {"page_size": page_size}
    if filter_:
        payload["filter"] = filter_
    r = requests.post(f"{API}/databases/{db_id}/query", headers=_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def update_page(page_id: str, properties: dict) -> dict:
    r = requests.patch(f"{API}/pages/{page_id}", headers=_headers(),
                       json={"properties": properties}, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Pre-Market-Briefs ─────────────────────────────────────────────────────
def write_premarket_brief(date_iso: str, n_setups: int, top_symbol: str,
                           brief_markdown: str) -> dict:
    db = require("NOTION_DB_PREMARKET", NOTION_DB_PREMARKET)
    props = {
        "Name": _title(f"Pre-Market {date_iso}"),
        # Optional schema fields — Notion silently ignores unknown property names,
        # but we send the expected ones. Adjust if your DB schema differs.
        "Datum": _date(date_iso),
        "Setups": _number(n_setups),
        "Top": _text_prop(top_symbol or "—"),
    }
    children = []
    # Split markdown into ≤1900-char paragraph blocks
    for chunk in _chunk(brief_markdown, 1800):
        children.append(_paragraph(chunk))
    return create_page(db, props, children)


# ── Trade-Journal ─────────────────────────────────────────────────────────
def write_trade(symbol: str, entry_date: str, entry: float, stop: float,
                target: float, shares: int, risk_eur: float, setup_tag: str = "20EMA-Pullback",
                notes: str = "") -> dict:
    db = require("NOTION_DB_JOURNAL", NOTION_DB_JOURNAL)
    props = {
        "Name": _title(f"{symbol} {entry_date}"),
        "Symbol": _text_prop(symbol),
        "Datum": _date(entry_date),
        "Entry": _number(entry),
        "SL": _number(stop),
        "TP": _number(target),
        "Size": _number(shares),
        "Risk EUR": _number(risk_eur),
        "Setup": _select(setup_tag),
        "Status": _select("Open"),
        "Notes": _text_prop(notes),
    }
    return create_page(db, props)


def list_open_trades() -> list[dict]:
    db = require("NOTION_DB_JOURNAL", NOTION_DB_JOURNAL)
    return query_db(db, filter_={"property": "Status", "select": {"equals": "Open"}})


def close_trade(page_id: str, exit_price: float, status: str, r_multiple: float,
                notes: str = "") -> dict:
    props = {
        "Status": _select(status),
        "Exit": _number(exit_price),
        "R Multiple": _number(round(r_multiple, 2)),
        "Notes": _text_prop(notes),
    }
    return update_page(page_id, props)


def _chunk(s: str, n: int) -> list[str]:
    return [s[i:i + n] for i in range(0, max(len(s), 1), n)] or [""]


# ── Property readers (lenient) ────────────────────────────────────────────
def read_number(page: dict, prop: str) -> float | None:
    v = page.get("properties", {}).get(prop, {}).get("number")
    return float(v) if v is not None else None


def read_select(page: dict, prop: str) -> str | None:
    sel = page.get("properties", {}).get(prop, {}).get("select")
    return sel.get("name") if sel else None


def read_text(page: dict, prop: str) -> str:
    rt = page.get("properties", {}).get(prop, {}).get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in rt)


def read_title(page: dict, prop: str = "Name") -> str:
    rt = page.get("properties", {}).get(prop, {}).get("title", [])
    return "".join(t.get("plain_text", "") for t in rt)
