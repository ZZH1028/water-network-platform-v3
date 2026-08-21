
from __future__ import annotations

from io import BytesIO
import pandas as pd


TEMPLATES = {
    "监测站信息": pd.DataFrame([
        {
            "station_id":"A01","station_name":"示例水位站","longitude":120.36,
            "latitude":31.55,"station_type":"水位站","warning_level":4.50,"data_source":"template"
        }
    ]),
    "水位数据": pd.DataFrame([
        {
            "station_id":"A01","monitor_time":"2026-08-01 08:00:00",
            "water_level":4.20,"quality_flag":"normal","data_source":"template"
        }
    ]),
    "流量数据": pd.DataFrame([
        {
            "station_id":"A01","monitor_time":"2026-08-01 08:00:00",
            "flow_value":18.2,"quality_flag":"normal","data_source":"template"
        }
    ]),
    "降雨数据": pd.DataFrame([
        {
            "station_id":"R01","monitor_time":"2026-08-01 08:00:00",
            "rainfall":6.5,"data_source":"template"
        }
    ]),
    "潮位数据": pd.DataFrame([
        {
            "station_id":"T01","monitor_time":"2026-08-01 08:00:00",
            "tide_level":3.18,"data_source":"template"
        }
    ]),
    "闸门信息": pd.DataFrame([
        {
            "gate_id":"G01","gate_name":"示例闸门","longitude":120.36,
            "latitude":31.55,"max_opening":100,"current_opening":40,"status":"正常"
        }
    ]),
    "泵站信息": pd.DataFrame([
        {
            "pump_id":"P01","pump_name":"示例泵站","longitude":120.36,
            "latitude":31.55,"design_flow":25,"current_flow":15,"running":1,"status":"正常"
        }
    ]),
}


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "数据") -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return bio.getvalue()
