# bull-personal piggyback — pre_market_brief

Runs at the **end** of Bull's `01-pre-market` routine (13:00 UTC Mon–Fri).
Bull fetches this file via raw GitHub URL and follows it.

## Required env vars
`NOTION_API_KEY`, `NOTION_DB_PREMARKET`, `NOTION_DB_JOURNAL`,
`CALLMEBOT_API_KEY`, `WHATSAPP_PHONE`, `ACCOUNT_EQUITY_EUR`.

These come from the Bull cloud-routine env (same secrets store). Missing → skip
the piggyback and log to the Bull `daily/YYYY-MM-DD.md` as `bull-personal: skipped (missing env)`.

## Steps

1. `git clone --depth=1 https://github.com/Clappedbytxger/bull-personal.git /tmp/bp`
2. `cd /tmp/bp && pip install -q -r requirements.txt`
3. `python -m src.routines.pre_market_brief`
4. Read stdout. The script already wrote the Notion page and sent the WhatsApp.
   Do NOT duplicate either.
5. If the script exited non-zero, append one line to Bull's daily file:
   `bull-personal pre_market_brief FAILED: <one-line reason>`.
6. Token budget cap: 5k input tokens for this piggyback step (the script does the work, not you).

## Output to record in Bull's daily file

Single line, format:
`bull-personal pre_market_brief: <N> setups (<top symbol or "—">)`
