from __future__ import annotations

import sys
import threading
import time
from typing import Callable

import pystray

import autostart
from icon_factory import make_battery_icon, make_status_icon
from models import DeviceRecord
from tray_promote import promote_python_tray_icons
from tray_reconcile import plan_reconcile
from version import ABOUT_TEXT, APP_NAME

# Let the tray context menu finish dismissing before a modal dialog.
_ABOUT_DIALOG_DELAY_S = 0.2
# MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST
_ABOUT_MB_FLAGS = 0x00000040 | 0x00010000 | 0x00040000


def _about_message_box() -> None:
    """Blocking About dialog — must not run on the pystray menu callback thread."""
    time.sleep(_ABOUT_DIALOG_DELAY_S)
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                ABOUT_TEXT,
                f"About {APP_NAME}",
                _ABOUT_MB_FLAGS,
            )
            return
        except Exception:
            pass
    print(ABOUT_TEXT)


def show_about_dialog() -> None:
    """Schedule About so OK can close (avoids pystray Win32 menu deadlock)."""
    threading.Thread(target=_about_message_box, daemon=True).start()


class TrayApp:
    def __init__(self, on_refresh: Callable[[], None], on_quit: Callable[[], None]) -> None:
        self._on_refresh = on_refresh
        self._on_quit = on_quit
        self._device_icons: dict[str, pystray.Icon] = {}
        self._status_icon: pystray.Icon | None = None
        self._lock = threading.Lock()

    def _toggle_autostart(self, *_args) -> None:
        autostart.set_enabled(not autostart.is_enabled())

    def _show_about(self, *_args) -> None:
        show_about_dialog()

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Refresh now", lambda *_: self._on_refresh()),
            pystray.MenuItem(
                "Start with Windows",
                self._toggle_autostart,
                checked=lambda _item: autostart.is_enabled(),
            ),
            pystray.MenuItem("About", self._show_about),
            pystray.MenuItem("Quit", lambda *_: self._on_quit()),
        )

    def _start_icon(self, icon: pystray.Icon) -> None:
        thread = threading.Thread(target=icon.run, daemon=True)
        thread.start()

    def start(self) -> None:
        self.apply_devices([], bluetooth_error=None)

    def stop(self) -> None:
        with self._lock:
            for icon in list(self._device_icons.values()):
                icon.stop()
            self._device_icons.clear()
            if self._status_icon is not None:
                self._status_icon.stop()
                self._status_icon = None

    def apply_devices(
        self,
        devices: list[DeviceRecord],
        *,
        bluetooth_error: str | None,
    ) -> None:
        with self._lock:
            plan = plan_reconcile(set(self._device_icons), devices, bluetooth_error=bluetooth_error)
            for device_id in plan.removes:
                icon = self._device_icons.pop(device_id, None)
                if icon is not None:
                    icon.stop()

            if plan.show_status:
                tip = plan.status_tooltip
                if self._status_icon is None:
                    self._status_icon = pystray.Icon(
                        f"{APP_NAME}-status",
                        make_status_icon("BT"),
                        tip,
                        self._menu(),
                    )
                    self._start_icon(self._status_icon)
                else:
                    self._status_icon.icon = make_status_icon("BT")
                    self._status_icon.title = tip
            else:
                if self._status_icon is not None:
                    self._status_icon.stop()
                    self._status_icon = None

            for device in plan.upserts:
                image = make_battery_icon(device.percent, device.kind)
                title = f"{device.name} — {device.percent}%"
                existing = self._device_icons.get(device.id)
                if existing is None:
                    icon = pystray.Icon(
                        f"{APP_NAME}-{device.id}",
                        image,
                        title,
                        self._menu(),
                    )
                    self._device_icons[device.id] = icon
                    self._start_icon(icon)
                    promote_python_tray_icons()
                else:
                    existing.icon = image
                    existing.title = title
