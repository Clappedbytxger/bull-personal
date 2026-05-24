"""Notion API thin wrapper for Robin's actual Trading-Hub DBs.

Schema verified 2026-05-24 against:
  Pre-Market Briefs (collection://048f4a90-c78d-4e75-acac-b78ac6ce0011)
  Trade Journal     (collection://f5f0636d-0422-4773-978b-8a79002c0c57)
"""
from __future__ import annotations

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


# ── property builders ────────────────────────────────────────────────────
def _title(text: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": text[:1900]}}]}


def _text(text: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": (text or "")[:1900]}}]}


def _number(n: float | int | None) -> dict:
    return {"number": float(n) if n is not None else None}


def _select(name: str) -> dict:
    return {"select": {"name": name}}


def _date(iso: str) -> dict:
    return {"date": {"start": iso}}


def _checkbox(b: bool) -> dict:
    return {"checkbox": b}


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:1900]}}]},
    }


def _chunk(s: str, n: int) -> list[str]:
    return [s[i:i + n] for i in range(0, max(len(s), 1), n)] or [""]


# ── core HTTP ────────────────────────────────────────────────────────────
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


# ── Pre-Market Briefs DB ─────────────────────────────────────────────────
def write_premarket_brief(
    date_iso: str,
    n_setups: int,
    setups_detail: str,
    earnings_today: str = "",
    macro_events: str = "",
    market_bias: str = "Neutral",
    brief_markdown: str = "",
) -> dict:
    db = require("NOTION_DB_PREMARKET", NOTION_DB_PREMARKET)
    props = {
        "Brief": _title(f"Pre-Market {date_iso}"),
        "Date": _date(date_iso),
        "Active Setups Count": _number(n_setups),
        "Setups Detail": _text(setups_detail),
        "Earnings Today": _text(earnings_today),
        "Macro Events": _text(macro_events),
        "Market Bias": _select(market_bias),
        "Reviewed": _checkbox(False),
    }
    children = [_paragraph(c) for c in _chunk(brief_markdown, 1800)] if brief_markdown else None
    return create_page(db, props, children)


# ── Trade Journal DB ─────────────────────────────────────────────────────
SETUP_MAP = {
    "20EMA-Pullback": "Pullback 20-EMA",
    "Pullback 20-EMA": "Pullback 20-EMA",
    "VCP": "VCP Breakout",
    "VCP Breakout": "VCP Breakout",
    "Mean Reversion": "Mean Reversion",
}

STATUS_MAP = {
    "Open": "Open",
    "Watching": "Watching",
    "Order Placed": "Order Placed",
    "Closed-Win": "Closed Win",
    "Closed Win": "Closed Win",
    "Closed-Loss": "Closed Loss",
    "Closed Loss": "Closed Loss",
    "Stopped": "Closed Loss",       # legacy alias
    "Cancelled": "Cancelled",
}


def write_trade(
    ticker: str,
    entry_date: str,
    entry: float,
    stop: float,
    target: float,
    shares: float,
    risk_eur: float,
    setup: str = "Pullback 20-EMA",
    direction: str = "Long",
    paper_or_live: str = "Paper",
    rationale: str = "",
) -> dict:
    db = require("NOTION_DB_JOURNAL", NOTION_DB_JOURNAL)
    position_size_eur = round(shares * entry, 2)  # rough; doesn't FX-convert
    risk_per_share = entry - stop if direction == "Long" else stop - entry
    planned_rr = round(((target - entry) if direction == "Long" else (entry - target)) /
                       max(abs(risk_per_share), 0.01), 2)

    props = {
        "Trade": _title(f"{ticker.upper()} {entry_date}"),
        "Ticker": _text(ticker.upper()),
        "Direction": _select(direction),
        "Entry Date": _date(entry_date),
        "Entry Price": _number(entry),
        "Stop Loss": _number(stop),
        "Target": _number(target),
        "Shares": _number(shares),
        "Position Size EUR": _number(position_size_eur),
        "Risk EUR": _number(risk_eur),
        "Planned R:R": _number(planned_rr),
        "Setup": _select(SETUP_MAP.get(setup, "Other")),
        "Status": _select("Open"),
        "Paper or Live": _select(paper_or_live),
        "Rationale": _text(rationale),
        "Rule Violation": _checkbox(False),
    }
    return create_page(db, props)


def list_open_trades() -> list[dict]:
    db = require("NOTION_DB_JOURNAL", NOTION_DB_JOURNAL)
    return query_db(db, filter_={"property": "Status", "select": {"equals": "Open"}})


def close_trade(
    page_id: str,
    exit_price: float,
    exit_date: str,
    status: str,         # "Closed Win" | "Closed Loss"
    actual_r: float,
    pnl_eur: float,
    pnl_pct: float,
    lesson: str = "",
) -> dict:
    props = {
        "Status": _select(STATUS_MAP.get(status, status)),
        "Exit Price": _number(exit_price),
        "Exit Date": _date(exit_date),
        "Actual R": _number(round(actual_r, 2)),
        "P&L EUR": _number(round(pnl_eur, 2)),
        "P&L Percent": _number(round(pnl_pct, 4)),
        "Lesson": _text(lesson),
    }
    return update_page(page_id, props)


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


def read_title(page: dict, prop: str = "Trade") -> str:
    rt = page.get("properties", {}).get(prop, {}).get("title", [])
    return "".join(t.get("plain_text", "") for t in rt)


def read_date(page: dict, prop: str) -> str | None:
    d = page.get("properties", {}).get(prop, {}).get("date")
    return d.get("start") if d else None
