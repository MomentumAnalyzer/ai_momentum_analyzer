---
name: zone-analysis-report
description: Create a detailed support and resistance report for one or more tickers using Trading Wiser and the fixed HTML report format.
---

# Zone analysis report

Create one detailed support and resistance report per requested ticker. The report is decision support, not financial advice. Never place or execute trades.

## Required workflow

Follow these phases in order for each ticker. Keep a completion checklist as you work. Do not draft conclusions before collecting Trading Wiser payloads or skip a phase silently.

### 1. Collect and verify source data

Use only the `tradingwiser` MCP server for platform data. For each ticker, call:

1. `get_zones` for current price, ATR, supports, resistances, and balance zones.
2. `get_scan` for grade, bias, phase, entry, stop, and target.
3. `get_indicators` for RSI, MACD, and ATR when available. Request `days=252` only when a longer window is needed.
4. `get_prices` for recent daily bars and the latest print / recent high.
5. `get_sentiment` for the sector snapshot and stored headlines.
6. `get_signal_brief` for direction and thesis.
7. `get_flow` for the options flow summary.

Once per report batch, call `get_market_sentiment` for the Fed / macro snapshot and `get_key_dates` for events today through the next 21 days. Track each call as succeeded, returned no data, or failed. Retry a failed or incomplete read-only call once; do not retry authentication failures. If authentication fails, stop and ask the user to verify credentials with `ai-momentum-analyzer install mcp`.

Record the as-of date returned by each call. Preserve missing values; never infer a number from another field. If sources disagree on a value that should match (including RSI), keep both values with source and date, flag the discrepancy, and do not silently choose one. Treat an empty zone list as a valid “no zones returned” result only if the API call succeeded.

### 2. Build sections and repair gaps

Build each section from its corresponding source, then check it before moving on:

1. **Zones:** Include every returned support and resistance, mapping fields exactly as specified below. If a successful call returned no zones, say so. If a returned zone lacks a field, preserve `null` and explain it in `key_insight`; use a clear phrase such as `Not returned:`. Never fill it from another zone.
2. **Indicators:** Create all five summary cards and include every available RSI, MACD, and ATR reading. A null card value needs a subtitle beginning with a clear reason such as `Unavailable:` or `Not returned:`. Use the same explicit wording in a null indicator's `reading`. Preserve source/date conflicts explicitly.
3. **Sentiment and events:** Include the available label, score, summary, market snapshot, and key dates. When the label or score is null, the summary must explicitly say `Unavailable:` or `Not returned:` and explain why.
4. **Risks, what is working, and implications:** Include grounded observations, or an explicit unavailable reason when the source data cannot support a conclusion.
5. **Recommendations:** Include all five audiences exactly: `Current Holders`, `New Buyers`, `Stop Placement`, `Target Levels`, and `Risk Summary`. Each needs grounded guidance or an explicit reason guidance is unavailable.

Before validating, revisit the relevant source once for any missing section or critical field. Retry only the relevant read-only MCP call; if data remains unavailable, say so clearly using `Unavailable:` or `Not returned:`. Do not write a hand-authored HTML fallback: it would bypass the fixed renderer and make output differ across clients.

Critical fields are the requested ticker, ISO report date, a successful `get_zones` response with current price, and a successful `get_scan` response. If any remains unavailable after the retry, do not render a seemingly complete report; tell the user which call/field failed and ask whether they want a clearly labeled partial report.

### 3. Validate only the permitted public facts

After collecting platform values, use the client's web/search tools only for public ticker information needed to check the report: latest quote, published moving averages / RSI when available, and relevant headlines. Use Yahoo Finance first; use one named secondary source only when a required field is absent there. Search only ticker symbols and public market context. Never include account data, position sizes, or cost basis.

If no web/search tool is available, do not substitute another MCP or external source. Mark the public check `thin` and put an explicit `Unavailable:` or `Not returned:` reason in each affected row's `note`. Skills guide tool use but cannot enforce a client's tool permissions; the client setup must restrict available tools if strict source isolation is required.

For each field mark `match`, `conflict`, or `thin`. A small quote timestamp difference is a match. Overall status is `conflict` if any checked field conflicts; otherwise `thin` if no outside field could be checked; otherwise `match`. Record source names and the time read. Do not replace Trading Wiser values with public-source values.

### 4. Build and validate the report data

Prepare one JSON object matching the bundled schema. The renderer can print the exact schema without needing the skill directory path:

```bash
tradingwiser-render-report --show-schema
```

Use only values from the tool payloads and checks above. Keep prose brief and tie each insight to an observed field. Do not recalculate Momentum Analyzer's grade.

Map zone payload fields exactly: `zone_low` → `low`, `zone_mid` → `mid`, `zone_high` → `high`, `touches_total` → `touches`, `rejections_total` → `rejections`, `breakouts_total` → `breakouts`, and `strength_label` → `strength`. Keep `distance_atr` and `distance_pct` as reported. Build the five summary cards from the corresponding payload fields: current price from `get_zones.price`; support distance from the nearest support; RSI(14), MACD histogram, and ATR(14) from `get_indicators` / `get_zones` when present. Use these exact summary card titles: `Current Price`, `Distance to Nearest Support`, `RSI(14)`, `MACD Histogram`, and `ATR(14)`. Use these exact recommendation audiences: `Current Holders`, `New Buyers`, `Stop Placement`, `Target Levels`, and `Risk Summary`. Identify scan fields (`entry`, `stop`, `target`) by name in those recommendation texts. Use ISO dates for `report_date` and UTC timestamps for `checked_at`.

The schema file is the data contract; the renderer loads and checks it before producing HTML. It also requires all five summary cards and recommendation audiences, and a reason whenever a summary-card value is null. Validate before rendering:

```bash
tradingwiser-render-report report.json --validate-only
```

If validation reports a field path and error, correct the JSON from source data and validate again. Make at most two correction passes. If the source lacks a value, preserve `null` and explain why in its explanatory field. Never invent data to make validation pass. The renderer fixes card and recommendation order, derives rejection rate only when rejection and touch counts are present and touches are greater than zero, and derives the overall public-check verdict from row verdicts.

Represent absent values as `null`, empty arrays, or a short note saying the source did not return the field. Never put HTML in the JSON. Do not invent a zone, touch count, indicator, date, price, or source. For a list of tickers, create and render one JSON object and one HTML file per ticker before moving to the next.

### 5. Render the fixed HTML report

Render through the installed package command. It locates the bundled renderer itself, so do not guess or construct the skill installation path:

```bash
tradingwiser-render-report report.json --output NVDA_detailed_zone_analysis.html
```

Use the requested output directory, or the current working directory by default. The render command validates again before writing. If it reports an error, make at most two correction passes and revalidate. If the renderer itself fails, show the error; do not silently switch to model-authored HTML. If the command is unavailable, tell the user to install or repair the `ai-momentum-analyzer` package; do not search for the script. The renderer owns section order, layout, escaping, number display, and missing-value labels. Preserve the returned HTML file without reformatting it.

## Fixed report contents

The renderer always emits these sections in this order:

1. Header and report date.
2. Summary cards: current price, nearest-support distance, RSI(14), MACD histogram, ATR(14).
3. Market sentiment alert.
4. Support zones, nearest first, with range, midpoint, strength, timeframe, touches, rejections, breakouts, rejection rate, distance, and a count-based insight. The nearest support is marked active.
5. Resistance zones with the same fields. If none were returned, show that explicitly. A recent high may be shown as a price high, never as a detected resistance zone.
6. Technical indicators with the reported values and concise readings.
7. Risks and what is working.
8. Trading implications table with zone, price range, qualitative action (`hold`, `wait`, or `stop`), and conviction. Do not include share counts or dollar position sizes.
9. Final recommendations for current holders, new buyers, stop, targets, and risk summary. Identify the Momentum Analyzer field used for each level.
10. Public market validation with overall status, individual comparisons, sources, and read time.
11. Disclaimer: “This report reads Momentum Analyzer output and public market data. It is not a trade recommendation.”

## Output

Tell the user the full path of each generated HTML file. If a required MCP call failed, identify the failed tool and leave its fields unavailable in the report rather than sourcing them elsewhere.
