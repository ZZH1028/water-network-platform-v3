"""Coordinate, scene configuration and untrusted metadata boundaries."""
import json

import pandas as pd
import pytest

from services.scene_service import (
    build_scene_payload, load_scene_rivers, safe_json_for_script,
    validate_public_resource_url,
)
from ui.scene3d import build_scene_html


def test_real_local_scene_sources_and_geographic_ranges(monkeypatch):
    monkeypatch.delenv("WATER_3D_TILESET_URL", raising=False)
    scene = build_scene_payload()
    assert len(scene["stations"]) == 194
    assert len(scene["facilities"]) == 32
    assert len(scene["rivers"]) == 110
    assert {station["status"] for station in scene["stations"]} == {"unknown"}
    assert all(station["water_level"] is None for station in scene["stations"])
    assert not scene["tileset_url"]
    for station in scene["stations"]:
        assert 120.3 < station["lng"] < 120.6
        assert 31.4 < station["lat"] < 31.7
    for river in scene["rivers"]:
        assert "EPSG:4528" in river["source"]
        assert all(120.3 < lng < 120.6 and 31.4 < lat < 31.7 for lng, lat in river["coordinates"])
    assert "吴淞高程" in scene["sources"]["sections"]


def test_runtime_water_levels_join_by_station_id_and_keep_gis_coordinates():
    sid = build_scene_payload()["stations"][0]["id"]
    latest = pd.DataFrame([{"station_id": sid, "station_name": "运行记录", "longitude": None,
                            "latitude": None, "water_level": 4.8, "warning_level": 4.5,
                            "monitor_time": "2026-10-20 13:00:00"},
                           {"station_id": "DEMO01", "station_name": "开发演示站", "longitude": 120.4,
                            "latitude": 31.5, "water_level": 3.5, "warning_level": 4.5}])
    scene = build_scene_payload(latest, focus_station="DEMO01")
    stations = {station["id"]: station for station in scene["stations"]}
    assert len(stations) == 195
    assert stations[sid]["status"] == "warning"
    assert stations[sid]["water_level"] == 4.8
    assert stations[sid]["source"].startswith("实测 GIS")
    assert stations["DEMO01"]["status"] == "measured"
    assert "演示" in stations["DEMO01"]["source"]
    assert scene["focus"] == [120.4, 31.5]


def test_nonfinite_numbers_do_not_become_measured_or_break_json():
    scene = build_scene_payload([{"station_id": "finite", "longitude": 120.4, "latitude": 31.5,
                                  "water_level": float("nan"), "warning_level": float("inf")},
                                 {"station_id": "invalid", "longitude": float("nan"), "latitude": 31.5}])
    stations = {station["id"]: station for station in scene["stations"]}
    assert "invalid" not in stations
    assert stations["finite"]["water_level"] is None
    assert stations["finite"]["status"] == "unknown"
    assert json.loads(safe_json_for_script(scene))["stations"]


def test_business_gate_and_pump_keep_actual_fields_and_do_not_collide_with_reference_ids():
    scene = build_scene_payload(runtime_facilities=[
        {"kind": "gate", "facility_id": "1", "name": "导入闸门", "longitude": 120.4,
         "latitude": 31.5, "current_opening": 42.5, "status": "检修", "data_source": "工程导入"},
        {"kind": "pump", "facility_id": "1", "name": "业务泵站", "longitude": 120.42,
         "latitude": 31.51, "current_flow": 18.2, "running": False, "data_source": "demo",
         "environment": "演示环境"},
    ])
    facilities = {row["id"]: row for row in scene["facilities"]}
    assert len(facilities) == 34
    assert {"reference:1", "gate:1", "pump:1"}.issubset(facilities)
    assert facilities["gate:1"]["current_opening"] == 42.5
    assert facilities["gate:1"]["status"] == "检修"
    assert facilities["gate:1"]["running"] is None
    assert facilities["pump:1"]["current_flow"] == 18.2
    assert facilities["pump:1"]["running"] is False
    assert facilities["pump:1"]["source"] == "业务数据库 · demo"
    assert facilities["pump:1"]["environment"] == "演示环境"
    assert facilities["reference:1"]["status"] == "未提供业务工况"


def test_facilities_with_invalid_or_unconverted_coordinates_are_not_falsely_positioned():
    scene = build_scene_payload(runtime_facilities=[
        {"kind": "gate", "facility_id": "unconverted", "longitude": 40520000, "latitude": 3480000},
        {"kind": "pump", "facility_id": "wrong-crs", "longitude": 120.4, "latitude": 31.5, "coord_type": "GCJ02"},
    ])
    assert len(scene["facilities"]) == 32
    assert scene["omitted_facilities"] == 2


@pytest.mark.parametrize("url", ["http://example.com/tileset.json", "https://localhost/a", "https://127.0.0.1/a",
                                 "https://[::1]/a", "https://10.10.0.1/a", "https://service.internal/a",
                                 "https://u:password@example.com/a", "https://example.com:8080/a", "javascript:alert(1)",
                                 "https://example.com/#fragment"])
def test_scene_configuration_rejects_nonpublic_or_credentialled_urls(url):
    with pytest.raises(ValueError):
        validate_public_resource_url(url)


def test_resource_url_keeps_signed_public_https_query():
    url = "https://terrain.example.org/project/tileset.json?token=browser-public-token"
    assert validate_public_resource_url(url) == url


def test_invalid_resource_configuration_fails_visibly_without_exposing_value(monkeypatch):
    monkeypatch.setenv("WATER_3D_TILESET_URL", "https://user:secret-password@localhost/tileset.json")
    scene = build_scene_payload()
    assert scene["config_error"]
    assert scene["tileset_url"] == ""
    assert "secret-password" not in safe_json_for_script(scene)


def test_geojson_without_explicit_wgs84_or_with_invalid_coordinates_is_not_drawn(tmp_path):
    path = tmp_path / "rivers.geojson"
    path.write_text(json.dumps({"features": [
        {"geometry": {"type": "LineString", "coordinates": [[40520000, 3480000], [40530000, 3490000]]}, "properties": {}},
        {"geometry": {"type": "LineString", "coordinates": [[120.4, 31.5], [400, 31.6]]}, "properties": {"display_crs": "WGS84"}},
        {"geometry": {"type": "LineString", "coordinates": [[120.4, 31.5], [120.5, 31.6]]}, "properties": {"display_crs": "WGS84", "name": "真实转换河线"}},
    ]}), encoding="utf-8")
    rivers = load_scene_rivers(path)
    assert len(rivers) == 1
    assert rivers[0]["name"] == "真实转换河线"


def test_untrusted_metadata_cannot_terminate_scene_script():
    unsafe = "</script><script>alert('metadata')</script>&\u2028"
    scene = build_scene_payload()
    scene["stations"][0]["name"] = unsafe
    serialized = safe_json_for_script(scene)
    assert "</script>" not in serialized
    assert "\\u003c" in serialized
    assert json.loads(serialized)["stations"][0]["name"] == unsafe
    document = build_scene_html(scene)
    assert document.count("<script>") == 1
    assert document.count("</script>") == 1
    assert "scene3DOnly:true" in document
    assert "sceneModePicker:false" in document
    assert "source-line" in document
    assert "椭球回退" in document
    assert "当前没有建筑级倾斜摄影实景" in document
