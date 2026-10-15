"""Ensure only one BatteryTray process runs at a time (Windows named mutex)."""

from __future__ import annotations

import ctypes
import sys
from typing import Any

from version import APP_NAME

# Win32: CreateMutexW succeeds but GetLastError == ERROR_ALREADY_EXISTS
ERROR_ALREADY_EXISTS = 183


class SingleInstanceLock:
    def __init__(self, handle: Any, *, _kernel: Any | None = None) -> None:
        self._handle = handle
        self._kernel = _kernel
        self.acquired = handle is not None and handle != 0

    def release(self) -> None:
        if not self._handle:
            return
        kernel = self._kernel
        if kernel is None and sys.platform == "win32":
            kernel = ctypes.windll.kernel32
        if kernel is not None:
            try:
                kernel.CloseHandle(self._handle)
            except Exception:
                pass
        self._handle = None


def _mutex_name(app_name: str) -> str:
    # Local\ avoids needing Global privilege; unique per user session is enough.
    safe = "".join(c if c.isalnum() else "_" for c in app_name)
    return f"Local\\{safe}_SingleInstance"


def try_acquire_single_instance(app_name: str = APP_NAME) -> SingleInstanceLock | None:
    """Return a held lock, or None if another instance already owns the mutex."""
    if sys.platform != "win32":
        # Non-Windows: allow run (no tray packaging target).
        return SingleInstanceLock(handle=1)

    kernel = ctypes.windll.kernel32
    kernel.SetLastError(0)
    handle = kernel.CreateMutexW(None, False, _mutex_name(app_name))
    if not handle:
        return None
    if kernel.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel.CloseHandle(handle)
        return None
    return SingleInstanceLock(handle=handle, _kernel=kernel)
