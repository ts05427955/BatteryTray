"""Razer Barracuda X 2.4 — intentionally passive.

Barracuda X 2.4 (``1532:0552``) is not supported in Synapse for battery, and the
dongle uses a Macronix vendor HID that is **not** OpenRazer Chroma. Opening that
HID and sending probe writes can disrupt the composite USB audio device; users
have seen the headset drop when BatteryTray quits after such probes.

Until a verified, read-only battery map exists (USB capture while a reader that
actually queries percent is running), this provider never opens HID and never
returns a percent. Keeping the provider registered preserves the architecture
for a future safe implementation.
"""

from __future__ import annotations

from models import DeviceRecord

TARGET_ID = "razer:barracuda-x-24"
TARGET_NAME = "Razer Barracuda X 2.4"
RAZER_VID = 0x1532


def _matches_barracuda_24(product: str) -> bool:
    n = (product or "").lower()
    if "barracuda" not in n:
        return False
    return "2.4" in n or "barracuda x" in n


async def read_synapse_battery() -> DeviceRecord | None:
    """Synapse does not expose Barracuda X battery on Windows."""
    return None


async def read_hid_battery(*, hid_mod=None) -> DeviceRecord | None:
    """Do not open Barracuda HID — probes can disconnect the headset audio path."""
    return None


class RazerProvider:
    async def scan(self) -> list[DeviceRecord]:
        record = await read_synapse_battery()
        if record is not None:
            return [record]
        record = await read_hid_battery()
        if record is not None:
            return [record]
        return []
