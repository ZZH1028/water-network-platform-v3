from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

from sqlalchemy import delete as sa_delete, func, select as sa_select

from core.config import BACKUP_DIR
from database.engine import session_scope
from database.models import (
    Alert, FlowData, Gate, ModelRegistry, MonitoringStation, OperationLog,
    PredictionResult, PredictionTask, PumpStation, RainfallData, RiverReach,
    RiverSection, SchedulingPlan, TideData, UploadedFile, User, WaterLevelData,
)

# Dependency-safe insertion order. Deletion uses the reverse order.
ALL_TABLES = [
    User, MonitoringStation, RiverReach, RiverSection, Gate, PumpStation,
    WaterLevelData, FlowData, RainfallData, TideData,
    PredictionTask, PredictionResult, SchedulingPlan,
    Alert, OperationLog, ModelRegistry, UploadedFile,
]


def create_json_backup_extended() -> dict:
    payload = {"generated_at": datetime.now().isoformat(), "platform_version": "V1.1", "tables": {}}
    with session_scope() as session:
        for model in ALL_TABLES:
            rows = session.scalars(sa_select(model)).all()
            payload["tables"][model.__tablename__] = [
                {
                    c.name: (
                        getattr(r, c.name).isoformat()
                        if isinstance(getattr(r, c.name), datetime)
                        else getattr(r, c.name)
                    )
                    for c in model.__table__.columns
                }
                for r in rows
            ]
    content = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    target = BACKUP_DIR / f"platform_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    target.write_text(content, encoding="utf-8")
    checksum = hashlib.md5(content.encode("utf-8")).hexdigest()
    return {
        "path": str(target), "size": len(content.encode("utf-8")), "checksum": checksum,
        "generated_at": payload["generated_at"], "table_count": len(payload["tables"]),
    }


def verify_backup(backup_path: str) -> dict:
    path = Path(backup_path)
    if not path.exists():
        return {"valid": False, "error": f"文件不存在: {backup_path}"}
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as e:
        return {"valid": False, "error": f"备份读取/解析失败: {e}"}
    errors = []
    if "generated_at" not in data:
        errors.append("缺少 generated_at 字段")
    if not isinstance(data.get("tables"), dict):
        errors.append("缺少 tables 字段或格式不正确")
    checksum = hashlib.md5(content.encode("utf-8")).hexdigest()
    if errors:
        return {"valid": False, "error": "; ".join(errors), "checksum": checksum}
    known = {m.__tablename__ for m in ALL_TABLES}
    present = set(data["tables"])
    return {
        "valid": True,
        "checksum": checksum,
        "generated_at": data["generated_at"],
        "table_count": len(present),
        "known_table_count": len(present & known),
        "missing_optional_tables": sorted(known - present),
        "file_size": len(content.encode("utf-8")),
    }


def _parse_value(model, key: str, value):
    if value is None:
        return None
    column = model.__table__.columns.get(key)
    if column is None:
        return value
    if "date" in str(column.type).lower():
        try:
            return datetime.fromisoformat(str(value))
        except (ValueError, TypeError):
            return value
    return value


def restore_from_json(backup_path: str, overwrite: bool = False) -> dict:
    check = verify_backup(backup_path)
    if not check.get("valid"):
        return {"success": False, "error": check.get("error", "备份校验失败")}
    data = json.loads(Path(backup_path).read_text(encoding="utf-8"))
    tables = data.get("tables", {})
    stats: dict[str, int | str] = {}

    with session_scope() as session:
        if overwrite:
            for model in reversed(ALL_TABLES):
                if model.__tablename__ in tables:
                    session.execute(sa_delete(model))
            session.flush()

        for model in ALL_TABLES:
            tname = model.__tablename__
            if tname not in tables:
                stats[tname] = 0
                continue
            existing = session.scalar(sa_select(func.count()).select_from(model)) or 0
            if existing > 0 and not overwrite:
                stats[tname] = f"跳过（已有 {existing} 条）"
                continue
            rows = tables[tname]
            for row_dict in rows:
                parsed = {
                    k: _parse_value(model, k, v)
                    for k, v in row_dict.items()
                    if k in model.__table__.columns
                }
                session.add(model(**parsed))
            stats[tname] = len(rows)

    total = sum(v for v in stats.values() if isinstance(v, int))
    return {"success": True, "total_restored": total, "table_stats": stats}
