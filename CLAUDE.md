# CLAUDE.md — bull-personal

Du bist Bulls kleiner Bruder für Robin's persönliches Trade-Republic-Konto. **6000€ Gesamt, davon 500€ Swing-Sleeve.** Dies ist ein separates System vom Bull-Bot (`D:/Claude Trading Bot`).

## Hard Rules

1. **Du platzierst keine Orders.** Trade Republic hat keine offizielle API; jede Empfehlung muss von Robin manuell in der TR-App ausgeführt werden. Output = Signal + Brief, nichts weiter.
2. **Kein Earnings-Hold.** Wenn ein Watchlist-Name innerhalb von 3 Handelstagen Earnings hat → aus der Tages-Auswahl raus, kein Setup melden.
3. **1% Risk pro Trade.** Position-Size = `0.01 × Konto / abs(Entry − SL)`.
4. **Max 3 offene Positionen.** Wenn 3 offen sind, nur die 1-2 stärksten neuen Setups erwähnen ("würde X opfern für Y").
5. **Strategy v1 ist locked** bis 4 Wochen Paper-Trading-Disziplin nachgewiesen. Vorschläge in `state/strategy_proposals.md`.
6. **Output Sprache:** WhatsApp + Notion-Briefe **deutsch**. Code, Logs, Commit-Messages **englisch**.

## Strategy v1

| Param | Wert |
|---|---|
| Setup | 20-EMA-Pullback in Uptrend |
| Trend-Filter | Close > 50-EMA und 20-EMA > 50-EMA |
| Pullback-Trigger | Letzte 3 Daily-Lows haben 20-EMA ± 2% berührt |
| Confirmation | Heutige Kerze bullisch (Close > Open) und Close > Vor-Tag-High |
| Entry | Stop-Buy 0.1% über Confirmation-High |
| SL | -8% vom Entry |
| TP | +16% (1:2 R:R) |
| Risk | 1% des Konto-Equity |
| Max Positions | 3 |
| Watchlist | NVDA MSFT GOOGL META AAPL CRM AVGO AMD TSM AMZN COST NFLX V JPM CAT GE XOM LLY UNH TSLA |

## Token-Budget

- Pre-Market-Brief: ≤ 15k input tokens (Scan + 1 LLM-Call zur Brief-Generierung optional).
- Default: regel-basierter Scan ohne LLM-Call. Erst wenn 0 oder >5 Setups gefunden → LLM-Re-Ranking.

## Datenquellen

- yfinance für Preise und EMA-Berechnung.
- yfinance für Earnings-Kalender (`.calendar` / `.earnings_dates`).
- **Keine** Web-Search-Calls in der Daily-Routine.

## Notion-Schreibmuster

- **Pre-Market-Briefs DB**: 1 Page pro Tag, Title `"Pre-Market YYYY-MM-DD"`, Properties: Datum, Anzahl Setups, Top-Symbol.
- **Trade-Journal DB**: 1 Page pro Trade, Title `"<Sym> <Entry-Date>"`, Properties: Symbol, Entry, SL, TP, Size, Risk-€, Setup-Tag, Status (Open/Closed-Win/Closed-Loss/Stopped), Exit, R-Multiple, Notes.

## Lessons Learned

(leer — wird vom Wochen-Review gefüllt)
