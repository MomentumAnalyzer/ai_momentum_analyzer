---
name: zone-analysis-report
description: Create a detailed support and resistance report for one or more tickers using Trading Wiser and the fixed HTML report format.
---

# Zone analysis report

Create one detailed support and resistance report per requested ticker. The report is decision support, not financial advice. Never place or execute trades.

## Required workflow

Follow these phases in order. Do not draft conclusions before collecting the Trading Wiser payloads. Do not skip a phase silently.

### 1. Collect Trading Wiser data

Use only the `tradingwiser` MCP server for platform data. For each ticker, call:

1. `get_zones` for current price, ATR, supports, resistances, and balance zones.
2. `get_scan` for grade, bias, phase, entry, stop, and target.
3. `get_indicators` for RSI, MACD, and ATR when available. Request `days=252` only when a longer window is needed.
4. `get_prices` for recent daily bars and the latest print / recent high.
5. `get_sentiment` for the sector snapshot and stored headlines.
6. `get_signal_brief` for direction and thesis.
7. `get_flow` for the options flow summary.

Once per report batch, call `get_market_sentiment` for the Fed / macro snapshot and `get_key_dates` for events today through the next 21 days. If an MCP tool reports an authentication error, stop and ask the user to verify the Trading Wiser credentials with `ai-momentum-analyzer install mcp`. Preserve missing values as missing; never infer a number from another field.

### 2. Validate only the permitted public facts

After collecting platform values, use the client's web/search tools only for public ticker information needed to check the report: latest quote, published moving averages / RSI when available, and relevant headlines. Use Yahoo Finance first; use one named secondary source only when a required field is absent there. Search only ticker symbols and public market context. Never include account data, position sizes, or cost basis.

If no web/search tool is available, do not substitute another MCP or external source. Mark the public check `thin` and explain that it could not be completed. Skills guide tool use but cannot enforce a client's tool permissions; the client setup must restrict available tools if strict source isolation is required.

For each field mark `match`, `conflict`, or `thin`. A small quote timestamp difference is a match. Overall status is `conflict` if any checked field conflicts; otherwise `thin` if no outside field could be checked; otherwise `match`. Record source names and the time read. Do not replace Trading Wiser values with public-source values.

### 3. Build the report data

Prepare one JSON object matching `assets/report-data-schema.json`. Use only values from the tool payloads and checks above. Keep prose brief and tie each insight to an observed field. Do not recalculate Momentum Analyzer's grade.

Map zone payload fields exactly: `zone_low` → `low`, `zone_mid` → `mid`, `zone_high` → `high`, `touches_total` → `touches`, `rejections_total` → `rejections`, `breakouts_total` → `breakouts`, and `strength_label` → `strength`. Keep `distance_atr` and `distance_pct` as reported. Build the five summary cards from the corresponding payload fields: current price from `get_zones.price`; support distance from the nearest support; RSI(14), MACD histogram, and ATR(14) from `get_indicators` / `get_zones` when present. Use these exact summary card titles: `Current Price`, `Distance to Nearest Support`, `RSI(14)`, `MACD Histogram`, and `ATR(14)`. Use these exact recommendation audiences: `Current Holders`, `New Buyers`, `Stop Placement`, `Target Levels`, and `Risk Summary`. Identify scan fields (`entry`, `stop`, `target`) by name in those recommendation texts. Use ISO dates for `report_date` and UTC timestamps for `checked_at`.

The renderer fixes the summary-card and recommendation order, derives rejection rate only when both rejection and touch counts are present and touches are greater than zero, and derives the overall public-check verdict from row verdicts.

Represent absent values as `null`, empty arrays, or a short note saying the source did not return the field. Never put HTML in the JSON. Do not invent a zone, touch count, indicator, date, price, or source. For a list of tickers, create and render one JSON object and one HTML file per ticker before moving to the next.

### 4. Render the fixed HTML report

Use the installed skill's `scripts/render_report.py` with the JSON file and an output path:

```bash
python3 /path/to/zone-analysis-report/scripts/render_report.py report.json --output NVDA_detailed_zone_analysis.html
```

Replace `/path/to/zone-analysis-report` with the installed skill directory. Use the requested output directory, or the current working directory by default. Do not write report HTML by hand. The renderer owns the section order, layout, escaping, number display, and missing-value labels. Preserve the returned HTML file without reformatting it.

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
