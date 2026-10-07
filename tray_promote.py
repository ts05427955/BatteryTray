"""Promote this app's Windows tray icons out of the overflow (^) menu."""

from __future__ import annotations

import sys
from pathlib import Path


def promote_python_tray_icons() -> int:
    """Set IsPromoted=1 for NotifyIconSettings entries of this python.exe.

    Returns how many registry values were updated. Safe no-op on non-Windows
    or if the key is missing.
    """
    if sys.platform != "win32":
        return 0
    try:
        import winreg
    except ImportError:
        return 0

    try:
        exe = Path(sys.executable).resolve()
    except OSError:
        return 0

    root = r"Control Panel\NotifyIconSettings"
    updated = 0
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root) as base:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(base, i)
                except OSError:
                    break
                i += 1
                with winreg.OpenKey(base, name, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
                    try:
                        path, _ = winreg.QueryValueEx(key, "ExecutablePath")
                    except FileNotFoundError:
                        continue
                    try:
                        if Path(str(path)).resolve() != exe:
                            continue
                    except OSError:
                        continue
                    winreg.SetValueEx(key, "IsPromoted", 0, winreg.REG_DWORD, 1)
                    updated += 1
    except OSError:
        return updated
    return updated
