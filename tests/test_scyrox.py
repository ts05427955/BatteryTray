from unittest.mock import MagicMock

import pytest

from models import DeviceRecord
from providers.scyrox import (
    CMD_BATTERY_LEVEL,
    CMD_DEVICE_ONLINE,
    REPORT_ID,
    ScyroxProvider,
    build_packet,
    decode_battery_response,
    _checksum,
    _is_candidate,
    read_hid_battery,
)


def test_checksum_and_packet_layout():
    pkt = build_packet(CMD_BATTERY_LEVEL, [])
    assert len(pkt) == 16
    assert pkt[0] == CMD_BATTERY_LEVEL
    assert pkt[4] == 0
    assert pkt[15] == _checksum(pkt)


def test_decode_battery_response():
    frame = [0] * 16
    frame[0] = CMD_BATTERY_LEVEL
    frame[5] = 77
    frame[6] = 0
    assert decode_battery_response(frame) == 77
    frame[5] = 200
    assert decode_battery_response(frame) is None


def test_candidate_filter():
    assert _is_candidate({"vendor_id": 0x3554, "product_id": 0xF5F7, "product_string": ""})
    assert _is_candidate({"vendor_id": 0x3554, "product_id": 0xF5F4, "product_string": "dongle"})
    assert _is_candidate(
        {"vendor_id": 0x3554, "product_id": 0x9999, "product_string": "Scyrox V8 Receiver"}
    )
    assert not _is_candidate({"vendor_id": 0x046D, "product_id": 0xC547, "product_string": "USB Receiver"})


class FakeScyroxDevice:
    def __init__(self, *, online: bool = True, percent: int = 88):
        self.online = online
        self.percent = percent
        self.opened_path = None
        self.writes: list[list[int]] = []

    def open_path(self, path):
        self.opened_path = path

    def close(self):
        pass

    def write(self, data):
        pkt = list(data)
        self.writes.append(pkt)
        return len(pkt)

    def send_feature_report(self, data):
        return self.write(data)

    def get_feature_report(self, *_args, **_kwargs):
        return []

    def read(self, _size, timeout_ms=0):
        if not self.writes:
            return []
        last = self.writes[-1]
        # last is [report_id, *16bytes]
        cmd = last[1] if len(last) > 1 else 0
        frame = [0] * 16
        frame[0] = cmd
        if cmd == CMD_DEVICE_ONLINE:
            frame[5] = 1 if self.online else 0
        elif cmd == CMD_BATTERY_LEVEL:
            frame[5] = self.percent
            frame[6] = 0
        return [REPORT_ID, *frame]


def _fake_hid(device: FakeScyroxDevice, info: dict):
    fake = MagicMock()
    fake.enumerate.return_value = [info]
    fake.device.return_value = device
    return fake


@pytest.mark.asyncio
async def test_read_hid_battery_scyrox_v8():
    device = FakeScyroxDevice(percent=88)
    info = {
        "path": b"scyrox-v8",
        "vendor_id": 0x3554,
        "product_id": 0xF5F7,
        "product_string": "Scyrox V8",
    }
    rec = await read_hid_battery(hid_mod=_fake_hid(device, info))
    assert rec == DeviceRecord(id="scyrox:v8", name="Scyrox V8", percent=88, kind="mouse")
    cmds = [w[1] for w in device.writes if len(w) > 1]
    assert CMD_DEVICE_ONLINE in cmds
    assert CMD_BATTERY_LEVEL in cmds


@pytest.mark.asyncio
async def test_offline_device_returns_none():
    device = FakeScyroxDevice(online=False, percent=50)
    info = {
        "path": b"scyrox-v8",
        "vendor_id": 0x3554,
        "product_id": 0xF5F7,
        "product_string": "Scyrox V8",
    }
    rec = await read_hid_battery(hid_mod=_fake_hid(device, info))
    assert rec is None


@pytest.mark.asyncio
async def test_provider_scan_empty_without_device(monkeypatch):
    async def _none(**_kwargs):
        return None

    monkeypatch.setattr("providers.scyrox.read_hid_battery", _none)
    assert await ScyroxProvider().scan() == []
