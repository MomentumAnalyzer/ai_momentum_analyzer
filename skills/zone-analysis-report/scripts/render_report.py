#!/usr/bin/env python3
"""Render deterministic Trading Wiser zone-analysis HTML from report JSON."""

from __future__ import annotations

import argparse
from datetime import date
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "report-template.html"
SCHEMA = SKILL_ROOT / "assets" / "report-data-schema.json"
DISCLAIMER = "This report reads Momentum Analyzer output and public market data. It is not a trade recommendation."
MISSING = "Not reported"


def _schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def _validate_node(value: Any, rule: dict[str, Any], path: str, root: dict[str, Any]) -> list[str]:
    if "$ref" in rule:
        ref = rule["$ref"]
        target = root
        for part in ref.removeprefix("#/").split("/"):
            target = target.get(part, {}) if isinstance(target, dict) else {}
        return _validate_node(value, target, path, root)

    errors: list[str] = []
    expected = rule.get("type")
    if expected:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(_schema_type_matches(value, item) for item in allowed):
            errors.append(f"{path}: expected {' or '.join(allowed)}, got {type(value).__name__}")
            return errors
    if "enum" in rule and value not in rule["enum"]:
        errors.append(f"{path}: expected one of {rule['enum']}, got {value!r}")
    if isinstance(value, dict):
        for key in rule.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required field is missing")
        for key, child_rule in rule.get("properties", {}).items():
            if key in value:
                errors.extend(_validate_node(value[key], child_rule, f"{path}.{key}", root))
    elif isinstance(value, list) and "items" in rule:
        for index, item in enumerate(value):
            errors.extend(_validate_node(item, rule["items"], f"{path}[{index}]", root))
    return errors


def validate_report(data: Any) -> list[str]:
    """Validate schema and report coverage before any HTML is written."""
    if not isinstance(data, dict):
        return ["$: expected object, got " + type(data).__name__]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = _validate_node(data, schema, "$", schema)
    if errors:
        return errors

    def explains_unavailable(value: Any) -> bool:
        note = str(value or "").lower()
        return any(marker in note for marker in ("unavailable", "not available", "not reported", "not returned", "not provided", "missing"))

    if not data["symbol"].strip():
        errors.append("$.symbol: must not be empty")
    try:
        date.fromisoformat(data["report_date"])
    except ValueError:
        errors.append("$.report_date: expected an ISO date such as 2026-09-25")

    expected_cards = {
        "current price", "distance to nearest support", "rsi(14)",
        "macd histogram", "atr(14)",
    }
    cards = data["summary_cards"]
    card_titles = [str(card["title"]).strip().lower() for card in cards]
    for title in sorted(expected_cards - set(card_titles)):
        errors.append(f"$.summary_cards: missing required card {title!r}")
    for title in sorted(expected_cards):
        if card_titles.count(title) > 1:
            errors.append(f"$.summary_cards: card {title!r} must appear only once")
    for index, card in enumerate(cards):
        if card["value"] is None and not (card["subtitle"] or "").strip():
            errors.append(f"$.summary_cards[{index}].subtitle: explain why the value is unavailable")
        elif card["value"] is None and not explains_unavailable(card["subtitle"]):
            errors.append(f"$.summary_cards[{index}].subtitle: state that the source value is unavailable or was not returned")
        if card_titles[index] == "current price" and card["value"] is None:
            errors.append(f"$.summary_cards[{index}].value: current price is required to render a report")

    for index, zone in enumerate(data["supports"] + data["resistances"]):
        missing_fields = [
            key for key in ("low", "mid", "high", "strength", "touches", "rejections", "breakouts", "distance_atr", "distance_pct")
            if zone[key] is None
        ]
        if missing_fields and not explains_unavailable(zone["key_insight"]):
            errors.append(
                f"$.zones[{index}].key_insight: explain unavailable zone fields {', '.join(missing_fields)}"
            )

    for index, reading in enumerate(data["technical_indicators"]):
        if reading["value"] is None and not explains_unavailable(reading["reading"]):
            errors.append(f"$.technical_indicators[{index}].reading: explain why the indicator value is unavailable")

    sentiment = data["market_sentiment"]
    if (sentiment["fed_label"] is None or sentiment["fed_score"] is None) and not explains_unavailable(sentiment["symbol_summary"]):
        errors.append("$.market_sentiment.symbol_summary: explain unavailable sentiment fields")

    for index, row in enumerate(data["public_market_check"]["rows"]):
        if row["result"] == "thin" and not explains_unavailable(row["note"]):
            errors.append(f"$.public_market_check.rows[{index}].note: explain why this comparison is thin")

    expected_audiences = {"current holders", "new buyers", "stop placement", "target levels", "risk summary"}
    audience_list = [str(item["audience"]).strip().lower() for item in data["recommendations"]]
    audiences = set(audience_list)
    for audience in sorted(expected_audiences - audiences):
        errors.append(f"$.recommendations: missing required audience {audience!r}")
    for audience in sorted(expected_audiences):
        if audience_list.count(audience) > 1:
            errors.append(f"$.recommendations: audience {audience!r} must appear only once")
    for index, item in enumerate(data["recommendations"]):
        if not item["text"].strip():
            errors.append(f"$.recommendations[{index}].text: must contain guidance or an explicit unavailable reason")
    return errors


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
    validation_errors = validate_report(data)
    if validation_errors:
        details = "\n - ".join(validation_errors)
        raise ValueError("Report data validation failed:\n - " + details)
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
    page_title = f"{symbol} Detailed Zone Analysis"
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
    for card_title, aliases, is_money in card_specs:
        card = next((card_map[alias] for alias in aliases if alias in card_map), {})
        raw_value = card.get("value")
        value = money(raw_value) if is_money else esc(raw_value)
        subtitle = esc(card.get("subtitle"))
        if not card:
            subtitle = "Data was not returned."
        ordered_cards.append(
            f'<article class="card"><div class="card-title">{card_title}</div>'
            f'<div class="card-value">{value}</div><div class="subtitle">{subtitle}</div></article>'
        )
    sentiment = data["market_sentiment"]
    fed = esc(sentiment.get("fed_label"))
    fed_score = esc(sentiment.get("fed_score"))
    sentiment_line = esc(sentiment.get("symbol_summary"))

    body: list[str] = [
        f'<header><h1>{page_title}</h1><p class="muted">Report Date: {esc(data.get("report_date"))}</p></header>',
        '<div class="cards">' + "".join(ordered_cards) + '</div>',
        f'<section class="alert"><h2>Market Sentiment Alert</h2><p><strong>Fed:</strong> {fed} &nbsp; <strong>Score:</strong> {fed_score}</p><p>{sentiment_line}</p></section>',
        zone_section("Support Zones", items(data["supports"], "supports"), "support"),
        zone_section("Resistance Zones", items(data["resistances"], "resistances"), "resistance"),
    ]

    indicators = items(data["technical_indicators"], "technical_indicators")
    indicator_html = "".join(
        f'<article class="reading"><h3>{esc(row.get("name"))}: {esc(row.get("value"))}</h3><p>{esc(row.get("reading"))}</p></article>'
        for row in indicators
    ) or '<p class="muted">The source returned no technical indicator readings.</p>'
    body.append(f'<section><h2>Technical Indicators</h2>{indicator_html}</section>')

    risk_list = items_to_strings(data["risks"], "risks")
    working_list = items_to_strings(data["working"], "working")
    risk_html = list_html(risk_list) if risk_list else '<p class="muted">No source-backed risk observations were returned.</p>'
    working_html = list_html(working_list) if working_list else '<p class="muted">No source-backed positive observations were returned.</p>'
    body.append('<section><h2>Risk vs. Opportunity</h2><div class="columns">'
                f'<div><h3>Key Risks</h3>{risk_html}</div>'
                f'<div><h3>What Is Working</h3>{working_html}</div></div></section>')

    implications = items(data["implications"], "implications")
    body.append('<section><h2>Trading Implications by Zone</h2><div class="table-wrap"><table><thead><tr>'
                '<th>Zone</th><th>Price range</th><th>Action</th><th>Conviction</th></tr></thead><tbody>'
                + ("".join(f'<tr><td>{esc(row.get("zone"))}</td><td>{esc(row.get("price_range"))}</td>'
                         f'<td>{esc(row.get("action"))}</td><td>{esc(row.get("conviction"))}</td></tr>'
                         for row in implications) or '<tr><td colspan="4">No source-backed implications were returned.</td></tr>')
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
    return template.replace("{{TITLE}}", page_title).replace("{{BODY}}", "\n".join(body))


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
    parser.add_argument("input", type=Path, nargs="?", help="JSON report data")
    parser.add_argument("--output", type=Path, help="HTML destination (defaults to SYMBOL_detailed_zone_analysis.html)")
    parser.add_argument("--validate-only", action="store_true", help="Validate schema and report coverage without writing HTML")
    parser.add_argument("--show-schema", action="store_true", help="Print the bundled report JSON Schema and exit")
    args = parser.parse_args(argv)
    if args.show_schema:
        print(SCHEMA.read_text(encoding="utf-8"), end="")
        return 0
    if args.input is None:
        parser.error("input is required unless --show-schema is used")
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        validation_errors = validate_report(data)
        if validation_errors:
            print("Report data validation failed:", file=sys.stderr)
            for error in validation_errors:
                print(f"  - {error}", file=sys.stderr)
            return 2
        if args.validate_only:
            print(f"Report data valid for {data['symbol']} ({data['report_date']}).")
            return 0
        output = args.output or Path(f"{str(data.get('symbol', 'report')).upper()}_detailed_zone_analysis.html")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(data), encoding="utf-8")
    except json.JSONDecodeError as exc:
        print(f"Invalid report JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Cannot render report: {exc}", file=sys.stderr)
        return 2
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
