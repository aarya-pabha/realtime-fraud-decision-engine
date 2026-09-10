# Tasko UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `src/frontend/app_tasko.py` to strip out dummy template content and integrate the actual 3-tab FraudOps functionality from `src/frontend/app.py`, while strictly preserving the Tasko design system (Donezo CSS variables and layout structure).

**Architecture:** We will replace the dummy `render_donezo_dashboard` and sidebar/header elements with the actual `render_tab_simulator`, `render_tab_operations`, and `render_tab_drift` functions ported from `app.py`. We will adapt class names from `ramp-*` / `action-card` to `donezo-white-card` and `btn-donezo-*`. All interactive callbacks will be imported from `app.py` and mapped to the new layout.

**Tech Stack:** Python, Dash, Plotly, HTML/CSS.

---

### Task 1: Clean Up Sidebar & Header

**Files:**
- Modify: `src/frontend/app_tasko.py`

- [ ] **Step 1: Update `donezo_sidebar`**
Remove the dummy "Settings", "Help", and "Sign Out" from the GENERAL section. Update the MENU section to strictly hold the 3 FraudOps tabs.

```python
def donezo_sidebar():
    return html.Div(
        className="donezo-sidebar",
        children=[
            html.Div([
                # Brand Header (Tasko Icon + Name)
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
                        html.Span("Tasko", style={"fontWeight": "800", "fontSize": "1.2rem", "color": "#202318", "letterSpacing": "-0.02em"})
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
```

- [ ] **Step 2: Update `donezo_header`**
Remove the dummy user profile ("Jessin Sam") and notification icons.

```python
def donezo_header():
    return html.Div(
        className="d-flex justify-content-between align-items-center mb-4",
        children=[
            # Search Bar (Donezo Pill)
            html.Div(
                className="donezo-search-box",
                children=[
                    html.Span("🔍", style={"fontSize": "0.85rem", "color": "#707367"}),
                    dcc.Input(placeholder="Search transaction, card token, IP...", type="text", style={"border": "none", "outline": "none", "width": "100%", "fontSize": "0.85rem"}),
                    html.Span("⌘F", className="donezo-kbd")
                ]
            ),
            # Right User Profile - Removed dummy profile
            html.Div(
                className="d-flex align-items-center gap-3",
                children=[]
            )
        ]
    )
```

### Task 2: Port FraudOps Layouts (Tab 1, Tab 2, Tab 3)

**Files:**
- Modify: `src/frontend/app_tasko.py`

- [ ] **Step 1: Delete Dummy Components**
Delete `render_donezo_dashboard()` entirely from `app_tasko.py`.

- [ ] **Step 2: Import Layout Renderers from `app.py`**
Copy the `render_tab_simulator()`, `render_tab_operations()`, and `render_tab_drift()` functions from `src/frontend/app.py` into `src/frontend/app_tasko.py`. 
For each function, change the CSS class `action-card` and any hardcoded bordered wrappers to use the Tasko `donezo-white-card` class. Preserve all IDs (e.g., `ramp-amt-val`, `ops-stream-table`) so the backend callbacks continue to work.

### Task 3: Implement Routing & Callbacks

**Files:**
- Modify: `src/frontend/app_tasko.py`

- [ ] **Step 1: Navigation Routing Callback**
Replace the dummy `update_donezo_nav` callback with the actual routing logic to switch tabs. Note that `donezo-active-tab` is used to store the state.

```python
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
```

- [ ] **Step 2: Port Backend Functional Callbacks**
Copy ALL of the remaining callbacks from `src/frontend/app.py` directly into `src/frontend/app_tasko.py` (replacing the dummy `update_donezo_metrics` callback). 
This includes:
- `handle_ramp_presets`
- `update_ramp_simulator`
- `update_ops_table`
- `update_ops_forensics`
- `handle_ops_feedback`
- `update_drift_center`

### Task 4: Verification

- [ ] **Step 1: Verify the server runs**
Run `.venv/Scripts/python.exe src/frontend/app_tasko.py` and ensure the application boots without layout or callback exceptions. Click through all 3 tabs to ensure routing works.
