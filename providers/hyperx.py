"""HyperX Cloud II Wireless battery via HID (no NGENUITY required).

Two dongle families exist:

* Kingston / older (VID ``0x0951``): 62-byte report, reply ``0B 00 BB 02``, % at byte 7
* HP / DTS (VID ``0x03F0``): 20-byte report ``06 FF BB 02``, reply same layout, % at byte 7
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

TARGET_ID = "hyperx:cloud-ii-wireless"
TARGET_NAME = "HyperX Cloud II Wireless"

# Kingston / HyperX and later HP IDs used by Cloud II Wireless dongles.
VENDOR_IDS = (0x0951, 0x03F0)
PRODUCT_IDS = {
    0x1718,  # Kingston Cloud II Wireless
    0x16EA,
    0x16EB,
    0x0B92,  # Cloud Flight S family (same legacy packet)
    0x018B,  # HP Cloud II Wireless
    0x0D93,  # HP Cloud II Wireless (DTS / newer)
    0x0696,  # HP Cloud II Wireless variant
}

GET_BATTERY_CMD = 2
REPORT_LEN = 62
DTS_REPORT_LEN = 20
READ_TIMEOUT_MS = 1000


def _battery_request() -> list[int]:
    pkt = [0] * REPORT_LEN
    pkt[0] = 0x06
    pkt[2] = 0x02
    pkt[4] = 0x9A
    pkt[7] = 0x68
    pkt[8] = 0x4A
    pkt[9] = 0x8E
    pkt[10] = 0x0A
    pkt[14] = 0xBB
    pkt[15] = GET_BATTERY_CMD
    return pkt


def _battery_request_dts() -> list[int]:
    pkt = [0] * DTS_REPORT_LEN
    pkt[0] = 0x06
    pkt[1] = 0xFF
    pkt[2] = 0xBB
    pkt[3] = GET_BATTERY_CMD
    return pkt


def _decode_battery_reply(data: list[int]) -> int | None:
    if len(data) < 8:
        return None
    # Legacy: [11, 0, 187, 2, ...] percent at [7]
    if data[0] == 11 and data[2] == 187 and data[3] == GET_BATTERY_CMD:
        percent = int(data[7])
        if 0 <= percent <= 100:
            return percent
        return None
    # HP / DTS: [6, 255, 187, 2, ...] percent at [7]
    if data[0] == 6 and data[1] == 255 and data[2] == 187 and data[3] == GET_BATTERY_CMD:
        percent = int(data[7])
        if 0 <= percent <= 100:
            return percent
        return None
    # Some stacks include a leading report id of 6 on the legacy payload.
    if data[0] == 6 and len(data) > 8 and data[1] == 0 and data[3] == 187 and data[4] == GET_BATTERY_CMD:
        percent = int(data[8])
        if 0 <= percent <= 100:
            return percent
    return None


def _name_looks_like_cloud_ii(product: str) -> bool:
    n = (product or "").lower()
    if "cloud ii" in n or "cloud 2" in n or "cloudii" in n:
        return True
    if "hyperx" in n and "wireless" in n:
        return True
    return False


def _is_candidate(info: dict[str, Any]) -> bool:
    vid = int(info.get("vendor_id") or 0)
    pid = int(info.get("product_id") or 0)
    product = str(info.get("product_string") or "")
    if vid not in VENDOR_IDS:
        return False
    if pid in PRODUCT_IDS:
        return True
    return _name_looks_like_cloud_ii(product)


def _requests_for(info: dict[str, Any]) -> list[list[int]]:
    vid = int(info.get("vendor_id") or 0)
    # Prefer the protocol that matches the vendor; always try the other as fallback.
    if vid == 0x03F0:
        return [_battery_request_dts(), _battery_request()]
    return [_battery_request(), _battery_request_dts()]


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


def _write_request(dev: Any, req: list[int]) -> bool:
    try:
        written = dev.write(req)
        if written is not None and written < 0:
            raise OSError("write failed")
        return True
    except Exception:
        pass
    try:
        # Feature-report path used by some Windows stacks / exclusive opens.
        dev.send_feature_report([0, *req] if req and req[0] != 0 else req)
        return True
    except Exception:
        return False


def _read_replies(dev: Any, *, timeout_ms: int = READ_TIMEOUT_MS) -> list[list[int]]:
    replies: list[list[int]] = []
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        remaining = max(1, int((deadline - time.monotonic()) * 1000))
        try:
            data = _as_int_list(dev.read(255, timeout_ms=min(80, remaining)))
        except TypeError:
            try:
                data = _as_int_list(dev.read(255))
            except Exception:
                data = []
        except Exception:
            data = []
        if data:
            replies.append(data)
            if _decode_battery_reply(data) is not None:
                return replies
        else:
            # No bytes this slice; keep polling until deadline.
            time.sleep(0.01)
    try:
        feat = _as_int_list(dev.get_feature_report(6, REPORT_LEN + 1))
        if feat:
            replies.append(feat[1:] if feat[0] == 6 and len(feat) > 8 else feat)
    except Exception:
        pass
    return replies


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
        try:
            dev.get_input_report(6, REPORT_LEN)
        except Exception:
            pass
        for req in _requests_for(info):
            if not _write_request(dev, req):
                continue
            for data in _read_replies(dev):
                percent = _decode_battery_reply(data)
                if percent is not None:
                    return percent
        return None
    finally:
        try:
            dev.close()
        except Exception:
            pass


def _read_cloud_ii_percent(hid_mod: Any | None = None) -> int | None:
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
        percent = await asyncio.to_thread(_read_cloud_ii_percent, hid_mod)
        if percent is None:
            return None
        return DeviceRecord(id=TARGET_ID, name=TARGET_NAME, percent=percent, kind="headset")
    except Exception:
        return None


class HyperXProvider:
    async def scan(self) -> list[DeviceRecord]:
        record = await read_hid_battery()
        if record is not None:
            return [record]
        return []
