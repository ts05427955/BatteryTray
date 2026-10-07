"""Register this app to start with Windows (current-user Run key)."""

from __future__ import annotations

import sys
from pathlib import Path

from version import APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = APP_NAME
# Previous branding; remove on enable/disable so friends don't get double launch.
_LEGACY_VALUE_NAMES = ("BLEBatteryTray",)


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def launch_command() -> str:
    if _is_frozen():
        return f'"{Path(sys.executable).resolve()}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    runner = pythonw if pythonw.is_file() else exe
    main_py = Path(__file__).resolve().parent / "main.py"
    return f'"{runner}" "{main_py}"'


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
        return str(value) == launch_command()
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:
        return

    def _delete_value(key: object, name: str) -> None:
        try:
            winreg.DeleteValue(key, name)  # type: ignore[arg-type]
        except FileNotFoundError:
            pass
        except OSError:
            pass

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        for legacy in _LEGACY_VALUE_NAMES:
            _delete_value(key, legacy)
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            _delete_value(key, VALUE_NAME)
