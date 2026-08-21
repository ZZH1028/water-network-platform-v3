from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from core.config import BASE_DIR
from database.engine import session_scope
from database.models import MonitoringStation
from sqlalchemy import select

GIS_ROOT = BASE_DIR / "data" / "gis"
STATION_TXT = GIS_ROOT / "station.txt"
GATEPUMP_TXT = GIS_ROOT / "gate_pump.txt"
RIVER_TXT = GIS_ROOT / "river.txt"


def _to_float(value: str) -> float:
    return float(str(value).strip())


@lru_cache(maxsize=1)
def load_gis_stations() -> tuple[dict, ...]:
    if not STATION_TXT.exists():
        return tuple()
    rows: list[dict] = []
    with STATION_TXT.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "station_id": str(row["StationID"]).strip(),
                "station_name": str(row["StationName"]).strip(),
                "lat": _to_float(row["Latitude"]),
                "lng": _to_float(row["Longitude"]),
                "coord_type": "WGS84",
                "data_source": "新吴实测station.txt",
            })
    return tuple(rows)


@lru_cache(maxsize=1)
def load_gate_pump_points() -> tuple[dict, ...]:
    if not GATEPUMP_TXT.exists():
        return tuple()
    rows: list[dict] = []
    with GATEPUMP_TXT.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "facility_id": str(row["GatePumpID"]).strip(),
                "facility_name": str(row["GatePumpName"]).strip(),
                "lat": _to_float(row["Latitude"]),
                "lng": _to_float(row["Longitude"]),
                "coord_type": "WGS84",
                "data_source": "新吴实测gate_pump.txt",
            })
    return tuple(rows)


@lru_cache(maxsize=1)
def load_river_sections() -> tuple[dict, ...]:
    if not RIVER_TXT.exists():
        return tuple()
    rows: list[dict] = []
    counters: dict[tuple[str, str], int] = {}
    with RIVER_TXT.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            reach_id = str(row["RiverID"]).strip()
            section_id = str(row["SectionID"]).strip()
            key = (reach_id, section_id)
            counters[key] = counters.get(key, 0) + 1
            rows.append({
                "reach_id": reach_id,
                "reach_name": str(row["RiverName"]).strip(),
                "section_id": section_id,
                "point_no": counters[key],
                "plane_x": _to_float(row["PlaneX"]),
                "plane_y": _to_float(row["PlaneY"]),
                "wusong_elev": _to_float(row["Elevation"]),
                "coord_type": "新吴本地平面坐标系",
                "data_source": "新吴实测river.txt",
            })
    return tuple(rows)


def get_station_info(station_id: str) -> dict | None:
    sid = str(station_id)
    for item in load_gis_stations():
        if item["station_id"] == sid:
            return dict(item)
    # Keep V1.0 demo/imported database stations compatible with the new GIS-aware model service.
    with session_scope() as session:
        row = session.scalar(select(MonitoringStation).where(MonitoringStation.station_id == sid).limit(1))
        if row is None:
            return None
        return {
            "station_id": row.station_id,
            "station_name": row.station_name,
            "lat": row.latitude,
            "lng": row.longitude,
            "coord_type": row.coord_type or "WGS84",
            "data_source": row.data_source,
        }


def get_gis_summary() -> dict:
    stations = load_gis_stations()
    facilities = load_gate_pump_points()
    sections = load_river_sections()
    reaches = {(r["reach_id"], r["reach_name"]) for r in sections}
    section_keys = {(r["reach_id"], r["section_id"]) for r in sections}
    return {
        "station_count": len(stations),
        "facility_count": len(facilities),
        "river_count": len(reaches),
        "section_count": len(section_keys),
        "section_point_count": len(sections),
    }
