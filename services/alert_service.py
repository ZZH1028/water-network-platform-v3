from __future__ import annotations

from datetime import datetime
import uuid

import pandas as pd
from sqlalchemy import select

from database.engine import session_scope
from database.models import Alert
from services.data_service import get_latest_station_levels
from services.log_service import add_log


def refresh_threshold_alerts() -> int:
    latest = get_latest_station_levels()
    created = 0
    with session_scope() as session:
        for row in latest.itertuples(index=False):
            if pd.isna(row.water_level) or pd.isna(row.warning_level):
                continue
            level, warning = float(row.water_level), float(row.warning_level)
            if level >= warning + .30:
                alert_level = "红色"
            elif level >= warning + .15:
                alert_level = "橙色"
            elif level >= warning:
                alert_level = "黄色"
            elif level >= warning - .15:
                alert_level = "蓝色"
            else:
                continue
            existing = session.scalar(
                select(Alert)
                .where(Alert.station_id == row.station_id, Alert.alert_status != "已解除")
                .order_by(Alert.id.desc())
                .limit(1)
            )
            if existing:
                continue
            session.add(Alert(
                alert_code=f"AL-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:4]}",
                station_id=row.station_id,
                alert_time=datetime.now(),
                alert_type="水位阈值预警",
                alert_level=alert_level,
                message=f"{row.station_name}当前水位{level:.2f} m，警戒水位{warning:.2f} m",
                alert_status="待确认",
            ))
            created += 1
    return created


def query_alerts(alert_level: str = "") -> pd.DataFrame:
    with session_scope() as session:
        stmt = select(Alert)
        if alert_level:
            stmt = stmt.where(Alert.alert_level == alert_level)
        rows = session.scalars(stmt.order_by(Alert.alert_time.desc())).all()
    return pd.DataFrame([{c.name: getattr(r, c.name) for c in Alert.__table__.columns} for r in rows])


def get_alert_by_id(alert_id: int) -> dict | None:
    with session_scope() as session:
        row = session.get(Alert, alert_id)
        return None if row is None else {c.name: getattr(row, c.name) for c in Alert.__table__.columns}


def update_alert_status(alert_id: int, status: str, username: str) -> bool:
    with session_scope() as session:
        row = session.get(Alert, alert_id)
        if row is None:
            return False
        old_status = row.alert_status
        row.alert_status = status
        row.handled_by = username
        row.handled_at = datetime.now()
    add_log(username, "预警处理", details=f"预警 {alert_id} 状态: {old_status} -> {status}", log_type="alert")
    return True
