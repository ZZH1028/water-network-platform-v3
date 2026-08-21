from __future__ import annotations

from datetime import datetime
import re
import uuid

import pandas as pd
from sqlalchemy import select, update

from database.engine import session_scope
from database.models import SchedulingPlan
from services.gis_service import load_gate_pump_points


def _constraint(constraints: dict, key: str, legacy_key: str, default: float) -> float:
    value = constraints.get(key, constraints.get(legacy_key, default))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_demo_plans(
    prediction: dict,
    weights: dict,
    constraints: dict,
    gate_factor: float | None = None,
    pump_factor: float | None = None,
) -> list[dict]:
    """Generate three GIS-aware demo plans while keeping the V1.0 call signature compatible."""
    batch = f"SC-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:4]}"
    mx = float(prediction["max_level"])
    sw = float(weights.get("防洪安全", 40))
    ew = float(weights.get("能耗控制", 10))
    gate_factor = float(prediction.get("gate_factor", .4) if gate_factor is None else gate_factor)
    pump_factor = float(prediction.get("pump_factor", .4) if pump_factor is None else pump_factor)

    facilities = load_gate_pump_points()
    facility_count = max(len(facilities), 1)
    max_gate_opening = _constraint(constraints, "max_gate_opening", "最大闸门开度", 100)
    max_pump_hours = _constraint(constraints, "max_pump_hours", "最大泵站运行时长", 24)

    station_id = prediction.get("station_id")
    station_name = prediction.get("station_name")
    station_lat = prediction.get("lat")
    station_lng = prediction.get("lng")

    drain_base = 70 + facility_count * 1.2
    pump_base = max(4, int(12 - pump_factor * 4))
    gate_base = max(2, int(6 + gate_factor * 3))

    plans = [
        {
            "plan_code": "A", "plan_name": "安全优先调度方案",
            "max_level": round(max(mx - .23 * max(gate_factor, .2), 0), 2),
            "drainage_volume": round(drain_base + sw * .12, 2),
            "energy_index": round(90 - ew * .3, 1),
            "gate_actions": min(gate_base + 2, facility_count), "pump_hours": min(pump_base + 7, max_pump_hours),
            "gate_recommendation": "主排闸80%，沿线辅助闸65%，同步开启", "pump_recommendation": "骨干泵站分时错峰持续运行",
            "score": round(88 + sw * .10 - ew * .03, 1),
        },
        {
            "plan_code": "B", "plan_name": "综合平衡调度方案",
            "max_level": round(max(mx - .17 * max(gate_factor, .2), 0), 2),
            "drainage_volume": round(drain_base + sw * .08, 2),
            "energy_index": round(70 - ew * .25, 1),
            "gate_actions": min(gate_base + 1, facility_count), "pump_hours": min(pump_base + 3, max_pump_hours),
            "gate_recommendation": "主排闸65%，支流辅助闸50%，间歇启闭", "pump_recommendation": "泵站轮换间歇运行",
            "score": round(90 + sw * .04 + ew * .02, 1),
        },
        {
            "plan_code": "C", "plan_name": "节能优先调度方案",
            "max_level": round(max(mx - .10 * max(gate_factor, .2), 0), 2),
            "drainage_volume": round(drain_base + sw * .04, 2),
            "energy_index": round(50 - ew * .2, 1),
            "gate_actions": min(max(gate_base - 1, 2), facility_count), "pump_hours": min(pump_base, max_pump_hours),
            "gate_recommendation": "主排闸50%，次要闸35%，按需启闭", "pump_recommendation": "核心泵站错峰间歇运行",
            "score": round(80 + ew * .12 + sw * .02, 1),
        },
    ]

    percent_pattern = re.compile(r"(\d+(?:\.\d+)?)%")
    for p in plans:
        openings = [float(x) for x in percent_pattern.findall(p["gate_recommendation"])]
        if openings and max(openings) > max_gate_opening:
            primary = max(0, round(max_gate_opening, 0))
            auxiliary = max(0, round(primary - 15, 0))
            p["gate_recommendation"] = f"主排闸{primary:.0f}%，辅助闸{auxiliary:.0f}%，控限运行"
        p.update({
            "batch_code": batch,
            "prediction_task_code": prediction["task_code"],
            "station_id": station_id,
            "station_name": station_name,
            "station_lat": station_lat,
            "station_lng": station_lng,
            "selected": False,
            "review_status": "待审核",
            "reviewed_by": None,
        })

    with session_scope() as session:
        session.add_all([SchedulingPlan(**p) for p in plans])
    return plans


def _rows_to_df(rows) -> pd.DataFrame:
    return pd.DataFrame([{c.name: getattr(r, c.name) for c in SchedulingPlan.__table__.columns} for r in rows])


def get_latest_plans() -> pd.DataFrame:
    with session_scope() as session:
        latest = session.scalar(select(SchedulingPlan.batch_code).order_by(SchedulingPlan.id.desc()).limit(1))
        if not latest:
            return pd.DataFrame()
        rows = session.scalars(
            select(SchedulingPlan).where(SchedulingPlan.batch_code == latest).order_by(SchedulingPlan.plan_code)
        ).all()
    return _rows_to_df(rows)


def get_plans_by_task_code(task_code: str) -> pd.DataFrame:
    with session_scope() as session:
        rows = session.scalars(
            select(SchedulingPlan)
            .where(SchedulingPlan.prediction_task_code == task_code)
            .order_by(SchedulingPlan.plan_code)
        ).all()
    return _rows_to_df(rows) if rows else pd.DataFrame()


def select_plan(plan_id: int, username: str) -> None:
    with session_scope() as session:
        row = session.get(SchedulingPlan, plan_id)
        if not row:
            return
        session.execute(update(SchedulingPlan).where(SchedulingPlan.batch_code == row.batch_code).values(selected=False))
        row.selected = True
        row.review_status = "已审核"
        row.reviewed_by = username
