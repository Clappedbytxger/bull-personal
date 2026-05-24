# Routine: eod_review

**Schedule (CET/CEST):** 21:30 Mon–Fri.
**Cron (UTC):** `30 19 * * 1-5` (winter) / `30 20 * * 1-5` (summer).
**WhatsApp:** only if action required (script decides).

## Task

1. Run: `python -m src.routines.eod_review`
2. Script pulls every Notion Trade-Journal page with Status=Open, fetches current close per symbol, and labels each as HOLD / EXIT-STOP / EXIT-TARGET / TRAIL-BE.
3. WhatsApp is sent only when ≥1 actionable position exists.
4. Commit + push.

## Notes

- Bar-data is daily close. TR has no overnight stops anyway — intraday tick precision isn't useful for swing.
- DATA-FAIL on a symbol → log to `logs/eod.log` and continue. Don't block the routine.
