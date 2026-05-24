# bull-personal

Robin's persönliches Swing-Trading-System für sein Trade-Republic-Konto.

**Distinct vom Bull Trading Bot** (`D:/Claude Trading Bot`) — das ist Robin's privates Portfolio, nicht der 100k-Paper-Bot.

## Was es macht

| Routine | Wann | WhatsApp | Output |
|---|---|---|---|
| `pre_market_brief` | 14:30 DE (Mo–Fr) | YES | Watchlist-Scan auf 20-EMA-Pullback, Setup-Kandidaten mit Entry/SL/TP. Notion + WhatsApp. |
| `trade_journal` | manuell nach Order | — | Robin loggt ausgeführten Trade in Notion Trade-Journal. |
| `eod_review` | 21:30 DE (Mo–Fr) | wenn Action | Check offene Positionen: Stop nachziehen, Exit, oder hold. |
| `weekly_review` | Fr 22:00 DE | YES | Winrate, avg R, Disziplin-Score, Lessons. Notion + WhatsApp. |

## Strategie v1 (locked bis 4-Wochen-Paper-Review)

- **Setup:** Pullback an 20-EMA in bestätigtem Uptrend (Preis > 50-EMA, 20 > 50).
- **Confirmation:** Heute bullische Kerze (Close > Open), Pullback-Low der letzten 3 Tage berührte ±2% an 20-EMA.
- **Entry:** über High des Confirmation-Tages (Stop-Buy in TR-App).
- **SL:** -8% vom Entry.
- **TP:** +16% (1:2 R:R).
- **Risk:** 1% des Kontos pro Trade.
- **Max:** 3 offene Positionen.
- **Watchlist (20):** NVDA MSFT GOOGL META AAPL CRM AVGO AMD TSM AMZN COST NFLX V JPM CAT GE XOM LLY UNH TSLA
- **Kein Earnings-Hold** — TR Stops greifen nicht außerhalb 8–22 DE-Zeit (siehe Trade-Republic-Constraints).

## Stack

- Python 3.11+
- `yfinance` für Marktdaten + EMA-Berechnung
- `requests` für CallMeBot WhatsApp + Notion API
- Claude Code Scheduled Routines für Cron

## Setup

```powershell
cd D:\bull-personal
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# .env mit Keys füllen
python -m src.routines.pre_market_brief --dry-run
```

## Env-Vars

| Key | Wofür |
|---|---|
| `NOTION_API_KEY` | Notion-Integration mit Zugriff auf Trading-Hub |
| `NOTION_DB_PREMARKET` | Pre-Market-Briefs DB-ID |
| `NOTION_DB_JOURNAL` | Trade-Journal DB-ID |
| `CALLMEBOT_API_KEY` | WhatsApp Outbound |
| `WHATSAPP_PHONE` | Robin's TR-Nummer im CallMeBot-Format |

## Constraints

- Trade Republic = manuelle Order-Ausführung. **Dieser Code platziert KEINE Orders.**
- WhatsApp ist outbound-only; Robin-Replies via direkter Notion-Page-Edit oder im nächsten interaktiven Chat.
- US-Stocks via LS Exchange / gettex 8–22 DE-Zeit, **keine Overnight-Stops** außerhalb des Fensters.
