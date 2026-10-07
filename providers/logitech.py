"""Logitech G502 X PLUS battery provider.

Tries G Hub's local WebSocket first. HID++ fallback (feature 0x1004 / 0x1000)
runs only when G Hub is unavailable. G Hub may occupy the HID++ interface, so
the HID path is expected to fail while G Hub holds the device.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from models import DeviceRecord
from providers.logitech_hidpp import matches_g502_x_plus_name, read_g502_percent

GHUB_WS = "ws://localhost:9010"
TARGET_ID = "logitech:g502-x-plus"
TARGET_NAME = "G502 X PLUS"
_GHUB_TIMEOUT_S = 5.0

WsConnectFactory = Callable[[str], Any]


def _default_ws_connect(uri: str) -> Any:
    import websockets

    return websockets.connect(
        uri,
        subprotocols=["json"],
        additional_headers={"Origin": "file://"},
    )


def _device_infos(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("deviceInfos", "devices"):
        items = payload.get(key)
        if isinstance(items, list):
            return [d for d in items if isinstance(d, dict)]
    return []


def _display_names(device: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("extendedDisplayName", "name", "displayName"):
        value = device.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def _has_battery_capability(device: dict[str, Any]) -> bool | None:
    """Return True/False if known, or None if G Hub omitted the flag."""
    if "hasBatteryStatus" in device:
        return bool(device["hasBatteryStatus"])
    caps = device.get("capabilities")
    if isinstance(caps, dict) and "hasBatteryStatus" in caps:
        return bool(caps["hasBatteryStatus"])
    return None


def _matches_g502_x_plus(device: dict[str, Any]) -> bool:
    if not matches_g502_x_plus_name(_display_names(device)):
        return False
    has_batt = _has_battery_capability(device)
    if has_batt is False:
        return False
    return True


def _device_id(device: dict[str, Any]) -> str | None:
    for key in ("id", "deviceId"):
        value = device.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _clamp_percent(value: Any) -> int | None:
    if value is None:
        return None
    try:
        pct = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, pct))


async def _recv_matching(ws: Any, path: str) -> dict[str, Any]:
    """G Hub may push OPTIONS (and other) frames before the response we want."""
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if not isinstance(msg, dict):
            continue
        if msg.get("path") == path and msg.get("payload") is not None:
            return msg


async def _read_ghub_battery_with_connect(ws_connect: WsConnectFactory) -> DeviceRecord | None:
    async with ws_connect(GHUB_WS) as ws:
        await ws.send(json.dumps({"msgId": "", "verb": "GET", "path": "/devices/list"}))
        list_msg = await _recv_matching(ws, "/devices/list")
        payload = list_msg.get("payload")
        if not isinstance(payload, dict):
            return None

        device_id: str | None = None
        for info in _device_infos(payload):
            if _matches_g502_x_plus(info):
                device_id = _device_id(info)
                if device_id:
                    break
        if not device_id:
            return None

        battery_path = f"/battery/{device_id}/state"
        await ws.send(json.dumps({"msgId": "", "verb": "GET", "path": battery_path}))
        battery_msg = await _recv_matching(ws, battery_path)
        battery_payload = battery_msg.get("payload")
        if not isinstance(battery_payload, dict):
            return None
        percent = _clamp_percent(battery_payload.get("percentage"))
        if percent is None:
            return None
        return DeviceRecord(id=TARGET_ID, name=TARGET_NAME, percent=percent, kind="mouse")


async def read_ghub_battery(*, ws_connect: WsConnectFactory | None = None) -> DeviceRecord | None:
    connect = ws_connect or _default_ws_connect
    try:
        return await asyncio.wait_for(
            _read_ghub_battery_with_connect(connect),
            timeout=_GHUB_TIMEOUT_S,
        )
    except Exception:
        return None


async def read_hid_battery(*, hid_mod: Any | None = None) -> DeviceRecord | None:
    try:
        percent = await asyncio.to_thread(read_g502_percent, hid_mod)
        if percent is None:
            return None
        return DeviceRecord(id=TARGET_ID, name=TARGET_NAME, percent=percent, kind="mouse")
    except Exception:
        return None


class LogitechProvider:
    async def scan(self) -> list[DeviceRecord]:
        record = await read_ghub_battery()
        if record is not None:
            return [record]
        record = await read_hid_battery()
        if record is not None:
            return [record]
        return []
