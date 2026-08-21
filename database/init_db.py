from __future__ import annotations

from sqlalchemy import inspect, select, text

from database.engine import Base, engine, session_scope
from database.models import ModelRegistry, User
from services.auth_service import hash_password


def _migrate_schema() -> None:
    """Add columns introduced after V1.0 to existing SQLite/PostgreSQL databases."""
    migrations = [
        ("alerts", "handled_at", "TIMESTAMP"),
        ("operation_logs", "log_type", "VARCHAR(32)"),
        ("monitoring_stations", "coord_type", "VARCHAR(30)"),
        ("river_reaches", "coord_type", "VARCHAR(30)"),
        ("gates", "data_source", "VARCHAR(128)"),
        ("gates", "coord_type", "VARCHAR(30)"),
        ("pump_stations", "data_source", "VARCHAR(128)"),
        ("pump_stations", "coord_type", "VARCHAR(30)"),
        ("prediction_results", "predicted_flow", "FLOAT"),
        ("scheduling_plans", "station_id", "VARCHAR(64)"),
        ("scheduling_plans", "station_name", "VARCHAR(128)"),
        ("scheduling_plans", "station_lat", "FLOAT"),
        ("scheduling_plans", "station_lng", "FLOAT"),
    ]
    for table, column, col_type in migrations:
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column in existing:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


def initialize_database(seed_demo: bool = False) -> None:
    # New tables (e.g. river_sections) are created directly; existing tables are then migrated in-place.
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
    with session_scope() as session:
        if session.scalar(select(User).where(User.username == "admin")) is None:
            session.add_all([
                User(username="admin", password_hash=hash_password("admin123"), role="管理员"),
                User(username="researcher", password_hash=hash_password("demo123"), role="科研人员"),
                User(username="dispatcher", password_hash=hash_password("demo123"), role="调度人员"),
                User(username="viewer", password_hash=hash_password("demo123"), role="查看用户"),
            ])

        registry = [
            ("模拟水位预测模型", "演示模型", "V1.1", "已启用", "predict()", "演示河网", "用于验证平台流程"),
            ("新吴GIS水位模拟预测模型", "GIS联动模型", "V1.1", "已启用", "run_demo_prediction()", "无锡新吴区", "读取station/gate_pump/river实测参考数据；核心预测公式仍为演示计算"),
            ("MIKE水动力模型", "机理模型", "-", "待接入", "run_mike_model()", "无锡河网", "需配置正式模型文件与边界条件"),
            ("多目标调度优化模型", "优化模型", "V1.1", "已启用", "generate_demo_plans()", "平原河网", "已接入GIS闸泵规模与运行约束；正式优化器可继续替换"),
        ]
        for name, mtype, version, status, iface, area, remarks in registry:
            if session.scalar(select(ModelRegistry).where(ModelRegistry.model_name == name).limit(1)) is None:
                session.add(ModelRegistry(model_name=name, model_type=mtype, version=version, status=status, interface_name=iface, applicable_area=area, remarks=remarks))
    if seed_demo:
        from database.seed import seed_demo_data
        seed_demo_data()
