"""DT-CARGO multi-page analytics app — Apple-inspired with 3D motion graphics."""

import streamlit as st

from src.webapp.overview import render_overview
from src.webapp.home import render_home
from src.webapp.project import render_project_overview
from src.webapp.distributions import render_distributions
from src.webapp.anomaly import render_anomaly_monitoring
from src.webapp.vehicle import render_vehicle_explorer
from src.webapp.track import render_track_explorer
from src.webapp.methodology import render_methodology
from src.webapp.cluster_analysis import render_cluster_analysis
from src.webapp.duration import render_tour_duration
from src.webapp.quality import render_quality
from src.webapp.vehicle_sim_page import render_vehicle_simulator
from src.webapp.walkthrough import render_project_walkthrough
from src.webapp.navigation import get_page_link, register_page_links


st.set_page_config(
    page_title="DT-CARGO | Fleet Intelligence",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      /* ─────────────────────────── Samsara Telematics Typography ─────────────────────────── */
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

      :root {
        /* Samsara Brand & Operations System */
        --sm-loud: #feae0f;          /* Samsara High-Vis Industrial Worksite Yellow */
        --sm-loud-hover: #e09908;
        --sm-loud-soft: rgba(254, 174, 15, 0.12);
        --sm-dark: #1c1917;          /* Samsara Inverse / Tarmac Obsidian */
        --sm-muted: #57534e;         /* Operations Medium Slate */
        --sm-faint: #f5f4f1;         /* Field Paper Off-White */
        --sm-line: #e7e5e0;          /* Samsara Hardware Line */
        --sm-blue: #0071e3;          /* Telematics Connected Signal Blue */
        --sm-blue-soft: rgba(0, 113, 227, 0.08);
        --sm-green: #10b981;         /* Operational Uptime Green */
        --sm-green-soft: rgba(16, 185, 129, 0.10);
        --sm-red: #ef4444;           /* Alert / Harsh Event Red */

        /* Liquid Glass Layering */
        --liquid-glass-fill: rgba(255, 255, 255, 0.78);
        --liquid-glass-border: rgba(255, 255, 255, 0.90);
        --liquid-glass-shadow: 0 16px 36px -10px rgba(28, 25, 23, 0.08), 0 0 0 1px rgba(255, 255, 255, 0.6) inset;
        --liquid-glass-highlight: inset 0 1px 1.5px 0 rgba(255, 255, 255, 0.95);
        --liquid-glass-blur: blur(28px) saturate(190%);

        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 18px;
        --radius-xl: 26px;
        --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
      }

      /* ─────────────────────────── Base & Mesh Canvas ─────────────────────────── */
      html, body {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        color: var(--sm-dark);
      }
      /* Ensure Material Symbols icon font is never overridden */
      [class*="material-symbols"],
      span[data-testid="stIconMaterial"],
      .material-symbols-rounded,
      [data-testid="stSidebarNav"] span:has(svg),
      [data-testid="stSidebarNav"] span[class*="material"] {
        font-family: 'Material Symbols Rounded' !important;
        font-style: normal !important;
        display: inline-block !important;
        visibility: visible !important;
        opacity: 1 !important;
      }
      [data-testid="stSidebarNav"] a span {
        visibility: visible !important;
      }
      .stApp {
        background:
          radial-gradient(circle at 15% 15%, rgba(254, 174, 15, 0.06) 0%, transparent 40%),
          radial-gradient(circle at 85% 15%, rgba(0, 113, 227, 0.05) 0%, transparent 35%),
          radial-gradient(circle at 50% 85%, rgba(16, 185, 129, 0.04) 0%, transparent 45%),
          #f7f6f2;
        color: var(--sm-dark);
      }
      .block-container {
        max-width: 1480px;
        padding-top: 2rem;
        padding-bottom: 3rem;
      }

      /* Keep scroll-to-content targets clear of the fixed translucent toolbar. */
      [data-testid="stMain"] {
        scroll-padding-top: 76px;
      }
      [data-testid="stMain"] [data-testid="stElementContainer"] {
        scroll-margin-top: 76px;
      }

      /* ─────────────────────────── Liquid Glass Navigation & Top Bar ─────────────────────────── */
      header[data-testid="stHeader"] {
        background: var(--liquid-glass-fill) !important;
        backdrop-filter: var(--liquid-glass-blur) !important;
        -webkit-backdrop-filter: var(--liquid-glass-blur) !important;
        border-bottom: 1px solid var(--sm-line) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
      }

      /* ─────────────────────────── Fleettrack / Samsara High-Contrast Sidebar ─────────────────────────── */
      [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 2px solid #e2e8f0 !important;
        min-width: 290px !important;
        z-index: 100 !important;
      }
      [data-testid="stSidebarUserContent"] {
        padding-top: 1rem;
      }
      /* Sidebar Section Group Headers */
      [data-testid="stSidebarNavItems"] > div:first-child,
      [data-testid="stSidebarNav"] h2,
      [data-testid="stSidebarNav"] header,
      [data-testid="stSidebar"] h3 {
        color: #0f172a !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        letter-spacing: -0.02em !important;
      }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #64748b !important;
        font-weight: 600 !important;
      }
      [data-testid="stSidebarNav"] { padding: 0.6rem 0.8rem; }

      /* Sidebar Navigation Links - Fleettrack High-Contrast Bold */
      [data-testid="stSidebarNavLink"],
      [data-testid="stSidebarNav"] a {
        border-radius: var(--radius-md) !important;
        padding: 0.65rem 0.95rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;            /* Pitch black/dark slate for 100% visibility */
        transition: all 0.22s var(--ease-spring) !important;
        border: 1px solid transparent !important;
        margin-bottom: 3px !important;
        display: flex !important;
        align-items: center !important;
        text-decoration: none !important;
      }
      /* Sidebar Link Text explicitly targeted */
      [data-testid="stSidebarNavLink"] span,
      [data-testid="stSidebarNav"] a span,
      [data-testid="stSidebarNavLink"] div,
      [data-testid="stSidebarNav"] p {
        color: #0f172a !important;            /* High-contrast solid text */
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        opacity: 1 !important;
        visibility: visible !important;
      }
      /* Sidebar Icons - Bright Fleettrack Amber / Green Accents */
      [data-testid="stSidebarNavLink"] span:first-child,
      [data-testid="stSidebarNav"] a span:first-child {
        font-size: 1.25rem !important;
        margin-right: 0.55rem !important;
        display: inline-block !important;
        opacity: 1 !important;
        filter: none !important;
      }
      /* Hover State */
      [data-testid="stSidebarNavLink"]:hover,
      [data-testid="stSidebarNav"] a:hover {
        background: #f1f5f9 !important;
        color: #0284c7 !important;
        transform: translateX(4px) !important;
      }
      [data-testid="stSidebarNavLink"]:hover span,
      [data-testid="stSidebarNav"] a:hover span {
        color: #0284c7 !important;
      }
      /* Active Page State - Fleettrack / Samsara Yellow-Amber Banner */
      [data-testid="stSidebarNavLink"][aria-current="page"],
      [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: #fffbeb !important;       /* Warm alert yellow tint */
        color: #b45309 !important;            /* High-vis active amber */
        font-weight: 800 !important;
        border-left: 4px solid #f59e0b !important;
        border-top: 1px solid #fde68a !important;
        border-right: 1px solid #fde68a !important;
        border-bottom: 1px solid #fde68a !important;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.15) !important;
      }
      [data-testid="stSidebarNavLink"][aria-current="page"] span,
      [data-testid="stSidebarNav"] a[aria-current="page"] span {
        color: #b45309 !important;
        font-weight: 800 !important;
      }

      /* ─────────────────────────── Samsara Telematics Typography ─────────────────────────── */
      h1, h2, h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--sm-dark);
        letter-spacing: -0.035em;
        font-weight: 800;
      }
      h1 {
        font-size: clamp(2.1rem, 3.6vw, 2.9rem);
        line-height: 1.15;
      }
      h2 { font-size: clamp(1.3rem, 2vw, 1.6rem); font-weight: 700; }
      p, label { color: var(--sm-muted); font-size: 0.98rem; line-height: 1.6; }
      [data-testid="stCaptionContainer"] {
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 0.08em;
        font-weight: 700;
        font-size: 0.76rem !important;
        text-transform: uppercase;
        color: var(--sm-muted);
      }

      /* ─────────────────────────── Samsara Telematics Metric Cards ─────────────────────────── */
      [data-testid="stMetric"] {
        background: var(--liquid-glass-fill) !important;
        backdrop-filter: var(--liquid-glass-blur) !important;
        -webkit-backdrop-filter: var(--liquid-glass-blur) !important;
        border: 1px solid var(--sm-line) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.25rem 1.4rem;
        min-height: 7.6rem;
        box-shadow: var(--liquid-glass-shadow), var(--liquid-glass-highlight) !important;
        transition: all 0.35s var(--ease-spring);
        position: relative;
        overflow: hidden;
      }
      /* Top High-Vis Accent Accent Edge */
      [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--sm-loud) 0%, var(--sm-blue) 100%);
        pointer-events: none;
      }
      [data-testid="stMetric"]:hover {
        border-color: rgba(254, 174, 15, 0.45) !important;
        box-shadow: 0 16px 36px -8px rgba(28, 25, 23, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.9) inset !important;
        transform: translateY(-4px);
      }
      [data-testid="stMetricLabel"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--sm-muted) !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        position: relative;
        z-index: 1;
      }
      [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', 'Plus Jakarta Sans', monospace !important;
        color: var(--sm-dark) !important;
        font-size: clamp(1.4rem, 2.3vw, 2.05rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.04em !important;
        position: relative;
        z-index: 1;
      }
      [data-testid="stMetricValue"] div {
        white-space: nowrap;
        overflow: visible;
        text-overflow: clip;
        color: var(--sm-dark) !important;
      }

      /* Metric Delta Indicators */
      [data-testid="stMetricDelta"] svg {
        fill: var(--sm-green) !important;
      }
      [data-testid="stMetricDelta"] div {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        color: var(--sm-green) !important;
      }

      /* ─────────────────────────── Table & Dataframe Visual Values ─────────────────────────── */
      [data-testid="stDataFrame"] {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--sm-line) !important;
        overflow: hidden;
        background: #ffffff !important;
      }
      [data-testid="stDataFrame"] table {
        font-family: 'Plus Jakarta Sans', sans-serif;
      }

      /* ─────────────────────────── Liquid Glass Containers & Cards ─────────────────────────── */
      div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--liquid-glass-fill) !important;
        backdrop-filter: var(--liquid-glass-blur) !important;
        -webkit-backdrop-filter: var(--liquid-glass-blur) !important;
        border: 1px solid var(--sm-line) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--liquid-glass-shadow), var(--liquid-glass-highlight) !important;
        transition: all 0.35s var(--ease-spring);
      }
      div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.06) !important;
      }

      /* ─────────────────────────── Expanders ─────────────────────────── */
      [data-testid="stExpander"] {
        background: var(--liquid-glass-fill) !important;
        backdrop-filter: var(--liquid-glass-blur) !important;
        -webkit-backdrop-filter: var(--liquid-glass-blur) !important;
        border-radius: var(--radius-lg) !important;
        border: 1px solid var(--sm-line) !important;
        box-shadow: var(--liquid-glass-shadow) !important;
        overflow: hidden;
        transition: all 0.3s var(--ease-spring);
      }
      [data-testid="stExpander"]:hover {
        border-color: rgba(254, 174, 15, 0.35) !important;
      }

      /* ─────────────────────────── Filter summary ─────────────────────────── */
      .st-key-filter-summary { color: var(--muted); font-size: 0.9rem; padding: 0.2rem 0 0.4rem; }

      /* ─────────────────────────── Scroll Story — Cinematic Stage ─────────────────────────── */
      .fleet-scroll-story {
        display: grid; grid-template-columns: minmax(0, 1.02fr) minmax(0, 0.98fr);
        gap: clamp(1.5rem, 4vw, 4rem); align-items: start; margin: 2rem 0 3rem;
      }
      .fleet-story-stage {
        position: sticky; top: 1.25rem; min-height: min(76vh, 680px); align-self: start;
        display: flex; flex-direction: column; justify-content: space-between; overflow: hidden;
        padding: clamp(1.5rem, 3vw, 2.75rem); color: #f3f7f4; border-radius: var(--radius-xl);
        background:
          radial-gradient(ellipse at 20% 80%, rgba(0,113,227,0.15), transparent 50%),
          radial-gradient(ellipse at 80% 20%, rgba(52,199,89,0.12), transparent 50%),
          radial-gradient(ellipse at 50% 50%, rgba(175,82,222,0.06), transparent 60%),
          linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 60px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
        animation: stage-entrance 1s var(--ease-spring) both;
      }

      /* ─────────────────────────── 3D Floating Particles (CSS only) ─────────────────────────── */
      .fleet-story-stage::before {
        content: '';
        position: absolute;
        inset: 0;
        background:
          radial-gradient(2px 2px at 10% 20%, rgba(255,255,255,0.3), transparent),
          radial-gradient(2px 2px at 30% 60%, rgba(0,113,227,0.4), transparent),
          radial-gradient(1.5px 1.5px at 60% 30%, rgba(52,199,89,0.3), transparent),
          radial-gradient(2px 2px at 80% 70%, rgba(175,82,222,0.3), transparent),
          radial-gradient(1px 1px at 90% 10%, rgba(255,255,255,0.2), transparent),
          radial-gradient(1.5px 1.5px at 45% 85%, rgba(90,200,250,0.3), transparent),
          radial-gradient(1px 1px at 15% 90%, rgba(255,149,0,0.2), transparent),
          radial-gradient(2px 2px at 70% 15%, rgba(255,255,255,0.15), transparent);
        animation: particle-drift 12s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
      }
      .fleet-story-stage > * { position: relative; z-index: 1; }

      .story-stage-header, .story-stage-footer, .story-chart-caption,
      .story-cluster-label { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }

      .story-status, .story-stage-kicker, .story-chapter-index {
        font-size: .72rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
      }
      .story-status {
        display: inline-flex; align-items: center; gap: .55rem;
        color: var(--teal);
      }
      .story-status i {
        width: .5rem; height: .5rem; border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 8px rgba(52,199,89,0.5), 0 0 20px rgba(52,199,89,0.2);
        animation: status-pulse 2s ease-in-out infinite;
      }
      .story-stage-range { color: rgba(255,255,255,0.5); font-size: .76rem; text-align: right; }
      .story-stage-core { margin: 1rem 0 1.1rem; }
      .story-stage-intro { display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; gap: .5rem; }
      .story-stage-copy { position: relative; z-index: 1; min-width: 0; }
      .story-stage-kicker { color: rgba(255,255,255,0.45); margin: 0 0 .55rem; }
      .fleet-story-stage .story-stage-value {
        color: #fff;
        font-size: clamp(2.7rem, 4vw, 3.7rem);
        font-weight: 800;
        line-height: .98;
        letter-spacing: -.065em;
        margin: 0;
        white-space: nowrap;
        text-shadow: 0 0 40px rgba(0,113,227,0.3);
        animation: value-count-in 0.8s var(--ease-spring) 0.3s both;
      }
      .story-stage-support { color: rgba(255,255,255,0.55); font-size: 1rem; margin: .75rem 0 1rem; }
      .story-chart { display: block; width: 100%; height: auto; margin-top: .8rem; overflow: visible; }
      .story-gridline { fill: none; stroke: rgba(255,255,255,.06); stroke-width: 1; }
      .story-chart-area { fill: url(#story-fill); }
      .story-chart-line {
        fill: none; stroke: url(#chart-line-gradient); stroke-width: 3;
        stroke-linecap: round; stroke-linejoin: round;
        stroke-dasharray: 1200; stroke-dashoffset: 1200;
        animation: draw-story-line 1.6s var(--ease-spring) .15s forwards;
        filter: drop-shadow(0 0 6px rgba(0,113,227,0.4));
      }
      .story-chart-dot {
        fill: #fff; stroke: var(--accent); stroke-width: 3;
        filter: drop-shadow(0 0 8px rgba(0,113,227,0.5));
        animation: dot-pulse 2s ease-in-out infinite 1.8s;
      }
      .story-chart-caption { color: rgba(255,255,255,0.4); font-size: .78rem; margin-top: .45rem; }

      .story-stage-footer {
        border-top: 1px solid rgba(255,255,255,0.08); padding-top: 1rem;
        color: rgba(255,255,255,0.5); font-size: .9rem;
      }
      .story-stage-footer strong {
        color: white; font-size: 1.1rem; font-weight: 700;
        text-shadow: 0 0 20px rgba(52,199,89,0.3);
      }

      /* ─────────────────────────── Story Chapters ─────────────────────────── */
      .fleet-story-chapters { padding: .25rem 0; }
      .story-chapter {
        min-height: 68vh; display: flex; flex-direction: column;
        justify-content: center; padding: 2rem .25rem;
        border-bottom: 1px solid var(--line);
        opacity: 0;
        transform: translateY(40px);
        animation: chapter-reveal 0.8s var(--ease-spring) forwards;
      }
      .story-chapter:nth-child(1) { animation-delay: 0.2s; }
      .story-chapter:nth-child(2) { animation-delay: 0.4s; }
      .story-chapter:nth-child(3) { animation-delay: 0.6s; }
      .story-chapter:last-child { border-bottom: 0; }
      .story-chapter-index {
        color: var(--accent); display: flex; align-items: center; gap: .8rem;
        margin: 0 0 1.2rem;
      }
      .story-chapter-index span { color: var(--muted); }
      .story-chapter h2 {
        font-size: clamp(1.7rem, 3vw, 2.55rem); max-width: 14ch;
        line-height: 1.08; margin: 0 0 1rem;
        background: linear-gradient(135deg, var(--ink) 0%, #424245 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .story-chapter > p:not(.story-chapter-index) {
        color: var(--muted); font-size: 1.02rem; line-height: 1.65; max-width: 48ch;
      }
      .story-note {
        display: inline-flex; align-self: flex-start; padding: .55rem .8rem;
        margin-top: .7rem; color: var(--accent); background: var(--accent-soft);
        border-radius: 999px; font-size: .8rem; font-weight: 600;
        transition: all 0.3s var(--ease-spring);
      }
      .story-note:hover { transform: scale(1.05); box-shadow: var(--shadow-sm); }

      .story-cluster-list { display: grid; gap: .85rem; margin-top: .6rem; }
      .story-cluster-data { display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; gap: 1.1rem; margin-top: .5rem; }
      .story-cluster-label { font-size: .84rem; color: var(--ink); margin-bottom: .4rem; }
      .story-cluster-label strong { font-weight: 700; font-variant-numeric: tabular-nums; }
      .story-empty { color: var(--muted); font-size: .88rem; margin: .8rem 0 0; }

      .story-bar-track {
        height: .5rem; overflow: hidden; border-radius: 999px;
        background: var(--line);
      }
      .story-bar-fill {
        display: block; width: 100%; height: 100%; border-radius: inherit;
        background: linear-gradient(90deg, var(--accent) 0%, var(--green) 100%);
        transform: scaleX(0); transform-origin: left;
        animation: bar-fill-in 1s var(--ease-spring) 0.5s forwards;
      }

      .story-review-callout {
        display: flex; align-items: baseline; gap: .8rem;
        padding: 1rem 0; margin-top: .5rem; border-top: 1px solid var(--line);
      }
      .story-review-callout strong {
        font-size: 2rem; letter-spacing: -.04em; color: var(--ink); font-weight: 800;
      }
      .story-review-callout span { color: var(--muted); font-size: .88rem; }

      /* ─────────────────────────── Quick Actions ─────────────────────────── */
      .st-key-quick-actions [data-testid="stPageLink"] a {
        display: block; background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--radius-md); padding: 0.75rem 0.9rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.4s var(--ease-spring);
        transform-style: preserve-3d;
      }
      .st-key-quick-actions [data-testid="stPageLink"] a:hover {
        background: var(--accent-soft);
        border-color: rgba(0,113,227,0.15);
        box-shadow: var(--shadow-md), var(--shadow-glow);
        transform: translateY(-4px) scale(1.02);
      }

      /* ─────────────────────────── Focus states ─────────────────────────── */
      .stButton > button:focus-visible, [data-testid="stPageLink"] a:focus-visible,
      [data-testid="stSidebarNav"] a:focus-visible {
        outline: 3px solid var(--accent); outline-offset: 2px;
      }

      /* ─────────────────────────── Interactive High-Tech MERN Buttons ─────────────────────────── */
      .stButton > button {
        background: linear-gradient(135deg, #1c1917 0%, #292524 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(254, 174, 15, 0.45) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;
        position: relative !important;
        overflow: hidden !important;
      }
      .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(254, 174, 15, 0.25), transparent);
        transition: left 0.5s ease;
      }
      .stButton > button:hover::before {
        left: 100%;
      }
      .stButton > button:hover {
        background: linear-gradient(135deg, #292524 0%, #000000 100%) !important;
        border-color: #feae0f !important;
        box-shadow: 0 8px 24px rgba(254, 174, 15, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-3px) scale(1.02) !important;
        color: #feae0f !important;
      }
      .stButton > button:active {
        transform: translateY(-1px) scale(0.99) !important;
      }

      /* Primary Call to Action Buttons */
      .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #feae0f 0%, #f59e0b 100%) !important;
        color: #1c1917 !important;
        border: 1px solid #d97706 !important;
        font-weight: 800 !important;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.35) !important;
      }
      .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 8px 28px rgba(245, 158, 11, 0.5) !important;
      }

      /* ─────────────────────────── Selectbox / Input styling ─────────────────────────── */
      [data-testid="stSelectbox"] > div > div {
        border-radius: var(--radius-md) !important;
      }

      /* ─────────────────────────── 3D Keyframe Animations ─────────────────────────── */
      @keyframes stage-entrance {
        from { opacity: 0; transform: perspective(1200px) rotateX(8deg) translateY(40px) scale(0.95); }
        to { opacity: 1; transform: perspective(1200px) rotateX(0) translateY(0) scale(1); }
      }
      @keyframes value-count-in {
        from { opacity: 0; transform: translateY(20px) scale(0.8); filter: blur(8px); }
        to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
      }
      @keyframes chapter-reveal {
        from { opacity: 0; transform: translateY(40px); }
        to { opacity: 1; transform: translateY(0); }
      }
      @keyframes vehicle-float {
        0%, 100% { transform: translateY(0px) rotate(-1deg); }
        50% { transform: translateY(-12px) rotate(1deg); }
      }
      @keyframes float-gentle {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
      }
      @keyframes particle-drift {
        0% { transform: translate(0, 0) rotate(0deg); opacity: 0.6; }
        100% { transform: translate(10px, -15px) rotate(5deg); opacity: 1; }
      }
      @keyframes status-pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(52,199,89,0.5), 0 0 20px rgba(52,199,89,0.2); }
        50% { opacity: 0.6; box-shadow: 0 0 12px rgba(52,199,89,0.8), 0 0 30px rgba(52,199,89,0.3); }
      }
      @keyframes dot-pulse {
        0%, 100% { r: 5; }
        50% { r: 7; }
      }
      @keyframes bar-fill-in {
        from { transform: scaleX(0); }
        to { transform: scaleX(var(--share)); }
      }
      @keyframes draw-story-line { to { stroke-dashoffset: 0; } }
      @keyframes story-arrive {
        from { opacity: .35; transform: translateY(24px); }
        to { opacity: 1; transform: translateY(0); }
      }
      @keyframes glow-rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
      }

      /* ─────────────────────────── Scroll-driven chapter animation ─────────────────────────── */
      @supports (animation-timeline: view(block)) {
        .story-chapter {
          animation: story-arrive linear both;
          animation-timeline: view(block);
          animation-range: entry 5% cover 34%;
        }
      }

      /* ─────────────────────────── 3D Hero Section ─────────────────────────── */
      .hero-3d {
        position: relative;
        padding: 3rem 2.5rem;
        margin: -1rem 0 2rem;
        border-radius: var(--radius-xl);
        background:
          radial-gradient(ellipse at 30% 40%, rgba(0,113,227,0.08), transparent 60%),
          radial-gradient(ellipse at 70% 60%, rgba(52,199,89,0.06), transparent 60%),
          var(--surface);
        border: 1px solid var(--line);
        box-shadow: var(--shadow-lg);
        overflow: hidden;
        animation: hero-entrance 1.2s var(--ease-spring) both;
      }
      .hero-3d::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(
          from 0deg,
          transparent 0deg,
          rgba(0,113,227,0.03) 60deg,
          transparent 120deg,
          rgba(52,199,89,0.03) 180deg,
          transparent 240deg,
          rgba(175,82,222,0.02) 300deg,
          transparent 360deg
        );
        animation: glow-rotate 20s linear infinite;
        pointer-events: none;
      }
      .hero-3d > * { position: relative; z-index: 1; }
      @keyframes hero-entrance {
        from { opacity: 0; transform: perspective(1000px) rotateX(5deg) translateY(30px); }
        to { opacity: 1; transform: perspective(1000px) rotateX(0) translateY(0); }
      }

      /* ─────────────────────────── 3D Orb Background Element ─────────────────────────── */
      .orb-container {
        position: absolute;
        top: 0; right: 0;
        width: 280px; height: 280px;
        pointer-events: none;
        z-index: 0;
      }
      .orb {
        width: 100%; height: 100%;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 35%,
          rgba(0,113,227,0.15),
          rgba(52,199,89,0.08) 40%,
          rgba(175,82,222,0.05) 70%,
          transparent 100%
        );
        filter: blur(40px);
        animation: orb-breathe 8s ease-in-out infinite;
      }
      @keyframes orb-breathe {
        0%, 100% { transform: scale(1) translate(0, 0); opacity: 0.7; }
        33% { transform: scale(1.15) translate(-10px, 15px); opacity: 0.9; }
        66% { transform: scale(0.95) translate(10px, -10px); opacity: 0.6; }
      }

      /* ─────────────────────────── Glassmorphic Info Cards ─────────────────────────── */
      .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-lg);
        padding: 1.2rem 1.4rem;
        box-shadow: var(--shadow-md);
        transition: all 0.4s var(--ease-spring);
      }
      .glass-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
      }

      /* ─────────────────────────── Animated gradient text ─────────────────────────── */
      .gradient-text {
        background: linear-gradient(
          135deg,
          var(--accent) 0%,
          var(--green) 25%,
          var(--purple) 50%,
          var(--accent) 75%,
          var(--green) 100%
        );
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shimmer 6s linear infinite;
      }

      /* ─────────────────────────── Responsive ─────────────────────────── */
      @media (max-width: 760px) {
        .block-container { padding: 1rem 1rem 2rem; }
        .st-key-kpi-grid [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.65rem; }
        .st-key-kpi-grid [data-testid="column"] { flex: 1 1 calc(50% - 0.65rem) !important; min-width: calc(50% - 0.65rem) !important; }
        .fleet-scroll-story { grid-template-columns: 1fr; gap: 1rem; }
        .fleet-story-stage { position: relative; top: auto; min-height: 390px; }
        .story-chapter { min-height: 340px; padding: 1.5rem 0; }
        .st-key-quick-actions [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.65rem; }
        .st-key-quick-actions [data-testid="column"] { flex: 1 1 calc(50% - 0.65rem) !important; min-width: calc(50% - 0.65rem) !important; }
        .hero-3d { padding: 2rem 1.5rem; }
      }
      @media (max-width: 480px) {
        .story-stage-intro { grid-template-columns: 1fr; gap: .1rem; }
        .story-cluster-data { grid-template-columns: 1fr; }
      }

      /* ─────────────────────────── Reduced motion ─────────────────────────── */
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          scroll-behavior: auto !important;
          transition-duration: 0.01ms !important;
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
        }
      }

      /* ─────────────────────────── Dataframe styling ─────────────────────────── */
      [data-testid="stDataFrame"] {
        border-radius: var(--radius-md) !important;
        overflow: hidden;
      }

      /* ─────────────────────────── Chart containers ─────────────────────────── */
      [data-testid="stVegaLiteChart"] {
        border-radius: var(--radius-md);
        overflow: hidden;
      }

      /* Compact top navigation replaces the built-in page sidebar. */
      section[data-testid="stSidebar"],
      button[data-testid="stSidebarCollapsedControl"],
      [data-testid="stToolbar"] { display: none !important; }
      header[data-testid="stHeader"] { display: none !important; }
      .block-container { padding-top: 1rem; }
      .st-key-global-navigation {
        position: relative; z-index: 5;
        margin: 0 0 1.35rem; padding: .35rem 0 .65rem;
        border-bottom: 1px solid rgba(88, 84, 77, .16);
        background: rgba(247, 246, 242, .9);
        backdrop-filter: blur(18px) saturate(145%);
        -webkit-backdrop-filter: blur(18px) saturate(145%);
      }
      .st-key-global-navigation [data-testid="stHorizontalBlock"] { align-items: center; }
      .st-key-global-navigation [data-testid="stPageLink"] a,
      .st-key-global-navigation [data-testid="stPopover"] button {
        min-height: 44px; border-radius: 999px; padding: .55rem .95rem;
        color: #20211f !important; font-weight: 700;
        border: 1px solid transparent; background: transparent;
      }
      .st-key-global-navigation [data-testid="stPageLink"] a:hover,
      .st-key-global-navigation [data-testid="stPopover"] button:hover {
        border-color: rgba(31, 38, 45, .13); background: rgba(255,255,255,.86);
      }
      .st-key-global-navigation [data-testid="stPopoverBody"] [data-testid="stPageLink"] a {
        min-height: 42px; border-radius: 10px; padding: .55rem .75rem;
      }
      .st-key-global-navigation [data-testid="stToggle"] label { white-space: nowrap; font-size: .85rem; }
      .st-key-global-navigation [data-testid="stToggle"] { justify-content: flex-end; }
      .st-key-home-hero {
        padding: clamp(1rem, 2.8vw, 2.4rem); border-radius: 28px; color: #f4f6f7;
        background-image: linear-gradient(90deg, rgba(14,22,27,.99) 0%, rgba(14,22,27,.92) 39%, rgba(14,22,27,.62) 66%, rgba(14,22,27,.28) 100%),
          url('/app/static/truck-medium.jpg');
        background-size: cover; background-position: center 56%; background-repeat: no-repeat;
        border: 1px solid rgba(255,255,255,.08);
        box-shadow: 0 18px 50px rgba(20,30,33,.17);
      }
      .st-key-home-hero h1, .st-key-home-hero h2, .st-key-home-hero h3,
      .st-key-home-hero p { color: #f4f6f7 !important; }
      .st-key-home-hero [data-testid="stCaptionContainer"] { color: #c9d2d3 !important; }
      .st-key-home-hero [data-testid="stPageLink"] a {
        min-height: 48px; display: flex; align-items: center; border-radius: 12px;
        padding: .7rem .9rem; border: 1px solid rgba(255,255,255,.2);
        background: rgba(255,255,255,.08); color: #fff !important;
        transition: background-color .18s ease, border-color .18s ease, transform .18s ease;
      }
      .st-key-home-hero [data-testid="stPageLink"] a:hover {
        background: rgba(255,255,255,.15); border-color: rgba(255,255,255,.38); transform: translateY(-2px);
      }
      .st-key-home-hero [data-testid="stIframe"] { border-radius: 18px; overflow: hidden; }
      .st-key-home-workflow { margin: 1.1rem 0 1.5rem; }
      [class*="st-key-home-step-"] {
        height: 100%; padding: 1rem 1.05rem;
        border: 1px solid #e3e1db; border-radius: 17px;
        background: rgba(255,255,255,.72); box-shadow: 0 6px 22px rgba(28,25,23,.04);
      }
      .home-step-kicker { color: #8a6725; font-size: .7rem; font-weight: 800; letter-spacing: .11em; }
      [class*="st-key-home-step-"] h4 { margin: .45rem 0 .5rem; color: #20211f; }
      [class*="st-key-home-step-"] p { min-height: 2.8rem; color: #515853; font-size: .91rem; }
      [class*="st-key-home-step-"] [data-testid="stPageLink"] a { min-height: 42px; color: #174e5b !important; font-weight: 700; }
      .home-kpi-grid {
        display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem;
      }
      .home-kpi {
        min-width: 0; min-height: 6.1rem; padding: .95rem 1rem;
        border: 1px solid #e3e1db; border-top: 3px solid #c38a2a; border-radius: 16px;
        background: rgba(255,255,255,.9); box-shadow: 0 6px 22px rgba(28,25,23,.045);
      }
      .home-kpi span { display: block; color: #666a66; font-size: .76rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
      .home-kpi strong { display: block; margin-top: .48rem; color: #20211f; font-size: clamp(1.15rem, 2vw, 1.55rem); font-weight: 760; line-height: 1.1; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
      .operator-metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; margin:.65rem 0 1rem; }
      .operator-metric-grid[data-count="3"] { grid-template-columns:repeat(3,minmax(0,1fr)); }
      .operator-metric {
        min-width:0; min-height:5.8rem; padding:.9rem 1rem;
        border:1px solid #e3e1db; border-top:3px solid #c38a2a; border-radius:16px;
        background:rgba(255,255,255,.9); box-shadow:0 6px 22px rgba(28,25,23,.045);
      }
      .operator-metric span { display:block; color:#666a66; font-size:.76rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
      .operator-metric strong { display:block; margin-top:.5rem; color:#20211f; font-size:clamp(1rem,1.8vw,1.4rem); font-weight:760; line-height:1.2; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }
      [class*="st-key-home-card-"] {
        height: 100%; padding: 1.1rem 1.2rem;
        border: 1px solid #e3e1db; border-radius: 18px;
        background: rgba(255,255,255,.82); box-shadow: 0 6px 22px rgba(28,25,23,.045);
      }
      .home-insight-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: .9rem; margin: 1rem 0 1.35rem; }
      .home-insight-card {
        min-width: 0; padding: 1.2rem 1.3rem; border: 1px solid #e3e1db; border-radius: 18px;
        background: rgba(255,255,255,.88); box-shadow: 0 6px 22px rgba(28,25,23,.045);
      }
      .home-insight-kicker { color: #8a6725; font-size: .72rem; font-weight: 800; letter-spacing: .1em; }
      .home-insight-card h3 { margin: .42rem 0 .65rem; color: #20211f; font-size: 1.3rem; line-height: 1.2; }
      .home-insight-value { display: block; color: #1b3c4d; font-size: clamp(1.6rem, 3vw, 2.15rem); line-height: 1.1; font-variant-numeric: tabular-nums; }
      .home-insight-card p { color: #515853; font-size: .94rem; line-height: 1.5; }
      .home-insight-note { margin:.8rem 0 .3rem; font-size:.84rem !important; }
      .home-insight-action {
        min-height: 44px; display: inline-flex; align-items: center; gap: .55rem; margin-top: .45rem;
        color: #174e5b !important; font-weight: 750; text-decoration: none !important;
      }
      .home-insight-action:hover { text-decoration: underline !important; }
      [class*="st-key-home-card-"] { margin: .45rem 0; }
      .home-card-image {
        position: relative; width: 100%; height: clamp(170px, 20vw, 220px); overflow: hidden;
        margin: 0 0 .85rem; border-radius: 12px; background: #1a292d;
      }
      .home-card-image img {
        display: block; width: 100%; height: 100%; object-fit: cover;
        object-position: center 56%; transform: scale(1); transition: transform .55s cubic-bezier(.2,.7,.2,1);
      }
      .home-card-image span {
        position: absolute; right: 9px; bottom: 9px; padding: 5px 8px;
        border: 1px solid rgba(255,255,255,.22); border-radius: 999px;
        background: rgba(17,25,29,.78); color: #fff; font-size: 10px;
        font-weight: 700; letter-spacing: .07em;
      }
      .home-card-image .home-card-kicker { left: 9px; right: auto; bottom: 9px; }
      .home-card-image .home-card-badge { right: 9px; }
      [class*="st-key-home-card-"]:hover .home-card-image img,
      [class*="st-key-home-card-"]:focus-within .home-card-image img { transform: scale(1.065); }
      [class*="st-key-home-card-"]:active .home-card-image img { transform: scale(.985); }
      [class*="st-key-home-card-"] h4 { margin: 0 0 .4rem; color: #20211f; }
      [class*="st-key-home-card-"] p { min-height: 3.2rem; font-size: .94rem; }
      [class*="st-key-home-card-"] [data-testid="stPageLink"] a {
        min-height: 42px; color: #174e5b !important; font-weight: 700;
      }
      .st-key-home-routes-0, .st-key-home-routes-1, .st-key-home-routes-2 {
        padding: clamp(1rem, 2vw, 1.5rem); margin: 1.1rem 0 1.4rem;
        border: 1px solid #e3e1db; border-radius: 22px; background: rgba(255,255,255,.47);
      }
      .home-pattern-row { margin: .75rem 0 1.15rem; }
      .home-pattern-heading { display: flex; justify-content: space-between; gap: .65rem; align-items: baseline; flex-wrap: wrap; }
      .home-pattern-row strong { color: #20211f; }
      .home-pattern-row span { color: #5c625f; font-size: .88rem; }
      .home-pattern-track { height: 8px; margin-top: .42rem; background: #e8e9e5; border-radius: 999px; overflow: hidden; }
      .home-pattern-fill { display: block; height: 100%; border-radius: inherit; }
      .home-pattern-fill-0 { background: #367ba0; }
      .home-pattern-fill-1 { background: #c38420; }
      @supports (animation-timeline: view(block)) {
        .st-key-home-metrics, .st-key-home-insights, .st-key-home-model-stage,
        .st-key-home-routes-0, .st-key-home-routes-1, .st-key-home-routes-2 {
          animation: home-section-reveal linear both;
          animation-timeline: view(block); animation-range: entry 0% entry 30%;
        }
        [class*="st-key-home-card-"] {
          animation: home-card-reveal linear both;
          animation-timeline: view(block); animation-range: entry 0% entry 58%;
        }
        .home-insight-card {
          animation: home-card-reveal linear both;
          animation-timeline: view(block); animation-range: entry 0% entry 58%;
        }
      }
      @keyframes home-section-reveal {
        from { opacity: .58; transform: translateY(22px) scale(.975); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      @keyframes home-card-reveal {
        from { opacity: .75; transform: scale(.965); }
        to { opacity: 1; transform: scale(1); }
      }
      @media (max-width: 760px) {
        .block-container { padding: .75rem .85rem 2rem; }
        .st-key-global-navigation { margin: 0 0 1rem; padding: .25rem 0 .5rem; }
        .st-key-global-navigation [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
        .st-key-global-navigation [data-testid="column"] { min-width: 0; }
        .st-key-global-navigation [data-testid="stPageLink"] a,
        .st-key-global-navigation [data-testid="stPopover"] button { padding: .45rem .65rem; font-size: .88rem; }
        .st-key-home-hero {
          padding: 1.1rem; border-radius: 21px;
          background-image: linear-gradient(180deg, rgba(14,22,27,.54) 0%, rgba(14,22,27,.82) 38%, rgba(14,22,27,.97) 100%),
            url('/app/static/truck-medium.jpg');
          background-position: center 24%;
        }
        .st-key-home-hero h1 { font-size: clamp(2rem, 8vw, 2.8rem); }
        .st-key-home-hero [data-testid="stHorizontalBlock"] {
          display: grid !important; grid-template-columns: minmax(0, 1fr) !important; gap: 1rem !important;
        }
        .st-key-home-hero [data-testid="column"] {
          flex: none !important; width: 100% !important; max-width: 100% !important; min-width: 0 !important;
        }
        .st-key-home-workflow [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .65rem; }
        .st-key-home-workflow [data-testid="column"] { flex: 1 1 100% !important; min-width: 100% !important; }
        [class*="st-key-home-step-"] p { min-height: 0; }
        .home-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
        .operator-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
        .home-insight-grid { grid-template-columns: minmax(0,1fr); }
        .st-key-home-routes-0 [data-testid="stHorizontalBlock"],
        .st-key-home-routes-1 [data-testid="stHorizontalBlock"],
        .st-key-home-routes-2 [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .6rem; }
        .st-key-home-routes-0 [data-testid="column"], .st-key-home-routes-1 [data-testid="column"],
        .st-key-home-routes-2 [data-testid="column"] { flex: 1 1 100% !important; min-width: 100% !important; }
        [class*="st-key-home-card-"] p { min-height: 0; }
        .home-card-image { height: 205px; }
      }
      @media (prefers-reduced-motion: reduce) {
        .st-key-home-metrics, .st-key-home-insights, .st-key-home-model-stage,
        .st-key-home-routes-0, .st-key-home-routes-1, .st-key-home-routes-2 {
          animation: none !important; opacity: 1 !important; transform: none !important;
        }
        .home-insight-card { animation: none !important; opacity: 1 !important; transform: none !important; }
        [class*="st-key-home-card-"] { animation: none !important; opacity: 1 !important; transform: none !important; }
        .st-key-home-hero [data-testid="stPageLink"] a { transition: none !important; }
        .home-card-image img { transition: none !important; transform: none !important; }
      }
      /* Keep frequent controls calm; reserve movement for the scroll story and 3D view. */
      .stButton > button {
        min-height: 42px;
        box-shadow: none !important;
        transition: background-color .16s ease, border-color .16s ease, color .16s ease !important;
      }
      .stButton > button::before { display: none !important; }
      .stButton > button:hover {
        transform: none !important;
        box-shadow: 0 3px 10px rgba(28,25,23,.1) !important;
      }
      .stButton > button[kind="primary"],
      .stButton > button[kind="primary"]:hover {
        color: #1c1917 !important;
        border-color: #bd8426 !important;
        background: #edb84b !important;
        box-shadow: 0 3px 10px rgba(150,101,19,.18) !important;
      }
      [data-testid="stMetric"]:hover { transform: none !important; }
      [data-testid="stMetric"]::before { background: #c38a2a !important; }
      [data-testid="stCaptionContainer"] { font-size: 10pt !important; letter-spacing: .045em !important; }
      @media (max-width: 760px) {
        .stButton > button { min-height: 44px; }
        [data-testid="stCaptionContainer"] { font-size: 11pt !important; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.get("dark_mode", False):
    st.markdown(
        """
        <style>
          .stApp { background: #11191e !important; color: #edf1f2 !important; }
          .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label,
          .stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"] {
            color: #edf1f2 !important;
          }
          .stApp [data-testid="stCaptionContainer"] { color: #bac5ca !important; }
          .st-key-global-navigation { background: rgba(17,25,30,.92) !important; border-color: rgba(255,255,255,.13) !important; }
          .st-key-global-navigation [data-testid="stPageLink"] a,
          .st-key-global-navigation [data-testid="stPopover"] button { color: #edf1f2 !important; }
          .st-key-global-navigation [data-testid="stPageLink"] a:hover,
          .st-key-global-navigation [data-testid="stPopover"] button:hover { background: rgba(255,255,255,.1) !important; }
          .home-kpi, .operator-metric, .home-insight-card, [class*="st-key-home-card-"],
          [class*="st-key-home-step-"], .st-key-home-routes-0, .st-key-home-routes-1, .st-key-home-routes-2 {
            background: rgba(31,42,49,.94) !important; border-color: rgba(219,231,236,.14) !important;
            box-shadow: 0 8px 26px rgba(0,0,0,.2) !important;
          }
          .home-kpi span, .operator-metric span, .home-insight-card p,
          [class*="st-key-home-step-"] p, [class*="st-key-home-card-"] p,
          .home-pattern-row span { color: #c3cdd1 !important; }
          .home-kpi strong, .operator-metric strong, .home-insight-card h3,
          .home-pattern-row strong, [class*="st-key-home-card-"] h4,
          [class*="st-key-home-step-"] h4 { color: #f4f7f8 !important; }
          .home-insight-value { color: #9fd5ef !important; }
          .home-insight-action, [class*="st-key-home-card-"] [data-testid="stPageLink"] a,
          [class*="st-key-home-step-"] [data-testid="stPageLink"] a { color: #a8d8df !important; }
          .home-pattern-track { background: #38474e !important; }
          .stApp [data-testid="stTextInput"] input, .stApp [data-testid="stNumberInput"] input,
          .stApp [data-testid="stSelectbox"] [role="combobox"], .stApp [data-testid="stDateInput"] input {
            color: #edf1f2 !important; background: #1d292f !important; border-color: #48565c !important;
          }
          .stApp [data-testid="stDataFrame"], .stApp [data-testid="stTable"] {
            background: #fff !important; border-radius: 12px;
          }
          .stApp [data-testid="stVegaLiteChart"], .stApp [data-testid="stPyplotGlobalUseContainer"] {
            background: rgba(255,255,255,.96) !important; border-radius: 12px; padding: .25rem;
          }
          .stApp [data-testid="stExpander"] { background: #1b272d !important; border-color: #39474e !important; }
          .stApp [data-testid="stAlert"] { background: #1b272d !important; color: #edf1f2 !important; }
          .home-step-kicker, .home-insight-kicker { color: #e7bc65 !important; }
          .st-key-home-hero { color: #f4f6f7 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def placeholder_page(
    section: str,
    title: str,
    description: str,
    primary_action: str,
    phase: str,
):
    """Create a consistent page shell while its analysis is being connected."""

    def render() -> None:
        st.caption(section.upper())
        st.title(title)
        st.write(description)

        # 3D Hero card
        st.markdown(f"""
        <div class="hero-3d">
            <div class="orb-container"><div class="orb"></div></div>
            <p style="font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin:0 0 .8rem;">YOUR NEXT ACTION</p>
            <p style="font-size:1.1rem;font-weight:600;color:var(--ink);margin:0 0 .5rem;">{primary_action}</p>
            <p style="font-size:.88rem;color:var(--muted);margin:0;">Ready for the next build phase</p>
        </div>
        """, unsafe_allow_html=True)

        if phase == "prediction":
            st.warning(
                "Pre-departure estimates are not ready yet. The current training "
                "template has no planned-distance or cargo values, so this page "
                "will wait for populated pre-trip data and a matching model."
            )
        else:
            st.info(
                "This destination is part of the app. Its data and investigation "
                "controls will be connected in the next build phases."
            )
        related = {
            "Anomaly Monitoring": "Data Quality",
            "Vehicle Explorer": "Fleet Overview",
            "Track Explorer": "Data Quality",
            "Model Insights": "Cluster Analysis",
            "Tour Duration": "Data Quality",
        }
        next_page = get_page_link(related.get(title, ""))
        if next_page is not None:
            st.page_link(next_page, label=f"Open {related[title]}", icon=":material/arrow_forward:")

    return render


PAGES = {
    "Start here": [
        st.Page(
            render_home,
            title="Home",
            icon="🏠",
            default=True,
        ),
    ],
    "Overview": [
        st.Page(
            render_overview,
            title="Fleet Overview",
            icon="🚚",
            url_path="fleet-overview",
        ),
        st.Page(
            render_vehicle_simulator,
            title="3D Speed Simulator",
            icon="⚡",
            url_path="speed-simulator",
        ),
        st.Page(
            render_project_overview,
            title="Project & Dataset",
            icon="ℹ️",
            url_path="project-dataset",
        ),
    ],
    "Investigate": [
        st.Page(
            render_anomaly_monitoring,
            title="Anomaly Monitoring",
            icon="⚠️",
            url_path="anomaly-monitoring",
        ),
        st.Page(
            render_vehicle_explorer,
            title="Vehicle Explorer",
            icon="🚛",
            url_path="vehicle-explorer",
        ),
        st.Page(
            render_track_explorer,
            title="Track Explorer",
            icon="📍",
            url_path="track-explorer",
        ),
    ],
    "Plan": [
        st.Page(
            render_tour_duration,
            title="Tour Duration Prediction",
            icon="⏱️",
            url_path="tour-duration",
        ),
    ],
    "Understand": [
        st.Page(
            render_cluster_analysis,
            title="Cluster Analysis",
            icon="📊",
            url_path="cluster-analysis",
        ),
        st.Page(
            render_quality,
            title="Data Quality",
            icon="🛡️",
            url_path="data-quality",
        ),
        st.Page(
            render_distributions,
            title="Data Distribution",
            icon="📊",
            url_path="data-distribution",
        ),
        st.Page(
            render_methodology,
            title="Model Insights",
            icon="🧠",
            url_path="model-insights",
        ),
    ],
    "Read & share": [
        st.Page(
            render_project_walkthrough,
            title="Project Walkthrough",
            icon="📖",
            url_path="project-walkthrough",
        ),
    ],
}


def render_global_navigation() -> None:
    """Show a compact global route menu without consuming a sidebar."""
    with st.container(key="global-navigation"):
        home, explore, appearance = st.columns([1.1, 0.9, 0.55], gap="small", vertical_alignment="center")
        home.page_link(get_page_link("Home"), label="DT-CARGO · Home", icon=":material/local_shipping:")
        with explore:
            with st.popover("Explore all pages", icon=":material/grid_view:", use_container_width=True):
                for section, section_pages in PAGES.items():
                    st.caption(section)
                    for destination in section_pages:
                        if destination.title != "Home":
                            st.page_link(destination, label=destination.title)
        with appearance:
            st.toggle("Dark", key="dark_mode", help="Switch between light and dark appearance.")


register_page_links(PAGES)
page = st.navigation(PAGES, position="hidden")
render_global_navigation()
page.run()
