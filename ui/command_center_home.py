from __future__ import annotations

import html
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from core.config import BASE_DIR
from services.alert_service import query_alerts
from services.data_service import (
    get_dashboard_statistics,
    get_latest_data_time,
    get_latest_station_levels,
    get_rainfall_series,
)
from services.gis_service import get_gis_summary, load_gate_pump_points, load_gis_stations


_GIS_DIR = BASE_DIR / "data" / "gis"


def inject_command_center_theme() -> None:
    st.markdown(
        """
        <style>
        /* ===== V4.0 指挥大屏首页 ===== */
        .stApp {
            background:
                radial-gradient(circle at 68% 18%, rgba(0,132,220,.12), transparent 31%),
                linear-gradient(155deg,#010b1d 0%,#021a38 47%,#011126 100%) !important;
        }
        [data-testid="stAppViewContainer"] > .main {background:transparent !important;}
        [data-testid="stHeader"] {background:rgba(1,15,34,.80) !important;border-bottom:1px solid rgba(44,151,216,.20) !important;}
        .public-topbar {
            background:linear-gradient(180deg,rgba(1,17,39,.98),rgba(2,27,56,.94)) !important;
            border:1px solid rgba(45,156,224,.24); border-radius:15px; padding:10px 14px !important; margin:-8px 0 8px !important;
            box-shadow:0 10px 28px rgba(0,0,0,.22);
        }
        .public-brand-title {color:#f0fbff !important;}
        .public-brand-sub {color:#69b6dc !important;}
        .public-version {background:rgba(4,47,88,.80) !important;color:#9bdcff !important;border-color:rgba(66,181,238,.25) !important;}
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            background:rgba(2,30,61,.88) !important;border-color:rgba(49,154,217,.24) !important;box-shadow:0 9px 25px rgba(0,0,0,.16) !important;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] label {color:#d9f3ff !important;}
        div[data-testid="stRadio"] > div[role="radiogroup"] label p {color:#d9f3ff !important;}
        div[data-testid="stRadio"] > div[role="radiogroup"] label:hover {background:rgba(14,133,199,.22) !important;}
        div[data-testid="stButton"] button {
            color:#eafaff !important; border:1px solid rgba(63,177,235,.28) !important;
            background:linear-gradient(145deg,rgba(5,67,118,.94),rgba(4,46,90,.95)) !important;
            box-shadow:0 8px 22px rgba(0,0,0,.16),inset 0 0 18px rgba(38,160,220,.06) !important;
        }
        div[data-testid="stButton"] button:hover {
            color:white !important; border-color:rgba(74,217,249,.56) !important;
            background:linear-gradient(145deg,#0878b6,#07508f) !important; transform:translateY(-2px);
        }
        .cc-shell {
            margin: 6px 0 0;
            padding: 22px 24px 26px;
            border: 1px solid rgba(28,139,218,.38);
            border-radius: 24px;
            color: #eefbff;
            background:
                radial-gradient(circle at 72% 32%, rgba(0,205,255,.15), transparent 30%),
                radial-gradient(circle at 8% 88%, rgba(12,119,214,.17), transparent 31%),
                linear-gradient(145deg,#021733 0%,#032550 44%,#02203f 100%);
            box-shadow: 0 30px 90px rgba(2,22,50,.36), inset 0 0 50px rgba(0,136,221,.05);
            overflow: hidden;
            position: relative;
        }
        .cc-shell:before {
            content:""; position:absolute; inset:0; pointer-events:none; opacity:.24;
            background-image:
                linear-gradient(rgba(28,147,220,.10) 1px, transparent 1px),
                linear-gradient(90deg, rgba(28,147,220,.10) 1px, transparent 1px);
            background-size: 34px 34px;
            mask-image: linear-gradient(to bottom, #000, transparent 92%);
        }
        .cc-hero {position:relative; z-index:2; display:grid; grid-template-columns:minmax(0,1.25fr) minmax(340px,.75fr); gap:24px; align-items:end;}
        .cc-eyebrow {font-size:11px; letter-spacing:3px; font-weight:900; color:#64e7ff; text-transform:uppercase;}
        .cc-title {margin:9px 0 10px; color:white; font-size:clamp(30px,3.2vw,54px); line-height:1.12; font-weight:950; letter-spacing:-1.5px; text-shadow:0 0 30px rgba(40,190,255,.16);}
        .cc-desc {max-width:920px; color:rgba(225,244,255,.76); font-size:14px; line-height:1.85;}
        .cc-livebar {display:flex; justify-content:flex-end; align-items:center; gap:10px; flex-wrap:wrap; padding-bottom:7px;}
        .cc-pill {display:inline-flex; align-items:center; gap:8px; padding:8px 11px; border:1px solid rgba(72,194,246,.25); border-radius:999px; background:rgba(2,41,79,.64); color:#bfeeff; font-size:11px; backdrop-filter:blur(9px);}
        .cc-dot {width:7px;height:7px;border-radius:50%;background:#38e7b2;box-shadow:0 0 0 4px rgba(56,231,178,.11),0 0 14px rgba(56,231,178,.58);}
        .cc-metric-grid {position:relative;z-index:2;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:20px 0 18px;}
        .cc-metric {padding:15px 15px 14px;border:1px solid rgba(62,173,238,.28);border-radius:15px;background:linear-gradient(180deg,rgba(10,61,111,.78),rgba(5,38,77,.80));box-shadow:inset 0 0 22px rgba(27,145,214,.08),0 10px 26px rgba(0,0,0,.12);}
        .cc-metric small {display:block;color:#8cc9eb;font-size:10px;letter-spacing:.3px;}
        .cc-metric b {display:block;margin-top:5px;color:#6ee9ff;font-size:26px;line-height:1;font-weight:900;}
        .cc-metric.warn b {color:#ff8c7a;}
        .cc-panel-title {display:flex;align-items:center;justify-content:space-between;margin:3px 0 10px;color:#dff7ff;font-size:13px;font-weight:900;letter-spacing:.4px;}
        .cc-panel-title span {font-size:9px;color:#69bfe8;font-weight:600;}
        .cc-side-card {padding:13px 14px;margin-bottom:10px;border:1px solid rgba(65,171,229,.22);border-radius:13px;background:linear-gradient(145deg,rgba(5,47,91,.88),rgba(4,35,70,.82));box-shadow:inset 3px 0 0 rgba(34,183,234,.32);}
        .cc-side-card .label {color:#80c6e8;font-size:9px;letter-spacing:.5px;}
        .cc-side-card .value {margin-top:5px;color:#ecfbff;font-size:20px;font-weight:900;}
        .cc-side-card .note {margin-top:4px;color:#77b6d5;font-size:9px;}
        .cc-alert {padding:10px 11px;margin-bottom:8px;border:1px solid rgba(79,167,218,.18);border-radius:11px;background:rgba(3,37,74,.76);}
        .cc-alert-top {display:flex;align-items:center;justify-content:space-between;gap:8px;}
        .cc-alert-level {font-size:10px;font-weight:900;}
        .cc-alert-time {color:#648eaa;font-size:8px;white-space:nowrap;}
        .cc-alert-msg {margin-top:5px;color:#c5e6f7;font-size:9px;line-height:1.5;}
        .cc-level-red {color:#ff6d6d}.cc-level-orange{color:#ffad67}.cc-level-yellow{color:#ffd75e}.cc-level-blue{color:#5cd7ff}
        .cc-map-frame {padding:8px;border:1px solid rgba(57,181,244,.40);border-radius:17px;background:linear-gradient(145deg,rgba(3,49,93,.92),rgba(3,31,65,.92));box-shadow:0 0 32px rgba(0,151,235,.10),inset 0 0 25px rgba(25,160,230,.06);}
        .cc-section-head {margin:20px 0 10px;color:#e8f9ff;font-size:15px;font-weight:950;letter-spacing:.5px;}
        .cc-section-head:before {content:"";display:inline-block;width:4px;height:16px;margin-right:8px;vertical-align:-3px;border-radius:999px;background:linear-gradient(#4ee7ff,#1187f0);box-shadow:0 0 12px rgba(49,202,255,.5);}
        .cc-announce {padding:12px 14px;border:1px solid rgba(51,154,216,.22);border-radius:13px;background:rgba(4,39,76,.74);color:#b9dded;font-size:10px;line-height:1.85;}
        .cc-announce b {color:#f0fbff;font-size:11px;}
        .cc-footer-strip {position:relative;z-index:2;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:1px;margin-top:18px;border:1px solid rgba(53,158,216,.20);border-radius:13px;overflow:hidden;background:rgba(1,26,55,.78);}
        .cc-footer-item {padding:12px 13px;border-right:1px solid rgba(60,155,210,.15);}
        .cc-footer-item:last-child{border-right:none}.cc-footer-item small{display:block;color:#6ea8c5;font-size:8px}.cc-footer-item b{display:block;margin-top:3px;color:#ddf8ff;font-size:15px}

        /* 首页的 Streamlit 按钮做成大屏快捷入口 */
        .cc-home-marker + div [data-testid="stButton"] button,
        div[data-testid="stButton"] button[kind="secondary"] {
            min-height:58px;
        }
        .cc-quick-note {margin:-3px 0 10px;color:#6faed0;font-size:9px;}

        @media (max-width: 1000px) {
            .cc-shell {padding:18px 14px 20px;border-radius:18px;}
            .cc-hero {grid-template-columns:1fr;}
            .cc-livebar {justify-content:flex-start;}
            .cc-metric-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
            .cc-footer-strip {grid-template-columns:repeat(2,minmax(0,1fr));}
        }
        @media (max-width: 640px) {
            .cc-title {font-size:30px;}
            .cc-metric-grid {grid-template-columns:1fr 1fr;}
            .cc-metric b {font-size:21px;}
            .cc-footer-strip {grid-template-columns:1fr 1fr;}
        }

        /* ===== V1.0 视觉统一：炭黑 + 卫星底图 + 青蓝/橙色强调 ===== */
        .stApp {background:radial-gradient(circle at 62% 8%,rgba(22,87,112,.13),transparent 29%),linear-gradient(155deg,#05090d 0%,#09141b 48%,#071018 100%) !important;}
        [data-testid="stHeader"] {background:rgba(5,10,14,.91) !important;border-bottom:1px solid rgba(65,164,197,.20) !important;}
        .public-topbar {background:linear-gradient(180deg,rgba(7,13,18,.97),rgba(10,23,31,.95)) !important;border-color:rgba(48,169,206,.25) !important;}
        .public-brand-title{font-size:20px !important;color:#f3fbff !important}.public-brand-sub{font-size:11px !important;color:#78b4c9 !important}.public-version{font-size:12px !important;background:rgba(12,32,42,.92) !important;color:#bdefff !important;border-color:rgba(62,184,217,.28) !important}
        div[data-testid="stRadio"] > div[role="radiogroup"] {background:rgba(8,19,26,.94) !important;border-color:rgba(59,164,196,.24) !important;}
        div[data-testid="stRadio"] > div[role="radiogroup"] label p{font-size:14px !important;font-weight:700 !important;}
        .cc-shell{border-color:rgba(55,183,220,.31);background:radial-gradient(circle at 73% 30%,rgba(24,108,135,.12),transparent 31%),linear-gradient(145deg,rgba(7,17,23,.98),rgba(9,27,36,.96) 54%,rgba(7,16,22,.98));box-shadow:0 28px 86px rgba(0,0,0,.42),inset 0 0 48px rgba(31,170,211,.035)}
        .cc-shell:before{opacity:.16;background-image:linear-gradient(rgba(52,169,204,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(52,169,204,.08) 1px,transparent 1px)}
        .cc-eyebrow{font-size:12px;color:#43d7ff}.cc-title{font-size:clamp(34px,3.5vw,58px);text-shadow:0 0 28px rgba(0,186,234,.12)}.cc-desc{font-size:16px;line-height:1.9;color:rgba(226,241,246,.82)}
        .cc-pill{font-size:12px;background:rgba(14,31,40,.78);border-color:rgba(68,181,215,.23);color:#caeffb}.cc-dot{background:#40df9d}
        .cc-metric{padding:17px 16px;border-color:rgba(66,172,205,.25);background:linear-gradient(180deg,rgba(18,41,53,.92),rgba(10,26,35,.94));box-shadow:inset 0 0 19px rgba(35,174,211,.035),0 12px 28px rgba(0,0,0,.20)}
        .cc-metric small{font-size:12px;color:#89bfd1}.cc-metric b{font-size:30px;color:#59ddff}.cc-metric.warn b{color:#ff9c42}
        .cc-panel-title{font-size:16px;color:#f0fbff}.cc-panel-title span{font-size:10px;color:#70b4cb}.cc-section-head{font-size:18px}.cc-section-head:before{background:linear-gradient(#17d7ff,#2c76ff)}
        .cc-side-card{padding:15px 16px;border-color:rgba(65,157,188,.23);background:linear-gradient(145deg,rgba(17,39,50,.94),rgba(10,26,34,.94));box-shadow:inset 3px 0 0 rgba(31,188,224,.42)}
        .cc-side-card .label{font-size:11px;color:#8bc0d2}.cc-side-card .value{font-size:24px}.cc-side-card .note{font-size:10px;color:#78a5b5}
        .cc-alert{padding:12px 13px;border-color:rgba(76,158,188,.20);background:rgba(12,30,39,.91)}.cc-alert-level{font-size:12px}.cc-alert-time{font-size:10px}.cc-alert-msg{font-size:11px;color:#c7e3ed}
        .cc-level-orange{color:#ff9e42}.cc-level-yellow{color:#ffd164}.cc-level-blue{color:#4ed9ff}.cc-level-red{color:#ff6464}
        .cc-map-frame{border-color:rgba(54,183,220,.42);background:rgba(6,17,23,.96);box-shadow:0 0 32px rgba(0,151,205,.08),inset 0 0 20px rgba(28,160,199,.04)}
        .cc-announce{font-size:12px;background:rgba(12,30,39,.91);border-color:rgba(64,157,187,.22);color:#c2dde7}.cc-announce b{font-size:13px}.cc-footer-strip{background:rgba(8,20,27,.96);border-color:rgba(65,159,190,.20)}.cc-footer-item small{font-size:10px}.cc-footer-item b{font-size:17px}
        .cc-quick-note{font-size:11px;color:#7caebf}
        div[data-testid="stButton"] button{font-size:14px !important;min-height:48px !important;background:linear-gradient(145deg,rgba(16,54,69,.96),rgba(10,35,46,.96)) !important;border-color:rgba(54,181,217,.30) !important}.cc-home-marker + div [data-testid="stButton"] button{min-height:62px !important;font-size:15px !important}.stButton button:hover{border-color:#43d7ff !important;background:linear-gradient(145deg,#143e4d,#0c2c3a) !important}
        .cc-realtime-clock{display:flex;justify-content:flex-end;align-items:center;gap:12px;margin:2px 0 9px;padding:9px 13px;border:1px solid rgba(65,169,201,.22);border-radius:11px;background:linear-gradient(90deg,rgba(8,18,24,.30),rgba(10,27,36,.88));color:#a9d4e2;font-size:12px;box-shadow:0 8px 20px rgba(0,0,0,.14)}
        .cc-realtime-clock .cc-clock-label{color:#65dfff;font-weight:800;letter-spacing:.5px}.cc-realtime-clock b{color:#fff;font-size:15px;letter-spacing:.6px}.cc-realtime-clock b:nth-of-type(2){color:#ffb24a;font-size:19px;font-variant-numeric:tabular-nums}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _dark_home_map() -> folium.Map:
    stations = load_gis_stations()
    facilities = load_gate_pump_points()
    center = [31.515, 120.425]
    m = folium.Map(location=center, zoom_start=11, tiles=None, control_scale=False, zoom_control=True, attribution_control=False, prefer_canvas=True)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery', name='卫星影像', show=True, overlay=False, max_zoom=19,
    ).add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='深色底图', show=False, overlay=False).add_to(m)

    geo = _GIS_DIR / 'river_network_full.geojson'
    if not geo.exists():
        geo = _GIS_DIR / 'river_network.geojson'
    river_obj = None
    if geo.exists():
        river_obj = json.loads(geo.read_text(encoding='utf-8'))
        full = geo.name == 'river_network_full.geojson'
        folium.GeoJson(
            river_obj, name='河网结构',
            style_function=lambda f: {
                'color':'#17d8ff' if int(f.get('properties',{}).get('section_count',2) or 2) < 5 else '#69f2ff',
                'weight':2.4 if int(f.get('properties',{}).get('section_count',2) or 2) < 5 else 4.2,
                'opacity':.88 if int(f.get('properties',{}).get('section_count',2) or 2) < 5 else 1,
            },
            highlight_function=lambda _: {'color':'#ffad43','weight':6,'opacity':1},
            tooltip=folium.GeoJsonTooltip(fields=['name','section_count'], aliases=['河道','断面数'], sticky=False) if full else folium.GeoJsonTooltip(fields=['name'], aliases=['河道']),
        ).add_to(m)
        if full:
            features=river_obj.get('features',[])
            for feature in sorted(features,key=lambda f:int(f.get('properties',{}).get('section_count',0)),reverse=True)[:14]:
                coords=feature.get('geometry',{}).get('coordinates',[])
                if not coords: continue
                lon,lat=coords[len(coords)//2]
                name=str(feature.get('properties',{}).get('name',''))
                folium.Marker([lat,lon], icon=folium.DivIcon(icon_size=(86,20), icon_anchor=(43,10), html=f'<div style="white-space:nowrap;text-align:center;color:#f3fdff;font-size:10px;font-weight:700;text-shadow:0 1px 5px #000;background:rgba(0,13,18,.38);padding:1px 4px;border-radius:4px">{name}</div>')).add_to(m)
            all_coords=[c for f in features for c in f.get('geometry',{}).get('coordinates',[]) if isinstance(c,list) and len(c)>=2]
            if all_coords:
                lons=[c[0] for c in all_coords]; lats=[c[1] for c in all_coords]
                m.fit_bounds([[min(lats),min(lons)],[max(lats),max(lons)]], padding=(8,8))

    for item in stations:
        folium.CircleMarker([item['lat'],item['lng']], radius=4, color='#c4fbff', weight=1, fill=True, fill_color='#12d6f4', fill_opacity=.92, tooltip=f"{item['station_name']}（{item['station_id']}）").add_to(m)
    for item in facilities:
        folium.CircleMarker([item['lat'],item['lng']], radius=5.2, color='#ffe8ad', weight=1, fill=True, fill_color='#ff9b2f', fill_opacity=.97, tooltip=f"{item['facility_name']}（{item['facility_id']}）").add_to(m)
    folium.LayerControl(collapsed=True,position='topright').add_to(m)
    return m


def _safe_float(value, default=0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _runtime_snapshot() -> dict:
    latest = get_latest_station_levels()
    water = latest[latest.station_type == "水位站"].dropna(subset=["water_level"]) if not latest.empty else pd.DataFrame()
    highest = _safe_float(water["water_level"].max(), 0.0) if not water.empty else 0.0
    avg_level = _safe_float(water["water_level"].mean(), 0.0) if not water.empty else 0.0
    rain = get_rainfall_series(24)
    rainfall_24h = _safe_float(rain["rainfall"].sum(), 0.0) if not rain.empty else 0.0
    return {"highest": highest, "avg_level": avg_level, "rainfall_24h": rainfall_24h}


def _alerts_html(limit: int = 4) -> str:
    alerts = query_alerts()
    if alerts.empty:
        return '<div class="cc-alert"><div class="cc-alert-msg">当前暂无预警信息。</div></div>'
    rows = []
    class_map = {"红色": "cc-level-red", "橙色": "cc-level-orange", "黄色": "cc-level-yellow", "蓝色": "cc-level-blue"}
    for r in alerts.head(limit).itertuples(index=False):
        level = str(getattr(r, "alert_level", "蓝色"))
        at = getattr(r, "alert_time", None)
        time_text = at.strftime("%m-%d %H:%M") if hasattr(at, "strftime") else str(at or "—")[:16]
        message = html.escape(str(getattr(r, "message", "")))
        rows.append(
            f'<div class="cc-alert"><div class="cc-alert-top"><span class="cc-alert-level {class_map.get(level,"cc-level-blue")}">{html.escape(level)}预警</span>'
            f'<span class="cc-alert-time">{html.escape(time_text)}</span></div><div class="cc-alert-msg">{message}</div></div>'
        )
    return "".join(rows)


@st.fragment(run_every="1s")
def _live_clock() -> None:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    weekdays = "一二三四五六日"
    st.markdown(
        f'<div class="cc-realtime-clock"><span class="cc-clock-label">实时系统时间</span><b>{now:%Y-%m-%d}</b><b>{now:%H:%M:%S}</b><span>星期{weekdays[now.weekday()]}</span></div>',
        unsafe_allow_html=True,
    )


def render_command_center_home(set_public_page) -> None:
    inject_command_center_theme()
    _live_clock()
    summary = get_gis_summary()
    stats = get_dashboard_statistics()
    snap = _runtime_snapshot()
    st.markdown(
        f"""
        <div class="cc-shell">
          <div class="cc-hero">
            <div>
              <div class="cc-eyebrow">SMART WATER NETWORK · DIGITAL TWIN · INTELLIGENT REGULATION</div>
              <div class="cc-title">面向河网运行的<br>数字孪生与智能调控平台</div>
              <div class="cc-desc">融合 GIS 空间底图、多源水情监测、三维河道断面、水动力预测、智能调度与风险预警，形成“感知—研判—预测—调度—处置”的水网运行数字化闭环。</div>
            </div>
            <div class="cc-livebar">
              <span class="cc-pill"><i class="cc-dot"></i>平台在线</span>
              <span class="cc-pill">最新数据 {html.escape(get_latest_data_time())}</span>
            </div>
          </div>
          <div class="cc-metric-grid">
            <div class="cc-metric"><small>河道对象</small><b>{summary['river_count']}</b></div>
            <div class="cc-metric"><small>监测站点</small><b>{summary['station_count']}</b></div>
            <div class="cc-metric"><small>闸泵设施</small><b>{summary['facility_count']}</b></div>
            <div class="cc-metric"><small>河道断面</small><b>{summary['section_count']}</b></div>
            <div class="cc-metric warn"><small>当前预警</small><b>{stats['alert_count']}</b></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 指挥中心主体：左侧实时信息 + 中间 GIS + 右侧预警。
    st.markdown('<div class="cc-section-head">河网运行态势</div>', unsafe_allow_html=True)
    left, center, right = st.columns([.72, 2.05, .82], gap="medium")
    with left:
        st.markdown('<div class="cc-panel-title">实时水情 <span>REAL-TIME</span></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="cc-side-card"><div class="label">24 小时累计降雨</div><div class="value">{snap['rainfall_24h']:.1f} mm</div><div class="note">平台雨量数据汇总</div></div>
            <div class="cc-side-card"><div class="label">当前平均水位</div><div class="value">{snap['avg_level']:.2f} m</div><div class="note">业务水位站均值</div></div>
            <div class="cc-side-card"><div class="label">当前最高水位</div><div class="value">{snap['highest']:.2f} m</div><div class="note">自动读取最新监测值</div></div>
            <div class="cc-side-card"><div class="label">断面测点</div><div class="value">{summary['section_point_count']:,}</div><div class="note">river.txt 工程断面数据</div></div>
            """,
            unsafe_allow_html=True,
        )
        rain = get_rainfall_series(24)
        if not rain.empty:
            plot = rain[["monitor_time", "rainfall"]].copy().sort_values("monitor_time")
            st.area_chart(plot.set_index("monitor_time"), height=155, color="#20c8ff")

    with center:
        st.markdown('<div class="cc-panel-title">河网 GIS 一张图 <span>GIS COMMAND MAP</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="cc-map-frame">', unsafe_allow_html=True)
        st_folium(_dark_home_map(), height=470, use_container_width=True, key="command_center_home_map")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="cc-panel-title">预警信息 <span>ALERTS</span></div>', unsafe_allow_html=True)
        st.markdown(_alerts_html(), unsafe_allow_html=True)
        st.markdown(
            f'<div class="cc-side-card"><div class="label">预测任务</div><div class="value">{stats["prediction_count"]}</div><div class="note">累计模型任务记录</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="cc-section-head">快速入口</div><div class="cc-quick-note">点击后直达平台现有功能；需要权限的功能会先进入登录页，登录成功后自动跳转。</div><div class="cc-home-marker"></div>', unsafe_allow_html=True)
    row1 = st.columns(4, gap="medium")
    actions1 = [
        ("🗺️ 进入 GIS 全景", "GIS全景", None),
        ("🧊 进入 3D 数字孪生", "数字孪生", None),
        ("📈 查看监测图表", "登录平台", "监测图表"),
        ("🌊 水动力预测", "登录平台", "水动力预测"),
    ]
    for col, (label, public_page, backend_target) in zip(row1, actions1):
        with col:
            if st.button(label, use_container_width=True, key=f"cc_{backend_target or public_page}_1"):
                set_public_page(public_page, backend_target)

    row2 = st.columns(4, gap="medium")
    actions2 = [
        ("🎛️ 智能调度", "登录平台", "智能调度"),
        ("🚨 风险预警", "登录平台", "预警中心"),
        ("⚖️ 方案比选", "登录平台", "方案比较"),
        ("⚙️ 系统管理", "登录平台", "系统管理"),
    ]
    for col, (label, public_page, backend_target) in zip(row2, actions2):
        with col:
            if st.button(label, use_container_width=True, key=f"cc_{backend_target}_2"):
                set_public_page(public_page, backend_target)

    lower_left, lower_right = st.columns([1.7, .8], gap="medium")
    with lower_left:
        st.markdown('<div class="cc-section-head">平台运行信息</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="cc-announce"><b>数据与模型状态</b><br>
            GIS 数据底座：{summary['station_count']} 个实测站、{summary['facility_count']} 个闸泵、{summary['river_count']} 条河道、{summary['section_count']} 个断面。<br>
            当前公网首页为只读展示；数据维护、模型运行、调度审核、用户与备份管理仍受登录和角色权限控制。</div>
            """,
            unsafe_allow_html=True,
        )
    with lower_right:
        st.markdown('<div class="cc-section-head">快捷链接</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("平台概览", use_container_width=True, key="cc_overview"):
                set_public_page("平台概览", None)
            if st.button("智能能力", use_container_width=True, key="cc_cap"):
                set_public_page("智能能力", None)
        with c2:
            if st.button("技术架构", use_container_width=True, key="cc_arch"):
                set_public_page("技术架构", None)
            if st.button("关于平台", use_container_width=True, key="cc_about"):
                set_public_page("关于平台", None)

    st.markdown(
        f"""
        <div class="cc-footer-strip">
          <div class="cc-footer-item"><small>今日降雨</small><b>{snap['rainfall_24h']:.1f} mm</b></div>
          <div class="cc-footer-item"><small>平均水位</small><b>{snap['avg_level']:.2f} m</b></div>
          <div class="cc-footer-item"><small>最高水位</small><b>{snap['highest']:.2f} m</b></div>
          <div class="cc-footer-item"><small>监测站点</small><b>{summary['station_count']} 个</b></div>
          <div class="cc-footer-item"><small>闸泵设施</small><b>{summary['facility_count']} 个</b></div>
          <div class="cc-footer-item"><small>断面测点</small><b>{summary['section_point_count']:,}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
