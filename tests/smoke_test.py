import os
from pathlib import Path
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(__file__).parent/'test.db').as_posix()}"
os.environ["SEED_DEMO_DATA"] = "true"
from database.init_db import initialize_database
from services.auth_service import authenticate
from services.data_service import get_dashboard_statistics

def test_smoke():
    initialize_database(seed_demo=True)
    assert authenticate("admin","admin123")
    stats=get_dashboard_statistics()
    assert stats["station_count"] >= 6
