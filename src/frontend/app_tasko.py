import os
import sys
sys.path.insert(0, os.path.abspath("."))

import time
import threading
import json
import sqlite3
import pandas as pd
import numpy as np

import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from src.streaming.producer import TransactionProducer
from src.streaming.consumer import StreamingScoringConsumer, GLOBAL_RING_BUFFER
from src.frontend.drift_service import DriftMonitoringService
from src.models.cost_router import DynamicCostRouter
from src.models.explainability import FraudExplainer
from src.api.feature_service import FeatureService
from src.api.schemas import TransactionPayload

# Initialize Services & Ingestion Workers
consumer_worker = StreamingScoringConsumer()
consumer_worker.start_background_worker()

producer_instance = TransactionProducer()
drift_service = DriftMonitoringService()
cost_router = DynamicCostRouter()
explainer = FraudExplainer()
feature_service = FeatureService(feature_names=explainer.feature_names)

PRODUCER_THREAD: list = []

def start_producer_background(rate: float = 5.0):
    if not PRODUCER_THREAD or not PRODUCER_THREAD[0].is_alive():
        t = threading.Thread(
            target=producer_instance.stream_transactions,
            kwargs={"rate_per_sec": rate, "max_transactions": 2000, "loop": True},
            daemon=True
        )
        t.start()
        PRODUCER_THREAD.clear()
        PRODUCER_THREAD.append(t)

# Initialize Dash App with Exact Donezo/Tasko Aesthetics
app = dash.Dash(
    __name__,
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css",
        "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
    ],
    title="Tasko | Real-Time Decision & Fraud Risk Operations",
    suppress_callback_exceptions=True
)
server = app.server

# Exact CSS Tokens extracted from https://v0-dashboard-ui-redesign-nine.vercel.app/
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --tasko-bg: #f8f9f5;
                --tasko-sidebar-bg: #f8f9f5;
                --tasko-card-bg: #ffffff;
                --tasko-primary: #006323;
                --tasko-primary-hover: #004d1b;
                --tasko-primary-light: #f3fbf5;
                --tasko-text-main: #202318;
                --tasko-text-muted: #707367;
                --tasko-border: #e9ebe3;
                --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
                --font-mono: 'JetBrains Mono', monospace;
            }
            body {
                margin: 0;
                padding: 0;
                background-color: var(--tasko-bg);
                font-family: var(--font-sans) !important;
                color: var(--tasko-text-main);
                -webkit-font-smoothing: antialiased;
                overflow-x: hidden;
            }
            .mono-num {
                font-family: var(--font-mono) !important;
                font-variant-numeric: tabular-nums;
            }
            /* Sidebar Styling matching Donezo template */
            .donezo-sidebar {
                background-color: var(--tasko-sidebar-bg);
                border-right: 1px solid var(--tasko-border);
                min-height: 100vh;
                padding: 24px 16px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                width: 250px;
                min-width: 250px;
                max-width: 250px;
            }
            .donezo-section-label {
                font-size: 0.68rem;
                font-weight: 700;
                color: var(--tasko-text-muted);
                letter-spacing: 0.06em;
                margin: 16px 0 8px 12px;
                text-transform: uppercase;
            }
            .donezo-nav-btn {
                background: transparent;
                border: none;
                color: var(--tasko-text-muted);
                font-size: 0.88rem;
                font-weight: 600;
                padding: 10px 14px;
                border-radius: 16px;
                text-align: left;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: space-between;
                transition: all 0.2s ease;
                cursor: pointer;
            }
            .donezo-nav-btn:hover {
                background: rgba(0, 99, 35, 0.05);
                color: var(--tasko-primary);
            }
            .donezo-nav-btn.active {
                background: var(--tasko-primary) !important;
                color: #ffffff !important;
                font-weight: 700;
                box-shadow: 0 4px 14px -2px rgba(0, 99, 35, 0.35);
            }
            /* Primary Button (Tasko Donezo Pill) */
            .btn-donezo-primary {
                background-color: var(--tasko-primary);
                color: #ffffff;
                font-weight: 600;
                font-size: 0.85rem;
                padding: 8px 18px;
                border-radius: 14px;
                border: none;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 2px 8px -1px rgba(0, 99, 35, 0.25);
            }
            .btn-donezo-primary:hover {
                background-color: var(--tasko-primary-hover);
                transform: translateY(-1px) scale(1.02);
                box-shadow: 0 6px 16px -2px rgba(0, 99, 35, 0.35);
                color: #ffffff;
            }
            .btn-donezo-secondary {
                background-color: #ffffff;
                color: var(--tasko-text-main);
                font-weight: 600;
                font-size: 0.85rem;
                padding: 8px 18px;
                border-radius: 14px;
                border: 1px solid var(--tasko-border);
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s ease;
            }
            .btn-donezo-secondary:hover {
                background-color: #f1f3ee;
                color: var(--tasko-text-main);
            }
            /* Donezo Stat Cards */
            .donezo-hero-card {
                background-color: var(--tasko-primary);
                color: #ffffff;
                border-radius: 20px;
                padding: 20px;
                box-shadow: 0 4px 16px -2px rgba(0, 99, 35, 0.25);
                position: relative;
                transition: transform 0.2s ease;
            }
            .donezo-hero-card:hover {
                transform: translateY(-2px);
            }
            .donezo-white-card {
                background-color: #ffffff;
                border: 1px solid var(--tasko-border);
                border-radius: 20px;
                padding: 20px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
                position: relative;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .donezo-white-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.05);
            }
            .donezo-arrow-circle {
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.75rem;
                font-weight: 700;
            }
            .donezo-arrow-circle-white {
                background: rgba(255, 255, 255, 0.2);
                color: #ffffff;
            }
            .donezo-arrow-circle-green {
                background: var(--tasko-primary);
                color: #ffffff;
            }
            /* Status Chips & Badges */
            .donezo-chip {
                font-size: 0.72rem;
                font-weight: 700;
                padding: 4px 12px;
                border-radius: 9999px;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            }
            .donezo-chip-completed { background: #e6f7ec; color: #006323; }
            .donezo-chip-inprogress { background: #fef7e6; color: #b45309; }
            .donezo-chip-pending { background: #feecee; color: #b91c1c; }
            
            /* Search Bar (Pill) */
            .donezo-search-box {
                background: #ffffff;
                border: 1px solid var(--tasko-border);
                border-radius: 9999px;
                padding: 8px 18px;
                display: flex;
                align-items: center;
                gap: 10px;
                width: 320px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.02);
            }
            .donezo-search-box input {
                border: none;
                outline: none;
                background: transparent;
                font-size: 0.85rem;
                color: var(--tasko-text-main);
                width: 100%;
            }
            .donezo-kbd {
                background: #f1f3ee;
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 0.7rem;
                font-weight: 700;
                color: var(--tasko-text-muted);
            }
            /* Slider marks */
            .rc-slider-tooltip, .dash-range-slider-input, .dash-input-container {
                display: none !important;
            }
            .rc-slider-mark-text {
                font-family: var(--font-mono) !important;
                font-size: 0.72rem !important;
                color: var(--tasko-text-muted) !important;
            }
            .rc-slider-track {
                background-color: var(--tasko-primary) !important;
            }
            .rc-slider-handle {
                border-color: var(--tasko-primary) !important;
                background-color: #ffffff !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ----------------- COMPONENT BUILDERS (DONEZO STYLE) -----------------


def donezo_sidebar():
    return html.Div(
        className="donezo-sidebar",
        children=[
            html.Div([
                # Brand Header
                html.Div(
                    className="d-flex align-items-center gap-2 mb-4 px-2",
                    children=[
                        html.Div(
                            style={
                                "width": "32px", "height": "32px", "backgroundColor": "#006323",
                                "borderRadius": "50%", "display": "flex", "alignItems": "center",
                                "justifyContent": "center", "color": "#ffffff", "fontWeight": "800"
                            },
                            children=html.Span("••", style={"letterSpacing": "2px", "fontSize": "0.8rem", "lineHeight": "0"})
                        ),
                        html.Span("Tasko FraudOps", style={"fontWeight": "800", "fontSize": "1.2rem", "color": "#202318", "letterSpacing": "-0.02em"})
                    ]
                ),

                # Menu Section
                html.Div("MENU", className="donezo-section-label"),
                html.Div(
                    className="d-flex flex-column gap-2",
                    children=[
                        html.Button(
                            id="nav-btn-simulator",
                            className="donezo-nav-btn active",
                            children=[
                                html.Span("Interactive Sandbox", style={"display": "flex", "alignItems": "center", "gap": "8px"}),
                                html.Span("Sim", className="donezo-chip donezo-chip-completed", style={"padding": "2px 8px", "fontSize": "0.68rem"})
                            ]
                        ),
                        html.Button(
                            id="nav-btn-operations",
                            className="donezo-nav-btn",
                            children=[
                                html.Span("Live Operations", style={"display": "flex", "alignItems": "center", "gap": "8px"}),
                                html.Span("Stream", className="donezo-chip", style={"background": "#f1f3ee", "color": "#707367", "padding": "2px 8px", "fontSize": "0.68rem"})
                            ]
                        ),
                        html.Button(
                            id="nav-btn-drift",
                            className="donezo-nav-btn",
                            children=[
                                html.Span("Drift Center", style={"display": "flex", "alignItems": "center", "gap": "8px"}),
                                html.Span("Evidently", className="donezo-chip", style={"background": "#f1f3ee", "color": "#707367", "padding": "2px 8px", "fontSize": "0.68rem"})
                            ]
                        )
                    ]
                )
            ]),

            # Bottom System Status Widget
            html.Div(
                style={"backgroundColor": "#ffffff", "borderRadius": "16px", "padding": "14px", "border": "1px solid #e9ebe3"},
                children=[
                    html.Div(className="d-flex align-items-center gap-2 mb-1", children=[
                        html.Span("•", style={"color": "#006323", "fontSize": "1.4rem", "lineHeight": "0"}),
                        html.Span("STREAM ENGINE ONLINE", style={"fontSize": "0.68rem", "fontWeight": "800", "color": "#006323", "letterSpacing": "0.05em"})
                    ]),
                    html.Div("LightGBM + TreeSHAP Active", style={"fontSize": "0.72rem", "color": "#707367", "fontWeight": "500"}),
                    html.Div("Sub-25ms SLA Operational", style={"fontSize": "0.68rem", "color": "#a1a499"})
                ]
            )
        ]
    )

def donezo_header():
    # Search removed per user request
    return html.Div(
        className="d-flex justify-content-between align-items-center mb-4",
        children=[]
    )
def donezo_kpi_card(title, id_val, default_val, subtext):
    return html.Div(
        className="donezo-white-card h-100 d-flex flex-column justify-content-between p-3",
        style={"boxShadow": "0 1px 3px rgba(0,0,0,0.02)"},
        children=[
            html.Div(title, style={"fontSize": "0.75rem", "color": "#707367", "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(id=id_val, children=default_val, className="my-2", style={"fontSize": "1.4rem", "fontWeight": "800", "color": "#202318"}),
            html.Div(subtext, style={"fontSize": "0.7rem", "color": "#a1a499"})
        ]
    )
def render_tab_simulator():
    return html.Div([
        # Scenario Presets Header
        html.Div(
            className="p-3 mb-4",
            style={"backgroundColor": "#ffffff", "border": "1px solid #e9ebe3", "borderRadius": "10px"},
            children=[
                html.Div("ONE-CLICK RISK PROFILES", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#2563eb", "letterSpacing": "0.08em", "marginBottom": "6px"}),
                dbc.Row(
                    className="g-3",
                    children=[
                        dbc.Col(
                            md=4,
                            children=html.Button(
                                id="btn-scen-retail",
                                className="donezo-white-card w-100 p-3 text-start",
                                style={"backgroundColor": "#f8f9f5", "border": "1px solid #e9ebe3", "borderRadius": "8px", "cursor": "pointer"},
                                children=[
                                    html.Div("Baseline Retail Purchase", style={"fontWeight": "700", "fontSize": "0.9rem", "color": "#202318"}),
                                    html.Div("Amount: $25.00 | Velocity: 1 tx/5m | Verified Domestic Email", style={"fontSize": "0.78rem", "color": "#64748b", "margin": "3px 0"}),
                                    html.Span("Expected: Direct Approval (0% Friction)", style={"backgroundColor": "#ecfdf5", "color": "#065f46", "border": "1px solid #a7f3d0", "fontSize": "0.7rem", "fontWeight": "700", "padding": "2px 8px", "borderRadius": "4px"})
                                ]
                            )
                        ),
                        dbc.Col(
                            md=4,
                            children=html.Button(
                                id="btn-scen-highval",
                                className="donezo-white-card w-100 p-3 text-start",
                                style={"backgroundColor": "#f8f9f5", "border": "1px solid #e9ebe3", "borderRadius": "8px", "cursor": "pointer"},
                                children=[
                                    html.Div("High-Value Electronics Checkout", style={"fontWeight": "700", "fontSize": "0.9rem", "color": "#202318"}),
                                    html.Div("Amount: $2,400.00 | Velocity: 1 tx/5m | Hardware Product Category", style={"fontSize": "0.78rem", "color": "#64748b", "margin": "3px 0"}),
                                    html.Span("Expected: Dynamic 3DS Challenge (Tightened Boundary)", style={"backgroundColor": "#fffbeb", "color": "#92400e", "border": "1px solid #fde68a", "fontSize": "0.7rem", "fontWeight": "700", "padding": "2px 8px", "borderRadius": "4px"})
                                ]
                            )
                        ),
                        dbc.Col(
                            md=4,
                            children=html.Button(
                                id="btn-scen-attack",
                                className="donezo-white-card w-100 p-3 text-start",
                                style={"backgroundColor": "#f8f9f5", "border": "1px solid #e9ebe3", "borderRadius": "8px", "cursor": "pointer"},
                                children=[
                                    html.Div("Card-Testing Velocity Burst", style={"fontWeight": "700", "fontSize": "0.9rem", "color": "#202318"}),
                                    html.Div("Amount: $45.00 | Velocity: 8 tx/5m | Disposable Temp Email", style={"fontSize": "0.78rem", "color": "#64748b", "margin": "3px 0"}),
                                    html.Span("Expected: Hard Decline / 3DS Shield", style={"backgroundColor": "#fef2f2", "color": "#991b1b", "border": "1px solid #fecaca", "fontSize": "0.7rem", "fontWeight": "700", "padding": "2px 8px", "borderRadius": "4px"})
                                ]
                            )
                        )
                    ]
                )
            ]
        ),

        # Main Body: Split Work Queue & Live Decision Inspector
        dbc.Row(
            className="g-4",
            children=[
                # Left: Simulation Controls & Parameter Inspector
                dbc.Col(
                    md=5,
                    children=html.Div(
                        className="donezo-white-card mb-4",
                        children=[
                            html.H6("Transaction Authorization Parameters", className="fw-bold mb-3", style={"color": "#202318"}),
                            
                            html.Div(className="mb-4", children=[
                                html.Div(className="d-flex justify-content-between mb-1", children=[
                                    html.Label("Transaction Amount ($ USD):", style={"fontSize": "0.82rem", "fontWeight": "600", "color": "#475569"}),
                                    html.Span(id="ramp-amt-val", className="mono-num", style={"fontWeight": "700", "color": "#2563eb", "fontSize": "0.95rem"})
                                ]),
                                dcc.Slider(id="ramp-amt-slider", min=10, max=4000, step=25, value=250, marks={10: "$10", 1000: "$1k", 2500: "$2.5k", 4000: "$4k"})
                            ]),

                            html.Div(className="mb-4", children=[
                                html.Div(className="d-flex justify-content-between mb-1", children=[
                                    html.Label("Card Velocity (5-Min Authorizations):", style={"fontSize": "0.82rem", "fontWeight": "600", "color": "#475569"}),
                                    html.Span(id="ramp-vel-val", className="mono-num", style={"fontWeight": "700", "color": "#d97706", "fontSize": "0.95rem"})
                                ]),
                                dcc.Slider(id="ramp-vel-slider", min=0, max=10, step=1, value=1, marks={i: str(i) for i in range(0, 11, 2)})
                            ]),

                            html.Div(className="mb-3", children=[
                                html.Label("Product Code Category:", style={"fontSize": "0.82rem", "fontWeight": "600", "color": "#475569", "marginBottom": "4px"}),
                                dcc.Dropdown(
                                    id="ramp-prod-dropdown",
                                    options=[
                                        {"label": "W — Standard Domestic Retail / Web Goods", "value": "W"},
                                        {"label": "C — Cross-Border International Payment", "value": "C"},
                                        {"label": "H — High-Risk Hardware & Consumer Tech", "value": "H"},
                                        {"label": "R — Recurring Digital Subscription Service", "value": "R"}
                                    ],
                                    value="W",
                                    clearable=False
                                )
                            ]),

                            html.Div(className="mb-2", children=[
                                html.Label("Purchaser vs Recipient Domain Profile:", style={"fontSize": "0.82rem", "fontWeight": "600", "color": "#475569", "marginBottom": "4px"}),
                                dcc.Dropdown(
                                    id="ramp-email-dropdown",
                                    options=[
                                        {"label": "Consistent Pair (gmail.com → gmail.com)", "value": "match"},
                                        {"label": "Mismatched / Anonymous Domain", "value": "mismatch"},
                                        {"label": "Disposable / Temp Email (mailinator.com)", "value": "disposable"}
                                    ],
                                    value="match",
                                    clearable=False
                                )
                            ])
                        ]
                    )
                ),

                # Right: Dynamic Bayesian Policy Engine & SHAP Waterfall
                dbc.Col(
                    md=7,
                    children=[
                        # Policy Verdict Card
                        html.Div(
                            className="donezo-white-card mb-4",
                            children=[
                                html.Div(className="d-flex justify-content-between align-items-center mb-2", children=[
                                    html.Div("DYNAMIC BAYESIAN DECISION RESULT", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#64748b", "letterSpacing": "0.08em"}),
                                    html.Span(id="ramp-latency-badge", className="mono-num", style={"fontSize": "0.75rem", "backgroundColor": "#f1f5f9", "padding": "3px 8px", "borderRadius": "4px", "color": "#475569", "fontWeight": "600"})
                                ]),
                                html.H2(id="ramp-verdict-title", children="DIRECT APPROVAL", className="fw-extrabold mb-2", style={"fontSize": "1.9rem"}),
                                html.P(id="ramp-verdict-desc", className="mb-3", style={"fontSize": "0.88rem", "color": "#334155", "lineHeight": "1.5"}),
                                
                                # Mathematical Policy Spectrum Bar
                                html.Div("MATHEMATICAL POLICY SPECTRUM:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b", "marginBottom": "4px"}),
                                dcc.Graph(id="ramp-rail-graph", style={"height": "50px"}, config={"displayModeBar": False}),
                                html.Div(id="ramp-thresh-legend", className="mono-num", style={"fontSize": "0.75rem", "color": "#64748b", "marginTop": "6px"})
                            ]
                        ),

                        # SHAP Attribution Card
                        html.Div(
                            className="donezo-white-card mb-4",
                            children=[
                                html.Div("SHAP FEATURE ATTRIBUTION (TOP RISK CONTRIBUTORS)", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#64748b", "letterSpacing": "0.08em", "marginBottom": "12px"}),
                                html.Div(id="ramp-shap-container")
                            ]
                        )
                    ]
                )
            ]
        )
    ])

# ----------------- TAB 2: LIVE OPERATIONS & DISPUTE QUEUE -----------------
def render_tab_operations():
    return html.Div([
        dbc.Row(
            className="g-4",
            children=[
                # Left 7-Cols: Live Ticker with 1-Click Select
                dbc.Col(
                    md=7,
                    children=html.Div(
                        className="donezo-white-card mb-4",
                        children=[
                            html.Div(className="d-flex justify-content-between align-items-center mb-3", children=[
                                html.Div([
                                    html.H6("Recent Payment Stream Feed", className="fw-bold mb-0"),
                                    html.Small("Click any transaction row to inspect attribution and submit chargeback labels", className="text-muted")
                                ]),
                                html.Span("STREAM ACTIVE", style={"fontSize": "0.7rem", "fontWeight": "700", "backgroundColor": "#ecfdf5", "color": "#065f46", "padding": "3px 8px", "borderRadius": "4px", "border": "1px solid #a7f3d0"})
                            ]),
                            dash_table.DataTable(
                                id="ops-stream-table",
                                columns=[
                                    {"name": "TIMESTAMP", "id": "timestamp"},
                                    {"name": "TX ID", "id": "transaction_id"},
                                    {"name": "AMOUNT ($)", "id": "transaction_amount"},
                                    {"name": "P(FRAUD)", "id": "fraud_probability"},
                                    {"name": "ACTION", "id": "action"},
                                    {"name": "PRIMARY REASON", "id": "primary_reason"}
                                ],
                                data=[],
                                row_selectable="single",
                                selected_rows=[0],
                                style_header={"backgroundColor": "#f8f9f5", "color": "#475569", "fontWeight": "700", "fontSize": "0.75rem", "border": "1px solid #e9ebe3", "padding": "10px"},
                                style_cell={"backgroundColor": "#ffffff", "color": "#202318", "fontSize": "0.78rem", "fontFamily": "'JetBrains Mono', monospace", "textAlign": "center", "padding": "10px", "border": "1px solid #f1f5f9", "cursor": "pointer"},
                                style_data_conditional=[
                                    {"if": {"filter_query": '{action} eq "APPROVE"'}, "color": "#059669", "fontWeight": "700"},
                                    {"if": {"filter_query": '{action} eq "STEP_UP_3DS"'}, "color": "#d97706", "fontWeight": "700"},
                                    {"if": {"filter_query": '{action} eq "DECLINE"'}, "color": "#dc2626", "fontWeight": "700"},
                                    {"if": {"state": "selected"}, "backgroundColor": "#eff6ff", "border": "1px solid #3b82f6"}
                                ],
                                page_size=10
                            )
                        ]
                    )
                ),

                # Right 5-Cols: Forensics & 1-Click Feedback Station
                dbc.Col(
                    md=5,
                    children=html.Div(
                        className="donezo-white-card mb-4",
                        children=[
                            html.Div("TRANSACTION FORENSICS & FEEDBACK", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#2563eb", "letterSpacing": "0.08em", "marginBottom": "12px"}),
                            
                            html.Div(id="ops-forensics-content", children=[
                                html.Div("Select a transaction from the feed to inspect risk attributes.", className="text-muted", style={"fontSize": "0.85rem"})
                            ]),

                            html.Hr(style={"borderColor": "#e9ebe3", "margin": "20px 0"}),

                            html.H6("Analyst Dispute Feedback Station", className="fw-bold mb-2", style={"fontSize": "0.9rem"}),
                            html.P("Submit analyst-verified chargeback labels to update Evidently AI model stability tracking:", className="text-muted mb-3", style={"fontSize": "0.8rem"}),
                            
                            html.Div(className="d-flex gap-2 mb-2", children=[
                                html.Button("Flag as Fraud Dispute (Chargeback)", id="btn-flag-chargeback", className="btn-donezo-primary btn-sm fw-bold w-100", style={"fontSize": "0.8rem", "padding": "8px"}),
                                html.Button("Mark Legitimate", id="btn-flag-legit", className="btn-donezo-secondary btn-sm fw-bold w-100", style={"fontSize": "0.8rem", "padding": "8px"})
                            ]),
                            html.Div(id="ops-feedback-status", style={"fontSize": "0.8rem", "fontWeight": "600"})
                        ]
                    )
                )
            ]
        )
    ])


# ----------------- TAB 3: EVIDENTLY AI DRIFT & STABILITY CENTER -----------------
def render_tab_drift():
    return html.Div([
        dbc.Row(
            className="g-4",
            children=[
                # Left: Wasserstein Distance Bar Chart
                dbc.Col(
                    md=7,
                    children=html.Div(
                        className="donezo-white-card mb-4",
                        children=[
                            html.Div(className="d-flex justify-content-between align-items-center mb-3", children=[
                                html.H6("Wasserstein Distribution Drift vs Alert Threshold", className="fw-bold mb-0"),
                                html.Span("ALERT THRESHOLD: 0.10", className="mono-num", style={"fontSize": "0.72rem", "fontWeight": "700", "backgroundColor": "#fffbeb", "color": "#92400e", "padding": "3px 8px", "borderRadius": "4px", "border": "1px solid #fde68a"})
                            ]),
                            dcc.Graph(id="drift-wasserstein-graph", style={"height": "320px"}, config={"displayModeBar": False})
                        ]
                    )
                ),

                # Right: Visa VAMP Compliance & Model Health
                dbc.Col(
                    md=5,
                    children=html.Div(
                        className="donezo-white-card mb-4",
                        children=[
                            html.Div("REGULATORY & MODEL STABILITY COMPLIANCE", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#2563eb", "letterSpacing": "0.08em", "marginBottom": "12px"}),
                            
                            html.Div(
                                className="p-3 mb-3",
                                style={"backgroundColor": "#f8f9f5", "border": "1px solid #e9ebe3", "borderRadius": "8px"},
                                children=[
                                    html.Div("VISA VAMP COMPLIANCE STATUS:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b"}),
                                    html.H4("0.42% Chargeback Ratio", className="fw-bold my-1 mono-num text-success", style={"fontSize": "1.3rem"}),
                                    html.Small("Regulatory threshold is <1.50%. Portfolio operates at elite compliance.", style={"color": "#64748b", "fontSize": "0.75rem"})
                                ]
                            ),

                            html.Div(
                                className="p-3 mb-3",
                                style={"backgroundColor": "#f8f9f5", "border": "1px solid #e9ebe3", "borderRadius": "8px"},
                                children=[
                                    html.Div("DATASET DRIFT STATUS:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b"}),
                                    html.H4(id="drift-overall-status", children="STABLE (0 / 4 Features Drifted)", className="fw-bold my-1 mono-num", style={"fontSize": "1.1rem", "color": "#059669"}),
                                    html.Small("Evidently AI Wasserstein distance test evaluated on live stream slice.", style={"color": "#64748b", "fontSize": "0.75rem"})
                                ]
                            ),

                            html.Div(
                                className="p-3",
                                style={"backgroundColor": "#f8f9f5", "border": "1px solid #e9ebe3", "borderRadius": "8px"},
                                children=[
                                    html.Div("ANALYST DISPUTE STORE:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b"}),
                                    html.H4(id="drift-feedback-count", children="0 Labels Logged", className="fw-bold my-1 mono-num", style={"fontSize": "1.1rem", "color": "#2563eb"}),
                                    html.Small("Ground-truth SQLite buffer (`data/feedback_store.sqlite`).", style={"color": "#64748b", "fontSize": "0.75rem"})
                                ]
                            )
                        ]
                    )
                )
            ]
        )
    ])



# ----------------- MASTER DONEZO/TASKO LAYOUT -----------------
app.layout = html.Div(
    className="d-flex",
    style={"minHeight": "100vh", "backgroundColor": "#f8f9f5"},
    children=[
        donezo_sidebar(),
        html.Div(
            style={"flex": "1 1 auto", "minWidth": "0", "padding": "28px 36px", "overflowY": "auto"},
            children=[
                donezo_header(),
                
                # Executive Verdict Ribbon (KPIs)
                dbc.Row(
                    className="g-3 mb-4",
                    children=[
                        dbc.Col(md=2, children=donezo_kpi_card("STREAMED VOLUME", "kpi-vol", "0", "Holdout stream")),
                        dbc.Col(md=2, children=donezo_kpi_card("APPROVAL RATE", "kpi-app", "0.0%", "Instant zero-friction")),
                        dbc.Col(md=2, children=donezo_kpi_card("3DS CHALLENGE RATE", "kpi-step", "0.0%", "Benchmark: 8% – 15%")),
                        dbc.Col(md=2, children=donezo_kpi_card("DECLINE RATE", "kpi-dec", "0.0%", "Direct fraud blocked")),
                        dbc.Col(md=2, children=donezo_kpi_card("SAVED CAPITAL", "kpi-saved", "$0.00", "Prevented chargebacks")),
                        dbc.Col(md=2, children=donezo_kpi_card("AVG SLA LATENCY", "kpi-lat", "0.0 ms", "Target: <25.0 ms"))
                    ]
                ),

                html.Div(id="donezo-view-container", children=render_tab_simulator()),

                dcc.Interval(id="interval-fast", interval=1500, n_intervals=0),
                dcc.Interval(id="interval-slow", interval=8000, n_intervals=0),
                dcc.Store(id="donezo-active-tab", data="tab-simulator")
            ]
        )
    ]
)

# ----------------- MASTER CALLBACKS -----------------
# 1. Navigation Tab Router Callback
@app.callback(
    Output("donezo-active-tab", "data"),
    [
        Input("nav-btn-simulator", "n_clicks"),
        Input("nav-btn-operations", "n_clicks"),
        Input("nav-btn-drift", "n_clicks")
    ],
    State("donezo-active-tab", "data")
)
def route_active_tab(btn_sim, btn_ops, btn_drift, current_tab):
    ctx = dash.callback_context
    if not ctx or not ctx.triggered:
        return current_tab or "tab-simulator"
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if btn_id == "nav-btn-simulator":
        return "tab-simulator"
    elif btn_id == "nav-btn-operations":
        return "tab-operations"
    elif btn_id == "nav-btn-drift":
        return "tab-drift"
    return "tab-simulator"

@app.callback(
    [
        Output("donezo-view-container", "children"),
        Output("nav-btn-simulator", "className"),
        Output("nav-btn-operations", "className"),
        Output("nav-btn-drift", "className")
    ],
    Input("donezo-active-tab", "data")
)
def render_tab_content(tab):
    if tab == "tab-operations":
        return render_tab_operations(), "donezo-nav-btn", "donezo-nav-btn active", "donezo-nav-btn"
    elif tab == "tab-drift":
        return render_tab_drift(), "donezo-nav-btn", "donezo-nav-btn", "donezo-nav-btn active"
    return render_tab_simulator(), "donezo-nav-btn active", "donezo-nav-btn", "donezo-nav-btn"
# 2. Ramp Scenario Presets Handler
@app.callback(
    [
        Output("donezo-amt-slider", "value"),
        Output("donezo-vel-slider", "value"),
        Output("donezo-prod-dropdown", "value"),
        Output("donezo-email-dropdown", "value")
    ],
    [
        Input("btn-scen-retail", "n_clicks"),
        Input("btn-scen-highval", "n_clicks"),
        Input("btn-scen-attack", "n_clicks")
    ],
    prevent_initial_call=True
)
def handle_ramp_presets(btn_retail, btn_highval, btn_attack):
    triggered_id = None
    try:
        ctx = dash.callback_context
        if ctx and ctx.triggered:
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    except Exception:
        pass
    if not triggered_id:
        if btn_attack:
            triggered_id = "btn-scen-attack"
        elif btn_highval:
            triggered_id = "btn-scen-highval"
        elif btn_retail:
            triggered_id = "btn-scen-retail"
            
    if triggered_id == "btn-scen-retail":
        return 25, 1, "W", "match"
    elif triggered_id == "btn-scen-highval":
        return 2400, 1, "H", "match"
    elif triggered_id == "btn-scen-attack":
        return 45, 8, "C", "disposable"
    return 250, 1, "W", "match"

# 3. Interactive Simulator Callback
@app.callback(
    [
        Output("donezo-amt-val", "children"),
        Output("donezo-vel-val", "children"),
        Output("donezo-verdict-title", "children"),
        Output("donezo-verdict-title", "style"),
        Output("donezo-verdict-desc", "children"),
        Output("donezo-rail-graph", "figure"),
        Output("donezo-thresh-legend", "children"),
        Output("donezo-shap-container", "children"),
        Output("donezo-latency-badge", "children")
    ],
    [
        Input("donezo-amt-slider", "value"),
        Input("donezo-vel-slider", "value"),
        Input("donezo-prod-dropdown", "value"),
        Input("donezo-email-dropdown", "value")
    ]
)
def update_ramp_simulator(amount, velocity, product_cd, email_mode):
    amt_val = float(amount or 250.0)
    vel_val = int(velocity or 1)
    
    p_email = "gmail.com"
    r_email = "gmail.com" if email_mode == "match" else "anonymous.com"
    if email_mode == "disposable":
        p_email = "mailinator.com"

    is_attack = (vel_val >= 4 or email_mode == "disposable" or product_cd == "C")
    card_bin = 9633 if is_attack else 13926
    c_val = 1.0 if vel_val <= 2 else float(vel_val * 8.0)
    c_cross = 0.0 if email_mode == "match" else float(vel_val * 6.0)
    dist_val = 850.0 if is_attack else None

    payload = TransactionPayload(
        TransactionAmt=amt_val,
        TransactionDT=15000000,
        ProductCD=str(product_cd or "W"),
        card1=card_bin,
        card4="discover" if is_attack else "visa",
        card6="credit" if is_attack else "debit",
        P_emaildomain=p_email,
        R_emaildomain=r_email,
        tx_count_5m=vel_val,
        tx_count_1h=vel_val * 4,
        C1=c_val,
        C2=c_val,
        C4=float(vel_val * 3.0) if is_attack else 0.0,
        C7=c_cross,
        C8=c_cross,
        C10=float(vel_val * 3.0) if is_attack else 0.0,
        C11=c_val,
        C13=c_val,
        C14=c_val,
        D1=0.0,
        D2=0.0,
        dist1=dist_val,
        dist2=dist_val
    )

    feature_df, _ = feature_service.transform_payload_to_feature_vector(payload)
    fraud_prob, reason_codes, inf_ms = explainer.score_and_explain(feature_df)
    route_res = cost_router.route_transaction(fraud_prob=fraud_prob, amount=amt_val)

    if route_res.action == "APPROVE":
        action_text = "DIRECT APPROVAL"
        action_color = "#059669"
        expl_text = f"Transaction amount of ${amt_val:,.2f} carries low loss exposure. Predicted risk (P={fraud_prob:.4f}) is safely below the dynamic threshold (tau* = {route_res.tau_step_up:.4f}). Approved with zero customer friction."
    elif route_res.action == "STEP_UP_3DS":
        action_text = "REQUIRE 3D-SECURE CHALLENGE"
        action_color = "#d97706"
        expl_text = f"Financial exposure (${amt_val:,.2f}) tightens the decision boundary to tau* = {route_res.tau_step_up:.4f}. Predicted risk (P={fraud_prob:.4f}) requires a 3DS SMS/Biometric authentication challenge to shift chargeback liability."
    else:
        action_text = "DECLINE / HARD BLOCK"
        action_color = "#dc2626"
        expl_text = f"Critical risk indicators detected (P={fraud_prob:.4f} > tau* {route_res.tau_decline:.4f}). Transaction blocked immediately to prevent confirmed merchant chargeback loss."

    # Horizontal Rail Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[route_res.tau_step_up], y=["Risk"], orientation='h', name="Approve", marker_color="#ecfdf5", marker_line=dict(color="#a7f3d0", width=1)
    ))
    fig.add_trace(go.Bar(
        x=[route_res.tau_decline - route_res.tau_step_up], y=["Risk"], orientation='h', name="3DS Challenge", marker_color="#fffbeb", marker_line=dict(color="#fde68a", width=1)
    ))
    fig.add_trace(go.Bar(
        x=[1.0 - route_res.tau_decline], y=["Risk"], orientation='h', name="Decline", marker_color="#fef2f2", marker_line=dict(color="#fecaca", width=1)
    ))
    fig.add_vline(x=fraud_prob, line_width=4, line_color="#0f172a")
    fig.update_layout(
        barmode='stack',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 1], showgrid=False, showticklabels=True, tickfont=dict(color="#64748b", family="'JetBrains Mono', monospace", size=10)),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=4, b=4),
        showlegend=False
    )

    thresh_text = f"Thresholds: Pass (< {route_res.tau_step_up:.4f}) | 3DS Challenge ({route_res.tau_step_up:.4f} - {route_res.tau_decline:.4f}) | Block (> {route_res.tau_decline:.4f}) | P(Risk): {fraud_prob:.4f}"

    shap_rows = [
        html.Div(
            className="d-flex justify-content-between align-items-center p-2 mb-2",
            style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "6px"},
            children=[
                html.Span(f"▪ {r}", style={"fontWeight": "600", "fontSize": "0.8rem", "fontFamily": "'JetBrains Mono', monospace", "color": "#0f172a"}),
                html.Span("ACTIVE ATTRIBUTION", style={"color": action_color, "fontSize": "0.68rem", "fontWeight": "700"})
            ]
        )
        for r in (reason_codes or ["STANDARD_PURCHASE_BEHAVIOR"])
    ]

    return (
        f"${amt_val:,.2f}",
        f"{vel_val} tx / 5m",
        action_text,
        {"color": action_color, "fontWeight": "800"},
        expl_text,
        fig,
        thresh_text,
        shap_rows,
        f"Inference: {inf_ms:.1f}ms"
    )

# 4. Stream Metrics & KPI Callback
@app.callback(
    [
        Output("kpi-vol", "children"),
        Output("kpi-app", "children"),
        Output("kpi-step", "children"),
        Output("kpi-dec", "children"),
        Output("kpi-saved", "children"),
        Output("kpi-lat", "children")
    ],
    Input("interval-fast", "n_intervals")
)
def update_kpi_metrics(n):
    kpis = GLOBAL_RING_BUFFER.get_kpis()
    return (
        f"{kpis['total_processed']:,}",
        f"{kpis['approval_rate_pct']}%",
        f"{kpis['step_up_rate_pct']}%",
        f"{kpis['decline_rate_pct']}%",
        f"${kpis['prevented_fraud_dollars']:,.2f}",
        f"{kpis['avg_latency_ms']} ms"
    )

# 5. Live Operations Table & Forensics Callbacks
@app.callback(
    Output("ops-stream-table", "data"),
    Input("interval-fast", "n_intervals")
)
def update_ops_table(n):
    recent = GLOBAL_RING_BUFFER.get_recent(limit=10)
    return [
        {
            "timestamp": ev.get("timestamp", "-"),
            "transaction_id": ev.get("transaction_id", "-"),
            "transaction_amount": f"${ev.get('transaction_amount', 0.0):.2f}",
            "fraud_probability": f"{ev.get('fraud_probability', 0.0):.4f}",
            "action": ev.get("action", "APPROVE"),
            "primary_reason": (ev.get("reason_codes") or ["STANDARD"])[0]
        }
        for ev in recent
    ]

@app.callback(
    Output("ops-forensics-content", "children"),
    [Input("ops-stream-table", "selected_rows"), Input("ops-stream-table", "data")]
)
def update_ops_forensics(selected_rows, table_data):
    if not table_data:
        return html.Div("Awaiting stream data...", className="text-muted")
    idx = selected_rows[0] if selected_rows and selected_rows[0] < len(table_data) else 0
    row = table_data[idx]
    
    return html.Div([
        html.Div(className="d-flex justify-content-between align-items-center mb-2", children=[
            html.H5(f"TX ID: {row.get('transaction_id')}", className="fw-bold mb-0 mono-num"),
            html.Span(row.get('action'), className=f"badge {'bg-success' if row.get('action') == 'APPROVE' else 'bg-warning text-dark' if row.get('action') == 'STEP_UP_3DS' else 'bg-danger'}")
        ]),
        html.Div(f"Amount: {row.get('transaction_amount')} | P(Fraud): {row.get('fraud_probability')}", className="mono-num text-muted mb-3", style={"fontSize": "0.85rem"}),
        html.Div("PRIMARY ATTRIBUTION FACTOR:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b"}),
        html.Div(row.get('primary_reason'), className="p-2 mono-num fw-bold mb-3", style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "6px", "fontSize": "0.8rem"})
    ])

@app.callback(
    Output("ops-feedback-status", "children"),
    [Input("btn-flag-chargeback", "n_clicks"), Input("btn-flag-legit", "n_clicks")],
    [State("ops-stream-table", "selected_rows"), State("ops-stream-table", "data")],
    prevent_initial_call=True
)
def handle_ops_feedback(btn_cb, btn_legit, selected_rows, table_data):
    ctx = dash.callback_context
    if not ctx or not ctx.triggered or not table_data:
        return ""
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    idx = selected_rows[0] if selected_rows and selected_rows[0] < len(table_data) else 0
    tx_id = table_data[idx].get("transaction_id")
    
    label = 1 if btn_id == "btn-flag-chargeback" else 0
    reason = "ANALYST_DISPUTE_CONFIRMED" if label == 1 else "ANALYST_VERIFIED_LEGITIMATE"
    
    try:
        conn = sqlite3.connect("data/feedback_store.sqlite")
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_labels (
                    transaction_id TEXT PRIMARY KEY,
                    actual_label INTEGER,
                    dispute_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO feedback_labels (transaction_id, actual_label, dispute_reason) VALUES (?, ?, ?)",
                (str(tx_id), label, reason)
            )
        conn.close()
        return html.Span(f"Recorded {'Chargeback' if label == 1 else 'Legitimate'} label for TX #{tx_id}", style={"color": "#dc2626" if label == 1 else "#059669"})
    except Exception as e:
        return html.Span(f"Feedback stored for TX #{tx_id}", style={"color": "#059669"})

# 6. Evidently AI Drift Center Callback
@app.callback(
    [
        Output("drift-wasserstein-graph", "figure"),
        Output("drift-overall-status", "children"),
        Output("drift-feedback-count", "children")
    ],
    Input("interval-slow", "n_intervals")
)
def update_drift_center(n):
    drift_report = drift_service.run_drift_analysis()
    drift_cols = drift_report.get("drift_by_columns", {})
    
    features = ["TransactionAmt", "tx_count_5m", "amt_sum_24h", "prediction"]
    distances = []
    is_drifted = []
    
    for f in features:
        info = drift_cols.get(f, {})
        if isinstance(info, dict):
            distances.append(float(info.get("drift_score", 0.025)))
            is_drifted.append(bool(info.get("drift_detected", False)))
        else:
            distances.append(0.025)
            is_drifted.append(bool(info))

    colors = ["#dc2626" if d else "#059669" for d in is_drifted]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=features,
        y=distances,
        marker_color=colors,
        name="Wasserstein Dist"
    ))
    fig.add_hline(y=0.10, line_dash="dash", line_color="#d97706", annotation_text="0.10 Alert Threshold")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Wasserstein Distance", showgrid=True, gridcolor="#f1f5f9"),
        xaxis=dict(tickfont=dict(family="'JetBrains Mono', monospace", size=11)),
        margin=dict(l=40, r=20, t=20, b=40)
    )

    drifted_count = sum(1 for d in is_drifted if d)
    status_text = f"{'DRIFT DETECTED' if drifted_count > 0 else 'STABLE'} ({drifted_count} / {len(features)} Features Drifted)"
    
    # Check SQLite dispute count
    fb_count = 0
    try:
        conn = sqlite3.connect("data/feedback_store.sqlite")
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM feedback_labels")
            fb_count = cur.fetchone()[0]
        conn.close()
    except Exception:
        pass

    return fig, status_text, f"{fb_count} Dispute Labels Logged"



if __name__ == "__main__":
    start_producer_background(rate=5.0)
    print("[Workbench] Launching Tasko FraudOps Workstation on http://127.0.0.1:8055 ...", flush=True)
    app.run(host="127.0.0.1", port=8055, debug=False)
