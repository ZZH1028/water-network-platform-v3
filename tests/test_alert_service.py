import os, sys, uuid
from pathlib import Path

# Use unique database for this test file
DB_PATH = Path(__file__).parent / f"test_alert_{uuid.uuid4().hex[:8]}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(str(Path(__file__).resolve().parents[1]))

from datetime import datetime
from database.engine import engine as _alert_engine
from database.init_db import initialize_database
from database.engine import session_scope
from database.models import Alert
from services.alert_service import update_alert_status, get_alert_by_id

ALERT_CODE = f"AL-TEST-{uuid.uuid4().hex[:6]}"


def setup_module():
    from database.models import Base
    Base.metadata.create_all(bind=_alert_engine)
    with session_scope() as s:
        a = Alert(alert_code=ALERT_CODE, station_id="A01", alert_time=datetime.now(),
                   alert_type="测试", alert_level="蓝色", message="测试预警", alert_status="待确认")
        s.add(a)
        s.commit()


class TestAlertUpdate:
    def test_update_sets_handled_at(self):
        with session_scope() as s:
            aid = s.scalar(
                __import__("sqlalchemy", fromlist=["select"]).select(Alert.id).where(Alert.alert_code == ALERT_CODE)
            )
        ok = update_alert_status(aid, "已确认", "admin")
        assert ok
        detail = get_alert_by_id(aid)
        assert detail["handled_by"] == "admin"
        assert detail["handled_at"] is not None
        assert detail["alert_status"] == "已确认"

    def test_get_nonexistent_alert(self):
        detail = get_alert_by_id(99999)
        assert detail is None

    def test_update_nonexistent_alert(self):
        ok = update_alert_status(99999, "已确认", "admin")
        assert not ok
