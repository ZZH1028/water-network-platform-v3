"""Prepare georeferenced, source-labelled data for the 3D river-network scene."""
from __future__ import annotations

import ipaddress
import json
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

from core.config import BASE_DIR
from services.gis_service import load_gate_pump_points, load_gis_stations

IMAGERY_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
TERRAIN_URL = "https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer"


def validate_public_resource_url(value: str, *, allow_empty: bool = True) -> str:
    """Only permit credential-free HTTPS resource addresses intended for browsers.

    User-supplied services must be public. No server fetch is performed here, and
    backend API credentials must never be used as a browser scene URL.
    """
    value = str(value or "").strip()
    if not value and allow_empty:
        return ""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("三维资源地址格式无效") from exc
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("三维资源须为不含用户名、密码或片段的公开 HTTPS 地址")
    if port not in (None, 443):
        raise ValueError("三维资源须使用标准 HTTPS 端口")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")) or "." not in host:
        raise ValueError("三维资源不能指向本机或内部网络")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("三维资源不能指向本机或内部网络")
    return value


def safe_json_for_script(value) -> str:
    """Serialize without allowing data to terminate an inline script element."""
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _number(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _position(lng, lat) -> tuple[float, float] | None:
    longitude, latitude = _number(lng), _number(lat)
    if longitude is None or latitude is None or not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return None
    return longitude, latitude


def _runtime_rows(latest) -> list[dict]:
    if latest is None:
        return []
    if hasattr(latest, "to_dict"):
        return latest.to_dict("records")
    return list(latest)


def load_scene_rivers(path: Path | None = None) -> list[dict]:
    path = path or BASE_DIR / "data" / "gis" / "river_network_full.geojson"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rivers = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        # Original PlaneX/PlaneY section coordinates are deliberately excluded.
        if geometry.get("type") != "LineString" or props.get("display_crs") != "WGS84":
            continue
        coordinates = []
        for point in geometry.get("coordinates", []):
            position = _position(*(point[:2])) if isinstance(point, (list, tuple)) and len(point) >= 2 else None
            if position is None:
                coordinates = []
                break
            coordinates.append(list(position))
        if len(coordinates) < 2:
            continue
        rivers.append({"id": str(props.get("reach_id", len(rivers))),
                       "name": str(props.get("name", "未命名河道")),
                       "coordinates": coordinates,
                       "source": str(props.get("source_crs_note", "WGS84 显示坐标")),
                       "section_count": props.get("section_count")})
    return rivers


def build_scene_payload(latest=None, focus_station: str | None = None, runtime_facilities=None) -> dict:
    stations = {}
    for row in load_gis_stations():
        position = _position(row.get("lng"), row.get("lat"))
        if position is None:
            continue
        sid = str(row["station_id"])
        stations[sid] = {"id": sid, "name": row["station_name"],
                         "lng": position[0], "lat": position[1],
                         "source": "实测 GIS 站点 / station.txt", "water_level": None,
                         "warning_level": None, "monitor_time": "暂无业务水情", "status": "unknown"}
    for row in _runtime_rows(latest):
        sid = str(row.get("station_id", ""))
        if not sid:
            continue
        position = _position(row.get("longitude"), row.get("latitude"))
        station = stations.get(sid)
        if station is None:
            if position is None:
                continue
            station = {"id": sid, "name": str(row.get("station_name") or sid),
                       "lng": position[0], "lat": position[1],
                       "source": "业务数据库站点（开发模式可含演示数据）"}
        level, warning = _number(row.get("water_level")), _number(row.get("warning_level"))
        timestamp = row.get("monitor_time")
        timestamp = str(timestamp) if timestamp is not None and str(timestamp) not in ("NaT", "nan") else "暂无业务水情"
        station.update({"water_level": level, "warning_level": warning, "monitor_time": timestamp,
                        "status": "warning" if level is not None and warning is not None and level >= warning else "measured" if level is not None else "unknown"})
        stations[sid] = station
    facilities = []
    for row in load_gate_pump_points():
        position = _position(row.get("lng"), row.get("lat"))
        if position is not None:
            facilities.append({"id": "reference:" + str(row["facility_id"]), "display_id": str(row["facility_id"]), "name": row["facility_name"],
                               "lng": position[0], "lat": position[1], "kind": "reference",
                               "source": "闸泵实测位置 / gate_pump.txt", "status": "未提供业务工况",
                               "current_opening": None, "current_flow": None, "running": None,
                               "updated_at": "未提供", "environment": "静态实测位置资料"})
    omitted_facilities = 0
    for row in _runtime_rows(runtime_facilities):
        kind = str(row.get("kind", ""))
        identifier = str(row.get("facility_id", ""))
        position = _position(row.get("longitude"), row.get("latitude"))
        crs = str(row.get("coord_type") or "WGS84").upper().replace(" ", "")
        if kind not in ("gate", "pump") or not identifier or position is None or crs not in ("WGS84", "EPSG:4326"):
            omitted_facilities += 1
            continue
        facilities.append({"id": kind + ":" + identifier, "display_id": identifier, "name": str(row.get("name") or identifier),
                           "lng": position[0], "lat": position[1], "kind": kind,
                           "source": "业务数据库 · " + str(row.get("data_source") or "来源未填写"),
                           "status": str(row.get("status") or "未提供业务工况"),
                           "current_opening": _number(row.get("current_opening")),
                           "current_flow": _number(row.get("current_flow")),
                           "running": row.get("running") if isinstance(row.get("running"), bool) else None,
                           "updated_at": str(row.get("updated_at") or "未提供"),
                           "environment": str(row.get("environment") or "业务记录，非设备在线证明")})
    config_error = ""
    try:
        tileset_url = validate_public_resource_url(os.getenv("WATER_3D_TILESET_URL", ""))
    except ValueError as exc:
        config_error, tileset_url = str(exc), ""
    focus = stations.get(str(focus_station)) if focus_station is not None else None
    return {"stations": list(stations.values()), "facilities": facilities, "rivers": load_scene_rivers(),
            "omitted_facilities": omitted_facilities,
            "imagery_url": IMAGERY_URL, "terrain_url": TERRAIN_URL,
            "tileset_url": tileset_url, "config_error": config_error,
            "center": [120.425, 31.515],
            "focus": [focus["lng"], focus["lat"]] if focus else None,
            "sources": {"imagery": "Esri World Imagery · 真实卫星/航摄影像",
                        "terrain": "Esri WorldElevation3D · 全球地形服务（在线加载）",
                        "river": "EPSG:4528 转换后的 WGS84 河网显示坐标；仅作空间展示",
                        "sections": "river.txt 为本地平面坐标与吴淞高程，未作为椭球高直接叠加",
                        "precision": "全球影像与地形不等同于本地工程测绘；倾斜摄影需接入已配准的 3D Tiles。"}}
