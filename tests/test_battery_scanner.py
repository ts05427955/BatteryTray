import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from battery_scanner import BluetoothUnavailableError, scan_battery_devices
from models import DeviceRecord


@pytest.mark.asyncio
async def test_reads_battery_and_skips_failures():
    d_ok = MagicMock()
    d_ok.address = "AA:BB"
    d_ok.name = "Test Mouse"

    d_bad = MagicMock()
    d_bad.address = "CC:DD"
    d_bad.name = "No Battery"

    client_ok = AsyncMock()
    client_ok.__aenter__.return_value = client_ok
    client_ok.__aexit__.return_value = None
    client_ok.read_gatt_char = AsyncMock(return_value=bytearray([87]))

    client_bad = AsyncMock()
    client_bad.__aenter__.side_effect = Exception("fail")

    def client_factory(address, *args, **kwargs):
        return client_ok if address == "AA:BB" else client_bad

    with patch("battery_scanner.BleakScanner.discover", new=AsyncMock(return_value=[d_ok, d_bad])):
        with patch("battery_scanner.BleakClient", side_effect=client_factory):
            devices = await scan_battery_devices(timeout=0.1)

    assert devices == [
        DeviceRecord(id="AA:BB", name="Test Mouse", percent=87, kind="mouse")
    ]


@pytest.mark.asyncio
async def test_bluetooth_unavailable():
    with patch(
        "battery_scanner.BleakScanner.discover",
        new=AsyncMock(side_effect=OSError("no adapter")),
    ):
        with pytest.raises(BluetoothUnavailableError):
            await scan_battery_devices(timeout=0.1)
