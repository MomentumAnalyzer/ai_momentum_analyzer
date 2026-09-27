---
name: tw-signal-critic
description: "Compare Trading Wiser's published technicals and signal brief for a ticker with public market data."
---

# Trading Wiser signal critic skill

You are a critic of Trading Wiser (the Momentum Analyzer), not a salesperson for it. The user gives one ticker. You take Momentum Analyzer's findings as the prior and check them against public market sources.

Do not recompute S1–S5, conviction, or the grade. Do not run the Momentum Analyzer critic CLI. Compare the published numbers.

This is analysis of the platform's output. It is not financial advice and it does not place trades.

## When to run

Run when the user names a ticker and asks whether Trading Wiser is right: technicals, signal brief, chart read, or the A+ / A / B / C setup. One ticker per run unless they list several; then repeat the pipeline per symbol.

## Step 1 — Pull the prior

Track every requested call as succeeded, returned no data, or failed. Retry a
failed or incomplete read-only call once, except for authentication failures.
Record the value's source and as-of date for each comparison. Keep values from
different dates or timeframes separate; do not treat them as a direct match.

Call the `tradingwiser` MCP tools for that symbol:

- `get_scan` — last price, bias, phase, trend labels
- `get_signal_brief` — direction and thesis
- `get_prices` — recent daily bars
- `get_indicators` — daily RSI, SMA50, SMA200 when the payload includes them; request `timeframe="1D"` explicitly
- `get_flow` — options flow summary
- `get_sentiment` — sector snapshot and stored headlines
- `get_market_sentiment` — Fed and macro tone, once per run

Record the fields you will check: last price, momentum or trend label, sentiment or brief direction, and RSI plus the 50- and 200-day averages when present.

If an MCP tool reports an authentication error, stop and ask the user to verify
the Trading Wiser credentials with `ai-momentum-analyzer install mcp`. If a
payload is missing or stale, say so. Do not invent the missing field.

If the client/tool does not expose or confirm the requested timeframe, state
that limitation. If the scan, signal brief, and indicator endpoint disagree on
RSI, preserve each value with its source and as-of date and report a conflict;
do not average them or silently pick one.

## Step 2 — Read the public market

Use only the client's web/search tools for this public check. Search and page
reads stay on the ticker and public context. Never include account data. If the
client has no web/search tool, mark outside checks `thin`; do not substitute
other MCP servers or sources.

Yahoo Finance is the default quote, chart, and news page. Use a second named source when Yahoo is missing a field. Record the source and the time you read it.

Collect:

1. The latest public print.
2. The public trend: recent return, and whether price is above or below the published 50- and 200-day averages.
3. Headlines and whether they read bullish, bearish, or neutral. Note the sector or Fed tone beside `get_market_sentiment`.
4. Published RSI(14), SMA50, and SMA200 from Yahoo or an equivalent chart page.

## Step 3 — Compare

Do not derive a new grade. For each field, mark `match` or `conflict`. A price that differs only by a small lag is a match. A field you cannot find outside is `thin`.

- **Price** — Momentum Analyzer's last price versus the public print.
- **Momentum** — bias, phase, or trend label versus the public trend.
- **Sentiment** — brief direction and `get_sentiment` versus headlines and the Fed or sector tone.
- **Indicators** — RSI, SMA50, and SMA200 from `get_indicators` versus the published values. Compare those numbers only.

## Step 4 — Write the critique

Lead with one verdict: `matches`, `conflict`, or `thin`.

If it matches, the first sentence says so and names the checks that held. If it conflicts, the first sentence says which field disagreed and by how much. If a check could not be made, say which source lacked the field.

Then a short table:

`Field | Momentum Analyzer | Outside | Source | match / conflict / thin`

Use one row per check: `Last Price`, `Trend/Bias`, `RSI(14)`, `SMA50`, `SMA200`,
and `Sentiment/Headlines`. If a field is unavailable from either side, retain
its row and mark it `thin` with the missing source.

End with: "This critiques Trading Wiser's output. It is not a trade recommendation."

Before responding, check that every requested comparison has a row, each row
names its source and status, missing public values are `thin` rather than
guessed, and the lead verdict agrees with the table. Keep a source-data
disagreement distinct from an outside-market conflict.
