
from __future__ import annotations

from pathlib import Path
import base64
import html

import plotly.graph_objects as go
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
LOGO_PATH = BASE_DIR / "assets" / "hhu_research_badge.png"


def _logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def inject_research_theme() -> None:
    css = """
    <style>
    :root {
        --hhu-primary: #0a4f8c;
        --hhu-secondary: #0e91aa;
        --hhu-deep: #06365f;
        --hhu-bg: #edf4f8;
        --hhu-card: rgba(255,255,255,.97);
        --hhu-line: #d2e1eb;
        --hhu-text: #17324b;
        --hhu-muted: #667d90;
        --hhu-success: #218c60;
        --hhu-warning: #d99a00;
        --hhu-danger: #ca4545;
    }

    html, body, [class*="css"] {
        font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
    }

    .stApp {
        color: var(--hhu-text);
        background:
            linear-gradient(rgba(245,249,252,.94), rgba(237,244,248,.96)),
            linear-gradient(90deg, rgba(21,96,140,.045) 1px, transparent 1px),
            linear-gradient(rgba(21,96,140,.045) 1px, transparent 1px);
        background-size: auto, 32px 32px, 32px 32px;
    }

    [data-testid="stHeader"] {
        background: rgba(255,255,255,.82);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(207,223,233,.8);
    }

    [data-testid="stAppViewContainer"] > .main {
        background:
            radial-gradient(circle at 88% 10%, rgba(16,158,178,.07), transparent 24%),
            radial-gradient(circle at 12% 86%, rgba(10,79,140,.065), transparent 28%);
    }

    .block-container {
        max-width: 1550px;
        padding-top: 1.3rem;
        padding-bottom: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(rgba(4,48,84,.97), rgba(6,91,111,.96)),
            linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px),
            linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px);
        background-size: auto, 26px 26px, 26px 26px;
        border-right: 1px solid rgba(255,255,255,.10);
        box-shadow: 8px 0 28px rgba(7,53,84,.14);
    }

    [data-testid="stSidebar"] * {
        color: #ffffff;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption {
        color: rgba(235,247,251,.72) !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] {
        background: transparent !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
        padding: 3px !important;
        background: transparent !important;
        border: 0 !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        min-height: 43px !important;
        display: flex !important;
        align-items: center !important;
        padding: 8px 10px !important;
        border-radius: 11px !important;
        border: 1px solid rgba(255,255,255,.075) !important;
        background: rgba(255,255,255,.045) !important;
        transition: .18s ease !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label p {
        color: rgba(245,252,255,.92) !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(20,190,210,.14) !important;
        border-color: rgba(53,214,225,.25) !important;
        transform: translateX(2px);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: inherit;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    h1, h2, h3 {
        color: #123e63;
        letter-spacing: .15px;
    }
    h1 {
        font-size: 1.85rem !important;
        margin-bottom: .25rem !important;
    }

    h2 {
        font-size: 1.35rem !important;
    }

    h3 {
        font-size: 1.08rem !important;
    }

    .hhu-login-wrap {
        margin: 1.2rem auto 1.4rem;
        max-width: 880px;
        display: grid;
        grid-template-columns: 1.08fr .92fr;
        border: 1px solid #cfdee8;
        border-radius: 24px;
        overflow: hidden;
        box-shadow: 0 26px 74px rgba(7,65,105,.20);
        background: #fff;
    }

    .hhu-login-intro {
        min-height: 390px;
        padding: 42px;
        position: relative;
        overflow: hidden;
        color: white;
        background:
            radial-gradient(circle at 82% 18%, rgba(72,207,217,.22), transparent 27%),
            linear-gradient(145deg,#06355f,#0a5a8f 58%,#0e879e);
    }

    .hhu-login-intro:before,
    .hhu-login-intro:after {
        content: "";
        position: absolute;
        border: 1px solid rgba(255,255,255,.15);
        border-radius: 50%;
    }

    .hhu-login-intro:before {
        width: 360px; height: 360px; right: -150px; top: -140px;
    }

    .hhu-login-intro:after {
        width: 220px; height: 220px; left: -80px; bottom: -90px;
    }

    .hhu-login-form-shell {
        padding: 38px 34px 16px;
        background: linear-gradient(180deg,#fff,#f8fbfd);
        border: 1px solid #d4e2eb;
        border-radius: 18px;
        box-shadow: 0 16px 44px rgba(15,72,109,.10);
    }

    .hhu-logo-row {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .hhu-logo-row img {
        width: 64px; height: 64px;
        background: white;
        border-radius: 50%;
        padding: 3px;
        box-shadow: 0 10px 26px rgba(0,0,0,.18);
    }

    .hhu-logo-row strong {
        display:block; font-size: 20px; letter-spacing: 2px;
    }

    .hhu-logo-row span {
        display:block; margin-top: 4px; font-size: 10px;
        letter-spacing: 1.5px; color: rgba(255,255,255,.72);
    }

    .hhu-login-title {
        position: relative;
        z-index: 1;
        margin-top: 36px;
        font-size: 31px;
        line-height: 1.35;
        font-weight: 800;
    }

    .hhu-login-desc {
        position: relative;
        z-index: 1;
        margin-top: 15px;
        color: rgba(255,255,255,.82);
        font-size: 14px;
        line-height: 1.85;
    }

    .hhu-sidebar-brand {
        padding: 8px 4px 18px;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,.13);
    }

    .hhu-sidebar-brand-row {
        display: flex;
        gap: 11px;
        align-items: center;
    }

    .hhu-sidebar-brand img {
        width: 50px;
        height: 50px;
        padding: 2px;
        border-radius: 50%;
        background: white;
        box-shadow: 0 8px 20px rgba(0,0,0,.18);
    }

    .hhu-sidebar-brand strong {
        display: block;
        font-size: 14px;
        line-height: 1.55;
        color: white;
    }

    .hhu-sidebar-brand small {
        display: block;
        margin-top: 3px;
        color: rgba(235,247,251,.67);
        font-size: 10px;
        letter-spacing: .3px;
    }

    .research-page-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 18px;
    }

    .research-page-title {
        display: flex;
        gap: 13px;
        align-items: flex-start;
    }

    .research-title-dot {
        margin-top: 7px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--hhu-secondary);
        box-shadow: 0 0 0 7px rgba(14,145,170,.11),
                    0 0 18px rgba(14,145,170,.35);
        flex: none;
    }

    .research-page-title h1 {
        margin: 0 !important;
    }

    .research-page-subtitle {
        margin-top: 6px;
        color: var(--hhu-muted);
        font-size: 13px;
    }

    .research-status {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        min-height: 34px;
        padding: 0 13px;
        border: 1px solid #cce5df;
        border-radius: 999px;
        color: var(--hhu-success);
        background: linear-gradient(90deg,#edf8f4,#f2fbf8);
        font-size: 12px;
        font-weight: 700;
        white-space: nowrap;
    }

    .research-status i {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--hhu-success);
        box-shadow: 0 0 0 4px rgba(33,140,96,.10);
    }

    .research-banner {
        margin: 4px 0 18px;
        padding: 12px 15px;
        border: 1px solid #c9e1eb;
        border-radius: 12px;
        color: #315f7d;
        background: linear-gradient(90deg,#edf7ff,#eefafa);
        box-shadow: inset 4px 0 0 var(--hhu-secondary);
        font-size: 13px;
        line-height: 1.65;
    }

    .metric-card {
        min-height: 126px;
        position: relative;
        overflow: hidden;
        padding: 17px;
        border: 1px solid #d1e1ea;
        border-radius: 16px;
        background: linear-gradient(180deg,rgba(255,255,255,.99),rgba(248,252,254,.97));
        box-shadow: 0 9px 25px rgba(19,73,111,.075);
        transition: transform .2s ease, box-shadow .2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 14px 32px rgba(19,73,111,.11);
    }

    .metric-card:before {
        content:"";
        position:absolute;left:0;right:0;top:0;height:3px;
        background: linear-gradient(90deg,var(--accent1,#0a4f8c),var(--accent2,#13a6b5));
    }

    .metric-card:after {
        content:"";
        position:absolute;
        width:92px;height:92px;border-radius:50%;
        right:-34px;top:-30px;
        background: radial-gradient(circle,rgba(26,146,173,.11),rgba(26,146,173,0));
    }

    .metric-top {
        display:flex;align-items:center;justify-content:space-between;gap:8px;
    }

    .metric-icon {
        width:31px;height:31px;border-radius:9px;
        display:grid;place-items:center;
        color:white;font-size:16px;font-weight:800;
        background:linear-gradient(135deg,var(--accent1,#0a4f8c),var(--accent2,#13a6b5));
        box-shadow:0 7px 16px rgba(10,79,140,.18);
    }

    .metric-label {
        color: var(--hhu-muted);
        font-size: 12px;
    }

    .metric-value {
        margin-top: 10px;
        color: #123e63;
        font-size: 28px;
        line-height: 1;
        font-weight: 800;
        letter-spacing: -.5px;
    }

    .metric-note {
        margin-top: 7px;
        color: #7890a1;
        font-size: 11px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: #d1e1ea !important;
        border-radius: 16px !important;
        background: rgba(255,255,255,.96);
        box-shadow: 0 9px 25px rgba(19,73,111,.065);
    }

    div[data-testid="stMetric"] {
        border: 1px solid #d2e1eb;
        border-radius: 14px;
        padding: 14px 16px;
        background: linear-gradient(180deg,#fff,#f8fcfe);
        box-shadow: 0 8px 22px rgba(24,74,116,.065);
    }

    div[data-testid="stMetricLabel"] {
        color: var(--hhu-muted);
    }

    div[data-testid="stMetricValue"] {
        color: #123e63;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        min-height: 40px;
        border-radius: 10px;
        border: 1px solid #c8dce8;
        font-weight: 700;
        transition: .18s ease;
    }

    [data-testid="stSidebar"] button[kind="secondary"],
    [data-testid="stSidebar"] [data-testid^="stBaseButton-secondary"] {
        background-color: #0a4f8c !important;
        background-image: linear-gradient(135deg,#0a4f8c,#0e91aa) !important;
        color: white !important;
        border: 1px solid #0e91aa !important;
        box-shadow: 0 7px 17px rgba(10,79,140,.18) !important;
    }

    [data-testid="stSidebar"] button[kind="secondary"]:hover,
    [data-testid="stSidebar"] [data-testid^="stBaseButton-secondary"]:hover {
        transform: translateY(-1px);
        background-color: #0e91aa !important;
        background-image: linear-gradient(135deg,#0e91aa,#0a4f8c) !important;
        border-color: #0a4f8c !important;
        color: white !important;
    }

    [data-testid="stSidebar"] button[kind="primary"]:last-of-type,
    [data-testid="stSidebar"] [data-testid^="stBaseButton-primary"]:last-of-type {
        background-color: #16c7d2 !important;
        background-image: none !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(22,199,210,.2) !important;
    }

    [data-testid="stSidebar"] button[kind="primary"]:last-of-type:hover,
    [data-testid="stSidebar"] [data-testid^="stBaseButton-primary"]:last-of-type:hover {
        transform: translateY(-1px);
        background-color: #12b0bb !important;
        background-image: none !important;
        border-color: #12b0bb !important;
        color: white !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        border-color: #0e91aa;
        color: #0a4f8c;
    }

    button[kind="primary"],
    button[kind="secondary"],
    [data-testid^="stBaseButton-primary"],
    [data-testid^="stBaseButton-secondary"],
    .stFormSubmitButton > button {
        color: white !important;
        border: none !important;
        background: linear-gradient(135deg,#0a4f8c,#0e91aa) !important;
        background-color: #0a4f8c !important;
        box-shadow: 0 7px 17px rgba(10,79,140,.19) !important;
    }

    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div,
    [data-baseweb="textarea"] > div {
        border-radius: 10px;
        border-color: #cfdfe9;
        background: rgba(255,255,255,.96);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #d2e1eb;
        border-radius: 13px;
        overflow: hidden;
        box-shadow: 0 8px 22px rgba(24,74,116,.055);
    }

    [data-testid="stFileUploader"] {
        padding: 10px;
        border: 1px dashed #afcad9;
        border-radius: 14px;
        background:
            linear-gradient(rgba(249,253,255,.96),rgba(244,250,253,.96)),
            repeating-linear-gradient(135deg,transparent 0 12px,rgba(25,129,169,.035) 12px 24px);
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid #cfe0e9;
    }

    .research-section-label {
        display:flex;
        align-items:center;
        gap:8px;
        margin: 5px 0 11px;
        color:#204f6e;
        font-size:15px;
        font-weight:800;
    }

    .research-section-label:before {
        content:"";
        width:4px;height:18px;border-radius:999px;
        background:linear-gradient(#0a4f8c,#0e91aa);
    }

    .research-footer {
        display:flex;
        justify-content:space-between;
        gap:20px;
        margin-top:28px;
        padding:14px 4px 2px;
        border-top:1px solid rgba(195,215,227,.78);
        color:#74899a;
        font-size:11px;
    }


    @media (max-width: 900px) {
        /* 1. 解决手机端内容被侧边栏遮挡、内边距过窄的问题 */
        .block-container {
            padding: 1rem !important;         /* 手机端缩小内边距，防止地图或图表被截断 */
            max-width: 100% !important;
        }
        
        /* 2. 移动端侧边栏宽度调整（避免侧边栏过宽遮挡主内容） */
        [data-testid="stSidebar"] {
            width: min(82vw, 300px) !important;
            min-width: min(82vw, 300px) !important;
            max-width: 300px !important;
        }

        /* 3. 移动端侧边栏内部排版优化 */
        [data-testid="stSidebar"] .hhu-sidebar-brand-row {
            flex-wrap: wrap;                  /* Logo和文字如果太挤，允许换行 */
            gap: 8px;
        }
        [data-testid="stSidebar"] .hhu-sidebar-brand strong {
            font-size: 12px !important;       /* 侧边栏主标题字体缩小 */
        }
        [data-testid="stSidebar"] .hhu-sidebar-brand small {
            font-size: 9px !important;        /* 侧边栏副标题字体缩小 */
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 6px 10px !important;     /* 侧边栏菜单项间距缩小，防止密集 */
            font-size: 13px !important;
        }

        /* 4. 移动端登录界面适配 */
        .hhu-login-wrap {
            grid-template-columns: 1fr;        /* 登录页左图右表单 变成 上下结构 */
            margin: 0.5rem;
            max-width: 100%;
        }
        .hhu-login-intro {
            min-height: 200px !important;      /* 登录页左侧背景图高度缩小 */
            padding: 25px !important;
        }
        .hhu-login-form-shell {
            padding: 20px !important;          /* 登录表单的内边距缩小，防止撑出屏幕 */
        }

        /* 5. 按钮和页面头部在移动端不重叠 */
        .research-page-header {
            flex-direction: column;
            align-items: flex-start !important;
            gap: 10px !important;
        }
        .research-status {
            white-space: normal;               /* 允许右上角状态标签换行 */
        }

        /* 6. 避免底部文字换行不对齐 */
        .research-footer {
            flex-direction: column !important;
            gap: 6px !important;
            text-align: center !important;
        }
    }

    /* ===== V1.0 全平台统一深色调度大屏主题 ===== */
    :root{
        --hhu-primary:#139ac7;--hhu-secondary:#20d0ef;--hhu-deep:#07131a;--hhu-bg:#071017;
        --hhu-card:rgba(16,35,45,.96);--hhu-line:rgba(62,153,183,.24);--hhu-text:#eaf7fb;--hhu-muted:#8eb0bd;
        --hhu-success:#3edc9b;--hhu-warning:#ffab42;--hhu-danger:#ff6262;
    }
    html,body,[class*="css"]{font-size:15px;color:var(--hhu-text)}
    .stApp{color:var(--hhu-text);background:radial-gradient(circle at 70% 9%,rgba(22,95,119,.13),transparent 30%),linear-gradient(155deg,#05090d 0%,#09141b 48%,#071018 100%) !important;background-size:auto !important}
    [data-testid="stHeader"]{background:rgba(5,10,14,.90) !important;backdrop-filter:blur(14px);border-bottom:1px solid rgba(61,160,191,.19)}
    [data-testid="stAppViewContainer"] > .main{background:radial-gradient(circle at 12% 86%,rgba(25,89,112,.08),transparent 30%),radial-gradient(circle at 88% 14%,rgba(255,151,46,.025),transparent 19%) !important}
    .block-container{max-width:1600px;padding-top:1.25rem;padding-left:2rem;padding-right:2rem}
    h1,h2,h3,h4,h5,h6{color:#eefaff !important}h1{font-size:2.05rem !important}h2{font-size:1.5rem !important}h3{font-size:1.18rem !important}
    [data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{color:#c7dde5;font-size:14px;line-height:1.75}
    label,[data-testid="stWidgetLabel"] p{color:#c9e1e9 !important;font-size:14px !important}.stCaption,[data-testid="stCaptionContainer"]{color:#7ea4b4 !important;font-size:12px !important}

    [data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(7,17,23,.99),rgba(10,31,40,.98)) !important;border-right:1px solid rgba(60,163,195,.22);box-shadow:8px 0 28px rgba(0,0,0,.25)}
    [data-testid="stSidebar"] *{color:#eefaff}.hhu-sidebar-brand strong{font-size:15px}.hhu-sidebar-brand small{font-size:11px;color:#83aebb}
    [data-testid="stSidebar"] [role="radiogroup"]{gap:7px !important} [data-testid="stSidebar"] [role="radiogroup"] label{background:rgba(16,39,50,.78) !important}
    [data-testid="stSidebar"] [role="radiogroup"] label{min-height:46px !important;padding:9px 11px !important;border-color:rgba(58,150,179,.18) !important;background:rgba(14,34,44,.82) !important}
    [data-testid="stSidebar"] [role="radiogroup"] label p{font-size:15px !important;font-weight:700 !important;color:#dceff5 !important}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(20,89,111,.52) !important;border-color:rgba(39,201,235,.34) !important}

    .research-page-header{margin-bottom:20px;padding:14px 16px;border:1px solid rgba(63,157,188,.20);border-radius:14px;background:linear-gradient(90deg,rgba(15,34,44,.92),rgba(9,25,33,.82));box-shadow:0 10px 26px rgba(0,0,0,.16)}
    .research-title-dot{background:#1ed5f3;box-shadow:0 0 0 7px rgba(30,213,243,.10),0 0 18px rgba(30,213,243,.32)}
    .research-page-title h1{font-size:2rem !important;color:#f2fbff !important}.research-page-subtitle{font-size:14px;color:#8fb1bf}
    .research-status{font-size:13px;color:#73e5ad;background:rgba(20,58,48,.50);border-color:rgba(62,214,155,.25)}.research-status i{background:#40df9d}
    .research-banner{font-size:14px;color:#bcd7e1;background:linear-gradient(90deg,rgba(13,38,49,.96),rgba(15,45,52,.94));border-color:rgba(61,163,193,.23);box-shadow:inset 4px 0 0 #1cccf1}

    .metric-card{min-height:132px;padding:18px;border-color:rgba(61,153,182,.22);background:linear-gradient(180deg,rgba(17,38,48,.96),rgba(10,25,33,.97));box-shadow:0 10px 26px rgba(0,0,0,.19)}.metric-card:hover{box-shadow:0 15px 34px rgba(0,0,0,.27)}
    .metric-label{font-size:13px;color:#8fb0bd}.metric-value{font-size:31px;color:#5adfff}.metric-note{font-size:12px;color:#769dac}.metric-icon{background:linear-gradient(135deg,#1182ad,#22cbe8)}
    div[data-testid="stVerticalBlockBorderWrapper"] > div{border-color:rgba(61,153,182,.22) !important;background:rgba(14,32,41,.95) !important;box-shadow:0 9px 25px rgba(0,0,0,.18)}
    div[data-testid="stMetric"]{border-color:rgba(61,153,182,.22);background:linear-gradient(180deg,rgba(17,38,48,.96),rgba(10,25,33,.97));box-shadow:0 8px 22px rgba(0,0,0,.18)}
    div[data-testid="stMetricLabel"]{color:#8eb0bd !important;font-size:13px !important}div[data-testid="stMetricValue"]{color:#5adfff !important;font-size:30px !important}div[data-testid="stMetricDelta"]{font-size:12px !important}

    .stButton>button,.stDownloadButton>button,.stFormSubmitButton>button,[data-testid^="stBaseButton"]{font-size:14px !important;min-height:42px;border-radius:9px !important;border:1px solid rgba(55,171,204,.29) !important;background:linear-gradient(135deg,rgba(17,81,105,.98),rgba(12,54,72,.98)) !important;color:#eefaff !important;box-shadow:0 7px 17px rgba(0,0,0,.18) !important}
    .stButton>button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover,[data-testid^="stBaseButton"]:hover{border-color:#41daf7 !important;background:linear-gradient(135deg,#126f8f,#0d4c64) !important;color:#fff !important}
    [data-testid="stSidebar"] button[kind="primary"]:last-of-type,[data-testid="stSidebar"] [data-testid^="stBaseButton-primary"]:last-of-type{background:linear-gradient(135deg,#d86e25,#f49a37) !important;border-color:rgba(255,181,89,.45) !important}

    [data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]>div{border-color:rgba(72,153,177,.26) !important;background:rgba(10,28,37,.96) !important;color:#eaf7fb !important}
    input,textarea,[data-baseweb="select"] input{color:#eaf7fb !important}.stNumberInput button{background:rgba(18,50,64,.85) !important;color:#eaf7fb !important}
    [data-baseweb="popover"],[role="listbox"]{background:#0c2029 !important;color:#eaf7fb !important}
    [role="option"]{color:#d9edf4 !important}[role="option"]:hover{background:#123746 !important}
    [data-testid="stTabs"] [data-baseweb="tab-list"]{gap:7px;background:rgba(8,22,29,.72);border-radius:10px;padding:5px}[data-testid="stTabs"] [data-baseweb="tab"]{font-size:14px;color:#a9c9d4;background:rgba(15,38,49,.76);border-radius:8px}[data-testid="stTabs"] [aria-selected="true"]{color:#fff !important;background:linear-gradient(90deg,#11688a,#128caf) !important}
    [data-testid="stDataFrame"]{border-color:rgba(62,153,182,.22);background:#0a1b23;box-shadow:0 8px 22px rgba(0,0,0,.17)}
    [data-testid="stFileUploader"]{border-color:rgba(76,166,193,.35);background:repeating-linear-gradient(135deg,rgba(12,31,40,.96) 0 12px,rgba(16,39,49,.96) 12px 24px)}
    [data-testid="stAlert"]{border-color:rgba(69,157,184,.25);background:rgba(14,35,44,.95);color:#dcecf2}
    .research-section-label{font-size:17px;color:#eefaff}.research-section-label:before{background:linear-gradient(#17d7ff,#2d75ff)}
    .research-footer{border-top-color:rgba(61,145,174,.20);color:#6f98a8;font-size:12px}

    /* Login keeps the same dark command-center language. */
    .hhu-login-wrap{border-color:rgba(63,158,188,.22);background:#0c2029;box-shadow:0 26px 74px rgba(0,0,0,.34)}.hhu-login-intro{background:radial-gradient(circle at 82% 18%,rgba(31,160,193,.20),transparent 28%),linear-gradient(145deg,#07141b,#0d3240 58%,#0d5366)}.hhu-login-form-shell{background:linear-gradient(180deg,#102a35,#0b1d25);border-color:rgba(64,156,184,.24)}

    @media(max-width:900px){.block-container{padding:1rem !important}.research-page-title h1{font-size:1.7rem !important}[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:14px !important}}


    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def login_brand_panel() -> None:
    logo = _logo_base64()
    st.markdown(
        f"""
        <div class="hhu-login-intro">
          <div class="hhu-logo-row">
            <img src="data:image/png;base64,{logo}" alt="HHU research badge">
            <div>
              <strong>河海大学</strong>
              <span>HOHAI UNIVERSITY</span>
            </div>
          </div>
          <div class="hhu-login-title">水网工程水力调控<br>智能平台</div>
          <div class="hhu-login-desc">
            面向平原河网的水情数据管理、河网GIS可视化、水动力预测、
            多目标调度、预警分析与科研决策支持一体化平台。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand(version: str) -> None:
    logo = _logo_base64()
    st.markdown(
        f"""
        <div class="hhu-sidebar-brand">
          <div class="hhu-sidebar-brand-row">
            <img src="data:image/png;base64,{logo}" alt="HHU research badge">
            <div>
              <strong>水网工程水力调控<br>智能平台</strong>
              <small>河海大学 · {html.escape(version)}</small>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="research-page-header">
          <div class="research-page-title">
            <span class="research-title-dot"></span>
            <div>
              <h1>{html.escape(title)}</h1>
              <div class="research-page-subtitle">{html.escape(subtitle)}</div>
            </div>
          </div>
          <div class="research-status"><i></i>系统运行正常</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def research_banner(text: str) -> None:
    st.markdown(
        f'<div class="research-banner">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str | int | float,
    icon: str,
    note: str = "",
    accent1: str = "#0a4f8c",
    accent2: str = "#13a6b5",
) -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--accent1:{accent1};--accent2:{accent2};">
          <div class="metric-top">
            <div class="metric-icon">{html.escape(icon)}</div>
            <div class="metric-label">{html.escape(label)}</div>
          </div>
          <div class="metric-value">{html.escape(str(value))}</div>
          <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(
        f'<div class="research-section-label">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def research_footer(version: str) -> None:
    st.markdown(
        f"""
        <div class="research-footer">
          <span>河海大学 · 水网工程水力调控智能平台</span>
          <span>{html.escape(version)} · 数据与模型结果仅用于研究和功能验证</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_plotly_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=18, t=34, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,24,32,.82)",
        font=dict(family="Microsoft YaHei, PingFang SC, Arial", color="#c9e3ec", size=13),
        colorway=["#23cfea", "#2c7dff", "#41d89a", "#ff9f32", "#8b78ff"],
        hoverlabel=dict(bgcolor="#0b2029", font_color="#eefaff", bordercolor="#2ac8eb"),
        legend=dict(bgcolor="rgba(8,25,33,.78)", bordercolor="rgba(66,158,187,.25)", borderwidth=1, font=dict(color="#c9e3ec")),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(92,158,181,.12)", zeroline=False, linecolor="rgba(103,161,181,.27)", tickfont=dict(color="#9fc0cc",size=12), title_font=dict(color="#c9e3ec",size=13))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(92,158,181,.12)", zeroline=False, linecolor="rgba(103,161,181,.27)", tickfont=dict(color="#9fc0cc",size=12), title_font=dict(color="#c9e3ec",size=13))
    return fig

