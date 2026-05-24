# Routine: weekly_review

**Schedule (CET/CEST):** Fri 22:00.
**Cron (UTC):** `0 20 * * 5` (winter) / `0 21 * * 5` (summer).
**WhatsApp:** YES.

## Task

1. Run: `python -m src.routines.weekly_review`
2. Script aggregates this week's closed trades (Mon → today), computes winrate, avg R, total R, and a discipline score (penalty for R:R deviations > 0.5R), writes a Notion summary page and German WhatsApp.
3. Commit + push.

## Discipline metric

`discipline = 100 - (rr_violations / n_trades * 100)` where a violation is a closed trade with `R > 2.5` (overshoot, didn't take 2R target) or `0 < R < 0.8` (early exit before planned 1:2 played out).

After 4 weeks of paper data, Robin reviews `state/strategy_proposals.md` and decides whether to unlock Strategy v2.
