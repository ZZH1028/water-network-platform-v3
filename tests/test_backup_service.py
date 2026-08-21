import os, sys
from pathlib import Path
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(__file__).parent / 'test_backup.db').as_posix()}"
os.environ["SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(str(Path(__file__).resolve().parents[1]))

from database.init_db import initialize_database
from services.backup_service import create_json_backup_extended, verify_backup, restore_from_json


def setup_module():
    initialize_database(seed_demo=True)


class TestBackup:
    def test_create_backup(self):
        result = create_json_backup_extended()
        assert "path" in result
        assert result["size"] > 0
        assert len(result["checksum"]) == 32

    def test_verify_valid_backup(self):
        result = create_json_backup_extended()
        verify = verify_backup(result["path"])
        assert verify["valid"] is True
        assert verify["table_count"] >= 10

    def test_verify_nonexistent(self):
        verify = verify_backup("nonexistent.json")
        assert verify["valid"] is False

    def test_restore_safe_mode(self):
        result = create_json_backup_extended()
        restore = restore_from_json(result["path"], overwrite=False)
        assert restore["success"] is True

    def test_restore_overwrite_mode(self):
        result = create_json_backup_extended()
        restore = restore_from_json(result["path"], overwrite=True)
        assert restore["success"] is True
        assert restore["total_restored"] > 0
