from pathlib import Path

from career_agent.runtime import ScanAlreadyRunning, ScanLock


def test_scan_lock_releases_for_next_run(tmp_path: Path) -> None:
    lock_path = tmp_path / "scan.lock"
    with ScanLock(lock_path):
        assert "pid=" in lock_path.read_text(encoding="utf-8")

    with ScanLock(lock_path):
        pass


def test_scan_lock_rejects_second_owner(tmp_path: Path) -> None:
    lock_path = tmp_path / "scan.lock"
    with ScanLock(lock_path):
        try:
            with ScanLock(lock_path):
                pass
        except ScanAlreadyRunning:
            pass
        else:
            raise AssertionError("Expected the second scan lock to fail")
