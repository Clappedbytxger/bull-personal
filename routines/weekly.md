# bull-personal piggyback — weekly_review

Runs at the **end** of Bull's `06-weekly-review` routine (Fri 21:30 UTC).

## Required env vars
Same as `pre_market.md`.

## Steps

1. `git clone --depth=1 https://github.com/Clappedbytxger/bull-personal.git /tmp/bp`
2. `cd /tmp/bp && pip install -q -r requirements.txt`
3. `python -m src.routines.weekly_review`
4. The script aggregates this week's closed Notion-Journal trades, writes a Notion summary page (Pre-Market-Briefs DB with `Weekly-` prefix), and sends a German WhatsApp summary. Do NOT duplicate output.
5. Token budget cap: 5k.

## Output to record in Bull's weekly file

Single line:
`bull-personal weekly_review: <N> trades, winrate <W>%, total <T>R`
