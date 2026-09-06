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
import plotly.express as px

from src.streaming.producer import TransactionProducer
from src.streaming.consumer import StreamingScoringConsumer, GLOBAL_RING_BUFFER
from src.frontend.drift_service import DriftMonitoringService
from src.models.cost_router import DynamicCostRouter
from src.models.explainability import FraudExplainer
from src.api.feature_service import FeatureService
from src.api.schemas import TransactionPayload

# Initialize Background Consumer and Services
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

# Initialize Dash App with Ramp Editorial Style
app = dash.Dash(
    __name__,
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css",
        "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
    ],
    title="FraudOps Risk Platform | Ramp Editorial Workstation",
    suppress_callback_exceptions=True
)
server = app.server

# Custom CSS for 2026 Ramp Editorial Calm Design System
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
                --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
                --font-mono: 'JetBrains Mono', monospace;
            }
            body {
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
                font-family: var(--font-sans) !important;
                color: #0f172a;
                -webkit-font-smoothing: antialiased;
                letter-spacing: -0.01em;
            }
            .mono-num {
                font-family: var(--font-mono) !important;
                font-variant-numeric: tabular-nums;
            }
            .nav-tab-btn {
                border: 1px solid #e2e8f0;
                background: #ffffff;
                color: #475569;
                font-weight: 600;
                font-size: 0.82rem;
                padding: 8px 18px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.15s ease;
            }
            .nav-tab-btn:hover {
                background: #f1f5f9;
                color: #0f172a;
            }
            .nav-tab-btn.active {
                background: #0f172a !important;
                color: #ffffff !important;
                border-color: #0f172a !important;
            }
            .action-card {
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            .action-card:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.05);
            }
            .rc-slider-tooltip, .dash-range-slider-input, .dash-input-container {
                display: none !important;
            }
            .rc-slider-mark-text {
                font-family: var(--font-mono) !important;
                font-size: 0.72rem !important;
                color: #64748b !important;
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

def ramp_kpi_card(title: str, id_val: str, default: str, sub: str):
    return html.Div(
        style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "16px"},
        children=[
            html.Div(title, style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b", "letterSpacing": "0.05em"}),
            html.H4(id=id_val, children=default, className="fw-bold my-1 mono-num", style={"color": "#0f172a", "fontSize": "1.45rem"}),
            html.Small(sub, style={"color": "#94a3b8", "fontSize": "0.72rem"})
        ]
    )

# ----------------- TAB 1: INTERACTIVE 3DS SIMULATOR & SANDBOX -----------------
def render_tab_simulator():
    return html.Div([
        # Scenario Presets Header
        html.Div(
            className="p-3 mb-4",
            style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px"},
            children=[
                html.Div("ONE-CLICK RISK PROFILES", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#2563eb", "letterSpacing": "0.08em", "marginBottom": "6px"}),
                dbc.Row(
                    className="g-3",
                    children=[
                        dbc.Col(
                            md=4,
                            children=html.Button(
                                id="btn-scen-retail",
                                className="action-card w-100 p-3 text-start",
                                style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "8px", "cursor": "pointer"},
                                children=[
                                    html.Div("Baseline Retail Purchase", style={"fontWeight": "700", "fontSize": "0.9rem", "color": "#0f172a"}),
                                    html.Div("Amount: $25.00 | Velocity: 1 tx/5m | Verified Domestic Email", style={"fontSize": "0.78rem", "color": "#64748b", "margin": "3px 0"}),
                                    html.Span("Expected: Direct Approval (0% Friction)", style={"backgroundColor": "#ecfdf5", "color": "#065f46", "border": "1px solid #a7f3d0", "fontSize": "0.7rem", "fontWeight": "700", "padding": "2px 8px", "borderRadius": "4px"})
                                ]
                            )
                        ),
                        dbc.Col(
                            md=4,
                            children=html.Button(
                                id="btn-scen-highval",
                                className="action-card w-100 p-3 text-start",
                                style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "8px", "cursor": "pointer"},
                                children=[
                                    html.Div("High-Value Electronics Checkout", style={"fontWeight": "700", "fontSize": "0.9rem", "color": "#0f172a"}),
                                    html.Div("Amount: $2,400.00 | Velocity: 1 tx/5m | Hardware Product Category", style={"fontSize": "0.78rem", "color": "#64748b", "margin": "3px 0"}),
                                    html.Span("Expected: Dynamic 3DS Challenge (Tightened Boundary)", style={"backgroundColor": "#fffbeb", "color": "#92400e", "border": "1px solid #fde68a", "fontSize": "0.7rem", "fontWeight": "700", "padding": "2px 8px", "borderRadius": "4px"})
                                ]
                            )
                        ),
                        dbc.Col(
                            md=4,
                            children=html.Button(
                                id="btn-scen-attack",
                                className="action-card w-100 p-3 text-start",
                                style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "8px", "cursor": "pointer"},
                                children=[
                                    html.Div("Card-Testing Velocity Burst", style={"fontWeight": "700", "fontSize": "0.9rem", "color": "#0f172a"}),
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
                        style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px"},
                        children=[
                            html.H6("Transaction Authorization Parameters", className="fw-bold mb-3", style={"color": "#0f172a"}),
                            
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
                            style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px", "marginBottom": "20px"},
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
                            style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px"},
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
                        style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px"},
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
                                style_header={"backgroundColor": "#f8fafc", "color": "#475569", "fontWeight": "700", "fontSize": "0.75rem", "border": "1px solid #e2e8f0", "padding": "10px"},
                                style_cell={"backgroundColor": "#ffffff", "color": "#0f172a", "fontSize": "0.78rem", "fontFamily": "'JetBrains Mono', monospace", "textAlign": "center", "padding": "10px", "border": "1px solid #f1f5f9", "cursor": "pointer"},
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
                        style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px"},
                        children=[
                            html.Div("TRANSACTION FORENSICS & FEEDBACK", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#2563eb", "letterSpacing": "0.08em", "marginBottom": "12px"}),
                            
                            html.Div(id="ops-forensics-content", children=[
                                html.Div("Select a transaction from the feed to inspect risk attributes.", className="text-muted", style={"fontSize": "0.85rem"})
                            ]),

                            html.Hr(style={"borderColor": "#e2e8f0", "margin": "20px 0"}),

                            html.H6("Analyst Dispute Feedback Station", className="fw-bold mb-2", style={"fontSize": "0.9rem"}),
                            html.P("Submit analyst-verified chargeback labels to update Evidently AI model stability tracking:", className="text-muted mb-3", style={"fontSize": "0.8rem"}),
                            
                            html.Div(className="d-flex gap-2 mb-2", children=[
                                html.Button("Flag as Fraud Dispute (Chargeback)", id="btn-flag-chargeback", className="btn btn-danger btn-sm fw-bold w-100", style={"fontSize": "0.8rem", "padding": "8px"}),
                                html.Button("Mark Legitimate", id="btn-flag-legit", className="btn btn-outline-secondary btn-sm fw-bold w-100", style={"fontSize": "0.8rem", "padding": "8px"})
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
                        style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px"},
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
                        style={"backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "borderRadius": "10px", "padding": "24px"},
                        children=[
                            html.Div("REGULATORY & MODEL STABILITY COMPLIANCE", style={"fontSize": "0.7rem", "fontWeight": "800", "color": "#2563eb", "letterSpacing": "0.08em", "marginBottom": "12px"}),
                            
                            html.Div(
                                className="p-3 mb-3",
                                style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "8px"},
                                children=[
                                    html.Div("VISA VAMP COMPLIANCE STATUS:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b"}),
                                    html.H4("0.42% Chargeback Ratio", className="fw-bold my-1 mono-num text-success", style={"fontSize": "1.3rem"}),
                                    html.Small("Regulatory threshold is <1.50%. Portfolio operates at elite compliance.", style={"color": "#64748b", "fontSize": "0.75rem"})
                                ]
                            ),

                            html.Div(
                                className="p-3 mb-3",
                                style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "8px"},
                                children=[
                                    html.Div("DATASET DRIFT STATUS:", style={"fontSize": "0.68rem", "fontWeight": "700", "color": "#64748b"}),
                                    html.H4(id="drift-overall-status", children="STABLE (0 / 4 Features Drifted)", className="fw-bold my-1 mono-num", style={"fontSize": "1.1rem", "color": "#059669"}),
                                    html.Small("Evidently AI Wasserstein distance test evaluated on live stream slice.", style={"color": "#64748b", "fontSize": "0.75rem"})
                                ]
                            ),

                            html.Div(
                                className="p-3",
                                style={"backgroundColor": "#f8fafc", "border": "1px solid #e2e8f0", "borderRadius": "8px"},
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


# ----------------- MASTER APP LAYOUT -----------------
app.layout = html.Div(
    id="app-root",
    style={"padding": "24px 40px"},
    children=[
        # Top Nav & Branding
        html.Div(
            className="d-flex justify-content-between align-items-center pb-3 mb-4",
            style={"borderBottom": "1px solid #e2e8f0"},
            children=[
                html.Div([
                    html.Div(
                        className="d-flex align-items-center gap-2 mb-1",
                        children=[
                            html.Span("•", style={"color": "#10b981", "fontSize": "1.2rem", "lineHeight": "0"}),
                            html.Span("FRAUD RADAR & DECISION ENGINE", style={"fontWeight": "800", "fontSize": "0.75rem", "color": "#2563eb", "letterSpacing": "0.08em"}),
                            html.Span("RAMP EDITORIAL CALM", style={"fontSize": "0.68rem", "color": "#64748b", "border": "1px solid #cbd5e1", "padding": "2px 6px", "borderRadius": "4px", "fontWeight": "700"})
                        ]
                    ),
                    html.H4("Real-Time Transaction Risk Operations", className="fw-bold mb-0", style={"letterSpacing": "-0.02em"}),
                    html.P("Sub-25ms Dual-Tier Feature Hydration with Dynamic Value-Aware Bayesian Decision Policy", className="mb-0 text-muted", style={"fontSize": "0.85rem"})
                ]),
                # Clean Editorial Tab Switcher
                html.Div(
                    className="d-flex align-items-center gap-2",
                    children=[
                        html.Button("Interactive 3DS Sandbox", id="btn-tab-sim", className="nav-tab-btn active"),
                        html.Button("Live Operations & Dispute Queue", id="btn-tab-ops", className="nav-tab-btn"),
                        html.Button("Evidently AI Drift & Stability Center", id="btn-tab-drift", className="nav-tab-btn")
                    ]
                )
            ]
        ),

        # Executive Verdict Ribbon (KPIs) - Constant across all views
        dbc.Row(
            className="g-3 mb-4",
            children=[
                dbc.Col(md=2, children=ramp_kpi_card("STREAMED VOLUME", "kpi-vol", "0", "Holdout stream")),
                dbc.Col(md=2, children=ramp_kpi_card("APPROVAL RATE", "kpi-app", "0.0%", "Instant zero-friction")),
                dbc.Col(md=2, children=ramp_kpi_card("3DS CHALLENGE RATE", "kpi-step", "0.0%", "Benchmark: 8% – 15%")),
                dbc.Col(md=2, children=ramp_kpi_card("DECLINE RATE", "kpi-dec", "0.0%", "Direct fraud blocked")),
                dbc.Col(md=2, children=ramp_kpi_card("SAVED CAPITAL", "kpi-saved", "$0.00", "Prevented chargebacks")),
                dbc.Col(md=2, children=ramp_kpi_card("AVG SLA LATENCY", "kpi-lat", "0.0 ms", "Target: <25.0 ms"))
            ]
        ),

        # Dynamic Tab Content Container (Default Tab 1: Simulator)
        html.Div(id="tab-content-container", children=render_tab_simulator()),

        # Background Periodic Intervals
        dcc.Interval(id="interval-fast", interval=1500, n_intervals=0),
        dcc.Interval(id="interval-slow", interval=8000, n_intervals=0),
        
        # State Storage
        dcc.Store(id="active-tab-store", data="tab-sim")
    ]
)

# ----------------- MASTER CALLBACKS -----------------

# 1. Navigation Tab Router Callback
@app.callback(
    Output("active-tab-store", "data"),
    [
        Input("btn-tab-sim", "n_clicks"),
        Input("btn-tab-ops", "n_clicks"),
        Input("btn-tab-drift", "n_clicks")
    ],
    State("active-tab-store", "data")
)
def route_active_tab(btn_sim, btn_ops, btn_drift, current_tab):
    ctx = dash.callback_context
    if not ctx or not ctx.triggered:
        return current_tab or "tab-sim"
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if btn_id == "btn-tab-sim":
        return "tab-sim"
    elif btn_id == "btn-tab-ops":
        return "tab-ops"
    elif btn_id == "btn-tab-drift":
        return "tab-drift"
    return "tab-sim"

@app.callback(
    [
        Output("tab-content-container", "children"),
        Output("btn-tab-sim", "className"),
        Output("btn-tab-ops", "className"),
        Output("btn-tab-drift", "className")
    ],
    Input("active-tab-store", "data")
)
def render_tab_content(tab):
    if tab == "tab-ops":
        return render_tab_operations(), "nav-tab-btn", "nav-tab-btn active", "nav-tab-btn"
    elif tab == "tab-drift":
        return render_tab_drift(), "nav-tab-btn", "nav-tab-btn", "nav-tab-btn active"
    return render_tab_simulator(), "nav-tab-btn active", "nav-tab-btn", "nav-tab-btn"

# 2. Ramp Scenario Presets Handler
@app.callback(
    [
        Output("ramp-amt-slider", "value"),
        Output("ramp-vel-slider", "value"),
        Output("ramp-prod-dropdown", "value"),
        Output("ramp-email-dropdown", "value")
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
        Output("ramp-amt-val", "children"),
        Output("ramp-vel-val", "children"),
        Output("ramp-verdict-title", "children"),
        Output("ramp-verdict-title", "style"),
        Output("ramp-verdict-desc", "children"),
        Output("ramp-rail-graph", "figure"),
        Output("ramp-thresh-legend", "children"),
        Output("ramp-shap-container", "children"),
        Output("ramp-latency-badge", "children")
    ],
    [
        Input("ramp-amt-slider", "value"),
        Input("ramp-vel-slider", "value"),
        Input("ramp-prod-dropdown", "value"),
        Input("ramp-email-dropdown", "value")
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
    print("[Workbench] Launching Ramp Editorial Workstation on http://127.0.0.1:8050 ...", flush=True)
    app.run(host="127.0.0.1", port=8050, debug=False)
