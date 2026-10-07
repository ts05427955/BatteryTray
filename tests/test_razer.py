from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import DeviceRecord
from providers.razer import (
    RazerProvider,
    _matches_barracuda_24,
    read_hid_battery,
    read_synapse_battery,
)


@pytest.mark.asyncio
async def test_synapse_success_returns_barracuda():
    async def fake_read():
        return DeviceRecord(
            id="razer:barracuda-x-24", name="Razer Barracuda X 2.4", percent=50, kind="headset"
        )

    with patch("providers.razer.read_synapse_battery", new=fake_read):
        with patch("providers.razer.read_hid_battery", new=AsyncMock(return_value=None)):
            out = await RazerProvider().scan()
    assert out == [
        DeviceRecord(
            id="razer:barracuda-x-24", name="Razer Barracuda X 2.4", percent=50, kind="headset"
        )
    ]


@pytest.mark.asyncio
async def test_both_fail_returns_empty():
    assert await RazerProvider().scan() == []


@pytest.mark.asyncio
async def test_read_synapse_battery_returns_none_without_local_api():
    assert await read_synapse_battery() is None


@pytest.mark.asyncio
async def test_read_hid_battery_never_opens_device():
    """Regression: probing Barracuda HID can drop the USB audio link on quit."""
    fake_hid = MagicMock()
    fake_hid.enumerate.return_value = [
        {
            "path": b"barracuda",
            "vendor_id": 0x1532,
            "product_id": 0x0552,
            "product_string": "Razer Barracuda X 2.4",
            "usage_page": 0xFF00,
            "usage": 0,
        }
    ]
    rec = await read_hid_battery(hid_mod=fake_hid)
    assert rec is None
    fake_hid.enumerate.assert_not_called()
    fake_hid.device.assert_not_called()


def test_barracuda_name_match_requires_barracuda_and_24_or_barracuda_x():
    assert _matches_barracuda_24("Razer Barracuda X 2.4")
    assert _matches_barracuda_24("BARRACUDA X 2.4 GHz")
    assert _matches_barracuda_24("Razer Barracuda X")
    assert not _matches_barracuda_24("Razer Barracuda")
    assert not _matches_barracuda_24("Razer BlackShark V2")
    assert not _matches_barracuda_24("G502 X PLUS")


def test_razer_provider_registered():
    from providers import default_providers
    from providers.razer import RazerProvider as RP

    assert any(type(p) is RP for p in default_providers())
