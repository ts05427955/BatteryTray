"""Scyrox V8 battery via HID (S-Center / web-driver protocol).

Protocol documented by community reimplementation of the Scyrox web app:
16-byte commands on report ID 8; BatteryLevel command ``4`` returns percent
at response byte 5.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from models import DeviceRecord

try:
    import hid as hid
except ImportError:
    hid = None  # type: ignore[assignment]

TARGET_ID = "scyrox:v8"
TARGET_NAME = "Scyrox V8"

VID = 0x3554
PRODUCT_IDS = {0xF5F7, 0xF5F4, 0xF5F6}
REPORT_ID = 8

CMD_ENCRYPTION = 1
CMD_PC_DRIVER_STATUS = 2
CMD_DEVICE_ONLINE = 3
CMD_BATTERY_LEVEL = 4


def _checksum(packet: list[int]) -> int:
    total = sum(packet[:15]) & 0xFF
    return (85 - total - REPORT_ID) & 0xFF


def build_packet(cmd: int, payload: list[int] | None = None) -> list[int]:
    payload = list(payload or [])
    if len(payload) > 10:
        raise ValueError("payload too long")
    pkt = [0] * 16
    pkt[0] = cmd & 0xFF
    pkt[4] = len(payload)
    for i, b in enumerate(payload):
        pkt[5 + i] = b & 0xFF
    pkt[15] = _checksum(pkt)
    return pkt


def decode_battery_response(frame: list[int]) -> int | None:
    """Decode a 16-byte response frame (without report id)."""
    if len(frame) < 6:
        return None
    # Some stacks leave cmd echo in byte 0; percent is at [5].
    percent = int(frame[5])
    if 0 <= percent <= 100:
        return percent
    return None


def _is_candidate(info: dict[str, Any]) -> bool:
    vid = int(info.get("vendor_id") or 0)
    pid = int(info.get("product_id") or 0)
    product = str(info.get("product_string") or "").lower()
    if vid == VID and pid in PRODUCT_IDS:
        return True
    if vid == VID and ("scyrox" in product or "v8" in product):
        return True
    return "scyrox" in product and "v8" in product


def _load_hid(hid_mod: Any | None) -> Any | None:
    if hid_mod is not None:
        return hid_mod
    if hid is not None:
        return hid
    try:
        return __import__("hid")
    except ImportError:
        return None


def _open_path(dev: Any, path: Any) -> bool:
    try:
        dev.open_path(path)
        return True
    except Exception:
        pass
    if isinstance(path, bytes):
        try:
            dev.open_path(path.decode("utf-8", errors="ignore"))
            return True
        except Exception:
            return False
    return False


def _as_int_list(raw: Any) -> list[int]:
    if not raw:
        return []
    try:
        return [int(b) for b in raw]
    except (TypeError, ValueError):
        return []


def _parse_response(buf: list[int]) -> list[int] | None:
    if len(buf) >= 17 and buf[0] in (REPORT_ID, 0):
        return buf[1:17]
    if len(buf) >= 16:
        return buf[:16]
    return None


def _exchange(dev: Any, req: list[int], *, timeout_s: float = 0.4) -> list[int] | None:
    report = [REPORT_ID, *req]
    try:
        written = dev.write(report)
        if written is not None and written < 0:
            return None
    except Exception:
        try:
            dev.send_feature_report(report)
        except Exception:
            return None

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
        try:
            raw = _as_int_list(dev.read(64, timeout_ms=min(40, remaining_ms)))
        except TypeError:
            try:
                raw = _as_int_list(dev.read(64))
            except Exception:
                raw = []
        except Exception:
            raw = []
        frame = _parse_response(raw)
        if frame is not None:
            return frame
        # Fallback: feature report read
        try:
            feat = _as_int_list(dev.get_feature_report(REPORT_ID, 17))
            frame = _parse_response(feat)
            if frame is not None:
                return frame
        except Exception:
            pass
    return None


def _handshake_and_battery(dev: Any) -> int | None:
    online = _exchange(dev, build_packet(CMD_DEVICE_ONLINE, []))
    if online is None:
        return None
    # Byte 5 == 1 means online in the vendor protocol; if absent, still try battery.
    if len(online) > 5 and online[5] not in (0, 1):
        # unexpected; continue anyway
        pass
    if len(online) > 5 and online[5] == 0:
        return None

    _exchange(dev, build_packet(CMD_PC_DRIVER_STATUS, [1]))
    _exchange(dev, build_packet(CMD_ENCRYPTION, [1, 2, 3, 4, 0, 0, 0, 0]))
    bat = _exchange(dev, build_packet(CMD_BATTERY_LEVEL, []))
    if bat is None:
        return None
    return decode_battery_response(bat)


def _try_interface(h: Any, info: dict[str, Any]) -> int | None:
    path = info.get("path")
    if not path:
        return None
    try:
        dev = h.device()
    except Exception:
        return None
    if not _open_path(dev, path):
        return None
    try:
        return _handshake_and_battery(dev)
    finally:
        try:
            dev.close()
        except Exception:
            pass


def _read_v8_percent(hid_mod: Any | None = None) -> int | None:
    h = _load_hid(hid_mod)
    if h is None:
        return None
    try:
        infos = list(h.enumerate())
    except Exception:
        return None
    for info in infos:
        if not isinstance(info, dict) or not _is_candidate(info):
            continue
        percent = _try_interface(h, info)
        if percent is not None:
            return percent
    return None


async def read_hid_battery(*, hid_mod: Any | None = None) -> DeviceRecord | None:
    try:
        percent = await asyncio.to_thread(_read_v8_percent, hid_mod)
        if percent is None:
            return None
        return DeviceRecord(id=TARGET_ID, name=TARGET_NAME, percent=percent, kind="mouse")
    except Exception:
        return None


class ScyroxProvider:
    async def scan(self) -> list[DeviceRecord]:
        record = await read_hid_battery()
        if record is not None:
            return [record]
        return []
