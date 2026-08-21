from __future__ import annotations

from datetime import datetime
import pandas as pd
from sqlalchemy import select

from database.engine import session_scope
from database.models import OperationLog


def add_log(username: str, action: str, result: str = "成功", details: str = "", client_ip: str = "", log_type: str = "") -> None:
    with session_scope() as session:
        session.add(OperationLog(
            operation_time=datetime.now(),
            username=username,
            action=action,
            result=result,
            details=details,
            client_ip=client_ip or None,
            log_type=log_type or None,
        ))


def query_logs(limit: int = 200, log_type: str = "") -> pd.DataFrame:
    with session_scope() as session:
        stmt = select(OperationLog).order_by(OperationLog.id.desc()).limit(limit)
        if log_type:
            stmt = stmt.where(OperationLog.log_type == log_type)
        rows = session.scalars(stmt).all()
    return pd.DataFrame([{
        "时间": r.operation_time, "用户": r.username, "操作": r.action,
        "类型": r.log_type, "结果": r.result, "说明": r.details, "IP": r.client_ip,
    } for r in rows])
