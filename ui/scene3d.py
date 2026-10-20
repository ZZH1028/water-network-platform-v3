"""Cesium 3D scene with real imagery, independently reported terrain and 3D Tiles."""
from __future__ import annotations

import streamlit as st
from streamlit.components.v1 import declare_component

from core.config import BASE_DIR, DEMO_MODE
from services.scene_service import build_scene_payload, safe_json_for_script

_scene_component = declare_component("water_scene3d", path=str(BASE_DIR / "static" / "scene3d"))


def build_scene_html(payload: dict, height: int = 620) -> str:
    """Return an escaped standalone test/export document from the shared template.

    Production uses the real HTTP component path and Streamlit render messages;
    this helper never writes business payloads to a shared static HTML file.
    """
    template = (BASE_DIR / "static" / "scene3d" / "index.html").read_text(encoding="utf-8")
    return template.replace("const INITIAL_DATA = null;", "const INITIAL_DATA = " + safe_json_for_script(payload) + ";")


def _load_runtime_facilities() -> list[dict]:
    """Read existing business facilities at the UI boundary, never in pure payload tests."""
    from sqlalchemy import select
    from database.engine import session_scope
    from database.models import Gate, PumpStation

    rows = []
    environment = "演示开发环境 · 业务字段不等同于设备实时在线状态" if DEMO_MODE else "业务记录 · 非设备实时在线证明"
    with session_scope() as session:
        for gate in session.scalars(select(Gate)).all():
            rows.append({"kind": "gate", "facility_id": gate.gate_id, "name": gate.gate_name,
                         "longitude": gate.longitude, "latitude": gate.latitude,
                         "coord_type": gate.coord_type, "data_source": gate.data_source,
                         "status": gate.status, "current_opening": gate.current_opening,
                         "updated_at": gate.updated_at, "environment": environment})
        for pump in session.scalars(select(PumpStation)).all():
            rows.append({"kind": "pump", "facility_id": pump.pump_id, "name": pump.pump_name,
                         "longitude": pump.longitude, "latitude": pump.latitude,
                         "coord_type": pump.coord_type, "data_source": pump.data_source,
                         "status": pump.status, "current_flow": pump.current_flow, "running": pump.running,
                         "updated_at": pump.updated_at, "environment": environment})
    return rows


def render_scene3d(latest=None, height: int = 620, key: str = "scene3d",
                   focus_station: str | None = None, show_controls: bool = True) -> None:
    """Render a 3D scene; `latest` accepts the existing station DataFrame or rows."""
    payload = build_scene_payload(latest=latest, focus_station=focus_station,
                                  runtime_facilities=_load_runtime_facilities())
    if show_controls:
        stations = payload["stations"]
        options = [""] + [station["id"] for station in stations]
        names = {station["id"]: station["name"] for station in stations}
        chosen = st.selectbox("空间定位", options, format_func=lambda sid: "全域河网" if not sid else f"{names[sid]} · {sid}", key=f"{key}_focus", index=options.index(str(focus_station)) if str(focus_station) in options else 0)
        if chosen:
            station = next(row for row in stations if row["id"] == chosen)
            payload["focus"] = [station["lng"], station["lat"]]
    asset = BASE_DIR / "static" / "cesium" / "Build" / "Cesium" / "Cesium.js"
    if not asset.is_file():
        st.error("三维引擎资源尚未安装。请运行项目安装步骤准备 Cesium 静态资源。")
        return
    _scene_component(payload=payload, height=max(340, min(int(height), 1200)), key=key, default=None)
    with st.expander("场景数据来源与精度", expanded=False):
        st.markdown("**真实卫星/航摄影像 + 在线地形**构成三维地球场景。建筑级倾斜摄影需接入已配准的 3D Tiles；未接入时不会生成或伪装真实建筑。")
        st.caption(" · ".join(payload["sources"].values()))
        if payload["omitted_facilities"]:
            st.warning(f"{payload['omitted_facilities']} 条业务设施缺少有效 WGS84 经纬度，未叠加到地球场景。请先核对坐标。")
        if payload["config_error"]:
            st.warning(payload["config_error"])
        elif payload["tileset_url"]:
            st.caption("已配置倾斜摄影服务，实际加载结果以场景右上角状态为准。")
        else:
            st.caption("倾斜摄影暂未接入。后续可在环境配置 WATER_3D_TILESET_URL，使用具备浏览器跨域访问许可的公开 HTTPS 3D Tiles 地址。")
