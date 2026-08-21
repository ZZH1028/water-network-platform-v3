from __future__ import annotations

from datetime import datetime, timedelta
import math, uuid
import random

from sqlalchemy import select

from database.engine import session_scope
from database.models import (
    MonitoringStation, RiverReach, Gate, PumpStation, Alert,
    WaterLevelData, FlowData, RainfallData, TideData,
)


def seed_demo_data() -> None:
    with session_scope() as session:
        if session.scalar(select(MonitoringStation).limit(1)) is None:
            session.add_all([
                MonitoringStation(station_id="A01", station_name="梅村水位站", longitude=120.300, latitude=31.535, station_type="水位站", warning_level=4.50, data_source="demo"),
                MonitoringStation(station_id="A02", station_name="硕放水位站", longitude=120.335, latitude=31.505, station_type="水位站", warning_level=4.45, data_source="demo"),
                MonitoringStation(station_id="A03", station_name="江溪水位站", longitude=120.375, latitude=31.565, station_type="水位站", warning_level=4.50, data_source="demo"),
                MonitoringStation(station_id="A04", station_name="旺庄水位站", longitude=120.405, latitude=31.545, station_type="水位站", warning_level=4.55, data_source="demo"),
                MonitoringStation(station_id="A05", station_name="新安水位站", longitude=120.445, latitude=31.500, station_type="水位站", warning_level=4.40, data_source="demo"),
                MonitoringStation(station_id="A06", station_name="鸿山水位站", longitude=120.500, latitude=31.495, station_type="水位站", warning_level=4.60, data_source="demo"),
                MonitoringStation(station_id="R01", station_name="梅村雨量站", longitude=120.315, latitude=31.575, station_type="雨量站", data_source="demo"),
                MonitoringStation(station_id="R02", station_name="新安雨量站", longitude=120.455, latitude=31.530, station_type="雨量站", data_source="demo"),
            ])
        if session.scalar(select(RiverReach).limit(1)) is None:
            session.add_all([
                RiverReach(reach_id="RV01", reach_name="伯渎港", start_node="N01", end_node="N02", length_km=14.5, roughness=0.028, data_source="demo"),
                RiverReach(reach_id="RV02", reach_name="望虞河支线", start_node="N02", end_node="N03", length_km=11.2, roughness=0.030, data_source="demo"),
                RiverReach(reach_id="RV03", reach_name="新安河", start_node="N03", end_node="N04", length_km=9.8, roughness=0.032, data_source="demo"),
            ])
        if session.scalar(select(Gate).limit(1)) is None:
            session.add_all([
                Gate(gate_id="G01", gate_name="伯渎港闸", longitude=120.355, latitude=31.550, current_opening=45),
                Gate(gate_id="G02", gate_name="新安节制闸", longitude=120.435, latitude=31.515, current_opening=35),
                Gate(gate_id="G03", gate_name="鸿山控制闸", longitude=120.485, latitude=31.505, current_opening=20),
            ])
        if session.scalar(select(PumpStation).limit(1)) is None:
            session.add_all([
                PumpStation(pump_id="P01", pump_name="梅村泵站", longitude=120.325, latitude=31.545, design_flow=28, current_flow=16, running=True),
                PumpStation(pump_id="P02", pump_name="江溪泵站", longitude=120.395, latitude=31.555, design_flow=25, current_flow=18, running=True, status="负载偏高"),
                PumpStation(pump_id="P03", pump_name="新安泵站", longitude=120.455, latitude=31.510, design_flow=30, current_flow=0, running=False),
            ])

        if session.scalar(select(Alert).limit(1)) is None:
            session.add_all([
                Alert(alert_code="AL-DEMO-001", station_id="A03", alert_time=datetime.now(), alert_type="水位阈值预警", alert_level="黄色", message="江溪水位站当前水位4.35 m，警戒水位4.50 m", alert_status="待确认"),
                Alert(alert_code="AL-DEMO-002", station_id="A04", alert_time=datetime.now(), alert_type="水位阈值预警", alert_level="橙色", message="旺庄水位站当前水位4.72 m，警戒水位4.55 m", alert_status="待确认"),
                Alert(alert_code="AL-DEMO-003", station_id="A06", alert_time=datetime.now(), alert_type="水位阈值预警", alert_level="蓝色", message="鸿山水位站当前水位4.48 m，警戒水位4.60 m", alert_status="待确认"),
            ])

        if session.scalar(select(WaterLevelData).limit(1)) is None:
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
            station_ids = ["A01","A02","A03","A04","A05","A06"]
            warnings = [4.50,4.45,4.50,4.55,4.40,4.60]
            for h in range(72, -1, -1):
                t = now - timedelta(hours=h)
                for idx, sid in enumerate(station_ids):
                    level = round(3.55 + idx*0.07 + 0.42*math.exp(-((h-16)/9)**2) + 0.11*math.sin((72-h)/5+idx/2) + random.uniform(-0.025,0.025), 3)
                    session.add(WaterLevelData(station_id=sid, monitor_time=t, water_level=level, quality_flag="warning" if level >= warnings[idx] else "normal", data_source="seed"))
                    flow = max(0, round(13 + idx*1.2 + 4*math.sin((72-h)/7+idx/3)+random.uniform(-0.8,0.8), 2))
                    session.add(FlowData(station_id=sid, monitor_time=t, flow_value=flow, data_source="seed"))
                session.add(RainfallData(station_id="R01", monitor_time=t, rainfall=max(0, round(4*math.sin((72-h)/10)+random.uniform(-1,2),2)), data_source="seed"))
                session.add(RainfallData(station_id="R02", monitor_time=t, rainfall=max(0, round(3.6*math.sin((72-h)/11+0.5)+random.uniform(-1,2),2)), data_source="seed"))
                session.add(TideData(station_id="T01", monitor_time=t, tide_level=round(3.05+0.35*math.sin((72-h)/6.2),3), data_source="seed"))
