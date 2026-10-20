from __future__ import annotations

from datetime import datetime, timedelta
import html
import math
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from core.config import DEMO_MODE, SEED_DEMO_DATA
from services.alert_service import query_alerts
from services.data_service import (
    get_dashboard_statistics, get_latest_data_time,
    get_latest_station_levels, get_rainfall_series,
)
from services.gis_service import get_gis_summary
from ui.scene3d import render_scene3d
from ui.theme import metric_card, section_label


def inject_command_center_theme() -> None:
    st.markdown(
        """<style>
        .cc-intro{display:flex;align-items:flex-end;justify-content:space-between;gap:32px;padding:22px 0 28px;}
        .cc-kicker{color:#66cdb8;font-size:10px;font-weight:650;letter-spacing:.2em;margin-bottom:12px;}
        .cc-title{color:#f0f6fb;font-size:34px;line-height:1.4;letter-spacing:-.045em;font-weight:650;}
        .cc-desc{color:#9bb2c5;font-size:13px;line-height:1.9;max-width:850px;margin-top:12px;}
        .cc-date{text-align:right;flex-shrink:0;color:#d8bb80;font-size:13px;line-height:1.9;font-variant-numeric:tabular-nums;}.cc-date small{display:block;color:#829eb5;font-size:11px;}
        .cc-data-notice{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;border:1px solid #314050;border-radius:7px;background:#112032;color:#92acc0;font-size:11px;line-height:1.8;margin-bottom:20px;}
        .cc-data-pill{color:#e2c78f;background:#3c3223;border:1px solid #655137;border-radius:4px;padding:1px 7px;font-size:10px;letter-spacing:.04em;}
        .cc-side-title{font-size:11px;color:#8faabd;letter-spacing:.1em;margin-bottom:10px;}.cc-water{border:1px solid #2b4155;background:#102236;border-radius:10px;padding:17px 18px;margin-bottom:12px;}
        .cc-water-label{color:#a1b7c9;font-size:11px;}.cc-water-value{color:#edf5fa;font-size:27px;font-weight:650;margin:8px 0 5px;letter-spacing:-.04em;font-variant-numeric:tabular-nums;}.cc-water-unit{font-size:12px;font-weight:400;color:#99b4c7;margin-left:4px;}.cc-water-note{color:#7796ad;font-size:10px;line-height:1.6;}
        .cc-water-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;border-top:1px solid #263d52;padding-top:13px;margin-top:13px;}.cc-water-grid b{display:block;color:#cbe2e9;font-size:17px;font-weight:600;margin-top:5px;}.cc-water-grid small{color:#8aa7bc;font-size:10px;}
        .cc-alert-item{border-bottom:1px solid #253a4e;padding:12px 0;}.cc-alert-item:last-child{border-bottom:0;}.cc-alert-head{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:10px;}.cc-alert-level{display:flex;align-items:center;gap:6px;font-weight:650;}.cc-alert-dot{width:5px;height:5px;border-radius:50%;background:currentColor;}.cc-alert-date{color:#7e9cb3;}.cc-alert-msg{font-size:11px;color:#afc3d2;margin-top:7px;line-height:1.8;}.cc-alert-empty{color:#8faaaf;padding:14px 0;font-size:12px;}
        .cc-scene-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;margin:25px 0 12px;}.cc-scene-heading h2{color:#e7f1f8;font-size:17px !important;letter-spacing:-.025em;margin:0 !important;}.cc-scene-heading p{margin:6px 0 0;font-size:11px;color:#819fb6;line-height:1.7;}.cc-scene-heading span{font-size:10px;letter-spacing:.1em;color:#d5bc88;white-space:nowrap;padding-top:5px;}
        .cc-entry-index{font-size:11px;color:#d8bb80;letter-spacing:.1em;}.cc-entry-title{font-size:18px;color:#e7f2f8;font-weight:600;margin:10px 0 8px;letter-spacing:-.02em;}.cc-entry-desc{color:#8eacbf;font-size:12px;line-height:1.85;margin-bottom:18px;min-height:46px;}
        .cc-source-note{border-top:1px solid #263b50;padding-top:15px;margin-top:25px;display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;font-size:10px;color:#728fa6;line-height:1.8;}
        @media(max-width:1000px){.cc-title{font-size:28px;}.cc-intro{align-items:flex-start;}.cc-date{display:none;}.cc-entry-desc{min-height:0;}}
        @media(max-width:600px){.cc-intro{padding:13px 0 20px;}.cc-title{font-size:26px;}.cc-scene-heading{display:block;}.cc-scene-heading span{display:block;margin-top:6px;}}
        </style>""",
        unsafe_allow_html=True,
    )


def _number(value, digits: int = 2) -> str:
    try:
        numeric = float(value)
        return f"{numeric:.{digits}f}" if math.isfinite(numeric) else "—"
    except (TypeError, ValueError):
        return "—"


def _runtime_snapshot(latest: pd.DataFrame) -> dict:
    water = latest[latest["station_type"] == "水位站"].dropna(subset=["water_level"]) if not latest.empty else pd.DataFrame()
    highest = water.loc[water["water_level"].idxmax()] if not water.empty else None
    rainfall = get_rainfall_series(24)
    average_rain = None
    if not rainfall.empty:
        rainfall = rainfall.copy()
        rainfall["monitor_time"] = pd.to_datetime(rainfall["monitor_time"], errors="coerce")
        end_time = rainfall["monitor_time"].max()
        selected = rainfall[rainfall["monitor_time"] > end_time - timedelta(hours=24)]
        if not selected.empty:
            average_rain = selected.groupby("station_id")["rainfall"].sum().mean()
    return {
        "highest": highest["water_level"] if highest is not None else None,
        "highest_station": str(highest["station_name"]) if highest is not None else "暂无水位记录",
        "average": water["water_level"].mean() if not water.empty else None,
        "rainfall": average_rain,
        "measured_station_count": len(water),
    }


def _alerts_html(alerts: pd.DataFrame, limit: int = 3) -> str:
    if alerts.empty:
        return '<div class="cc-alert-empty">暂无未解除预警</div>'
    colors = {"红色": "#f18b91", "橙色": "#eeb07a", "黄色": "#dfc27c", "蓝色": "#83b8e6"}
    rows = []
    for row in alerts.head(limit).itertuples(index=False):
        level = str(getattr(row, "alert_level", "蓝色"))
        at = getattr(row, "alert_time", None)
        time_text = at.strftime("%m-%d %H:%M") if hasattr(at, "strftime") else "—"
        status = html.escape(str(getattr(row, "alert_status", "待确认")))
        message = html.escape(str(getattr(row, "message", "")))
        rows.append(f'<div class="cc-alert-item"><div class="cc-alert-head"><span class="cc-alert-level" style="color:{colors.get(level, "#83b8e6")}"><i class="cc-alert-dot"></i>{html.escape(level)} · {status}</span><span class="cc-alert-date">{html.escape(time_text)}</span></div><div class="cc-alert-msg">{message}</div></div>')
    return "".join(rows)


def render_command_center_home(set_public_page) -> None:
    inject_command_center_theme()
    summary = get_gis_summary()
    stats = get_dashboard_statistics()
    latest = get_latest_station_levels()
    snapshot = _runtime_snapshot(latest)
    alerts = query_alerts()
    if not alerts.empty:
        alerts = alerts[alerts["alert_status"] != "已解除"]
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    data_label = "演示水情" if DEMO_MODE or SEED_DEMO_DATA else "业务水情"
    st.markdown(
        f'''<div class="cc-intro"><div><div class="cc-kicker">WATER NETWORK · SITUATIONAL AWARENESS</div><div class="cc-title">看见河网，理解水势。</div><div class="cc-desc">以三维空间连接水情、工程与知识，让每一次研判有数据可查、每一步操作有依据可循。</div></div><div class="cc-date">{now:%Y.%m.%d}<small>北京时间 · 星期{"一二三四五六日"[now.weekday()]}</small></div></div><div class="cc-data-notice"><span class="cc-data-pill">{data_label}</span><span>水位数据更新于 {html.escape(get_latest_data_time())}</span><span>·</span><span>空间资料与水情数据分别标识，卫星影像不代表实时现场。</span></div>''',
        unsafe_allow_html=True,
    )
    cards = [
        ("河道空间对象", summary["river_count"], "≈", f'{summary["section_count"]} 个河道断面'),
        ("GIS 监测站点", summary["station_count"], "⌖", f'{snapshot["measured_station_count"]} 个业务站具有水位记录'),
        ("闸泵空间设施", summary["facility_count"], "▥", "工程点位资料"),
        ("待关注预警", len(alerts), "△", f'累计 {stats["prediction_count"]} 项预测任务'),
    ]
    for column, item in zip(st.columns(4, gap="medium"), cards):
        with column:
            metric_card(*item)

    st.markdown('<div class="cc-scene-heading"><div><h2>三维河网 · 空间态势</h2><p>卫星影像、地形与工程要素叠加，支持缩放、倾斜和对象定位。</p></div><span>XINWU · WUXI</span></div>', unsafe_allow_html=True)
    scene, details = st.columns([3.5, 1], gap="large")
    with scene:
        render_scene3d(latest=latest, height=590, key="home_scene", show_controls=False)
    with details:
        st.markdown(
            f'''<div class="cc-water"><div class="cc-side-title">水情摘要 · {data_label}</div><div class="cc-water-label">当前最高水位</div><div class="cc-water-value">{_number(snapshot["highest"])}<span class="cc-water-unit">m</span></div><div class="cc-water-note">{html.escape(snapshot["highest_station"])}</div><div class="cc-water-grid"><div><small>平均水位 / m</small><b>{_number(snapshot["average"])}</b></div><div><small>近 24h 站均降雨 / mm</small><b>{_number(snapshot["rainfall"], 1)}</b></div></div></div><div class="cc-side-title">预警关注 · {len(alerts)} 条未解除</div>{_alerts_html(alerts)}''',
            unsafe_allow_html=True,
        )
        if st.button("查看预警工作台 →", key="cc_alerts", width="stretch"):
            set_public_page("登录平台", "预警中心")
        st.caption("降雨按已载入的近 24 小时记录计算各雨量站累计值后取均值；缺测时不补零。")

    section_label("从这里开始")
    entries = [
        ("01 / EXPLORE", "实景三维", "在真实卫星影像和地形上定位站点、河道与闸泵，查看空间关系和数据来源。", "打开三维场景 →", "实景三维", None),
        ("02 / ASK", "水知 AI 助手", "检索平原感潮河网专业资料，追溯引用来源，或获取平台功能的逐步操作指引。", "向水知提问 →", "水知AI助手", None),
        ("03 / OPERATE", "协同业务工作台", "从数据检查到预测、调度和预警处置，在权限控制下完成日常业务流程。", "进入业务工作台 →", "登录平台", "平台首页"),
    ]
    for column, (index, title, description, label, destination, target) in zip(st.columns(3, gap="medium"), entries):
        with column:
            with st.container(border=True):
                st.markdown(f'<div class="cc-entry-index">{index}</div><div class="cc-entry-title">{title}</div><div class="cc-entry-desc">{description}</div>', unsafe_allow_html=True)
                if st.button(label, key=f"cc_entry_{destination}", width="stretch", type="primary" if destination == "实景三维" else "secondary"):
                    set_public_page(destination, target)

    section_label("业务快捷入口")
    actions = [("数据与资料", "数据中心"), ("水动力预测", "水动力预测"), ("智能调度", "智能调度"), ("风险预警", "预警中心")]
    for column, (label, target) in zip(st.columns(4, gap="medium"), actions):
        with column:
            if st.button(label, key=f"cc_work_{target}", width="stretch"):
                set_public_page("登录平台", target)
    st.caption("业务操作需要登录，并按角色授予权限。预测与调度的演示结果应与正式工程模型区分。")
    st.markdown(
        f'<div class="cc-source-note"><span>空间资料：项目站点、闸泵与河道数据 · 断面测点 {summary["section_point_count"]:,} 个</span><span>场景图层来源与加载状态可在三维视窗中查看</span></div>',
        unsafe_allow_html=True,
    )
