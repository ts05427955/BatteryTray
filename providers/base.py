from __future__ import annotations

from typing import Protocol

from models import DeviceRecord


class BatteryProvider(Protocol):
    async def scan(self) -> list[DeviceRecord]: ...
