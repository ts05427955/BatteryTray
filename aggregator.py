from __future__ import annotations

from models import DeviceRecord
from providers.base import BatteryProvider


async def aggregate_battery_devices(
    providers: list[BatteryProvider] | None = None,
) -> list[DeviceRecord]:
    if providers is None:
        from providers import default_providers

        providers = default_providers()
    results: list[DeviceRecord] = []
    for p in providers:
        try:
            results.extend(await p.scan())
        except Exception:
            continue
    return results
