from __future__ import annotations

import asyncio
import threading

import autostart
from aggregator import aggregate_battery_devices
from models import DeviceRecord
from tray_app import TrayApp

REFRESH_SECONDS = 60


class App:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._refresh_asap = threading.Event()
        self._last_devices: list[DeviceRecord] = []
        self._tray = TrayApp(on_refresh=self.request_refresh, on_quit=self.request_quit)

    def request_refresh(self) -> None:
        self._refresh_asap.set()

    def request_quit(self) -> None:
        self._stop.set()
        self._refresh_asap.set()

    async def _scan_once(self) -> None:
        try:
            devices = await aggregate_battery_devices()
            self._last_devices = devices
            self._tray.apply_devices(devices, bluetooth_error=None)
        except Exception:
            # Keep last good set; surface as status only if we have never succeeded
            if self._last_devices:
                self._tray.apply_devices(self._last_devices, bluetooth_error=None)
            else:
                self._tray.apply_devices([], bluetooth_error="Scan failed; will retry")

    async def run_async(self) -> None:
        autostart.set_enabled(True)
        self._tray.start()
        try:
            await self._scan_once()
            while not self._stop.is_set():
                for _ in range(REFRESH_SECONDS):
                    if self._stop.is_set() or self._refresh_asap.is_set():
                        break
                    await asyncio.sleep(1)
                if self._stop.is_set():
                    break
                self._refresh_asap.clear()
                await self._scan_once()
        except asyncio.CancelledError:
            pass
        finally:
            self._tray.stop()

    def run(self) -> None:
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.request_quit()
            self._tray.stop()


if __name__ == "__main__":
    App().run()
