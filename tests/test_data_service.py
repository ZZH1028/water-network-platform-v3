import os, sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "test_data.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(str(Path(__file__).resolve().parents[1]))

import pandas as pd
from database.init_db import initialize_database
from services.data_service import (
    validate_dataframe, import_with_validation, save_dataframe,
    export_table, export_all_tables,
)


def setup_module():
    initialize_database(seed_demo=True)


class TestValidateDataframe:
    def test_valid_row(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"2027-08-01 10:00:00","water_level":4.0}])
        summary, errors = validate_dataframe("水位数据", df)
        assert len(errors) == 0

    def test_missing_required_field(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"2027-08-01 10:00:00"}])
        summary, errors = validate_dataframe("水位数据", df)
        assert len(summary) > 0

    def test_nonexistent_station(self):
        df = pd.DataFrame([{"station_id":"NONEXISTENT","monitor_time":"2027-08-01 10:00:00","water_level":4.0}])
        summary, errors = validate_dataframe("水位数据", df)
        assert len(errors) > 0
        assert any("不存在" in e["error"] for e in errors)

    def test_bad_date_format(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"not-a-date","water_level":4.0}])
        summary, errors = validate_dataframe("水位数据", df)
        assert len(errors) > 0

    def test_non_numeric_value(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"2027-08-01 10:00:00","water_level":"abc"}])
        summary, errors = validate_dataframe("水位数据", df)
        assert len(errors) > 0

    def test_row_numbers_in_errors(self):
        df = pd.DataFrame([
            {"station_id":"A01","monitor_time":"2027-08-01 11:00:00","water_level":4.0},
            {"station_id":"NONEXISTENT","monitor_time":"bad","water_level":"abc"},
        ])
        summary, errors = validate_dataframe("水位数据", df)
        error_rows = {e["row"] for e in errors}
        assert 2 in error_rows


class TestImportWithValidation:
    def test_good_data_inserted(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"2027-08-01 20:00:00","water_level":5.0}])
        result = import_with_validation("水位数据", df, "tester")
        assert result.inserted == 1
        assert len(result.errors) == 0

    def test_bad_data_skipped(self):
        df = pd.DataFrame([
            {"station_id":"A01","monitor_time":"2027-08-01 21:00:00","water_level":5.0},
            {"station_id":"NONEXISTENT","monitor_time":"2027-08-01 22:00:00","water_level":5.0},
        ])
        result = import_with_validation("水位数据", df, "tester")
        assert result.inserted == 1
        assert len(result.errors) > 0

    def test_duplicate_skipped(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"2027-08-01 20:00:00","water_level":5.0}])
        result = import_with_validation("水位数据", df, "tester")
        assert result.inserted == 0
        assert result.skipped + result.updated >= 0


class TestSaveDataframeBackwardCompat:
    def test_returns_int(self):
        df = pd.DataFrame([{"station_id":"A01","monitor_time":"2027-08-01 23:00:00","water_level":5.5}])
        n = save_dataframe("水位数据", df, "tester")
        assert isinstance(n, int)
        assert n == 1


class TestExport:
    def test_export_csv(self):
        p = export_table("水位数据", "csv")
        assert p.exists()
        assert p.stat().st_size > 0

    def test_export_xlsx(self):
        p = export_table("监测站信息", "xlsx")
        assert p.exists()
        assert p.stat().st_size > 0

    def test_export_all(self):
        p = export_all_tables("csv")
        assert p.exists()
        assert p.stat().st_size > 0
        assert p.suffix == ".zip"

    def test_export_with_filter(self):
        p = export_table("水位数据", "csv", station_id="A01", date_from="2027-01-01", date_to="2027-12-31")
        assert p.exists()
