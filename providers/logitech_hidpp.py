"""Minimal HID++ 2.0 battery I/O for G502-class LIGHTSPEED.

G Hub / Options+ may already hold an exclusive open on the HID++ interface; in
that case this path returns None. Prefer the G Hub WebSocket path when it works.

Battery percent is decoded only from feature 0x1004 (unifiedBattery getStatus)
or 0x1000 (batteryUnity / batteryStatus level). Coarse levels and voltage
curves are not converted into a made-up percentage.
"""

from __future__ import annotations

from typing import Any

try:
    import hid as hid
except ImportError:
    hid = None  # type: ignore[assignment]

LOGI_VID = 0x046D
HIDPP_USAGE_PAGE = 0xFF00
SW_ID = 0x01
SHORT_ID = 0x10
LONG_ID = 0x11
ROOT_INDEX = 0x00
FEAT_DEVICE_NAME = 0x0005
FEAT_BATTERY_UNITY = 0x1000
FEAT_UNIFIED_BATTERY = 0x1004
DEVICE_INDICES = (0x01, 0xFF)
_GENERIC_RECEIVER_MARKERS = ("receiver", "lightspeed", "unifying", "bolt")


def matches_g502_x_plus_name(label: str) -> bool:
    n = (label or "").lower()
    if "g502" not in n:
        return False
    return "x plus" in n or "x+" in n


def _load_hid(hid_mod: Any | None) -> Any | None:
    if hid_mod is not None:
        return hid_mod
    if hid is not None:
        return hid
    try:
        return __import__("hid")
    except ImportError:
        return None


def _short(device_idx: int, feat_idx: int, func: int, *params: int) -> list[int]:
    pkt = [SHORT_ID, device_idx, feat_idx, ((func & 0x0F) << 4) | (SW_ID & 0x0F)]
    padded = list(params) + [0, 0, 0]
    pkt.extend(padded[:3])
    return pkt


def _long(device_idx: int, feat_idx: int, func: int, *params: int) -> list[int]:
    pkt = [LONG_ID, device_idx, feat_idx, ((func & 0x0F) << 4) | (SW_ID & 0x0F)]
    padded = list(params) + [0] * 16
    pkt.extend(padded[:16])
    return pkt


def _flush(dev: Any) -> None:
    for _ in range(16):
        try:
            data = dev.read(64, timeout_ms=1)
        except Exception:
            break
        if not data:
            break


def _transact(dev: Any, request: list[int], timeout_ms: int = 80, attempts: int = 10) -> list[int] | None:
    _flush(dev)
    try:
        dev.write(request)
    except Exception:
        return None
    want_dev = request[1]
    want_feat = request[2]
    want_funcsw = request[3]
    for _ in range(attempts):
        try:
            raw = dev.read(64, timeout_ms=timeout_ms)
        except Exception:
            return None
        if not raw:
            continue
        resp = list(raw)
        if len(resp) < 5 or resp[0] not in (SHORT_ID, LONG_ID):
            continue
        if resp[1] != want_dev:
            continue
        if resp[2] in (0x8F, 0xFF):
            return None
        if resp[2] == want_feat and resp[3] == want_funcsw:
            return resp
    return None


def _feature_request(dev: Any, device_idx: int, feat_idx: int, func: int, *params: int) -> list[int] | None:
    resp = _transact(dev, _long(device_idx, feat_idx, func, *params))
    if resp is not None:
        return resp
    return _transact(dev, _short(device_idx, feat_idx, func, *params))


def _get_feature_index(dev: Any, device_idx: int, feature_id: int) -> int | None:
    resp = _transact(dev, _short(device_idx, ROOT_INDEX, 0, feature_id >> 8, feature_id & 0xFF, 0))
    if not resp or len(resp) < 5:
        return None
    idx = resp[4]
    if idx == 0:
        return None
    return idx


def _decode_unified_battery(resp: list[int]) -> int | None:
    if len(resp) < 5:
        return None
    percent = resp[4]
    if 0 <= percent <= 100:
        return percent
    return None


def _decode_battery_unity(resp: list[int]) -> int | None:
    if len(resp) < 5:
        return None
    percent = resp[4]
    status = resp[6] if len(resp) > 6 else 0
    # Spec: charge-complete reports 0 unknown + status 3; map that to 100.
    if status == 3:
        return 100
    if 1 <= percent <= 100:
        return percent
    if status == 0 and percent == 0:
        return 0
    return None


def _read_percent(dev: Any, device_idx: int) -> int | None:
    unified_idx = _get_feature_index(dev, device_idx, FEAT_UNIFIED_BATTERY)
    if unified_idx is not None:
        resp = _feature_request(dev, device_idx, unified_idx, 1)
        if resp is not None:
            percent = _decode_unified_battery(resp)
            if percent is not None:
                return percent

    unity_idx = _get_feature_index(dev, device_idx, FEAT_BATTERY_UNITY)
    if unity_idx is not None:
        resp = _feature_request(dev, device_idx, unity_idx, 0)
        if resp is not None:
            percent = _decode_battery_unity(resp)
            if percent is not None:
                return percent
    return None


def _read_device_name(dev: Any, device_idx: int) -> str | None:
    feat_idx = _get_feature_index(dev, device_idx, FEAT_DEVICE_NAME)
    if feat_idx is None:
        return None
    count_resp = _feature_request(dev, device_idx, feat_idx, 0)
    if not count_resp or len(count_resp) < 5:
        return None
    length = count_resp[4]
    if length <= 0:
        return None
    chunks: list[bytes] = []
    offset = 0
    while offset < min(length, 48):
        resp = _feature_request(dev, device_idx, feat_idx, 1, offset)
        if not resp or len(resp) < 5:
            break
        chunks.append(bytes(resp[4:]))
        offset += 16
    raw = b"".join(chunks)[:length].split(b"\x00", 1)[0]
    name = raw.decode("utf-8", errors="replace").strip()
    return name or None


def _product_is_generic_receiver(product: str) -> bool:
    n = (product or "").strip().lower()
    if not n:
        return True
    return any(marker in n for marker in _GENERIC_RECEIVER_MARKERS)


def _is_hidpp_interface(info: dict[str, Any]) -> bool:
    if info.get("vendor_id") != LOGI_VID:
        return False
    usage_page = info.get("usage_page")
    return usage_page in (None, 0, HIDPP_USAGE_PAGE)


def _candidate_sort_key(info: dict[str, Any]) -> tuple[int, int, int]:
    product = str(info.get("product_string") or "")
    named = 0 if matches_g502_x_plus_name(product) else 1
    page_rank = 0 if info.get("usage_page") == HIDPP_USAGE_PAGE else 1
    usage_rank = 0 if info.get("usage") == 2 else 1
    return (named, page_rank, usage_rank)


def _select_candidates(infos: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for info in infos:
        if not isinstance(info, dict) or not _is_hidpp_interface(info):
            continue
        product = str(info.get("product_string") or "")
        if matches_g502_x_plus_name(product) or _product_is_generic_receiver(product):
            out.append(info)
    out.sort(key=_candidate_sort_key)
    return out


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


def _try_interface(h: Any, info: dict[str, Any]) -> int | None:
    path = info.get("path")
    if not path:
        return None
    product_is_target = matches_g502_x_plus_name(str(info.get("product_string") or ""))
    try:
        dev = h.device()
    except Exception:
        return None
    if not _open_path(dev, path):
        return None
    try:
        for device_idx in DEVICE_INDICES:
            if not product_is_target:
                reported = _read_device_name(dev, device_idx)
                if not matches_g502_x_plus_name(reported or ""):
                    continue
            percent = _read_percent(dev, device_idx)
            if percent is not None:
                return percent
        return None
    finally:
        try:
            dev.close()
        except Exception:
            pass


def read_g502_percent(hid_mod: Any | None = None) -> int | None:
    h = _load_hid(hid_mod)
    if h is None:
        return None
    try:
        infos = list(h.enumerate())
    except Exception:
        return None
    for info in _select_candidates(infos):
        percent = _try_interface(h, info)
        if percent is not None:
            return percent
    return None
