from __future__ import annotations

from bleak import BleakClient, BleakScanner

from models import DeviceRecord, classify_kind

BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"


class BluetoothUnavailableError(Exception):
    pass


async def _read_one(address: str, name: str | None) -> DeviceRecord | None:
    try:
        async with BleakClient(address, timeout=5.0) as client:
            raw = await client.read_gatt_char(BATTERY_LEVEL)
            percent = int(raw[0]) if raw else None
            if percent is None:
                return None
            percent = max(0, min(100, percent))
            display = name or address
            return DeviceRecord(
                id=address,
                name=display,
                percent=percent,
                kind=classify_kind(display),
            )
    except Exception:
        return None


async def scan_battery_devices(timeout: float = 8.0) -> list[DeviceRecord]:
    try:
        found = await BleakScanner.discover(timeout=timeout)
    except Exception as exc:
        raise BluetoothUnavailableError("Bluetooth is off or unavailable") from exc

    results: list[DeviceRecord] = []
    for dev in found:
        address = getattr(dev, "address", None)
        if not address:
            continue
        record = await _read_one(address, getattr(dev, "name", None))
        if record is not None:
            results.append(record)
    return results
