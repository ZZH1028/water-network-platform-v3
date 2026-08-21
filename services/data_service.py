from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
import json
import random
import shutil
import uuid
import zipfile

import pandas as pd
from sqlalchemy import func, select

from core.config import UPLOAD_DIR, EXPORT_DIR, BACKUP_DIR
from database.engine import session_scope
from database.models import (
    MonitoringStation, RiverReach, Gate, PumpStation,
    WaterLevelData, FlowData, RainfallData, TideData,
    Alert, PredictionTask, UploadedFile, User,
)

DATASET_CONFIG = {
    "监测站信息": {"model": MonitoringStation, "required": ["station_id","station_name","longitude","latitude","station_type"]},
    "水位数据": {"model": WaterLevelData, "required": ["station_id","monitor_time","water_level"]},
    "流量数据": {"model": FlowData, "required": ["station_id","monitor_time","flow_value"]},
    "降雨数据": {"model": RainfallData, "required": ["station_id","monitor_time","rainfall"]},
    "潮位数据": {"model": TideData, "required": ["station_id","monitor_time","tide_level"]},
    "闸门信息": {"model": Gate, "required": ["gate_id","gate_name","longitude","latitude"]},
    "泵站信息": {"model": PumpStation, "required": ["pump_id","pump_name","longitude","latitude"]},
}

TIME_SERIES_TYPES = {"水位数据", "流量数据", "降雨数据", "潮位数据"}
ENTITY_TYPES = {"监测站信息", "闸门信息", "泵站信息"}

COLUMN_MAPPING = {
    "测站编码":"station_id", "站点编码":"station_id", "监测站名称":"station_name",
    "站点名称":"station_name", "监测时间":"monitor_time", "采集时间":"monitor_time",
    "实时水位":"water_level", "水位":"water_level", "流量":"flow_value",
    "降雨量":"rainfall", "潮位":"tide_level", "经度":"longitude", "纬度":"latitude",
    "站点类型":"station_type", "警戒水位":"warning_level", "数据来源":"data_source",
    "闸门编号":"gate_id", "闸门名称":"gate_name", "泵站编号":"pump_id", "泵站名称":"pump_name",
}


@dataclass
class ImportResult:
    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict] = field(default_factory=list)


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("仅支持CSV、XLSX和XLS文件。")
    return df.rename(columns={c: COLUMN_MAPPING.get(str(c).strip(), str(c).strip()) for c in df.columns})


def _load_valid_station_ids() -> set[str]:
    with session_scope() as session:
        rows = session.scalars(select(MonitoringStation.station_id)).all()
    return set(rows)


def validate_row(dataset_type: str, row: dict, row_index: int, valid_station_ids: set[str]) -> list[dict]:
    errors = []
    config = DATASET_CONFIG[dataset_type]
    required = config["required"]
    excel_row = row_index + 1

    for field in required:
        val = row.get(field)
        if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
            errors.append({"row": excel_row, "field": field, "error": "必填字段缺失"})

    if dataset_type in TIME_SERIES_TYPES and "station_id" in row:
        sid = str(row.get("station_id", ""))
        if sid and sid not in valid_station_ids:
            errors.append({"row": excel_row, "field": "station_id", "error": f"站点 {sid} 在监测站表中不存在"})

    if "monitor_time" in row and "monitor_time" in config["required"]:
        mt = row.get("monitor_time")
        if mt is not None and not (isinstance(mt, float) and pd.isna(mt)):
            try:
                pd.Timestamp(mt)
            except Exception:
                errors.append({"row": excel_row, "field": "monitor_time", "error": "无法识别的日期时间格式"})

    numeric_fields = {
        "longitude": (-180, 180), "latitude": (-90, 90),
        "water_level": None, "flow_value": None, "rainfall": None, "tide_level": None,
        "warning_level": None, "max_opening": None, "current_opening": None,
        "design_flow": None, "current_flow": None,
    }
    for nf, bounds in numeric_fields.items():
        if nf in row:
            val = row[nf]
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                try:
                    num = float(val)
                    if bounds:
                        lo, hi = bounds
                        if num < lo or num > hi:
                            errors.append({"row": excel_row, "field": nf, "error": f"值 {num} 超出范围[{lo},{hi}]"})
                except (ValueError, TypeError):
                    errors.append({"row": excel_row, "field": nf, "error": f"非数字内容: {val}"})

    return errors


def validate_dataframe(dataset_type: str, df: pd.DataFrame) -> tuple[list[str], list[dict]]:
    config = DATASET_CONFIG[dataset_type]
    required = config["required"]
    summary_errors = []
    row_errors = []

    missing = [c for c in required if c not in df.columns]
    if missing:
        return [f"缺少必填字段：{', '.join(missing)}"], []
    if df.empty:
        return ["文件中没有数据。"], []

    valid_station_ids = _load_valid_station_ids()

    for pos, (_, row) in enumerate(df.iterrows()):
        errs = validate_row(dataset_type, row.to_dict(), pos, valid_station_ids)
        row_errors.extend(errs)

    if row_errors:
        failed_rows = sorted(set(e["row"] for e in row_errors))
        summary_errors.append(f"共 {len(failed_rows)} 行存在数据问题（行号: {failed_rows[:20]}{'...' if len(failed_rows) > 20 else ''}）")

    for col in [c for c in df.columns if c.endswith("_time")]:
        if pd.to_datetime(df[col], errors="coerce").isna().any():
            summary_errors.append(f"{col}存在无法识别的日期时间。")

    return summary_errors, row_errors


def _save_upload_copy(uploaded_file, dataset_type: str, username: str) -> tuple[str, int]:
    suffix = Path(uploaded_file.name).suffix.lower()
    stored_name = f"{datetime.now():%Y%m%d_%H%M%S}_{username}_{uuid.uuid4().hex[:8]}{suffix}"
    content = uploaded_file.getvalue()
    (UPLOAD_DIR / stored_name).write_bytes(content)
    with session_scope() as session:
        session.add(UploadedFile(stored_name=stored_name, original_name=uploaded_file.name, dataset_type=dataset_type, uploaded_by=username, file_size=len(content), import_status="已保存"))
    return stored_name, len(content)


def import_with_validation(dataset_type: str, df: pd.DataFrame, username: str = "system", uploaded_file=None) -> ImportResult:
    result = ImportResult(total_rows=len(df))
    config = DATASET_CONFIG[dataset_type]
    model = config["model"]
    valid_station_ids = _load_valid_station_ids()
    seen_keys = set()

    if uploaded_file is not None:
        _save_upload_copy(uploaded_file, dataset_type, username)

    invalid_row_indices = set()
    for pos, (_, row) in enumerate(df.iterrows()):
        errs = validate_row(dataset_type, row.to_dict(), pos, valid_station_ids)
        if errs:
            result.errors.extend(errs)
            invalid_row_indices.add(pos)

    data = df.copy()
    with session_scope() as session:
        for pos, (_, row) in enumerate(data.iterrows()):
            if pos in invalid_row_indices:
                continue
            row_dict = row.to_dict()

            if model is MonitoringStation:
                obj = session.scalar(select(model).where(model.station_id == str(row_dict["station_id"])))
                values = dict(station_name=str(row_dict["station_name"]), longitude=float(row_dict["longitude"]), latitude=float(row_dict["latitude"]), station_type=str(row_dict["station_type"]), warning_level=float(row_dict["warning_level"]) if pd.notna(row_dict.get("warning_level")) else None, data_source=str(row_dict.get("data_source","file_upload")))
            elif model is Gate:
                obj = session.scalar(select(model).where(model.gate_id == str(row_dict["gate_id"])))
                values = dict(gate_name=str(row_dict["gate_name"]), longitude=float(row_dict["longitude"]), latitude=float(row_dict["latitude"]), max_opening=float(row_dict.get("max_opening",100)), current_opening=float(row_dict.get("current_opening",0)), status=str(row_dict.get("status","正常")))
            elif model is PumpStation:
                obj = session.scalar(select(model).where(model.pump_id == str(row_dict["pump_id"])))
                values = dict(pump_name=str(row_dict["pump_name"]), longitude=float(row_dict["longitude"]), latitude=float(row_dict["latitude"]), design_flow=float(row_dict["design_flow"]) if pd.notna(row_dict.get("design_flow")) else None, current_flow=float(row_dict.get("current_flow",0)), running=bool(row_dict.get("running",False)), status=str(row_dict.get("status","正常")))
            else:
                sid, t = str(row_dict["station_id"]), pd.Timestamp(row_dict["monitor_time"]).to_pydatetime()
                key = (sid, t)
                if key in seen_keys:
                    result.skipped += 1
                    continue
                seen_keys.add(key)
                obj = session.scalar(select(model).where(model.station_id == sid, model.monitor_time == t))
                if model is WaterLevelData:
                    values = dict(water_level=float(row_dict["water_level"]), quality_flag=str(row_dict.get("quality_flag","normal")), data_source=str(row_dict.get("data_source","file_upload")))
                elif model is FlowData:
                    values = dict(flow_value=float(row_dict["flow_value"]), quality_flag=str(row_dict.get("quality_flag","normal")), data_source=str(row_dict.get("data_source","file_upload")))
                elif model is RainfallData:
                    values = dict(rainfall=float(row_dict["rainfall"]), data_source=str(row_dict.get("data_source","file_upload")))
                else:
                    values = dict(tide_level=float(row_dict["tide_level"]), data_source=str(row_dict.get("data_source","file_upload")))

            if obj is None:
                if model is MonitoringStation:
                    obj = model(station_id=str(row_dict["station_id"]), **values)
                elif model is Gate:
                    obj = model(gate_id=str(row_dict["gate_id"]), **values)
                elif model is PumpStation:
                    obj = model(pump_id=str(row_dict["pump_id"]), **values)
                else:
                    obj = model(station_id=sid, monitor_time=t, **values)
                session.add(obj)
                result.inserted += 1
            else:
                all_same = all(getattr(obj, k, None) == v for k, v in values.items())
                if all_same:
                    result.skipped += 1
                else:
                    for key, value in values.items():
                        setattr(obj, key, value)
                    result.updated += 1

    return result


def save_dataframe(dataset_type: str, df: pd.DataFrame, username: str = "system", uploaded_file=None) -> int:
    result = import_with_validation(dataset_type, df, username, uploaded_file)
    return result.inserted + result.updated


def query_table(dataset_type: str, limit: int = 5000) -> pd.DataFrame:
    model = DATASET_CONFIG[dataset_type]["model"]
    with session_scope() as session:
        rows = session.scalars(select(model).order_by(model.id.desc()).limit(limit)).all()
    return pd.DataFrame([{c.name: getattr(r, c.name) for c in model.__table__.columns} for r in rows])


def get_station_options() -> pd.DataFrame:
    with session_scope() as session:
        rows = session.scalars(select(MonitoringStation).order_by(MonitoringStation.station_id)).all()
    return pd.DataFrame([{"station_id":r.station_id,"station_name":r.station_name,"longitude":r.longitude,"latitude":r.latitude,"station_type":r.station_type,"warning_level":r.warning_level} for r in rows])


def get_latest_station_levels() -> pd.DataFrame:
    with session_scope() as session:
        stations = session.scalars(select(MonitoringStation).order_by(MonitoringStation.station_id)).all()
        result = []
        for s in stations:
            latest = session.scalar(select(WaterLevelData).where(WaterLevelData.station_id == s.station_id).order_by(WaterLevelData.monitor_time.desc()).limit(1))
            result.append({"station_id":s.station_id,"station_name":s.station_name,"longitude":s.longitude,"latitude":s.latitude,"station_type":s.station_type,"warning_level":s.warning_level,"monitor_time":latest.monitor_time if latest else None,"water_level":latest.water_level if latest else None,"quality_flag":latest.quality_flag if latest else None})
    return pd.DataFrame(result)


def _series(model, value_field: str, station_id: str | None, hours: int) -> pd.DataFrame:
    stmt = select(model).order_by(model.monitor_time.desc()).limit(hours if station_id else hours*2)
    if station_id:
        stmt = stmt.where(model.station_id == station_id)
    with session_scope() as session:
        rows = session.scalars(stmt).all()
    return pd.DataFrame([{"monitor_time":r.monitor_time, value_field:getattr(r,value_field), "station_id":r.station_id} for r in reversed(rows)])


def get_water_level_series(station_id: str, hours: int = 72): return _series(WaterLevelData,"water_level",station_id,hours)
def get_flow_series(station_id: str, hours: int = 72): return _series(FlowData,"flow_value",station_id,hours)
def get_rainfall_series(hours: int = 72): return _series(RainfallData,"rainfall",None,hours)
def get_tide_series(hours: int = 72): return _series(TideData,"tide_level",None,hours)


def get_dashboard_statistics() -> dict:
    with session_scope() as session:
        return {
            "river_count": session.scalar(select(func.count()).select_from(RiverReach)) or 0,
            "station_count": session.scalar(select(func.count()).select_from(MonitoringStation)) or 0,
            "gate_count": session.scalar(select(func.count()).select_from(Gate)) or 0,
            "pump_count": session.scalar(select(func.count()).select_from(PumpStation)) or 0,
            "alert_count": session.scalar(select(func.count()).select_from(Alert).where(Alert.alert_status != "已解除")) or 0,
            "prediction_count": session.scalar(select(func.count()).select_from(PredictionTask)) or 0,
        }


def get_latest_data_time() -> str:
    with session_scope() as session:
        value = session.scalar(select(func.max(WaterLevelData.monitor_time)))
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "暂无数据"


def simulate_realtime_update() -> int:
    latest = get_latest_station_levels()
    now = datetime.now().replace(microsecond=0)
    with session_scope() as session:
        for row in latest.itertuples(index=False):
            if row.station_type != "水位站":
                continue
            base = float(row.water_level) if pd.notna(row.water_level) else 3.7
            new_level = round(base + random.uniform(-0.025,0.045),3)
            session.add(WaterLevelData(station_id=row.station_id, monitor_time=now, water_level=new_level, quality_flag="warning" if pd.notna(row.warning_level) and new_level >= float(row.warning_level) else "normal", data_source="realtime_simulation"))
    return int((latest["station_type"] == "水位站").sum())


def create_json_backup() -> Path:
    tables = [MonitoringStation,RiverReach,Gate,PumpStation,WaterLevelData,FlowData,RainfallData,TideData,Alert,PredictionTask,UploadedFile,User]
    payload = {"generated_at":datetime.now().isoformat(),"tables":{}}
    with session_scope() as session:
        for model in tables:
            rows = session.scalars(select(model)).all()
            payload["tables"][model.__tablename__] = [{c.name:(getattr(r,c.name).isoformat() if isinstance(getattr(r,c.name),datetime) else getattr(r,c.name)) for c in model.__table__.columns} for r in rows]
    target = BACKUP_DIR / f"platform_export_{datetime.now():%Y%m%d_%H%M%S}.json"
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    return target


# -- Export Functions --

def _build_export_query(dataset_type: str, station_id: str | None = None, date_from: str | None = None, date_to: str | None = None):
    config = DATASET_CONFIG[dataset_type]
    model = config["model"]
    stmt = select(model)
    if station_id and hasattr(model, "station_id"):
        stmt = stmt.where(model.station_id == station_id)
    if date_from and hasattr(model, "monitor_time"):
        stmt = stmt.where(model.monitor_time >= pd.Timestamp(date_from).to_pydatetime())
    if date_to and hasattr(model, "monitor_time"):
        stmt = stmt.where(model.monitor_time <= pd.Timestamp(date_to).to_pydatetime())
    stmt = stmt.order_by(model.id.asc())
    return model, stmt


def _query_to_dataframe(model, stmt) -> pd.DataFrame:
    with session_scope() as session:
        rows = session.scalars(stmt).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{c.name: getattr(r, c.name) for c in model.__table__.columns} for r in rows])


def export_table(dataset_type: str, format: str = "csv", station_id: str | None = None, date_from: str | None = None, date_to: str | None = None) -> Path:
    if dataset_type not in DATASET_CONFIG:
        raise ValueError(f"未知数据集类型: {dataset_type}")
    model, stmt = _build_export_query(dataset_type, station_id, date_from, date_to)
    df = _query_to_dataframe(model, stmt)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "csv":
        target = EXPORT_DIR / f"{dataset_type}_{stamp}.csv"
        df.to_csv(target, index=False, encoding="utf-8-sig")
    elif format == "xlsx":
        target = EXPORT_DIR / f"{dataset_type}_{stamp}.xlsx"
        df.to_excel(target, index=False, engine="openpyxl")
    else:
        raise ValueError(f"不支持的格式: {format}")
    return target


def export_all_tables(format: str = "csv") -> Path:
    if format not in ("csv", "xlsx"):
        raise ValueError(f"不支持的格式: {format}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = EXPORT_DIR / f"全部数据_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dtype in DATASET_CONFIG:
            try:
                model, stmt = _build_export_query(dtype)
                df = _query_to_dataframe(model, stmt)
                if df.empty:
                    continue
                bio = BytesIO()
                if format == "csv":
                    df.to_csv(bio, index=False, encoding="utf-8-sig")
                    fname = f"{dtype}.csv"
                else:
                    df.to_excel(bio, index=False, engine="openpyxl")
                    fname = f"{dtype}.xlsx"
                zf.writestr(fname, bio.getvalue())
            except Exception:
                continue
    return zip_path
