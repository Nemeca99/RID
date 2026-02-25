"""
RID Mission Control — Streamlit SCADA Dashboard
================================================
Live RID stability calculator with SCADA-grade visualization.
Run:  L:\.venv\Scripts\streamlit run app.py --server.address 0.0.0.0 --server.port 8501
"""

import sys, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from rid import rle_n, ltp_n, rsr_n, stability_scalar, diagnostic_step, discrepancy_01
from rid.semantic_physics import UnifiedSemanticPhysics

# ════════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="RID Mission Control",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — SCADA Dark Theme
# ════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
  /* ── Base ── */
  html, body, [data-testid="stAppViewContainer"] {
    background: #080b14;
    color: #c8d8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }
  [data-testid="stSidebar"] {
    background: #0d1220;
    border-right: 1px solid #1e2d4a;
  }
  [data-testid="stSidebar"] * { color: #8aaed4 !important; }

  /* ── Header ── */
  .rid-header {
    display: flex; align-items: center; gap: 20px;
    padding: 18px 28px 12px;
    background: linear-gradient(135deg, #0d1220 0%, #0f1d38 60%, #091428 100%);
    border-bottom: 1px solid #1a3260;
    border-radius: 12px;
    margin-bottom: 20px;
  }
  .rid-logo {
    font-size: 2.6rem; font-weight: 800; letter-spacing: 0.04em;
    background: linear-gradient(90deg, #00d4ff, #4af5b0);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .rid-subtitle {
    font-size: 0.82rem; color: #4a7aaa; letter-spacing: 0.15em; text-transform: uppercase;
    margin-top: 3px;
  }
  .rid-live-badge {
    margin-left: auto; display: flex; align-items: center; gap: 8px;
    font-size: 0.75rem; color: #4af5b0; letter-spacing: 0.12em;
  }
  .pulse-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #4af5b0;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(1.4)} }

  /* ── Metric Cards ── */
  .metric-card {
    background: linear-gradient(145deg, #0d1828, #101e35);
    border: 1px solid #1a3260;
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
    transition: border-color 0.3s;
  }
  .metric-card:hover { border-color: #00d4ff44; }
  .metric-label {
    font-size: 0.7rem; color: #4a7aaa; letter-spacing: 0.14em;
    text-transform: uppercase; margin-bottom: 6px;
  }
  .metric-value {
    font-size: 2rem; font-weight: 700; letter-spacing: 0.02em;
  }
  .metric-sub { font-size: 0.72rem; color: #3a5a84; margin-top: 4px; }

  /* ── Status Badge ── */
  .status-badge {
    display: inline-block; padding: 6px 18px; border-radius: 99px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .badge-green  { background: #004422; color: #4af5b0; border: 1px solid #4af5b020; }
  .badge-amber  { background: #3a2200; color: #ffaa00; border: 1px solid #ffaa0020; }
  .badge-red    { background: #3a0a0a; color: #ff5555; border: 1px solid #ff555520; }

  /* ── Physics row ── */
  .phys-card {
    background: #0a111e;
    border: 1px solid #152240;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
  }
  .phys-label { font-size: 0.68rem; color: #3a5a84; letter-spacing: 0.1em; text-transform: uppercase; }
  .phys-value { font-size: 1.25rem; font-weight: 600; color: #c8d8f0; }

  /* ── Section headers ── */
  .section-title {
    font-size: 0.68rem; color: #2a4a6a; letter-spacing: 0.25em;
    text-transform: uppercase; border-bottom: 1px solid #1a2a40;
    padding-bottom: 6px; margin: 18px 0 12px;
  }

  /* Streamlit overrides */
  .stSlider [data-baseweb="slider"] { padding: 4px 0; }
  .stMarkdown hr { border-color: #1a2a40; }
  div[data-testid="metric-container"] {
    background: #0d1828; border-radius: 10px;
    border: 1px solid #1a3260; padding: 12px;
  }

  /* Tab styling */
  .stTabs [role="tab"] {
    color: #3a5a84;
    background: transparent;
    border-radius: 8px 8px 0 0;
    font-size: 0.78rem; letter-spacing: 0.1em;
  }
  .stTabs [role="tab"][aria-selected="true"] {
    color: #00d4ff;
    background: #0d1828;
    border-bottom: 2px solid #00d4ff;
  }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════════

if "history" not in st.session_state:
    st.session_state.history = []   # list of (beat, S_n, RSR, LTP, RLE, F_real)

if "beat" not in st.session_state:
    st.session_state.beat = 0

# ════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def sn_color(v):
    if v >= 0.95:  return "#4af5b0"
    if v >= 0.80:  return "#00d4ff"
    if v >= 0.60:  return "#ffaa00"
    return "#ff5555"

def sn_badge_class(v):
    if v >= 0.80: return "badge-green"
    if v >= 0.60: return "badge-amber"
    return "badge-red"

def make_gauge(value, label, color, min_=0, max_=1, suffix=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 28, "color": color, "family": "Inter"}},
        gauge={
            "axis": {"range": [min_, max_], "tickcolor": "#2a4060",
                     "tickfont": {"size": 9, "color": "#3a5a84"}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "#080b14",
            "borderwidth": 0,
            "steps": [
                {"range": [min_, max_ * 0.6], "color": "#1a0608"},
                {"range": [max_ * 0.6, max_ * 0.8], "color": "#1a1608"},
                {"range": [max_ * 0.8, max_], "color": "#081a10"},
            ],
            "threshold": {"line": {"color": color, "width": 2},
                          "thickness": 0.75, "value": value},
        },
        title={"text": f"<b>{label}</b>",
               "font": {"size": 11, "color": "#4a7aaa", "family": "Inter"}},
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=50, b=10, l=20, r=20),
        paper_bgcolor="#0d1828",
        plot_bgcolor="#0d1828",
        font={"family": "Inter"},
    )
    return fig


def make_trend(history, label, key):
    if not history:
        return go.Figure()
    df = pd.DataFrame(history, columns=["beat","S_n","RSR","LTP","RLE","F_real"])
    fig = go.Figure()
    colors = {"S_n": "#00d4ff", "RSR": "#4af5b0", "LTP": "#ffaa00", "RLE": "#bb88ff", "F_real": "#ff8844"}
    for k, c in colors.items():
        if k == key or key == "all":
            fig.add_trace(go.Scatter(
                x=df["beat"], y=df[k],
                mode="lines", name=k,
                line=dict(color=c, width=2),
                fill="tozeroy",
                fillcolor=c.replace(")", ",0.06)").replace("rgb", "rgba") if "rgb" in c else c + "10",
            ))
    fig.update_layout(
        height=200,
        margin=dict(t=10, b=30, l=40, r=20),
        paper_bgcolor="#080b14",
        plot_bgcolor="#080b14",
        xaxis=dict(gridcolor="#1a2540", color="#3a5a84", title="Beat"),
        yaxis=dict(gridcolor="#1a2540", color="#3a5a84", range=[0, 1.05]),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#4a7aaa", size=10)),
        font=dict(family="Inter"),
    )
    return fig


# ════════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="rid-header">
  <div>
    <div class="rid-logo">⬡ RID</div>
    <div class="rid-subtitle">Mission Control · Stability Intelligence Platform</div>
  </div>
  <div class="rid-live-badge">
    <div class="pulse-dot"></div>
    ONLINE
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙ Input Parameters")
    st.markdown('<div class="section-title">RLE — Memory Efficiency</div>', unsafe_allow_html=True)
    E_n    = st.slider("Capacity (E_n)", 0.01, 1.0, 1.0, 0.01, help="System capacity before step")
    U_n    = st.slider("Loss (U_n)",     0.0,  1.0, 0.0, 0.01, help="Energy lost during step")
    E_next = st.slider("Remaining (E_next)", 0.0, 1.0, 1.0, 0.01, help="Capacity after step")

    st.markdown('<div class="section-title">LTP — Structural Adequacy</div>', unsafe_allow_html=True)
    n_n = st.slider("Support (n_n)", 0.01, 200.0, 100.0, 0.5, help="Structural support available")
    d_n = st.slider("Demand (d_n)",  0.01, 200.0, 100.0, 0.5, help="Cognitive/operational demand")

    st.markdown('<div class="section-title">RSR — Identity Continuity</div>', unsafe_allow_html=True)
    y_n    = st.slider("Observable (y_n)",      0.0, 1.0, 0.5, 0.01, help="Current observable state")
    recon  = st.slider("Reconstruction (recon)", 0.0, 1.0, 0.5, 0.01, help="Reconstructed prior state")

    st.markdown('<div class="section-title">Physics Engine</div>', unsafe_allow_html=True)
    gpu_options = {"4 GB (Budget)": 4.0, "8 GB RTX 3060 Ti": 8.0,
                   "16 GB RTX 4080": 16.0, "24 GB RTX 4090": 24.0, "80 GB H100": 80.0}
    gpu_label = st.selectbox("GPU VRAM", list(gpu_options.keys()), index=1)
    gpu_vram  = gpu_options[gpu_label]
    tokens    = st.slider("Prompt Tokens", 0, 4096, 200, 10, help="Token count for physics calculation")

    st.markdown("---")
    if st.button("🔄 Log Reading", use_container_width=True):
        st.session_state.beat += 1

    if st.button("🗑 Clear History", use_container_width=True):
        st.session_state.history = []
        st.session_state.beat = 0


# ════════════════════════════════════════════════════════════════════════════════
# COMPUTE
# ════════════════════════════════════════════════════════════════════════════════

RLE  = rle_n(E_next, U_n, E_n)
LTP  = ltp_n(n_n, d_n)
D    = discrepancy_01(y_n, recon)
RSR  = 1.0 - D
S_n  = stability_scalar(RSR, LTP, RLE)
diag = diagnostic_step(RSR, LTP, RLE)

physics = UnifiedSemanticPhysics(hardware_capacity_gb=gpu_vram)
ps = physics.compute(s_n=S_n, stm_load=U_n, ltp=LTP, rle=RLE, prompt_tokens=float(tokens))

# Append to history on every render (auto) or on button click
current = [st.session_state.beat, S_n, RSR, LTP, RLE, ps.realized_force]
if not st.session_state.history or st.session_state.history[-1] != current:
    st.session_state.history.append(current)
    if len(st.session_state.history) > 200:
        st.session_state.history = st.session_state.history[-200:]


# ════════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════════

tab_calc, tab_import, tab_ref = st.tabs(["  ⬡ LIVE CALCULATOR  ", "  ↑ BATCH IMPORT  ", "  ◈ REFERENCE  "])

# ── TAB 1: LIVE CALCULATOR ───────────────────────────────────────────────────
with tab_calc:

    # ── TOP ROW: Gauges ──────────────────────────────────────────────────────
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.plotly_chart(make_gauge(RSR, "RSR — Identity", sn_color(RSR)), use_container_width=True, key="g_rsr")
    with g2:
        st.plotly_chart(make_gauge(LTP, "LTP — Structure", sn_color(LTP)), use_container_width=True, key="g_ltp")
    with g3:
        st.plotly_chart(make_gauge(RLE, "RLE — Memory", sn_color(RLE)), use_container_width=True, key="g_rle")
    with g4:
        st.plotly_chart(make_gauge(S_n, "S_n — STABILITY", sn_color(S_n)), use_container_width=True, key="g_sn")

    # ── STATUS BAR ────────────────────────────────────────────────────────────
    col_status, col_action = st.columns([1, 2])
    with col_status:
        badge_class = sn_badge_class(S_n)
        status_text = "NOMINAL" if S_n >= 0.95 else ("WATCH" if S_n >= 0.80 else ("DEGRADE" if S_n >= 0.60 else "CRITICAL"))
        st.markdown(f'<div style="margin:10px 0"><span class="status-badge {badge_class}">{status_text}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-sub" style="margin-top:6px">S_n = <b style="color:{sn_color(S_n)}">{S_n:.4f}</b></div>', unsafe_allow_html=True)
    with col_action:
        action_colors = {
            "continue": "#4af5b0", "intervene_rle": "#00d4ff",
            "intervene_rsr": "#ffaa00", "check_rsr": "#ffaa00",
            "mandatory_descent": "#ff5555", "check_ltp": "#ff8844",
        }
        ac = diag.action
        acolor = action_colors.get(ac, "#88aacc")
        st.markdown(f"""
        <div style="background:#0a111e;border:1px solid #1a2a40;border-left:3px solid {acolor};
                    border-radius:8px;padding:10px 14px;margin-top:6px">
          <div style="font-size:0.65rem;color:#3a5a84;letter-spacing:0.12em;text-transform:uppercase">FIDF Diagnostic Action</div>
          <div style="font-size:1.1rem;font-weight:700;color:{acolor};margin-top:3px">{ac.upper().replace('_',' ')}</div>
          <div style="font-size:0.72rem;color:#4a6080;margin-top:2px">{diag.message if hasattr(diag,'message') and diag.message else 'System operating within parameters'}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:22px">SEMANTIC PHYSICS ENGINE</div>', unsafe_allow_html=True)

    # ── PHYSICS ROW ─────────────────────────────────────────────────────────
    p1, p2, p3, p4, p5, p6 = st.columns(6)

    def phys_card(col, label, value, unit="", color="#c8d8f0", alert=False):
        border = "border-color:#ff555540;" if alert else ""
        col.markdown(f"""
        <div class="phys-card" style="{border}">
          <div class="phys-label">{label}</div>
          <div class="phys-value" style="color:{color}">{value:.4f}<span style="font-size:0.7rem;color:#3a5a84"> {unit}</span></div>
        </div>""", unsafe_allow_html=True)

    phys_card(p1, "Λ_floor",   ps.lambda_floor,   "%",  "#00d4ff")
    phys_card(p2, "Λ_mismatch", ps.lambda_mismatch, "%",  "#ffaa00" if ps.lambda_mismatch > 0.1 else "#4a7aaa")
    phys_card(p3, "Λ_total",    ps.lambda_total,    "%",  "#ff8844" if ps.lambda_total > 0.3 else "#4a7aaa")
    phys_card(p4, "F_raw",      ps.raw_force,       "u",  "#bb88ff")
    phys_card(p5, "F_realized", ps.realized_force,  "u",  sn_color(S_n))
    phys_card(p6, "GPU Friction",ps.gpu_friction,   "u",  "#3a5a84")

    # Descent alert
    if ps.kernel_descent:
        st.markdown("""
        <div style="background:#3a0808;border:1px solid #ff5555;border-radius:10px;
                    padding:12px 18px;margin-top:8px;display:flex;align-items:center;gap:12px">
          <span style="font-size:1.4rem">⚠</span>
          <div>
            <div style="color:#ff5555;font-weight:700;font-size:0.9rem">KERNEL DESCENT TRIGGERED</div>
            <div style="color:#884444;font-size:0.75rem">Realized force ≤ 0 — system cannot produce useful output. Reduce complexity.</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # GPU efficiency bar
    eff = ps.realized_force / ps.raw_force if ps.raw_force > 0 else 0.0
    st.markdown(f"""
    <div style="margin-top:14px">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px">
        <span style="font-size:0.68rem;color:#3a5a84;letter-spacing:0.12em;text-transform:uppercase">GPU EFFICIENCY ({gpu_label})</span>
        <span style="font-size:0.78rem;color:{sn_color(eff)};font-weight:600">{eff*100:.1f}%</span>
      </div>
      <div style="background:#0a111e;height:6px;border-radius:3px;overflow:hidden">
        <div style="width:{eff*100:.1f}%;height:100%;background:linear-gradient(90deg,{sn_color(S_n)},{sn_color(eff)});border-radius:3px;transition:width 0.4s"></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── TREND CHART ──────────────────────────────────────────────────────────
    if len(st.session_state.history) > 1:
        st.markdown('<div class="section-title" style="margin-top:22px">SESSION TREND</div>', unsafe_allow_html=True)
        st.plotly_chart(make_trend(st.session_state.history, "All", "all"),
                        use_container_width=True, key="trend_all")


# ── TAB 2: BATCH IMPORT ──────────────────────────────────────────────────────
with tab_import:
    st.markdown("### Batch Analysis — File Import")
    st.markdown("""
    Upload a **CSV** or **JSON** file with RID input columns. The engine will compute
    RLE, LTP, RSR, S_n, and physics outputs for every row.
    """)

    st.markdown("""
    **Required columns (choose one mapping):**

    | Mode | Required Columns |
    |------|-----------------|
    | Full RLE | `E_n`, `U_n`, `E_next` |
    | Full LTP | `n_n`, `d_n` |
    | Full RSR | `y_n`, `recon` |
    | Physics  | `tokens` (optional) |

    Missing columns use safe defaults (1.0 / stable).
    """)

    col_up, col_gpu = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("Drop CSV or JSON", type=["csv", "json"],
                                     label_visibility="collapsed")
    with col_gpu:
        batch_gpu_label = st.selectbox("GPU", list(gpu_options.keys()), index=1, key="batch_gpu")
        batch_gpu = gpu_options[batch_gpu_label]

    if uploaded:
        try:
            if uploaded.name.endswith(".json"):
                df_in = pd.read_json(uploaded)
            else:
                df_in = pd.read_csv(uploaded)

            st.markdown(f"**Loaded {len(df_in)} rows · {len(df_in.columns)} columns**")
            st.dataframe(df_in.head(5), use_container_width=True, height=160)

            phys_batch = UnifiedSemanticPhysics(hardware_capacity_gb=batch_gpu)
            results = []
            for _, row in df_in.iterrows():
                _E_n    = float(row.get("E_n",    1.0))
                _U_n    = float(row.get("U_n",    0.0))
                _E_next = float(row.get("E_next", max(0.0, _E_n - _U_n)))
                _n_n    = float(row.get("n_n", row.get("support", 100.0)))
                _d_n    = float(row.get("d_n", row.get("demand",  100.0)))
                _y_n    = float(row.get("y_n", row.get("observable", 0.5)))
                _recon  = float(row.get("recon", row.get("reconstruction", _y_n)))
                _toks   = float(row.get("tokens", row.get("prompt_tokens", 0.0)))

                _RLE = rle_n(_E_next, _U_n, _E_n)
                _LTP = ltp_n(max(0.01, _n_n), max(0.01, _d_n))
                _RSR = 1.0 - discrepancy_01(_y_n, _recon)
                _Sn  = stability_scalar(_RSR, _LTP, _RLE)
                _ps  = phys_batch.compute(s_n=_Sn, stm_load=_U_n, ltp=_LTP, rle=_RLE,
                                          prompt_tokens=_toks)
                _diag = diagnostic_step(_RSR, _LTP, _RLE)

                results.append({
                    "RLE": round(_RLE, 4), "LTP": round(_LTP, 4),
                    "RSR": round(_RSR, 4), "S_n": round(_Sn, 4),
                    "Λ_floor": round(_ps.lambda_floor, 4),
                    "λ_mismatch": round(_ps.lambda_mismatch, 4),
                    "F_realized": round(_ps.realized_force, 4),
                    "descent": _ps.kernel_descent,
                    "action": _diag.action,
                })

            df_out = pd.concat([df_in.reset_index(drop=True),
                                pd.DataFrame(results)], axis=1)

            st.markdown("---")
            st.markdown(f"**Results — {len(df_out)} rows computed**")

            # Color-code S_n in table
            def color_sn(v):
                c = sn_color(v) if isinstance(v, float) else "#c8d8f0"
                return f"color: {c}; font-weight: 600"

            styled = df_out.style.applymap(color_sn, subset=["S_n"])
            st.dataframe(styled, use_container_width=True, height=350)

            # S_n trend chart
            fig_batch = go.Figure()
            fig_batch.add_trace(go.Scatter(
                y=df_out["S_n"].tolist(), mode="lines+markers",
                line=dict(color="#00d4ff", width=2),
                marker=dict(size=4, color=[sn_color(v) for v in df_out["S_n"]]),
                name="S_n"
            ))
            fig_batch.add_hline(y=1.0, line=dict(color="#4af5b040", dash="dot"))
            fig_batch.add_hline(y=0.8, line=dict(color="#ffaa0040", dash="dot"))
            fig_batch.update_layout(
                height=220, title="S_n across batch",
                paper_bgcolor="#080b14", plot_bgcolor="#080b14",
                xaxis=dict(gridcolor="#1a2540", color="#3a5a84"),
                yaxis=dict(gridcolor="#1a2540", color="#3a5a84", range=[0, 1.05]),
                title_font=dict(color="#4a7aaa", size=12),
                margin=dict(t=40, b=30, l=40, r=20),
            )
            st.plotly_chart(fig_batch, use_container_width=True, key="batch_chart")

            # Download
            csv_bytes = df_out.to_csv(index=False).encode()
            st.download_button("⬇ Download Results CSV", csv_bytes,
                               file_name="rid_batch_results.csv", mime="text/csv",
                               use_container_width=True)

        except Exception as e:
            st.error(f"Import error: {e}")

    else:
        # Show sample template
        sample = pd.DataFrame([
            {"E_n": 1.0, "U_n": 0.02, "E_next": 0.98, "n_n": 100, "d_n": 100, "y_n": 0.5, "recon": 0.5, "tokens": 200},
            {"E_n": 1.0, "U_n": 0.05, "E_next": 0.95, "n_n": 80,  "d_n": 100, "y_n": 0.5, "recon": 0.6, "tokens": 400},
            {"E_n": 1.0, "U_n": 0.10, "E_next": 0.90, "n_n": 60,  "d_n": 100, "y_n": 0.7, "recon": 0.5, "tokens": 800},
        ])
        st.markdown("**Example CSV format:**")
        st.dataframe(sample, use_container_width=True, height=130)
        csv_template = sample.to_csv(index=False).encode()
        st.download_button("⬇ Download Template CSV", csv_template,
                           file_name="rid_template.csv", mime="text/csv")


# ── TAB 3: REFERENCE ─────────────────────────────────────────────────────────
with tab_ref:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Framework Formulas")
        for formula, desc, src in [
            ("RLE_n = (E_next − U_n) / E_n",    "Recursive Load Efficiency — remaining memory fraction", "RLE Axioms PDF"),
            ("LTP_n = min(1, n_n / d_n)",         "Layer Transition Principle — structure meets demand",    "LTP Canonical Spec"),
            ("RSR_n = 1 − D(y_n, recon_n)",       "Recursive State Reconstruction — identity continuity",  "RSR PDF"),
            ("S_n = RSR × LTP × RLE",             "Master stability scalar — product of all three axes",   "Canonical Spec"),
            ("Λ_floor = T_c / T_h = 1/VRAM",    "Irreducible second-law heat loss — hardware floor",     "Semantic Physics PDF"),
            ("F_raw = mass × S_n",                "Newtonian output force — S_n acts as acceleration",     "Semantic Physics PDF"),
            ("F_real = F_raw − friction − loss",  "Realized force — what actually reaches token output",   "Semantic Physics PDF"),
        ]:
            st.markdown(f"""
            <div style="background:#0a111e;border:1px solid #152240;border-radius:8px;
                        padding:12px 14px;margin-bottom:8px">
              <code style="color:#4af5b0;font-size:0.88rem">{formula}</code>
              <div style="color:#6a8aaa;font-size:0.72rem;margin-top:5px">{desc}</div>
              <div style="color:#2a4060;font-size:0.65rem;margin-top:2px">Source: {src}</div>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("### Diagnostic Actions")
        for action, desc, color in [
            ("continue",          "S_n = 1.0 — all axes nominal",                              "#4af5b0"),
            ("intervene_rle",     "RLE < 1.0 — memory/load pressure detected",                  "#00d4ff"),
            ("intervene_rsr",     "RSR < 0.9 — identity drift — state reconstruction failing",  "#ffaa00"),
            ("check_ltp",         "LTP < 1.0 — structural demand exceeds capacity",              "#ff8844"),
            ("mandatory_descent", "S_n critically low — complexity reduction required",          "#ff5555"),
        ]:
            st.markdown(f"""
            <div style="background:#0a111e;border-left:3px solid {color};border-radius:0 8px 8px 0;
                        padding:10px 14px;margin-bottom:8px">
              <code style="color:{color};font-size:0.82rem">{action.upper().replace('_',' ')}</code>
              <div style="color:#6a8aaa;font-size:0.72rem;margin-top:4px">{desc}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("### GPU capacity floors")
        gpu_table = pd.DataFrame([
            {"GPU": "RTX 3060 Ti 8GB",  "Λ_floor": "12.50%", "Efficiency@1200T": "85.2%"},
            {"GPU": "RTX 4080 16GB",    "Λ_floor": "6.25%",  "Efficiency@1200T": "91.8%"},
            {"GPU": "RTX 4090 24GB",    "Λ_floor": "4.17%",  "Efficiency@1200T": "94.0%"},
            {"GPU": "H100 80GB",        "Λ_floor": "1.25%",  "Efficiency@1200T": "97.1%"},
        ])
        st.dataframe(gpu_table, use_container_width=True, hide_index=True, height=168)


