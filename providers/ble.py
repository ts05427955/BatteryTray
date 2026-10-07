from __future__ import annotations

from battery_scanner import BluetoothUnavailableError, scan_battery_devices
from models import DeviceRecord


class BleProvider:
    async def scan(self) -> list[DeviceRecord]:
        try:
            return await scan_battery_devices()
        except BluetoothUnavailableError:
            return []
