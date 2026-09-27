#!/usr/bin/env python3
"""Render deterministic Trading Wiser zone-analysis HTML from report JSON."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "report-template.html"
DISCLAIMER = "This report reads Momentum Analyzer output and public market data. It is not a trade recommendation."
MISSING = "Not reported"


def esc(value: Any) -> str:
    if value is None or value == "":
        return MISSING
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return html.escape(str(value), quote=True)


def items(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"every item in {field} must be an object")
    return value


def money(value: Any) -> str:
    if value is None or value == "":
        return MISSING
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    if isinstance(value, str) and "$" not in value:
        try:
            return f"${float(value):,.2f}"
        except ValueError:
            pass
    return esc(value)


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").replace("ATR", "").strip())
    except ValueError:
        match = re.search(r"-?\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else None


def zone_section(title: str, zones: list[dict[str, Any]], kind: str) -> str:
    if not zones:
        label = "supports" if kind == "support" else "resistances"
        return f'<section><h2>{title}</h2><p class="muted">Momentum Analyzer returned no {label}.</p></section>'
    zones = sorted(zones, key=lambda z: (number(z.get("distance_atr")) is None, number(z.get("distance_atr")) or 0))
    rows = []
    for index, zone in enumerate(zones):
        strength_raw = str(zone.get("strength") or "").lower()
        if strength_raw in ("major", "strong"):
            strength, strength_class = "STRONG", "major"
        elif strength_raw == "moderate":
            strength, strength_class = "MODERATE", "moderate"
        elif strength_raw in ("minor", "mild"):
            strength, strength_class = "MILD", "minor"
        else:
            strength, strength_class = MISSING, "moderate"
        active = kind == "support" and index == 0
        name = zone.get("name") or ("Active Support" if active else f"{title[:-1]} {index + 1}")
        if active and "active" not in str(name).lower():
            name = f"Active Support — {name}"
        timeframe = zone.get("timeframe")
        if timeframe:
            name += f" ({timeframe})"
        metrics = [
            ("Touches", esc(zone.get("touches"))),
            ("Rejections", esc(zone.get("rejections"))),
            ("Breakouts", esc(zone.get("breakouts"))),
        ]
        touches, rejects = number(zone.get("touches")), number(zone.get("rejections"))
        rate = f"{rejects / touches * 100:.1f}%" if touches and touches > 0 and rejects is not None else MISSING
        metrics.append(("Rejection rate", rate))
        if zone.get("distance_atr") is not None:
            metrics.append(("Distance (ATR)", esc(zone.get("distance_atr"))))
        if zone.get("distance_pct") is not None:
            metrics.append(("Distance (%)", esc(zone.get("distance_pct"))))
        metric_html = "".join(f'<div class="metric"><span class="label">{label}</span><strong>{value}</strong></div>' for label, value in metrics)
        cls = f"zone {kind}" + (" active" if active else "")
        active_badge = '<span class="badge">ACTIVE ZONE</span>' if active else ""
        insight = f'<p class="subtitle">{esc(zone.get("key_insight"))}</p>' if zone.get("key_insight") else ""
        rows.append(
            f'<article class="{cls}"><div class="zone-head"><h3>{esc(name)}</h3>'
            f'{active_badge}'
            f'<span class="badge strength-{strength_class}">{strength}</span></div>'
            f'<div class="zone-levels"><span><span class="label">Low</span><br><strong>{money(zone.get("low"))}</strong></span>'
            f'<span><span class="label">Mid</span><br><strong>{money(zone.get("mid"))}</strong></span>'
            f'<span><span class="label">High</span><br><strong>{money(zone.get("high"))}</strong></span></div>'
            f'<div class="metrics">{metric_html}</div>{insight}</article>'
        )
    return f'<section><h2>{title}</h2>{"".join(rows)}</section>'


def render(data: dict[str, Any]) -> str:
    required = ("symbol", "report_date", "summary_cards", "market_sentiment", "supports", "resistances",
                "technical_indicators", "risks", "working", "implications", "recommendations", "public_market_check")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("missing required top-level fields: " + ", ".join(missing))
    for field in ("market_sentiment", "public_market_check"):
        if not isinstance(data[field], dict):
            raise ValueError(f"{field} must be a JSON object")

    symbol = esc(str(data["symbol"]).strip().upper())
    if symbol == MISSING:
        raise ValueError("symbol cannot be empty")
    title = f"{symbol} Detailed Zone Analysis"
    supplied_cards = items(data["summary_cards"], "summary_cards")
    card_map = {str(card.get("title", "")).strip().lower(): card for card in supplied_cards}
    card_specs = (
        ("Current Price", ("current price", "price"), True),
        ("Distance to Nearest Support", ("distance to nearest support", "nearest support distance"), False),
        ("RSI(14)", ("rsi(14)", "rsi 14", "rsi"), False),
        ("MACD Histogram", ("macd histogram", "macd hist"), False),
        ("ATR(14)", ("atr(14)", "atr 14", "atr"), True),
    )
    ordered_cards = []
    for title, aliases, is_money in card_specs:
        card = next((card_map[alias] for alias in aliases if alias in card_map), {})
        raw_value = card.get("value")
        value = money(raw_value) if is_money else esc(raw_value)
        subtitle = esc(card.get("subtitle"))
        if not card:
            subtitle = "Data was not returned."
        ordered_cards.append(
            f'<article class="card"><div class="card-title">{title}</div>'
            f'<div class="card-value">{value}</div><div class="subtitle">{subtitle}</div></article>'
        )
    sentiment = data["market_sentiment"]
    fed = esc(sentiment.get("fed_label"))
    fed_score = esc(sentiment.get("fed_score"))
    sentiment_line = esc(sentiment.get("symbol_summary"))

    body: list[str] = [
        f'<header><h1>{title}</h1><p class="muted">Report Date: {esc(data.get("report_date"))}</p></header>',
        '<div class="cards">' + "".join(ordered_cards) + '</div>',
        f'<section class="alert"><h2>Market Sentiment Alert</h2><p><strong>Fed:</strong> {fed} &nbsp; <strong>Score:</strong> {fed_score}</p><p>{sentiment_line}</p></section>',
        zone_section("Support Zones", items(data["supports"], "supports"), "support"),
        zone_section("Resistance Zones", items(data["resistances"], "resistances"), "resistance"),
    ]

    indicators = items(data["technical_indicators"], "technical_indicators")
    indicator_html = "".join(
        f'<article class="reading"><h3>{esc(row.get("name"))}: {esc(row.get("value"))}</h3><p>{esc(row.get("reading"))}</p></article>'
        for row in indicators
    ) or f'<p>{MISSING}</p>'
    body.append(f'<section><h2>Technical Indicators</h2>{indicator_html}</section>')

    risk_list = items_to_strings(data["risks"], "risks")
    working_list = items_to_strings(data["working"], "working")
    body.append('<section><h2>Risk vs. Opportunity</h2><div class="columns">'
                f'<div><h3>Key Risks</h3>{list_html(risk_list)}</div>'
                f'<div><h3>What Is Working</h3>{list_html(working_list)}</div></div></section>')

    implications = items(data["implications"], "implications")
    body.append('<section><h2>Trading Implications by Zone</h2><div class="table-wrap"><table><thead><tr>'
                '<th>Zone</th><th>Price range</th><th>Action</th><th>Conviction</th></tr></thead><tbody>'
                + "".join(f'<tr><td>{esc(row.get("zone"))}</td><td>{esc(row.get("price_range"))}</td>'
                         f'<td>{esc(row.get("action"))}</td><td>{esc(row.get("conviction"))}</td></tr>'
                         for row in implications)
                + '</tbody></table></div></section>')

    recommendations = items(data["recommendations"], "recommendations")
    recommendation_map = {
        str(row.get("audience", "")).strip().lower(): row.get("text")
        for row in recommendations
    }
    recommendation_order = (
        ("Current Holders", ("current holders", "holders")),
        ("New Buyers", ("new buyers", "buyers")),
        ("Stop Placement", ("stop placement", "stop")),
        ("Target Levels", ("target levels", "targets")),
        ("Risk Summary", ("risk summary", "risk")),
    )
    recommendation_html = []
    for label, aliases in recommendation_order:
        value = next((recommendation_map[key] for key in aliases if key in recommendation_map), None)
        recommendation_html.append(
            f'<article class="recommendation"><h3>{label}</h3><p>{esc(value)}</p></article>'
        )
    body.append('<section><h2>Final Recommendation</h2>' + "".join(recommendation_html) + '</section>')

    check = data["public_market_check"]
    checks = items(check.get("rows", []), "public_market_check.rows")
    for row in checks:
        if row.get("result") not in ("match", "conflict", "thin"):
            raise ValueError("public_market_check row result must be match, conflict, or thin")
    statuses = {str(row.get("result", "thin")).lower() for row in checks}
    overall = "conflict" if "conflict" in statuses else "thin" if not statuses or statuses == {"thin"} else "match"
    status_html = f'<span class="status status-{overall}">OVERALL: {overall.upper()}</span>'
    sources = items_to_strings(check.get("sources", []), "public_market_check.sources")
    source_html = list_html(sources) if sources else f'<p class="muted">{MISSING}</p>'
    rows_html = "".join(
        f'<tr><td>{esc(row.get("field"))}</td><td>{esc(row.get("momentum_analyzer"))}</td>'
        f'<td>{esc(row.get("public"))}</td><td>{esc(row.get("source"))}</td>'
        f'<td><span class="status status-{esc(row.get("result"))}">{esc(row.get("result"))}</span></td>'
        f'<td>{esc(row.get("note"))}</td></tr>' for row in checks
    )
    if not rows_html:
        rows_html = '<tr><td colspan="6">No fields checked</td></tr>'
    body.append('<section><h2>Public Market Validation</h2>' + status_html
                + f'<p class="subtitle">Checked: {esc(check.get("checked_at"))}</p>'
                + f'<h3>Sources</h3>{source_html}<div class="table-wrap"><table><thead><tr>'
                '<th>Field</th><th>Momentum Analyzer</th><th>Public</th><th>Source</th><th>Result</th><th>Notes</th>'
                f'</tr></thead><tbody>{rows_html}</tbody></table></div></section>')
    body.append(f'<section class="disclaimer"><h2>Disclaimer</h2><p>{DISCLAIMER}</p></section>')

    template = TEMPLATE.read_text(encoding="utf-8")
    return template.replace("{{TITLE}}", title).replace("{{BODY}}", "\n".join(body))


def items_to_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    return [str(item) for item in value]


def list_html(values: list[str]) -> str:
    if not values:
        return f'<p class="muted">{MISSING}</p>'
    return '<ul>' + "".join(f'<li>{esc(value)}</li>' for value in values) + '</ul>'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON data matching assets/report-data-schema.json")
    parser.add_argument("--output", type=Path, help="HTML destination (defaults to SYMBOL_detailed_zone_analysis.html)")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("report JSON must contain one object")
        output = args.output or Path(f"{str(data.get('symbol', 'report')).upper()}_detailed_zone_analysis.html")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(data), encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Cannot render report: {exc}", file=sys.stderr)
        return 2
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
