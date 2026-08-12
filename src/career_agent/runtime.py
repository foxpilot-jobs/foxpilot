"""Runtime coordination for single-user local operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Self


class ScanAlreadyRunning(RuntimeError):
    """Raised when another FoxPilot scan owns the local lock."""


class ScanLock:
    """Cross-platform advisory lock for the local scan pipeline."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as error:
            self._file.close()
            self._file = None
            raise ScanAlreadyRunning(
                "Another FoxPilot scan is already running. Wait for it to finish."
            ) from error

        self._file.seek(0)
        self._file.truncate()
        self._file.write(f"pid={os.getpid()}\n")
        self._file.flush()
        return self

    def __exit__(self, *_args) -> None:
        if self._file is None:
            return
        if os.name == "nt":
            import msvcrt

            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
        self._file = None
