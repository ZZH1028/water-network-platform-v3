from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from core.config import APP_NAME, APP_VERSION, BASE_DIR
from services.data_service import (
    get_dashboard_statistics,
    get_latest_data_time,
    get_latest_station_levels,
    get_rainfall_series,
)
from services.gis_service import get_gis_summary, load_river_sections
from ui.theme import style_plotly_figure


LOGO_PATH = BASE_DIR / "assets" / "hhu_logo.png"


def _logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def inject_public_site_theme() -> None:
    st.markdown(
        """
        <style>
        .public-shell {max-width: 1500px; margin: 0 auto;}
        .public-topbar {
            position:sticky; top:0; z-index:80; display:flex; align-items:center; justify-content:space-between; gap:20px;
            padding:10px 4px 12px; margin:-10px 0 8px; backdrop-filter:blur(18px);
            background:linear-gradient(180deg,rgba(237,244,248,.96),rgba(237,244,248,.75),rgba(237,244,248,0));
        }
        .public-brand {display:flex; align-items:center; gap:13px; min-width:0;}
        .public-brand img {width:54px; height:54px; object-fit:contain; background:#fff; border-radius:50%; padding:2px; box-shadow:0 8px 22px rgba(7,62,97,.15);}
        .public-brand-title {font-size:18px; font-weight:950; color:#0c3d63; letter-spacing:.15px;}
        .public-brand-sub {font-size:10px; color:#6c8397; letter-spacing:1.55px; margin-top:2px;}
        .public-version {display:inline-flex; align-items:center; gap:8px; padding:9px 13px; border-radius:999px; border:1px solid #c8dde8; background:rgba(255,255,255,.88); color:#416b82; font-size:11px; white-space:nowrap; box-shadow:0 8px 24px rgba(10,67,104,.06);}
        .public-version:before {content:""; width:7px; height:7px; border-radius:50%; background:#1ead75; box-shadow:0 0 0 4px rgba(30,173,117,.10);}
        div[data-testid="stRadio"] > div[role="radiogroup"] {gap:5px; flex-wrap:wrap; padding:5px; border:1px solid #cfdfE8; border-radius:15px; background:rgba(255,255,255,.88); box-shadow:0 10px 28px rgba(14,65,100,.07);}
        div[data-testid="stRadio"] > div[role="radiogroup"] label {background:transparent; border-radius:10px; padding:7px 11px; transition:.18s ease;}
        div[data-testid="stRadio"] > div[role="radiogroup"] label:hover {background:#eaf5fa; transform:translateY(-1px);}

        .public-hero {position:relative; overflow:hidden; min-height:540px; border-radius:32px; margin:17px 0 22px; color:#fff; background:linear-gradient(132deg,#032b52 0%,#064e7c 46%,#078394 100%); box-shadow:0 32px 82px rgba(5,55,89,.25);}
        .public-hero-grid {position:relative; z-index:2; display:grid; grid-template-columns:1.16fr .84fr; min-height:540px;}
        .public-hero-copy {padding:66px 24px 56px 60px;}
        .public-hero-kicker {font-size:11px; letter-spacing:2.8px; color:#9feff0; font-weight:900;}
        .public-hero h1 {color:#fff !important; font-size:50px !important; line-height:1.14; margin:18px 0 17px !important; max-width:760px; letter-spacing:-1.4px;}
        .public-hero-desc {max-width:760px; color:rgba(235,250,252,.86); font-size:15px; line-height:1.95;}
        .public-hero-tags {display:flex; flex-wrap:wrap; gap:9px; margin-top:28px;}
        .public-hero-tag {padding:8px 12px; border:1px solid rgba(255,255,255,.20); border-radius:999px; background:rgba(255,255,255,.08); color:#edfeff; font-size:11px; backdrop-filter:blur(8px);}
        .hero-live {display:flex; gap:18px; margin-top:30px; flex-wrap:wrap;}
        .hero-live-item {min-width:125px; padding-left:13px; border-left:2px solid rgba(132,239,237,.72);}
        .hero-live-item b {display:block; font-size:24px; color:#fff;}
        .hero-live-item span {display:block; color:rgba(225,246,249,.70); font-size:10px; margin-top:3px;}
        .public-hero-visual {position:relative; min-height:540px; overflow:hidden;}
        .hero-orbit {position:absolute; left:50%; top:50%; width:410px; height:410px; transform:translate(-46%,-50%); border:1px solid rgba(255,255,255,.18); border-radius:50%; box-shadow:0 0 0 58px rgba(255,255,255,.035),0 0 0 118px rgba(255,255,255,.018);}
        .hero-orbit:before,.hero-orbit:after {content:""; position:absolute; border-radius:50%; border:1px dashed rgba(154,239,238,.23);}
        .hero-orbit:before {inset:55px;} .hero-orbit:after {inset:115px;}
        .hero-map-card {position:absolute; width:330px; height:305px; left:48%; top:50%; transform:translate(-45%,-50%) rotate(-4deg); border-radius:28px; border:1px solid rgba(255,255,255,.20); background:linear-gradient(145deg,rgba(255,255,255,.16),rgba(255,255,255,.055)); backdrop-filter:blur(15px); box-shadow:0 30px 70px rgba(0,0,0,.18); overflow:hidden;}
        .hero-map-card:before {content:""; position:absolute; inset:0; background:linear-gradient(32deg,transparent 20%,rgba(140,238,239,.16) 21%,transparent 22%,transparent 44%,rgba(140,238,239,.20) 45%,transparent 46%,transparent 68%,rgba(140,238,239,.14) 69%,transparent 70%);}
        .river-line {position:absolute; height:4px; border-radius:8px; background:linear-gradient(90deg,rgba(113,231,239,.10),#8ceef0,rgba(113,231,239,.15)); box-shadow:0 0 18px rgba(114,234,239,.42); transform-origin:left center;}
        .r1 {width:260px; left:28px; top:75px; transform:rotate(21deg);} .r2 {width:245px; left:42px; top:185px; transform:rotate(-17deg);} .r3 {width:180px; left:94px; top:138px; transform:rotate(64deg);} .r4 {width:160px; left:90px; top:230px; transform:rotate(-48deg);} .r5 {width:125px; left:168px; top:110px; transform:rotate(-70deg);}
        .map-node {position:absolute; width:11px; height:11px; border-radius:50%; background:#ecffff; border:3px solid #20c3cc; box-shadow:0 0 0 6px rgba(32,195,204,.14),0 0 20px rgba(120,242,242,.72);}
        .n1 {left:70px;top:88px}.n2 {left:166px;top:117px}.n3 {left:245px;top:148px}.n4 {left:126px;top:201px}.n5 {left:230px;top:205px}.n6 {left:174px;top:255px}
        .hero-float {position:absolute; padding:10px 13px; border-radius:13px; background:rgba(3,47,78,.65); border:1px solid rgba(255,255,255,.16); backdrop-filter:blur(12px); box-shadow:0 12px 26px rgba(0,0,0,.16); font-size:10px; color:#dffbfc;}
        .hf1 {right:36px;top:85px}.hf2 {left:8px;bottom:90px}.hf3 {right:48px;bottom:42px}
        .hero-float b {display:block; font-size:16px; color:#fff; margin-bottom:2px;}

        .public-section {margin:40px 0 16px;}
        .public-section-kicker {font-size:10px; color:#0b8fa5; font-weight:950; letter-spacing:2px; margin-bottom:8px;}
        .public-section h2 {margin:0 !important; font-size:29px !important; color:#103e62; letter-spacing:-.4px;}
        .public-section p {margin-top:10px; color:#688095; line-height:1.8; font-size:13px; max-width:900px;}
        .public-stat-grid {display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:13px; margin:16px 0 26px;}
        .public-stat {position:relative; overflow:hidden; padding:20px 18px; border:1px solid #d2e2ea; border-radius:18px; background:linear-gradient(180deg,#fff,#f7fbfd); box-shadow:0 11px 30px rgba(18,72,108,.07);}
        .public-stat:after {content:""; position:absolute; width:75px; height:75px; right:-28px; top:-31px; border-radius:50%; background:rgba(14,145,170,.07);}
        .public-stat b {display:block; font-size:29px; color:#075885; letter-spacing:-.6px;}
        .public-stat span {display:block; margin-top:7px; color:#71889a; font-size:11px;}
        .public-card-grid {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:17px 0 25px;}
        .public-card {min-height:190px; padding:23px; border:1px solid #d3e2ea; border-radius:20px; background:linear-gradient(180deg,#fff,#f8fcfe); box-shadow:0 11px 30px rgba(18,72,108,.065); transition:.2s ease;}
        .public-card:hover {transform:translateY(-4px); box-shadow:0 18px 42px rgba(18,72,108,.11); border-color:#b9d7e3;}
        .public-card-icon {width:43px; height:43px; display:grid; place-items:center; border-radius:13px; color:#fff; font-size:10px; font-weight:950; letter-spacing:.4px; background:linear-gradient(135deg,#07598e,#0ca5ae); box-shadow:0 8px 20px rgba(8,99,143,.20);}
        .public-card h3 {margin:17px 0 8px !important; color:#173f60; font-size:16px !important;}
        .public-card p {margin:0; color:#708799; font-size:12px; line-height:1.78;}
        .public-flow {display:flex; gap:10px; align-items:stretch; margin:18px 0 26px; flex-wrap:wrap;}
        .public-flow-step {flex:1 1 150px; position:relative; padding:18px; border:1px solid #d4e3eb; border-radius:17px; background:#fff; min-width:150px; box-shadow:0 8px 23px rgba(12,67,103,.045);}
        .public-flow-step strong {display:block; color:#154765; font-size:14px;}
        .public-flow-step span {display:block; margin-top:7px; color:#7890a1; font-size:11px; line-height:1.55;}
        .public-note {padding:15px 17px; border-radius:14px; background:linear-gradient(90deg,#eef8ff,#effafa); border:1px solid #cbe3ec; color:#3f6b82; font-size:12px; line-height:1.78;}
        .public-about {padding:27px; border:1px solid #d2e2ea; border-radius:21px; background:rgba(255,255,255,.92); box-shadow:0 12px 32px rgba(16,70,105,.065);}
        .public-about h3 {margin-top:0 !important;}
        .public-twin-banner {display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:16px 0 22px;}
        .twin-panel {padding:23px; border-radius:20px; background:linear-gradient(145deg,#062f55,#086a82); color:#fff; min-height:145px; box-shadow:0 15px 38px rgba(5,62,96,.15);}
        .twin-panel b {display:block;font-size:22px;margin-bottom:8px}.twin-panel span {font-size:12px;line-height:1.7;color:rgba(235,251,252,.78)}
        .public-footer {margin:42px 0 12px; padding:19px 4px 4px; border-top:1px solid #d4e2ea; display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; color:#7b8f9f; font-size:10px;}
        @media (max-width: 1050px) {.public-hero-grid {grid-template-columns:1fr}.public-hero-visual {display:none}.public-hero-copy {padding:48px 38px}.public-hero {min-height:auto}.public-stat-grid {grid-template-columns:repeat(2,minmax(0,1fr));}.public-card-grid {grid-template-columns:1fr}.public-twin-banner{grid-template-columns:1fr}}
        @media (max-width: 620px) {.public-topbar{align-items:flex-start}.public-brand-title{font-size:14px}.public-version{display:none}.public-hero-copy{padding:34px 22px}.public-hero h1{font-size:31px !important}.public-stat-grid{grid-template-columns:1fr 1fr}.hero-live{gap:12px}.hero-live-item{min-width:100px}}

        /* ===== V1.0 全公网版块统一为“调度模拟大屏”视觉 ===== */
        .public-shell{max-width:1600px}
        .public-topbar{background:linear-gradient(180deg,rgba(6,11,15,.98),rgba(10,23,30,.95));border:1px solid rgba(55,167,200,.22);border-radius:13px;padding:11px 15px;margin:-8px 0 10px;box-shadow:0 14px 34px rgba(0,0,0,.24)}
        .public-brand img{background:rgba(245,252,255,.96);box-shadow:0 8px 22px rgba(0,0,0,.22)}
        .public-brand-title{font-size:20px;color:#f2fbff}.public-brand-sub{font-size:11px;color:#78adbe}.public-version{font-size:12px;border-color:rgba(60,177,211,.26);background:rgba(12,31,40,.88);color:#bdefff;box-shadow:none}
        div[data-testid="stRadio"] > div[role="radiogroup"]{gap:6px;padding:6px;border:1px solid rgba(58,164,195,.22);background:rgba(8,19,25,.94);box-shadow:0 10px 28px rgba(0,0,0,.18)}
        div[data-testid="stRadio"] > div[role="radiogroup"] label{padding:9px 13px}div[data-testid="stRadio"] > div[role="radiogroup"] label p{color:#d9edf4 !important;font-size:14px !important;font-weight:700 !important}div[data-testid="stRadio"] > div[role="radiogroup"] label:hover{background:rgba(29,125,154,.20)}
        .public-hero{background:radial-gradient(circle at 72% 33%,rgba(22,110,139,.17),transparent 31%),linear-gradient(135deg,#071118,#0b2029 52%,#08141a);border:1px solid rgba(56,170,202,.25);box-shadow:0 32px 82px rgba(0,0,0,.35)}
        .public-hero-kicker{font-size:12px;color:#48d8ff}.public-hero h1{font-size:52px !important}.public-hero-desc{font-size:16px}.public-hero-tag{font-size:12px;background:rgba(16,40,49,.75);border-color:rgba(82,187,215,.20)}.hero-live-item b{font-size:27px}.hero-live-item span{font-size:11px}
        .hero-map-card{background:linear-gradient(145deg,rgba(15,43,53,.82),rgba(8,23,31,.80));border-color:rgba(85,194,219,.22)}.hero-float{background:rgba(9,27,35,.87)}
        .public-section{margin:34px 0 16px}.public-section-kicker{font-size:11px;color:#45d9ff}.public-section h2{font-size:31px !important;color:#effaff}.public-section p{font-size:14px;color:#91b3c1;max-width:1040px}
        .public-stat{padding:21px 19px;border-color:rgba(64,156,186,.22);background:linear-gradient(180deg,rgba(17,38,48,.96),rgba(10,25,33,.97));box-shadow:0 12px 30px rgba(0,0,0,.20)}.public-stat:after{background:rgba(36,195,231,.05)}.public-stat b{font-size:31px;color:#5be0ff}.public-stat span{font-size:12px;color:#86adbd}
        .public-card{padding:24px;border-color:rgba(65,157,186,.22);background:linear-gradient(180deg,rgba(17,38,48,.96),rgba(10,25,33,.97));box-shadow:0 12px 30px rgba(0,0,0,.18)}.public-card:hover{border-color:rgba(60,209,242,.43);box-shadow:0 18px 42px rgba(0,0,0,.28)}.public-card-icon{background:linear-gradient(135deg,#0d77a4,#21c9e7)}.public-card h3{font-size:18px !important;color:#f1fbff}.public-card p{font-size:13px;color:#90b2c0}
        .public-flow-step{padding:19px;border-color:rgba(65,155,184,.22);background:linear-gradient(180deg,rgba(17,38,48,.95),rgba(9,24,32,.96));box-shadow:0 8px 23px rgba(0,0,0,.18)}.public-flow-step strong{font-size:15px;color:#f0fbff}.public-flow-step span{font-size:12px;color:#8eb2c1}
        .public-note{font-size:13px;color:#b6d3de;background:linear-gradient(90deg,rgba(13,38,49,.96),rgba(15,45,52,.94));border-color:rgba(61,163,193,.23);box-shadow:inset 4px 0 0 #1cccf1}
        .public-about{padding:28px;border-color:rgba(66,158,187,.22);background:linear-gradient(180deg,rgba(17,38,48,.96),rgba(10,25,33,.97));box-shadow:0 12px 32px rgba(0,0,0,.20)}.public-about h3{color:#f0fbff !important;font-size:19px !important}.public-about p{color:#93b5c2;font-size:14px;line-height:1.85}
        .twin-panel{background:linear-gradient(145deg,rgba(14,48,60,.98),rgba(7,27,36,.98));border:1px solid rgba(62,180,211,.22);box-shadow:0 15px 38px rgba(0,0,0,.21)}.twin-panel b{font-size:23px}.twin-panel span{font-size:13px;color:#abd0db}
        .public-footer{border-top-color:rgba(63,151,180,.20);color:#6f98a9;font-size:11px}
        /* public charts/metrics */
        .stMarkdown h3{color:#eefaff !important;font-size:20px !important}.stCaption{color:#7ea7b7 !important;font-size:12px !important}
        </style>
        """,
        unsafe_allow_html=True,
    )


def public_topbar() -> None:
    logo = _logo_base64()
    st.markdown(
        f"""
        <div class="public-topbar">
          <div class="public-brand">
            <img src="data:image/png;base64,{logo}" alt="platform logo">
            <div><div class="public-brand-title">{html.escape(APP_NAME)}</div><div class="public-brand-sub">HOHAI UNIVERSITY · SMART WATER NETWORK · DIGITAL TWIN</div></div>
          </div>
          <div class="public-version">{html.escape(APP_VERSION)} · Public Web</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(kicker: str, title: str, desc: str) -> None:
    st.markdown(f'<div class="public-section"><div class="public-section-kicker">{html.escape(kicker)}</div><h2>{html.escape(title)}</h2><p>{html.escape(desc)}</p></div>', unsafe_allow_html=True)


def _stat_cards(items: list[tuple[str, str]]) -> None:
    body = "".join(f'<div class="public-stat"><b>{html.escape(str(v))}</b><span>{html.escape(k)}</span></div>' for k, v in items)
    st.markdown(f'<div class="public-stat-grid">{body}</div>', unsafe_allow_html=True)


def _capability_cards() -> None:
    cards = [
        ("GIS", "河网 GIS 一张图", "整合监测站、河道、断面与闸泵设施空间信息，公开页面可直接查看工程对象与空间分布。"),
        ("3D", "数字孪生三维展示", "利用河道断面本地平面坐标与吴淞高程生成可旋转三维点云，并可按河道和断面查看空间形态。"),
        ("DATA", "多源水情数据中心", "统一管理水位、流量、降雨、潮位等数据，支持质量校验、筛选查询、导入导出和审计。"),
        ("AI", "水动力预测", "预测任务绑定站点和空间位置，形成水位、流量、峰值、风险等级以及超警戒时长等结果。"),
        ("OPS", "多目标智能调度", "围绕防洪、排涝、生态、能耗与航运目标生成候选方案，并保留人工审核和推荐环节。"),
        ("SYS", "多人协同与安全", "角色权限、用户启停、操作日志、预警处置、备份恢复与 PostgreSQL 多人部署形成管理闭环。"),
    ]
    body = "".join(f'<div class="public-card"><div class="public-card-icon">{html.escape(icon)}</div><h3>{html.escape(title)}</h3><p>{html.escape(desc)}</p></div>' for icon, title, desc in cards)
    st.markdown(f'<div class="public-card-grid">{body}</div>', unsafe_allow_html=True)


def render_home(set_public_page) -> None:
    summary = get_gis_summary()
    stats = get_dashboard_statistics()
    st.markdown(
        f"""
        <div class="public-hero">
          <div class="public-hero-grid">
            <div class="public-hero-copy">
              <div class="public-hero-kicker">SMART WATER NETWORK · DIGITAL TWIN · INTELLIGENT REGULATION</div>
              <h1>面向河网运行的数字孪生与智能调控平台</h1>
              <div class="public-hero-desc">将水情监测、GIS 空间对象、河道断面、水动力预测、调度方案、风险预警和多人协同统一到一个 Web 门户中。公开网站负责展示与态势浏览，登录后的业务平台负责数据修改、模型运行、调度审核与系统管理。</div>
              <div class="public-hero-tags"><span class="public-hero-tag">GIS 河网</span><span class="public-hero-tag">3D 数字孪生</span><span class="public-hero-tag">多源监测</span><span class="public-hero-tag">水动力预测</span><span class="public-hero-tag">智能调度</span><span class="public-hero-tag">风险预警</span></div>
              <div class="hero-live"><div class="hero-live-item"><b>{summary['station_count']}</b><span>GIS 实测监测站</span></div><div class="hero-live-item"><b>{summary['facility_count']}</b><span>闸泵设施</span></div><div class="hero-live-item"><b>{summary['section_point_count']:,}</b><span>河道断面测点</span></div></div>
            </div>
            <div class="public-hero-visual">
              <div class="hero-orbit"></div>
              <div class="hero-map-card"><span class="river-line r1"></span><span class="river-line r2"></span><span class="river-line r3"></span><span class="river-line r4"></span><span class="river-line r5"></span><span class="map-node n1"></span><span class="map-node n2"></span><span class="map-node n3"></span><span class="map-node n4"></span><span class="map-node n5"></span><span class="map-node n6"></span></div>
              <div class="hero-float hf1"><b>{summary['river_count']} 条</b>河道空间对象</div><div class="hero-float hf2"><b>{summary['section_count']} 个</b>河道断面</div><div class="hero-float hf3"><b>{stats['alert_count']} 条</b>当前业务预警</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, _ = st.columns([.21, .21, .21, .37])
    with c1:
        if st.button("进入业务平台", type="primary", use_container_width=True, key="hero_login"): set_public_page("登录平台")
    with c2:
        if st.button("查看 GIS 全景", use_container_width=True, key="hero_gis"): set_public_page("GIS全景")
    with c3:
        if st.button("进入 3D 数字孪生", use_container_width=True, key="hero_twin"): set_public_page("数字孪生")

    _section("PLATFORM FOUNDATION", "真实 GIS 数据底座", "公开首页指标直接读取当前整合包中的 GIS 与业务数据库；展示层与后台操作层分离，避免公开页面暴露数据维护权限。")
    _stat_cards([("GIS监测站", f"{summary['station_count']} 个"),("闸泵设施", f"{summary['facility_count']} 个"),("河道数量", f"{summary['river_count']} 条"),("河道断面", f"{summary['section_count']} 个"),("断面测点", f"{summary['section_point_count']:,} 个")])
    st.caption(f"业务数据库：{stats['station_count']} 个监测站｜{stats['alert_count']} 条当前预警｜最新数据时间：{get_latest_data_time()}")
    _section("CORE CAPABILITIES", "从感知到决策的一体化能力", "平台围绕空间感知、数据治理、模型预测、智能调度和协同管理形成完整业务链。")
    _capability_cards()
    _section("OPERATION LOOP", "六阶段运行闭环", "让数据、模型与调度不再分散在不同工具中，而是在统一平台内形成连续的决策过程。")
    st.markdown("""<div class="public-flow"><div class="public-flow-step"><strong>01 数据接入</strong><span>水位 / 流量 / 降雨 / 潮位 / GIS / 设施</span></div><div class="public-flow-step"><strong>02 质量治理</strong><span>逐行校验 / 重复识别 / 留痕</span></div><div class="public-flow-step"><strong>03 GIS 感知</strong><span>二维地图 / 三维断面 / 工程定位</span></div><div class="public-flow-step"><strong>04 模型预测</strong><span>水位 / 流量 / 风险 / 超警戒时长</span></div><div class="public-flow-step"><strong>05 智能调度</strong><span>多目标权重 / 运行约束 / 候选方案</span></div><div class="public-flow-step"><strong>06 审核闭环</strong><span>人工推荐 / 预警处置 / 日志 / 备份</span></div></div>""", unsafe_allow_html=True)
    st.markdown('<div class="public-note">当前版本已经具备公开 Web 门户、二维 GIS、真实断面三维展示、业务后台和多人部署能力。水动力预测与调度计算核心仍为可替换的演示模型，工程化应用时应接入经过验证的专业模型和实时数据接口。</div>', unsafe_allow_html=True)


def render_overview() -> None:
    _section("LIVE DATA", "公开数据概览", "以只读方式展示平台当前数据覆盖范围和基础运行态势；公开页面不会提供导入、删除、用户管理或备份恢复权限。")
    summary, stats = get_gis_summary(), get_dashboard_statistics()
    _stat_cards([("GIS监测站", summary["station_count"]),("GIS闸泵", summary["facility_count"]),("业务站点", stats["station_count"]),("当前预警", stats["alert_count"]),("预测任务", stats["prediction_count"])])
    latest = get_latest_station_levels(); left, right = st.columns([1.3, .7], gap="large")
    with left:
        st.markdown("### 站点水位态势")
        water = latest[latest.station_type == "水位站"].dropna(subset=["water_level"]) if not latest.empty else pd.DataFrame()
        if water.empty: st.info("暂无水位数据。")
        else:
            show = water.sort_values("water_level", ascending=False).head(12)
            fig = go.Figure(go.Bar(x=show["station_name"], y=show["water_level"], text=show["water_level"].round(2), textposition="outside")); fig.update_layout(xaxis_title="站点", yaxis_title="水位（m）")
            st.plotly_chart(style_plotly_figure(fig, 410), use_container_width=True)
    with right:
        st.markdown("### 运行摘要")
        if not latest.empty:
            water = latest[latest.station_type == "水位站"].dropna(subset=["water_level"])
            if not water.empty:
                h = water.loc[water.water_level.idxmax()]; st.metric("最高水位", f"{float(h.water_level):.2f} m", h.station_name)
        rain = get_rainfall_series(24); st.metric("24小时累计降雨", f"{rain.rainfall.sum():.1f} mm" if not rain.empty else "0.0 mm"); st.metric("GIS断面测点", f"{summary['section_point_count']:,}"); st.caption(f"最新业务数据时间：{get_latest_data_time()}")


def render_gis(build_map) -> None:
    _section("2D GIS PANORAMA", "河网 GIS 全景", "以卫星影像为底图展示完整河网结构、监测站与闸泵设施；河道按 110 条工程对象组织，重点河道名称常显，点击河线可查看结构信息。")
    summary = get_gis_summary(); _stat_cards([("实测监测站",summary["station_count"]),("闸泵设施",summary["facility_count"]),("河道数量",summary["river_count"]),("断面数量",summary["section_count"]),("断面测点",f"{summary['section_point_count']:,}")])
    latest = get_latest_station_levels(); st_folium(build_map(latest, include_reference=True), height=650, use_container_width=True, key="public_gis_map")
    st.caption("GIS 页新增完整河网结构展示层：由 river.txt 的工程平面坐标生成河道结构线并转换为 WGS84 展示坐标；断面原始工程坐标仍在“数字孪生”页面保留，用于三维断面分析。")


@lru_cache(maxsize=1)
def _river_df() -> pd.DataFrame:
    return pd.DataFrame(load_river_sections())


def _twin_3d_figure(df: pd.DataFrame, title: str, max_points: int = 6500) -> go.Figure:
    if len(df) > max_points:
        step = max(1, len(df) // max_points); df = df.iloc[::step].copy()
    x0, y0 = df["plane_x"].min(), df["plane_y"].min()
    fig = go.Figure(go.Scatter3d(
        x=df["plane_x"]-x0, y=df["plane_y"]-y0, z=df["wusong_elev"], mode="markers",
        marker=dict(size=2.4, color=df["wusong_elev"], colorscale="Viridis", opacity=.78, colorbar=dict(title="高程 m")),
        text=df["reach_name"] + " · 断面" + df["section_id"].astype(str), hovertemplate="%{text}<br>X=%{x:.1f} m<br>Y=%{y:.1f} m<br>高程=%{z:.2f} m<extra></extra>"
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#eefaff", size=18)),
        height=650, margin=dict(l=0,r=0,t=45,b=0), paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Microsoft YaHei, PingFang SC, Arial", color="#c9e3ec", size=13),
        scene=dict(
            bgcolor="#091820", aspectmode="data",
            xaxis=dict(title="相对 X（m）", backgroundcolor="#091820", gridcolor="rgba(99,166,188,.18)", color="#b9d5df"),
            yaxis=dict(title="相对 Y（m）", backgroundcolor="#091820", gridcolor="rgba(99,166,188,.18)", color="#b9d5df"),
            zaxis=dict(title="吴淞高程（m）", backgroundcolor="#091820", gridcolor="rgba(99,166,188,.18)", color="#b9d5df"),
        ),
    )
    return fig


def render_digital_twin() -> None:
    _section("3D DIGITAL TWIN", "数字孪生 · 河网三维空间", "直接使用 river.txt 中的本地平面坐标与吴淞高程构建可旋转、缩放和悬停查询的三维河道断面点云。")
    df = _river_df()
    if df.empty: st.warning("暂无河道断面数据。"); return
    st.markdown('<div class="public-twin-banner"><div class="twin-panel"><b>真实工程坐标</b><span>三维视图不把本地平面坐标伪装成经纬度，而是保留 PlaneX / PlaneY / 吴淞高程的数据含义。</span></div><div class="twin-panel"><b>二维 GIS + 三维断面互补</b><span>二维地图负责站点和设施地理定位；三维数字孪生负责查看河道、断面和高程空间结构。</span></div></div>', unsafe_allow_html=True)
    rivers = sorted(df["reach_name"].dropna().unique().tolist())
    c1,c2,c3 = st.columns([1.1,1.1,.8])
    with c1: mode = st.selectbox("三维范围", ["全河网概览","按河道查看","按断面查看"])
    selected_river = None; selected_section = None
    with c2:
        if mode != "全河网概览": selected_river = st.selectbox("河道", rivers)
        else: st.selectbox("河道", ["全部河道"], disabled=True)
    with c3:
        if mode == "按断面查看" and selected_river:
            sections = sorted(df.loc[df.reach_name==selected_river,"section_id"].astype(str).unique().tolist()); selected_section = st.selectbox("断面", sections)
        else: st.selectbox("断面", ["自动"], disabled=True)
    view = df
    title = "河网断面三维点云概览"
    if selected_river:
        view = view[view.reach_name == selected_river]; title = f"{selected_river} · 三维河道断面"
    if selected_section is not None:
        view = view[view.section_id.astype(str) == str(selected_section)]; title = f"{selected_river} · 断面 {selected_section}"
    a,b,c,d = st.columns(4)
    a.metric("当前测点", f"{len(view):,}"); b.metric("最低高程", f"{view.wusong_elev.min():.2f} m"); c.metric("最高高程", f"{view.wusong_elev.max():.2f} m"); d.metric("高差", f"{(view.wusong_elev.max()-view.wusong_elev.min()):.2f} m")
    st.plotly_chart(_twin_3d_figure(view,title), use_container_width=True, config={"displaylogo":False,"scrollZoom":True})
    if selected_river:
        st.markdown("### 河道断面纵览")
        profile = view.groupby("section_id",as_index=False).agg(mean_elev=("wusong_elev","mean"),min_elev=("wusong_elev","min"),max_elev=("wusong_elev","max"))
        profile["section_order"] = range(1,len(profile)+1)
        fig2=go.Figure(); fig2.add_trace(go.Scatter(x=profile.section_order,y=profile.mean_elev,mode="lines+markers",name="平均高程")); fig2.add_trace(go.Scatter(x=profile.section_order,y=profile.min_elev,mode="lines",name="最低高程")); fig2.add_trace(go.Scatter(x=profile.section_order,y=profile.max_elev,mode="lines",name="最高高程")); fig2.update_layout(xaxis_title="断面序列",yaxis_title="吴淞高程（m）")
        st.plotly_chart(style_plotly_figure(fig2,390),use_container_width=True)
    st.markdown('<div class="public-note">三维视图目前表达的是实测/参考断面空间结构，不等同于完整水动力数字孪生仿真。后续接入实时水位、流速场和专业模型后，可进一步叠加时变水面、淹没范围和调度过程动画。</div>', unsafe_allow_html=True)


def render_capabilities() -> None:
    _section("INTELLIGENCE", "智能能力", "公开网站负责能力展示与结果浏览；预测运行、调度生成、预警处理、数据修改和系统管理仅在登录后开放。")
    _capability_cards(); st.markdown("### 预测与调度输出"); a,b,c=st.columns(3)
    with a: st.info("**水动力预测**\n\n站点水位 / 预测流量 / 峰值 / 风险等级 / 超警戒时长")
    with b: st.info("**调度优化**\n\n防洪 / 排涝 / 生态 / 能耗 / 航运多目标权重与运行约束")
    with c: st.info("**方案审核**\n\nA/B/C 候选方案 / 多维比较 / 人工推荐 / 日志留痕")


def render_architecture() -> None:
    _section("ARCHITECTURE", "平台技术架构", "公开 Web 门户与登录后的业务平台共用同一套数据与服务层，本地可使用 SQLite，正式多人部署可切换 PostgreSQL。")
    st.markdown("""<div class="public-flow"><div class="public-flow-step"><strong>公开访问层</strong><span>首页 · 数据概览 · GIS · 数字孪生 · 项目介绍</span></div><div class="public-flow-step"><strong>业务交互层</strong><span>监测 · 预测 · 调度 · 预警 · 数据中心</span></div><div class="public-flow-step"><strong>服务层</strong><span>认证 · 校验 · 模型接口 · 日志 · 备份</span></div><div class="public-flow-step"><strong>数据层</strong><span>SQLite / PostgreSQL · GIS · Excel / CSV</span></div><div class="public-flow-step"><strong>公网部署层</strong><span>Docker · 反向代理 / Tunnel · HTTPS · 自定义域名</span></div></div>""", unsafe_allow_html=True)
    st.markdown('<div class="public-about"><h3>公网部署方式</h3><p>V1.0 包内同时提供本地访问、临时公网预览和服务器长期部署说明。生产环境建议让 HTTPS 在反向代理或托管平台终止，而不是直接由 Streamlit 处理证书。</p></div>', unsafe_allow_html=True)


def render_about() -> None:
    _section("ABOUT", "关于平台", "V1.0 的目标是把原有“后台系统”提升为公开展示网站、数字孪生展示与业务平台一体化入口。")
    st.markdown("""<div class="public-about"><h3>平台定位</h3><p>面向河网运行管理、科研验证、成果展示与决策支持，将多源水情、空间对象、预测结果、调度方案和管理流程统一到同一 Web 平台。</p><h3>公开网站</h3><p>包含正式首页、实时数据概览、二维 GIS、三维数字孪生、智能能力、技术架构和项目介绍；无需登录即可浏览。</p><h3>登录后的业务系统</h3><p>完整保留数据中心、监测图表、水动力预测、智能调度、方案比较、预警中心、模型管理、用户权限、操作日志和备份恢复。</p><h3>工程化扩展</h3><p>可继续接入实时接口、专业水动力模型、设备控制接口、时变水面与淹没范围三维动画，以及面向移动端的独立展示页面。</p></div>""", unsafe_allow_html=True)


def public_footer() -> None:
    st.markdown(f'<div class="public-footer"><span>河海大学 · {html.escape(APP_NAME)}</span><span>{html.escape(APP_VERSION)} · Public Web / GIS / Digital Twin / Business Platform</span></div>', unsafe_allow_html=True)
