# bull-personal piggyback — eod_review

Runs at the **end** of Bull's `05-close-summary` routine (21:15 UTC Mon–Fri).

## Required env vars
Same as `pre_market.md`.

## Steps

1. `git clone --depth=1 https://github.com/Clappedbytxger/bull-personal.git /tmp/bp` (skip if /tmp/bp already exists from earlier today — `git -C /tmp/bp pull --ff-only`)
2. `cd /tmp/bp && pip install -q -r requirements.txt`
3. `python -m src.routines.eod_review`
4. The script queries Notion for open trades, evaluates each, and WhatsApps Robin ONLY if at least one needs manual action. Silent on all-HOLD days. Do NOT add your own messaging.
5. Token budget cap: 5k.

## Output to record in Bull's daily file

Single line:
`bull-personal eod_review: <M> open trades, <K> actionable`
