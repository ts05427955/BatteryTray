from models import DeviceRecord
from tray_reconcile import plan_reconcile


def _dev(id_: str, pct: int = 50) -> DeviceRecord:
    return DeviceRecord(id=id_, name=id_, percent=pct, kind="other")


def test_bluetooth_error_clears_devices():
    plan = plan_reconcile({"a"}, [_dev("a")], bluetooth_error="Bluetooth is off")
    assert plan.show_status is True
    assert plan.status_tooltip == "Bluetooth is off"
    assert plan.upserts == []
    assert plan.removes == ["a"]


def test_no_devices_shows_status():
    plan = plan_reconcile(set(), [], bluetooth_error=None)
    assert plan.show_status is True
    assert plan.status_tooltip == "No battery devices found"
    assert plan.upserts == []
    assert plan.removes == []


def test_devices_hide_status_and_remove_stale():
    plan = plan_reconcile({"old", "keep"}, [_dev("keep", 80), _dev("new", 20)], bluetooth_error=None)
    assert plan.show_status is False
    assert {d.id for d in plan.upserts} == {"keep", "new"}
    assert plan.removes == ["old"]
