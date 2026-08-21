from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="查看用户")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MonitoringStation(Base, TimestampMixin):
    __tablename__ = "monitoring_stations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    station_name: Mapped[str] = mapped_column(String(128))
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    station_type: Mapped[str] = mapped_column(String(32))
    warning_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_source: Mapped[str] = mapped_column(String(128), default="manual")
    coord_type: Mapped[str | None] = mapped_column(String(30), default="WGS84", nullable=True)


class RiverReach(Base, TimestampMixin):
    __tablename__ = "river_reaches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reach_id: Mapped[str] = mapped_column(String(64), unique=True)
    reach_name: Mapped[str] = mapped_column(String(128))
    start_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    end_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    length_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    roughness: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_source: Mapped[str] = mapped_column(String(128), default="manual")
    coord_type: Mapped[str | None] = mapped_column(String(30), default="新吴本地平面坐标系", nullable=True)


class RiverSection(Base, TimestampMixin):
    __tablename__ = "river_sections"
    __table_args__ = (UniqueConstraint("reach_id", "section_id", "point_no", name="uq_river_section_point"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reach_id: Mapped[str] = mapped_column(String(64), index=True)
    section_id: Mapped[str] = mapped_column(String(64), index=True)
    point_no: Mapped[int] = mapped_column(Integer)
    plane_x: Mapped[float] = mapped_column(Float)
    plane_y: Mapped[float] = mapped_column(Float)
    wusong_elev: Mapped[float] = mapped_column(Float)
    data_source: Mapped[str] = mapped_column(String(128), default="新吴实测river.txt")
    coord_type: Mapped[str | None] = mapped_column(String(30), default="新吴本地平面坐标系", nullable=True)


class Gate(Base, TimestampMixin):
    __tablename__ = "gates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gate_id: Mapped[str] = mapped_column(String(64), unique=True)
    gate_name: Mapped[str] = mapped_column(String(128))
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    max_opening: Mapped[float] = mapped_column(Float, default=100)
    current_opening: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="正常")
    data_source: Mapped[str | None] = mapped_column(String(128), default="manual", nullable=True)
    coord_type: Mapped[str | None] = mapped_column(String(30), default="WGS84", nullable=True)


class PumpStation(Base, TimestampMixin):
    __tablename__ = "pump_stations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pump_id: Mapped[str] = mapped_column(String(64), unique=True)
    pump_name: Mapped[str] = mapped_column(String(128))
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    design_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_flow: Mapped[float] = mapped_column(Float, default=0)
    running: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="正常")
    data_source: Mapped[str | None] = mapped_column(String(128), default="manual", nullable=True)
    coord_type: Mapped[str | None] = mapped_column(String(30), default="WGS84", nullable=True)


class WaterLevelData(Base, TimestampMixin):
    __tablename__ = "water_level_data"
    __table_args__ = (UniqueConstraint("station_id", "monitor_time", name="uq_water_station_time"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    monitor_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    water_level: Mapped[float] = mapped_column(Float)
    quality_flag: Mapped[str] = mapped_column(String(32), default="normal")
    data_source: Mapped[str] = mapped_column(String(128), default="manual")


class FlowData(Base, TimestampMixin):
    __tablename__ = "flow_data"
    __table_args__ = (UniqueConstraint("station_id", "monitor_time", name="uq_flow_station_time"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    monitor_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    flow_value: Mapped[float] = mapped_column(Float)
    quality_flag: Mapped[str] = mapped_column(String(32), default="normal")
    data_source: Mapped[str] = mapped_column(String(128), default="manual")


class RainfallData(Base, TimestampMixin):
    __tablename__ = "rainfall_data"
    __table_args__ = (UniqueConstraint("station_id", "monitor_time", name="uq_rain_station_time"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    monitor_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    rainfall: Mapped[float] = mapped_column(Float)
    data_source: Mapped[str] = mapped_column(String(128), default="manual")


class TideData(Base, TimestampMixin):
    __tablename__ = "tide_data"
    __table_args__ = (UniqueConstraint("station_id", "monitor_time", name="uq_tide_station_time"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    monitor_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    tide_level: Mapped[float] = mapped_column(Float)
    data_source: Mapped[str] = mapped_column(String(128), default="manual")


class PredictionTask(Base, TimestampMixin):
    __tablename__ = "prediction_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    model_type: Mapped[str] = mapped_column(String(64))
    input_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    max_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    results: Mapped[list["PredictionResult"]] = relationship(cascade="all, delete-orphan")


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("prediction_tasks.id", ondelete="CASCADE"), index=True)
    predict_time: Mapped[datetime] = mapped_column(DateTime)
    predicted_level: Mapped[float] = mapped_column(Float)
    predicted_flow: Mapped[float | None] = mapped_column(Float, nullable=True)


class SchedulingPlan(Base, TimestampMixin):
    __tablename__ = "scheduling_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_code: Mapped[str] = mapped_column(String(64), index=True)
    prediction_task_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    station_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    station_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    station_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    plan_code: Mapped[str] = mapped_column(String(16))
    plan_name: Mapped[str] = mapped_column(String(64))
    max_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    drainage_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    gate_actions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pump_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    gate_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    pump_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(32), default="待审核")
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    alert_time: Mapped[datetime] = mapped_column(DateTime)
    alert_type: Mapped[str] = mapped_column(String(64))
    alert_level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_status: Mapped[str] = mapped_column(String(32), default="待确认")
    handled_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OperationLog(Base):
    __tablename__ = "operation_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    log_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result: Mapped[str] = mapped_column(String(32), default="成功")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ModelRegistry(Base, TimestampMixin):
    __tablename__ = "model_registry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128))
    model_type: Mapped[str] = mapped_column(String(64))
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    interface_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    applicable_area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class UploadedFile(Base, TimestampMixin):
    __tablename__ = "uploaded_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stored_name: Mapped[str] = mapped_column(String(256), unique=True)
    original_name: Mapped[str] = mapped_column(String(256))
    dataset_type: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    import_status: Mapped[str] = mapped_column(String(32), default="待处理")
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
