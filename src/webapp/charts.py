"""Responsive, accessible SVG charts for the fleet operations dashboard."""

from __future__ import annotations

from html import escape
import math
import re
import uuid

import streamlit as st
import streamlit.components.v1 as components


PALETTE = ["#63a9ff", "#46d6a0", "#ffc45e", "#c49bff", "#ff8c7a"]


def _number(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if math.isfinite(numeric) else 0.0


def _color(value: str, index: int) -> str:
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value or "") else PALETTE[index % len(PALETTE)]


def _display(value: float) -> str:
    return f"{value:,.0f}" if value.is_integer() else f"{value:,.1f}"


def render_metric_grid(items: list[tuple[str, object]], *, label: str = "Key figures") -> None:
    """Show key figures in a labeled grid that reflows from four to two columns."""
    cards = []
    for name, value in items:
        safe_name = escape(str(name))
        safe_value = escape(str(value))
        cards.append(
            f'<article class="operator-metric" role="group" aria-label="{safe_name}: {safe_value}">'
            f'<span>{safe_name}</span><strong>{safe_value}</strong></article>'
        )
    st.markdown(
        f'<div class="operator-metric-grid" data-count="{len(cards)}" role="group" aria-label="{escape(label, quote=True)}">'
        f'{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _line_svg(
    chart_id: str,
    title: str,
    summary: str,
    labels: list[str],
    series: list[dict[str, object]],
    max_value: float,
    *,
    compact: bool,
    tablet: bool = False,
) -> str:
    """Build a line chart at the target width instead of shrinking desktop labels on phones."""
    if compact:
        width, top, right, bottom, left, plot_height = 320.0, 22.0, 12.0, 42.0, 72.0, 200.0
        layout = "mobile"
    elif tablet:
        width, top, right, bottom, left, plot_height = 520.0, 20.0, 16.0, 40.0, 60.0, 188.0
        layout = "tablet"
    else:
        width, top, right, bottom, left, plot_height = 760.0, 26.0, 20.0, 48.0, 64.0, 210.0
        layout = "desktop"
    plot_width = width - left - right
    scale_max = max(max_value, 1.0)
    tick_values = [0.0, scale_max / 2.0, scale_max]
    ticks = []
    for value in tick_values:
        y = top + plot_height - (value / scale_max * plot_height)
        ticks.append(
            f'<line class="gridline" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" />'
            f'<text class="axis-label" x="{left-9}" y="{y+4:.1f}" text-anchor="end">{escape(_display(value))}</text>'
        )

    x_ticks = []
    if labels:
        tick_count = min(4 if compact else 6, len(labels))
        indices = (
            sorted(set(round(index * (len(labels) - 1) / (tick_count - 1)) for index in range(tick_count)))
            if tick_count > 1 else [0]
        )
        for index in indices:
            x = left + (plot_width * index / max(len(labels) - 1, 1))
            label = labels[index]
            x_ticks.append(
                f'<text class="axis-label x-label" x="{x:.1f}" y="{top+plot_height+25:.1f}" '
                f'text-anchor="middle" title="{escape(label, quote=True)}">{escape(label)}</text>'
            )

    lines = []
    legends = []
    defs = []
    for series_index, item in enumerate(series):
        values = item["values"]
        color = item["color"]
        if not labels or not values:
            continue
        points = []
        for point_index, value in enumerate(values):
            x = left + (plot_width * point_index / max(len(values) - 1, 1))
            y = top + plot_height - (value / scale_max * plot_height)
            points.append((x, y, value))
        path = " ".join(
            ("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}"
            for index, (x, y, _) in enumerate(points)
        )
        if len(series) == 1:
            fill_id = f"{chart_id}-fill-{series_index}"
            area_path = (
                f"{path} L {points[-1][0]:.1f} {top+plot_height:.1f} "
                f"L {points[0][0]:.1f} {top+plot_height:.1f} Z"
            )
            lines.append(f'<path class="area" d="{area_path}" fill="url(#{fill_id})" aria-hidden="true" />')
            defs.append(
                f'<linearGradient id="{fill_id}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0%" stop-color="{color}" stop-opacity=".3"/>'
                f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient>'
            )
        lines.append(
            f'<path class="series-line" d="{path}" stroke="{color}" pathLength="1" '
            f'style="--series-delay:{series_index*120}ms" aria-hidden="true" />'
        )
        for point_index, (x, y, value) in enumerate(points):
            point_label = labels[point_index] if point_index < len(labels) else f"Point {point_index + 1}"
            accessible = escape(f"{item['label']}, {point_label}: {_display(value)}", quote=True)
            lines.append(
                f'<circle class="point" cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" '
                f'tabindex="0" role="img" aria-label="{accessible}">'
                f'<title>{escape(str(item["label"]))} · {escape(point_label)}: {_display(value)}</title></circle>'
            )
        legends.append(
            f'<span class="legend-item"><i style="--series-color:{color}"></i>{escape(str(item["label"]))}</span>'
        )

    chart_height = top + plot_height + bottom
    return (
        f'<svg class="chart-svg chart-svg-{layout}" '
        f'viewBox="0 0 {width:.0f} {chart_height:.0f}" role="img" '
        f'aria-labelledby="{chart_id}-title {chart_id}-desc">'
        f'<title id="{chart_id}-title">{escape(title)}</title>'
        f'<desc id="{chart_id}-desc">{escape(summary)} The horizontal axis shows the provided categories and the vertical axis shows values.</desc>'
        f'<defs>{"".join(defs)}</defs>{"".join(ticks)}{"".join(lines)}{"".join(x_ticks)}</svg>'
    )


def render_line_chart(
    title: str,
    summary: str,
    x_labels: list[str],
    series: list[dict[str, object]],
    *,
    height: int = 470,
) -> None:
    """Render desktop and compact chart layouts without clipping labels or the plot."""
    chart_id = f"fleet-chart-{uuid.uuid4().hex}"
    labels = [str(label) for label in x_labels]
    normalized = []
    for index, item in enumerate(series):
        values = [_number(value) for value in item.get("values", [])]
        if len(values) < len(labels):
            values += [0.0] * (len(labels) - len(values))
        normalized.append({
            "label": str(item.get("label", f"Series {index + 1}")),
            "values": values[:len(labels)],
            "color": _color(str(item.get("color", "")), index),
        })
    max_value = max((max(item["values"], default=0.0) for item in normalized), default=0.0)
    legend_items = []
    for item in normalized:
        legend_items.append(
            f'<span class="legend-item"><i style="--series-color:{item["color"]}"></i>'
            f'{escape(item["label"])}</span>'
        )
    legend = f'<div class="chart-legend">{"".join(legend_items)}</div>' if len(normalized) > 1 else ""
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
      *{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display",Inter,sans-serif;color:#f5f7fb}}
      .chart-card{{border:1px solid rgba(185,204,232,.15);border-radius:20px;padding:19px 20px 14px;background:radial-gradient(ellipse at 88% 0%,rgba(99,169,255,.11),transparent 34%),linear-gradient(145deg,#131d2c,#101722);box-shadow:0 14px 34px rgba(12,20,32,.12);overflow:hidden}}
      .chart-eyebrow{{font-size:11px;letter-spacing:.13em;text-transform:uppercase;font-weight:750;color:#86b7ff}}
      .chart-title{{font-size:19px;line-height:1.25;font-weight:760;letter-spacing:-.02em;margin:6px 0 4px;color:#fff}}
      .chart-summary{{font-size:14px;line-height:1.45;color:#c4cedb;margin:0;max-width:70ch}}
      .chart-svg{{display:block;width:100%;height:auto;margin:10px auto 0;overflow:visible}}
      .chart-svg-desktop{{max-width:860px}}
      .chart-svg-tablet,.chart-svg-mobile{{display:none}}
      .gridline{{stroke:rgba(197,213,235,.16);stroke-width:1;stroke-dasharray:2 5}}
      .axis-label{{font:12px -apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif;fill:#c0ccda}}
      .series-line{{fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;animation:draw-line 1s cubic-bezier(.2,.7,.2,1) var(--series-delay) forwards}}
      .area{{opacity:.9;animation:area-in .8s ease-out both}}
      .point{{stroke:#111a27;stroke-width:2;cursor:crosshair;transition:r .16s ease,filter .16s ease}}
      .point:hover,.point:focus{{r:7;filter:drop-shadow(0 0 6px currentColor);outline:none}}
      .chart-legend{{display:flex;flex-wrap:wrap;gap:14px;margin:9px 4px 0;color:#e2e9f1;font-size:13px}}
      .legend-item{{display:inline-flex;align-items:center;gap:7px}}.legend-item i{{width:9px;height:9px;border-radius:50%;background:var(--series-color);flex:0 0 auto}}
      @keyframes draw-line{{to{{stroke-dashoffset:0}}}}@keyframes area-in{{from{{opacity:0}}to{{opacity:.9}}}}
      @media(max-width:760px){{
        .chart-card{{padding:16px 13px 12px;border-radius:16px}}
        .chart-title{{font-size:17px}}.chart-summary{{font-size:14px}}
        .chart-svg-desktop{{display:none}}
        .chart-legend{{font-size:13px;gap:10px}}
      }}
      @media(min-width:431px) and (max-width:760px){{.chart-svg-tablet{{display:block;max-width:520px}}.chart-svg-tablet .axis-label{{font-size:12px}}}}
      @media(max-width:430px){{.chart-svg-mobile{{display:block;max-width:320px}}.chart-svg-mobile .axis-label{{font-size:12px}}}}
      @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}.series-line{{stroke-dashoffset:0}}}}
    </style></head><body><figure class="chart-card" aria-label="{escape(title, quote=True)}">
      <div class="chart-eyebrow">Operations intel · trend</div><figcaption><h2 class="chart-title">{escape(title)}</h2><p class="chart-summary">{escape(summary)}</p></figcaption>
      {legend}{_line_svg(chart_id + "-desktop",title,summary,labels,normalized,max_value,compact=False)}{_line_svg(chart_id + "-tablet",title,summary,labels,normalized,max_value,compact=False,tablet=True)}{_line_svg(chart_id + "-mobile",title,summary,labels,normalized,max_value,compact=True)}
    </figure></body></html>"""
    components.html(html, height=max(height, 520), scrolling=False)


def render_horizontal_bars(
    title: str,
    summary: str,
    labels: list[str],
    values: list[object],
    *,
    colors: list[str] | None = None,
    height: int | None = None,
    show_rank: bool = True,
) -> None:
    """Render responsive comparison bars with exact values and keyboard semantics."""
    numeric_values = [_number(value) for value in values]
    count = min(len(labels), len(numeric_values))
    max_value = max(max(numeric_values[:count], default=0.0), 1.0)
    rows = []
    for index in range(count):
        label = str(labels[index])
        value = numeric_values[index]
        color = _color(colors[index] if colors and index < len(colors) else "", index)
        bar_width = max(0.0, min(100.0, value / max_value * 100.0))
        label_safe = escape(label, quote=True)
        rank = f'<span class="rank">{index+1:02d}</span>' if show_rank else ""
        rows.append(
            f'<div class="bar-row" role="group" aria-label="{label_safe}: {_display(value)}">'
            f'<div class="bar-row-head"><span class="bar-label"><i style="--bar-color:{color}"></i>'
            f'{rank}<span>{escape(label)}</span></span>'
            f'<strong>{_display(value)}</strong></div>'
            f'<div class="bar-track" aria-hidden="true"><span class="bar-fill" '
            f'style="--bar-width:{bar_width:.2f}%;--bar-color:{color}"></span></div></div>'
        )
    if not rows:
        rows.append('<p class="empty">No values are available for this selection.</p>')

    summary_lines = min(4, max(1, math.ceil(len(summary) / 58)))
    title_lines = min(3, max(1, math.ceil(len(title) / 32)))
    frame_height = height or max(270, 130 + count * 48 + summary_lines * 17 + title_lines * 19)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
      *{{box-sizing:border-box}}body{{margin:0;background:transparent;color:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display",Inter,sans-serif}}
      .chart-card{{border:1px solid rgba(185,204,232,.15);border-radius:20px;padding:19px 20px 18px;background:radial-gradient(ellipse at 90% 0%,rgba(99,169,255,.1),transparent 36%),linear-gradient(145deg,#131d2c,#101722);box-shadow:0 14px 34px rgba(12,20,32,.12);overflow:visible}}
      .eyebrow{{font-size:11px;letter-spacing:.13em;text-transform:uppercase;font-weight:750;color:#86b7ff}}
      h2{{font-size:19px;line-height:1.25;font-weight:760;letter-spacing:-.02em;margin:6px 0 4px;color:#fff}}
      .summary{{font-size:14px;line-height:1.45;color:#c4cedb;margin:0 0 15px;max-width:70ch}}
      .bar-list{{display:grid;gap:14px}}.bar-row{{min-width:0}}
      .bar-row-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:6px;font-size:14px}}
      .bar-label{{display:flex;align-items:flex-start;gap:8px;min-width:0;flex:1;color:#e6edf6}}
      .bar-label i{{display:inline-block;width:9px;height:9px;margin-top:5px;border-radius:50%;background:var(--bar-color);flex:0 0 auto}}
      .rank{{font-size:11px;letter-spacing:.04em;color:#a7b5c5;font-variant-numeric:tabular-nums;flex:0 0 auto}}
      .bar-label span:last-child{{min-width:0;overflow-wrap:anywhere}}
      .bar-row-head strong{{font-size:14px;color:#fff;font-variant-numeric:tabular-nums;white-space:nowrap;flex:0 0 auto}}
      .bar-track{{height:10px;border-radius:99px;background:rgba(193,210,234,.15);overflow:hidden}}
      .bar-fill{{display:block;height:100%;width:var(--bar-width);border-radius:inherit;background:var(--bar-color);transform-origin:left;animation:fill-bar .85s cubic-bezier(.2,.7,.2,1) both}}
      @keyframes fill-bar{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}.empty{{color:#c4cedb;font-size:14px;margin:8px 0}}
      @media(max-width:540px){{.chart-card{{padding:16px 13px;border-radius:16px}}h2{{font-size:17px}}.summary{{font-size:14px}}.bar-list{{gap:13px}}}}
      @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}}}
    </style></head><body><section class="chart-card" aria-label="{escape(title, quote=True)}"><div class="eyebrow">Operations intel · comparison</div><h2>{escape(title)}</h2><p class="summary">{escape(summary)}</p><div class="bar-list">{"".join(rows)}</div></section></body></html>"""
    components.html(html, height=frame_height, scrolling=False)
