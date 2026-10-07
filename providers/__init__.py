from __future__ import annotations

from providers.base import BatteryProvider
from providers.ble import BleProvider
from providers.hyperx import HyperXProvider
from providers.logitech import LogitechProvider
from providers.razer import RazerProvider
from providers.scyrox import ScyroxProvider


def default_providers() -> list[BatteryProvider]:
    return [
        BleProvider(),
        LogitechProvider(),
        ScyroxProvider(),
        RazerProvider(),
        HyperXProvider(),
    ]
