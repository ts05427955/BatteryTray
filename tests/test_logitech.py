import json
import sys
from contextlib import contextmanager, ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import DeviceRecord
from providers.logitech import LogitechProvider, _matches_g502_x_plus, read_ghub_battery, read_hid_battery

LOGI_VID = 0x046D
HIDPP_USAGE_PAGE = 0xFF00
G502_HIDPP_IFACE = {
    "path": b"g502-x-plus-hidpp",
    "vendor_id": LOGI_VID,
    "product_id": 0xC547,
    "product_string": "G502 X PLUS",
    "usage_page": HIDPP_USAGE_PAGE,
    "usage": 2,
}


class FakeHidppDevice:
    """Scripted HID++ 2.0 device: Root getFeature + battery feature replies."""

    def __init__(self, *, feature_index_by_id: dict[int, int], battery_percent: int):
        self.feature_index_by_id = dict(feature_index_by_id)
        self.battery_percent = battery_percent
        self._queue: list[list[int]] = []
        self.opened_path = None

    def open_path(self, path):
        self.opened_path = path

    def close(self):
        pass

    def write(self, data):
        pkt = list(data)
        if len(pkt) < 6:
            return len(pkt)
        _report, dev_idx, feat_idx, func_sw = pkt[0], pkt[1], pkt[2], pkt[3]
        func = (func_sw >> 4) & 0x0F
        swid = func_sw & 0x0F
        if feat_idx == 0x00 and func == 0:
            feat_id = (pkt[4] << 8) | pkt[5]
            idx = self.feature_index_by_id.get(feat_id, 0)
            self._queue.append([0x10, dev_idx, 0x00, swid, idx, 0x00, 0x00])
        else:
            feat_id = next(
                (fid for fid, idx in self.feature_index_by_id.items() if idx == feat_idx),
                None,
            )
            if feat_id == 0x1004 and func == 1:
                resp = [0x11, dev_idx, feat_idx, func_sw, self.battery_percent, 0x08, 0x00]
                resp.extend([0] * (20 - len(resp)))
                self._queue.append(resp)
            elif feat_id == 0x1000 and func == 0:
                resp = [0x11, dev_idx, feat_idx, func_sw, self.battery_percent, 0x00, 0x00]
                resp.extend([0] * (20 - len(resp)))
                self._queue.append(resp)
        return len(pkt)

    def read(self, size, timeout_ms=0):
        if self._queue:
            return self._queue.pop(0)
        return []


def _fake_hid_module(device: FakeHidppDevice, interfaces: list[dict]):
    fake_hid = MagicMock()
    fake_hid.enumerate.return_value = interfaces
    fake_hid.device.return_value = device
    return fake_hid


@contextmanager
def patched_hid(fake_hid):
    with ExitStack() as stack:
        stack.enter_context(patch.dict(sys.modules, {"hid": fake_hid}))
        hidpp_mod = sys.modules.get("providers.logitech_hidpp")
        if hidpp_mod is not None:
            stack.enter_context(patch.object(hidpp_mod, "hid", fake_hid))
        yield



class _FakeGhubWs:
    """Simulates G Hub: OPTIONS first, then path-matched GET replies."""

    def __init__(self, messages: list[dict]):
        self._messages = list(messages)
        self.sent: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def send(self, data: str):
        self.sent.append(json.loads(data))

    async def recv(self):
        if not self._messages:
            raise AssertionError("no more websocket messages")
        return json.dumps(self._messages.pop(0))


@pytest.mark.asyncio
async def test_ghub_skips_options_and_reads_battery():
    messages = [
        {"msgId": "", "verb": "OPTIONS", "path": "/", "origin": "backend"},
        {
            "msgId": "",
            "verb": "GET",
            "path": "/devices/list",
            "payload": {
                "deviceInfos": [
                    {
                        "id": "dev00000000",
                        "extendedDisplayName": "G502 X PLUS Wireless Gaming Mouse",
                        "capabilities": {"hasBatteryStatus": True},
                    }
                ]
            },
        },
        {
            "msgId": "",
            "verb": "GET",
            "path": "/battery/dev00000000/state",
            "payload": {"percentage": 94, "charging": False},
        },
    ]
    fake = _FakeGhubWs(messages)

    def connect(_uri: str):
        return fake

    rec = await read_ghub_battery(ws_connect=connect)
    assert rec == DeviceRecord(
        id="logitech:g502-x-plus",
        name="G502 X PLUS",
        percent=94,
        kind="mouse",
    )


@pytest.mark.asyncio
async def test_ghub_success_returns_g502():
    async def fake_read():
        return DeviceRecord(id="logitech:g502-x-plus", name="G502 X PLUS", percent=76, kind="mouse")

    with patch("providers.logitech.read_ghub_battery", new=fake_read):
        with patch("providers.logitech.read_hid_battery", new=AsyncMock(return_value=None)):
            out = await LogitechProvider().scan()
    assert out == [DeviceRecord(id="logitech:g502-x-plus", name="G502 X PLUS", percent=76, kind="mouse")]


@pytest.mark.asyncio
async def test_ghub_fail_falls_through_to_hid_hook():
    with patch("providers.logitech.read_ghub_battery", new=AsyncMock(return_value=None)):
        with patch(
            "providers.logitech.read_hid_battery",
            new=AsyncMock(
                return_value=DeviceRecord(
                    id="logitech:g502-x-plus", name="G502 X PLUS", percent=55, kind="mouse"
                )
            ),
        ):
            out = await LogitechProvider().scan()
    assert out[0].percent == 55


@pytest.mark.asyncio
async def test_both_fail_returns_empty():
    with patch("providers.logitech.read_ghub_battery", new=AsyncMock(return_value=None)):
        with patch("providers.logitech.read_hid_battery", new=AsyncMock(return_value=None)):
            assert await LogitechProvider().scan() == []


@pytest.mark.asyncio
async def test_read_hid_battery_returns_g502_from_unified_battery():
    device = FakeHidppDevice(feature_index_by_id={0x1004: 0x06}, battery_percent=72)
    fake_hid = _fake_hid_module(device, [G502_HIDPP_IFACE])
    with patched_hid(fake_hid):
        rec = await read_hid_battery()
    assert rec == DeviceRecord(
        id="logitech:g502-x-plus",
        name="G502 X PLUS",
        percent=72,
        kind="mouse",
    )


@pytest.mark.asyncio
async def test_read_hid_battery_returns_g502_from_battery_unity():
    device = FakeHidppDevice(feature_index_by_id={0x1000: 0x09}, battery_percent=41)
    fake_hid = _fake_hid_module(device, [G502_HIDPP_IFACE])
    with patched_hid(fake_hid):
        rec = await read_hid_battery()
    assert rec == DeviceRecord(
        id="logitech:g502-x-plus",
        name="G502 X PLUS",
        percent=41,
        kind="mouse",
    )


def test_g502_name_match_requires_x_plus_not_bare_x():
    assert _matches_g502_x_plus({"name": "G502 X PLUS"})
    assert _matches_g502_x_plus({"extendedDisplayName": "Logitech G502 X+"})
    assert not _matches_g502_x_plus({"name": "G502 X LIGHTSPEED"})
    assert not _matches_g502_x_plus({"name": "G502 HERO"})
