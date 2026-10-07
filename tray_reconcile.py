from __future__ import annotations

from dataclasses import dataclass

from models import DeviceRecord


@dataclass(frozen=True)
class ReconcilePlan:
    upserts: list[DeviceRecord]
    removes: list[str]
    show_status: bool
    status_tooltip: str


def plan_reconcile(
    previous_ids: set[str],
    devices: list[DeviceRecord],
    *,
    bluetooth_error: str | None,
) -> ReconcilePlan:
    if bluetooth_error is not None:
        return ReconcilePlan(
            upserts=[],
            removes=sorted(previous_ids),
            show_status=True,
            status_tooltip=bluetooth_error,
        )
    if not devices:
        return ReconcilePlan(
            upserts=[],
            removes=sorted(previous_ids),
            show_status=True,
            status_tooltip="No battery devices found",
        )
    current = {d.id for d in devices}
    return ReconcilePlan(
        upserts=list(devices),
        removes=sorted(previous_ids - current),
        show_status=False,
        status_tooltip="",
    )
