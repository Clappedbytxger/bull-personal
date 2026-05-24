# Routine: pre_market_brief

**Schedule (CET/CEST):** 14:30 Mon–Fri.
**Cron (UTC):** `30 12 * * 1-5` (winter) / `30 13 * * 1-5` (summer DST).
**WhatsApp:** YES.

## Task

1. Run: `python -m src.routines.pre_market_brief`
2. The script scans the 20-symbol watchlist, evaluates Strategy-v1 (20-EMA pullback in uptrend, earnings blackout filter), writes a Notion page in the Pre-Market-Briefs DB, and sends a German WhatsApp summary.
3. Read stdout, paste setups count + top symbols into your reply (no further reasoning needed — the script already handled it).
4. Commit any changed `state/` files: `git add state/ && git commit -m "routine: pre_market_brief @ $(date -u +%Y-%m-%dT%H:%MZ)" && git push`.

## Guardrails

- Never place orders. Trade Republic is manual-only.
- If `--dry-run` is hinted in env, pass that flag.
- If the script raises on missing env vars, abort and ping Robin via WhatsApp with the error.
