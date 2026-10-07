from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DeviceKind = Literal["headset", "mouse", "controller", "other"]


@dataclass(frozen=True)
class DeviceRecord:
    id: str
    name: str
    percent: int
    kind: DeviceKind


def classify_kind(name: str) -> DeviceKind:
    n = (name or "").lower()
    if any(k in n for k in ("headset", "headphone", "head", "ear", "buds")):
        return "headset"
    if "mouse" in n:
        return "mouse"
    if any(k in n for k in ("control", "pad", "xbox", "dual")):
        return "controller"
    return "other"
