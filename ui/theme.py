from __future__ import annotations

import base64
import html
from pathlib import Path
import re

import plotly.graph_objects as go
import streamlit as st

from core.config import DEMO_MODE, SEED_DEMO_DATA

BASE_DIR = Path(__file__).resolve().parents[1]
LOGO_PATH = BASE_DIR / "assets" / "hhu_research_badge.png"


def _logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def inject_research_theme() -> None:
    """Shared visual system for the portal and authenticated workspace."""
    st.markdown(
        """<style>
        :root{--hhu-bg:#081321;--hhu-card:#101f31;--hhu-line:#25384c;--hhu-text:#edf4fa;--hhu-muted:#9baec0;--hhu-primary:#43d2b5;--hhu-secondary:#43d2b5;--hhu-gold:#d8bb80;--hhu-success:#57d8a8;--hhu-warning:#eac078;--hhu-danger:#f58c8c;}
        html,body,[class*="css"]{font-family:"Inter","PingFang SC","Microsoft YaHei",sans-serif;}
        .stApp{background:#081321 !important;color:var(--hhu-text);}
        [data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 70% 0,rgba(28,83,96,.12),transparent 45%),#081321;}
        [data-testid="stHeader"]{background:rgba(8,19,33,.94) !important;border-bottom:1px solid rgba(82,111,138,.18);backdrop-filter:blur(14px);}
        .block-container{max-width:1760px;padding:1.4rem 2.4rem 3rem;}
        h1,h2,h3,h4,h5,h6{color:#edf4fa !important;font-weight:650 !important;letter-spacing:-.025em;}
        h1{font-size:2rem !important;line-height:1.35 !important;}h2{font-size:1.45rem !important;}h3{font-size:1.1rem !important;}
        [data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{color:#becdd9;font-size:14px;line-height:1.85;}
        [data-testid="stCaptionContainer"] p,.stCaption{color:#92a7b9 !important;font-size:12px !important;line-height:1.7;}
        [data-testid="stWidgetLabel"] p,label{color:#bfcedb !important;}a{color:#62d6c1;}a:hover{color:#a8eee0;}
        #MainMenu,footer{visibility:hidden;}[data-testid="stAppDeployButton"],.stDeployButton{display:none!important;}
        [data-testid="stSidebar"]{background:#0c1929 !important;border-right:1px solid #203248;}
        [data-testid="stSidebar"] [role="radiogroup"]{display:flex !important;flex-direction:column !important;gap:5px !important;background:transparent !important;border:0 !important;padding:0 !important;}
        [data-testid="stSidebar"] [role="radiogroup"] label{min-height:43px;padding:8px 12px !important;border:1px solid transparent !important;border-radius:9px;background:transparent !important;transition:background .15s;}
        [data-testid="stSidebar"] [role="radiogroup"] label p{color:#b8cad9 !important;font-size:14px !important;font-weight:500 !important;}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#173247 !important;border-color:#2b525e !important;}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:#7de1cb !important;}
        [data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#13263a !important;}
        .hhu-sidebar-brand{padding:8px 0 24px;margin-bottom:14px;border-bottom:1px solid #23364b;}
        .hhu-sidebar-brand-row{display:flex;align-items:center;gap:12px;}
        .hhu-sidebar-brand img{width:44px;height:44px;border-radius:50%;background:#fff;padding:2px;}
        .hhu-sidebar-brand strong{display:block;color:#f1f6fb;font-size:15px;line-height:1.6;letter-spacing:.02em;}
        .hhu-sidebar-brand small{display:block;color:#8198ad;font-size:10px;margin-top:5px;}
        .research-page-header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin:8px 0 23px;}
        .research-page-title{display:flex;gap:13px;align-items:flex-start;}.research-title-dot{width:4px;height:30px;background:#49cdb3;border-radius:3px;margin-top:7px;flex:none;}
        .research-page-title h1{margin:0 !important;}.research-page-subtitle{color:#92a9bc;font-size:13px;margin-top:8px;line-height:1.75;max-width:900px;}
        .research-status{display:inline-flex;align-items:center;gap:8px;white-space:nowrap;border:1px solid #314559;background:#112337;color:#b1c8d7;border-radius:6px;padding:7px 10px;font-size:11px;margin-top:8px;}
        .research-status i{width:6px;height:6px;background:#d8bb80;border-radius:50%;}
        .research-banner{padding:12px 16px;margin:0 0 20px;border:1px solid #28444e;border-left:3px solid #4ab99f;border-radius:7px;background:#10292f;color:#b7d5d2;font-size:12px;line-height:1.8;}
        .metric-card{padding:19px 20px;min-height:122px;border:1px solid #263a50;border-radius:11px;background:#101f31;}
        .metric-top{display:flex;align-items:center;justify-content:space-between;gap:8px;}.metric-icon{color:#69d3c0;font-size:16px;}.metric-label{color:#9eb4c8;font-size:12px;}
        .metric-value{font-size:29px;font-weight:650;color:#f2f7fb;margin-top:10px;letter-spacing:-.04em;line-height:1.2;font-variant-numeric:tabular-nums;}.metric-note{color:#7e98ad;font-size:11px;margin-top:7px;}
        [data-testid="stMetric"]{padding:16px 18px;border:1px solid #273c51;border-radius:10px;background:#102033;box-shadow:none !important;}
        [data-testid="stMetricLabel"] p{color:#9eb2c5 !important;font-size:12px !important;}[data-testid="stMetricValue"]{color:#f1f6fb;font-size:1.8rem !important;letter-spacing:-.03em;}
        [data-testid="stMetricValue"] p{font-size:1.6rem!important;line-height:1.35!important;color:#f1f6fb!important;}
        [data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#263b50 !important;border-radius:11px !important;box-shadow:none !important;}
        [data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button{min-height:40px;border-radius:7px !important;border:1px solid #354e65 !important;background:#142b40 !important;color:#d8e6ef !important;box-shadow:none !important;font-weight:500;transition:background .15s,border-color .15s;}
        [data-testid="stButton"] button:hover,[data-testid="stDownloadButton"] button:hover,[data-testid="stFormSubmitButton"] button:hover{background:#1b3b4e !important;border-color:#5b9f9b !important;color:#f0fffb !important;}
        button[kind="primary"],[data-testid^="stBaseButton-primary"]{background:#48c7ac !important;border-color:#48c7ac !important;color:#06271f !important;font-weight:650 !important;}
        button[kind="primary"]:hover,[data-testid^="stBaseButton-primary"]:hover{background:#6bdcc2 !important;color:#06271f !important;}
        [data-testid="stButton"] button p,[data-testid="stDownloadButton"] button p,[data-testid="stFormSubmitButton"] button p{color:inherit !important;font-size:13px;line-height:1.5;}
        button:focus-visible,a:focus-visible{outline:2px solid #d8bb80 !important;outline-offset:3px;}
        [data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]>div{background:#0d1d2e !important;border-color:#32495f !important;border-radius:7px !important;color:#e6eff6 !important;}
        input,textarea,[data-baseweb="select"] input{color:#e6eff6 !important;}[data-baseweb="popover"],[role="listbox"]{background:#102237 !important;color:#dbe7f0 !important;}[role="option"]:hover{background:#1d3b4f !important;}
        [data-testid="stTabs"] [data-baseweb="tab-list"]{gap:14px;border-bottom:1px solid #263b50;background:transparent;}
        [data-testid="stTabs"] [data-baseweb="tab"]{padding:10px 4px;color:#9cb3c7;background:transparent;font-size:13px;}
        [data-testid="stTabs"] [aria-selected="true"]{color:#73dfc7 !important;background:transparent !important;}
        [data-testid="stDataFrame"]{border:1px solid #263c51;border-radius:9px;overflow:hidden;box-shadow:none !important;}
        [data-testid="stFileUploader"]{border:1px dashed #365166;border-radius:10px;padding:9px;background:#0e2031;}
        [data-testid="stAlert"]{border-radius:8px;border:1px solid #294352;background:#112738;color:#c9e0e8;}
        [data-testid="stExpander"]{border-color:#293d51 !important;border-radius:8px !important;}
        [data-testid="stChatMessage"]{border:1px solid #263e51;border-radius:12px;background:#102234;padding:18px;}
        [data-testid="stChatInput"]{border-color:#3b615f !important;border-radius:12px !important;background:#102638 !important;}
        .research-section-label{display:flex;align-items:center;gap:10px;color:#e0ebf4;font-size:15px;font-weight:600;margin:5px 0 13px;}
        .research-section-label:before{content:"";height:14px;width:3px;border-radius:3px;background:#d5ba83;}
        .research-footer{display:flex;justify-content:space-between;gap:20px;padding-top:18px;margin-top:32px;border-top:1px solid #23374c;color:#7892a7;font-size:11px;line-height:1.8;}
        .hhu-login-intro{padding:38px 32px;min-height:410px;border:1px solid #2a4659;border-radius:16px;background:radial-gradient(ellipse at 100% 0,rgba(61,147,139,.19),transparent 65%),#102a3a;}
        .hhu-logo-row{display:flex;gap:14px;align-items:center;}.hhu-logo-row img{width:56px;height:56px;background:#fff;border-radius:50%;padding:2px;}.hhu-logo-row strong{color:#f3f7fb;display:block;font-size:19px;letter-spacing:.1em;}.hhu-logo-row span{display:block;color:#8faebf;font-size:10px;letter-spacing:.16em;margin-top:4px;}
        .hhu-login-title{color:#f2f7fb;font-size:30px;font-weight:650;line-height:1.5;letter-spacing:-.03em;margin-top:40px;}.hhu-login-desc{color:#a8c1ce;font-size:14px;line-height:1.9;margin-top:20px;}.hhu-login-eyebrow{font-size:11px;color:#d8bb80;letter-spacing:.14em;margin-top:32px;}
        @media(max-width:950px){.block-container{padding:1.2rem !important;}.research-page-header{flex-direction:column;gap:4px;}.research-page-title h1{font-size:1.6rem !important;}.research-status{margin-left:17px;}.research-footer{flex-direction:column;gap:4px;}.hhu-login-intro{min-height:300px;padding:24px;}.hhu-login-title{font-size:25px;margin-top:25px;}}
        @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none !important;transition:none !important;scroll-behavior:auto !important;}}
        </style>""",
        unsafe_allow_html=True,
    )


def login_brand_panel() -> None:
    st.markdown(
        f'''<div class="hhu-login-intro"><div class="hhu-logo-row"><img src="data:image/png;base64,{_logo_base64()}" alt="河海大学校徽"><div><strong>河海大学</strong><span>HOHAI UNIVERSITY</span></div></div><div class="hhu-login-eyebrow">WATER NETWORK INTELLIGENCE</div><div class="hhu-login-title">从空间感知<br>到水网协同决策</div><div class="hhu-login-desc">在统一的专业工作台中浏览三维河网、管理水情资料、开展预测与调度，并向水知助手检索专业依据和操作指引。</div></div>''',
        unsafe_allow_html=True,
    )


def sidebar_brand(version: str) -> None:
    st.markdown(
        f'''<div class="hhu-sidebar-brand"><div class="hhu-sidebar-brand-row"><img src="data:image/png;base64,{_logo_base64()}" alt="河海大学校徽"><div><strong>水网智能工作台</strong><small>{html.escape(version)}</small></div></div></div>''',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    workspace = "演示工作区" if DEMO_MODE or SEED_DEMO_DATA else "业务工作区"
    st.markdown(
        f'''<div class="research-page-header"><div class="research-page-title"><span class="research-title-dot"></span><div><h1>{html.escape(title)}</h1><div class="research-page-subtitle">{html.escape(subtitle)}</div></div></div><div class="research-status"><i></i>{workspace}</div></div>''',
        unsafe_allow_html=True,
    )


def research_banner(text: str) -> None:
    st.markdown(f'<div class="research-banner">{html.escape(text)}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str | int | float, icon: str, note: str = "", accent1: str = "#43d2b5", accent2: str = "#d8bb80") -> None:
    color = accent1 if re.fullmatch(r"#[0-9a-fA-F]{3,8}", accent1) else "#43d2b5"
    st.markdown(
        f'''<div class="metric-card"><div class="metric-top"><div class="metric-label">{html.escape(label)}</div><div class="metric-icon" style="color:{color}">{html.escape(icon)}</div></div><div class="metric-value">{html.escape(str(value))}</div><div class="metric-note">{html.escape(note)}</div></div>''',
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(f'<div class="research-section-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def research_footer(version: str) -> None:
    note = "演示水情与模型结果用于功能验证" if DEMO_MODE or SEED_DEMO_DATA else "工程决策请结合实测数据与适用模型复核"
    st.markdown(
        f'<div class="research-footer"><span>河海大学 · 水网工程水力调控智能平台</span><span>{html.escape(version)} · {note}</span></div>',
        unsafe_allow_html=True,
    )


def style_plotly_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=20, r=18, t=36, b=24),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1e30",
        font=dict(family="Inter, PingFang SC, Microsoft YaHei, Arial", color="#c3d4e1", size=12),
        colorway=["#57cdb4", "#729ee8", "#d8bb80", "#a59cdb", "#ed9c92"],
        hoverlabel=dict(bgcolor="#142c40", font_color="#edf5fa", bordercolor="#4f9d92"),
        legend=dict(bgcolor="rgba(13,30,48,.86)", borderwidth=0, font=dict(color="#afc3d3")),
    )
    axis = dict(showgrid=True, gridcolor="rgba(110,141,167,.13)", zeroline=False, linecolor="#2c4258", tickfont=dict(color="#8ea8bc", size=11), title_font=dict(color="#bbcedc", size=12))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    fig.update_scenes(bgcolor="#0d1e30", xaxis=dict(gridcolor="#263c51", zerolinecolor="#324c61"), yaxis=dict(gridcolor="#263c51", zerolinecolor="#324c61"), zaxis=dict(gridcolor="#263c51", zerolinecolor="#324c61"))
    return fig

