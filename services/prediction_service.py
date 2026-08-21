from __future__ import annotations

from datetime import datetime, timedelta
import json
import math
import uuid

import pandas as pd
from sqlalchemy import select

from database.engine import session_scope
from database.models import PredictionResult, PredictionTask
from services.gis_service import get_station_info, load_gis_stations


def run_demo_prediction(
    station_id: str,
    current_level: float,
    rainfall: float,
    tide_level: float,
    gate_factor: float,
    pump_factor: float,
    hours: int,
    created_by: str,
) -> dict:
    station_info = get_station_info(str(station_id))
    if station_info is None:
        raise ValueError(f"station_id={station_id} 不存在，请核对数据库或 data/gis/station.txt")

    code = f"PR-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:4]}"
    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    values: list[float] = []
    flows: list[float] = []
    times: list[datetime] = []

    for i in range(hours + 1):
        value = round(
            current_level
            + (rainfall / 100) * .62 * (1 - math.exp(-i / 7))
            + (tide_level - 3) * .12 * math.sin(i / 4.5)
            - (gate_factor * .11 + pump_factor * .15) * (i / max(hours, 1))
            + .04 * math.sin(i / 2.4),
            3,
        )
        times.append(start + timedelta(hours=i))
        values.append(value)
        flows.append(round(max(value, 0) * 12.5, 2))

    mx = max(values)
    risk = "红色" if mx >= 4.8 else "橙色" if mx >= 4.65 else "黄色" if mx >= 4.5 else "蓝色" if mx >= 4.35 else "正常"
    input_payload = {
        "station_name": station_info["station_name"],
        "station_lat": station_info["lat"],
        "station_lng": station_info["lng"],
        "coord_type": station_info.get("coord_type", "WGS84"),
        "data_source": station_info.get("data_source"),
        "current_level": current_level,
        "rainfall": rainfall,
        "tide_level": tide_level,
        "gate_factor": gate_factor,
        "pump_factor": pump_factor,
        "hours": hours,
    }

    with session_scope() as session:
        task = PredictionTask(
            task_code=code,
            station_id=str(station_id),
            model_type="新吴GIS水位模拟预测模型",
            input_json=json.dumps(input_payload, ensure_ascii=False),
            status="已完成",
            max_level=mx,
            risk_level=risk,
            created_by=created_by,
        )
        session.add(task)
        session.flush()
        session.add_all([
            PredictionResult(task_id=task.id, predict_time=t, predicted_level=v, predicted_flow=f)
            for t, v, f in zip(times, values, flows)
        ])

    return {
        "task_code": code,
        "station_id": str(station_id),
        "station_name": station_info["station_name"],
        "lat": station_info["lat"],
        "lng": station_info["lng"],
        "times": times,
        "values": values,
        "flows": flows,
        "max_level": mx,
        "risk_level": risk,
        "over_hours": sum(v > 4.5 for v in values),
        "gate_factor": gate_factor,
        "pump_factor": pump_factor,
    }


def _task_input(task: PredictionTask) -> dict:
    try:
        return json.loads(task.input_json or "{}")
    except Exception:
        return {}


def get_latest_prediction() -> dict | None:
    with session_scope() as session:
        task = session.scalar(select(PredictionTask).order_by(PredictionTask.id.desc()).limit(1))
        if not task:
            return None
        rows = session.scalars(
            select(PredictionResult)
            .where(PredictionResult.task_id == task.id)
            .order_by(PredictionResult.predict_time)
        ).all()

    station_info = get_station_info(task.station_id) or {}
    payload = _task_input(task)
    series = pd.DataFrame([
        {
            "predict_time": r.predict_time,
            "predicted_level": r.predicted_level,
            "predicted_flow": r.predicted_flow,
        }
        for r in rows
    ])
    return {
        "task_code": task.task_code,
        "station_id": task.station_id,
        "station_name": station_info.get("station_name", payload.get("station_name", "未知站点")),
        "lat": station_info.get("lat", payload.get("station_lat")),
        "lng": station_info.get("lng", payload.get("station_lng")),
        "max_level": task.max_level,
        "risk_level": task.risk_level,
        "created_at": task.created_at,
        "status": task.status,
        "gate_factor": float(payload.get("gate_factor", .4)),
        "pump_factor": float(payload.get("pump_factor", .4)),
        "over_hours": int((series["predicted_level"] > 4.5).sum()) if not series.empty else 0,
        "series": series,
    }


def list_prediction_tasks(limit: int = 50) -> pd.DataFrame:
    gis_map = {s["station_id"]: s for s in load_gis_stations()}
    with session_scope() as session:
        rows = session.scalars(select(PredictionTask).order_by(PredictionTask.id.desc()).limit(limit)).all()
    data = []
    for r in rows:
        info = gis_map.get(r.station_id) or get_station_info(r.station_id) or {}
        data.append({
            "task_code": r.task_code,
            "station_id": r.station_id,
            "station_name": info.get("station_name", "未知"),
            "station_lat": info.get("lat"),
            "station_lng": info.get("lng"),
            "model_type": r.model_type,
            "status": r.status,
            "max_level": r.max_level,
            "risk_level": r.risk_level,
            "created_by": r.created_by,
            "created_at": r.created_at,
        })
    return pd.DataFrame(data)
