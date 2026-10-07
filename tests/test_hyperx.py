from unittest.mock import MagicMock

import pytest

from models import DeviceRecord
from providers.hyperx import (
    GET_BATTERY_CMD,
    _battery_request,
    _battery_request_dts,
    _decode_battery_reply,
    _is_candidate,
    read_hid_battery,
)


def test_decode_cloud_ii_battery_reply():
    pkt = [0] * 20
    pkt[0], pkt[2], pkt[3], pkt[7] = 11, 187, GET_BATTERY_CMD, 70
    assert _decode_battery_reply(pkt) == 70
    pkt[7] = 200
    assert _decode_battery_reply(pkt) is None
    assert _decode_battery_reply([1, 2, 3]) is None


def test_decode_cloud_ii_dts_battery_reply():
    # HP / DTS dongle: [6, 255, 187, cmd, ..., percent at 7]
    pkt = [0] * 20
    pkt[0], pkt[1], pkt[2], pkt[3], pkt[7] = 6, 255, 187, GET_BATTERY_CMD, 64
    assert _decode_battery_reply(pkt) == 64
    assert _battery_request_dts()[0:4] == [0x06, 0xFF, 0xBB, GET_BATTERY_CMD]


def test_cloud_ii_candidate_ids_and_name():
    assert _is_candidate({"vendor_id": 0x0951, "product_id": 0x1718, "product_string": ""})
    assert _is_candidate({"vendor_id": 0x03F0, "product_id": 0x018B, "product_string": ""})
    assert _is_candidate({"vendor_id": 0x03F0, "product_id": 0x0D93, "product_string": ""})
    assert _is_candidate({"vendor_id": 0x03F0, "product_id": 0x0696, "product_string": ""})
    assert _is_candidate(
        {"vendor_id": 0x03F0, "product_id": 0x9999, "product_string": "HP HyperX Cloud II Wireless"}
    )
    assert not _is_candidate({"vendor_id": 0x1532, "product_id": 0x0552, "product_string": "Barracuda"})


class FakeHidDevice:
    def __init__(self, reply: list[int]):
        self.reply = reply
        self.opened_path = None
        self.wrote = None

    def open_path(self, path):
        self.opened_path = path

    def close(self):
        pass

    def get_input_report(self, *_args, **_kwargs):
        return []

    def write(self, data):
        self.wrote = list(data)
        return len(data)

    def send_feature_report(self, data):
        self.wrote = list(data)
        return len(data)

    def read(self, _size, timeout_ms=0):
        return self.reply

    def get_feature_report(self, *_args, **_kwargs):
        return []


def _fake_hid(device: FakeHidDevice, info: dict):
    fake = MagicMock()
    fake.enumerate.return_value = [info]
    fake.device.return_value = device
    return fake


@pytest.mark.asyncio
async def test_read_hid_battery_cloud_ii():
    reply = [0] * 16
    reply[0], reply[2], reply[3], reply[7] = 11, 187, GET_BATTERY_CMD, 70
    device = FakeHidDevice(reply)
    info = {
        "path": b"cloud-ii",
        "vendor_id": 0x0951,
        "product_id": 0x1718,
        "product_string": "HyperX Cloud II Wireless",
    }
    rec = await read_hid_battery(hid_mod=_fake_hid(device, info))
    assert rec == DeviceRecord(
        id="hyperx:cloud-ii-wireless",
        name="HyperX Cloud II Wireless",
        percent=70,
        kind="headset",
    )
    assert device.wrote == _battery_request()


@pytest.mark.asyncio
async def test_read_hid_battery_cloud_ii_dts():
    reply = [0] * 16
    reply[0], reply[1], reply[2], reply[3], reply[7] = 6, 255, 187, GET_BATTERY_CMD, 55
    device = FakeHidDevice(reply)
    info = {
        "path": b"cloud-ii-dts",
        "vendor_id": 0x03F0,
        "product_id": 0x0D93,
        "product_string": "HyperX Cloud II Wireless",
    }
    rec = await read_hid_battery(hid_mod=_fake_hid(device, info))
    assert rec == DeviceRecord(
        id="hyperx:cloud-ii-wireless",
        name="HyperX Cloud II Wireless",
        percent=55,
        kind="headset",
    )
    assert device.wrote == _battery_request_dts()


@pytest.mark.asyncio
async def test_provider_empty_when_no_reply():
    device = FakeHidDevice([])
    info = {
        "path": b"cloud-ii",
        "vendor_id": 0x0951,
        "product_id": 0x1718,
        "product_string": "HyperX Cloud II Wireless",
    }
    rec = await read_hid_battery(hid_mod=_fake_hid(device, info))
    assert rec is None
