# Routine: trade_journal (manual)

**Schedule:** none (manual CLI invocation by Robin after each TR-App order fill).
**WhatsApp:** no.

## Task

Robin runs:
```powershell
python -m src.routines.trade_journal NVDA --entry 142.30 --shares 3
# or with explicit SL/TP:
python -m src.routines.trade_journal NVDA --entry 142.30 --stop 131.00 --target 165.00 --shares 3
```

Default SL = -8%, TP = +16% (Strategy v1). Script writes a Notion Trade-Journal page with Status=Open.

When Robin closes the trade in TR, he updates the Notion page directly (Status, Exit, R Multiple) — no CLI for the close path. The weekly_review picks it up automatically.
