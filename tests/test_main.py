import inspect

from unittest.mock import AsyncMock, MagicMock, patch



import pytest



from models import DeviceRecord





def test_refresh_wait_uses_asyncio_sleep_not_event_wait():
    from main import App

    src = inspect.getsource(App.run_async)
    assert "asyncio.sleep" in src
    assert "_refresh_asap.wait" not in src


def test_run_swallows_keyboard_interrupt():
    from main import App

    src = inspect.getsource(App.run)
    assert "KeyboardInterrupt" in src
    src_async = inspect.getsource(App.run_async)
    assert "CancelledError" in src_async





@pytest.mark.asyncio

async def test_scan_success_applies_devices():

    from main import App



    devices = [DeviceRecord(id="AA:BB", name="Test Mouse", percent=87, kind="mouse")]

    app = App()

    app._tray = MagicMock()

    with patch("main.aggregate_battery_devices", new=AsyncMock(return_value=devices)):

        await app._scan_once()

    app._tray.apply_devices.assert_called_once_with(devices, bluetooth_error=None)

    assert app._last_devices == devices





@pytest.mark.asyncio

async def test_aggregate_empty_shows_no_devices_status_path():

    from main import App



    app = App()

    app._tray = MagicMock()

    with patch("main.aggregate_battery_devices", new=AsyncMock(return_value=[])):

        await app._scan_once()

    app._tray.apply_devices.assert_called_once_with([], bluetooth_error=None)





@pytest.mark.asyncio

async def test_aggregate_with_vendor_devices_ignores_ble_absence():

    from main import App



    devices = [DeviceRecord(id="logitech:g502-x-plus", name="G502 X PLUS", percent=70, kind="mouse")]

    app = App()

    app._tray = MagicMock()

    with patch("main.aggregate_battery_devices", new=AsyncMock(return_value=devices)):

        await app._scan_once()

    app._tray.apply_devices.assert_called_once_with(devices, bluetooth_error=None)





@pytest.mark.asyncio

async def test_scan_unexpected_error_keeps_last_devices():

    from main import App



    last = [DeviceRecord(id="AA:BB", name="Test Mouse", percent=87, kind="mouse")]

    app = App()

    app._tray = MagicMock()

    app._last_devices = last

    with patch("main.aggregate_battery_devices", new=AsyncMock(side_effect=RuntimeError("timeout"))):

        await app._scan_once()

    app._tray.apply_devices.assert_called_once_with(last, bluetooth_error=None)





@pytest.mark.asyncio

async def test_scan_unexpected_error_without_cache_shows_retry():

    from main import App



    app = App()

    app._tray = MagicMock()

    with patch("main.aggregate_battery_devices", new=AsyncMock(side_effect=RuntimeError("timeout"))):

        await app._scan_once()

    app._tray.apply_devices.assert_called_once_with(

        [], bluetooth_error="Scan failed; will retry"

    )

