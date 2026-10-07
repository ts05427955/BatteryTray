import pytest

from aggregator import aggregate_battery_devices
from models import DeviceRecord


class FakeProvider:
    def __init__(self, devices=None, error=None):
        self._devices = devices or []
        self._error = error

    async def scan(self):
        if self._error:
            raise self._error
        return list(self._devices)


@pytest.mark.asyncio
async def test_aggregate_merges_providers():
    a = DeviceRecord(id="logitech:g502-x-plus", name="G502 X PLUS", percent=80, kind="mouse")
    b = DeviceRecord(id="razer:barracuda-x-24", name="Razer Barracuda X 2.4", percent=50, kind="headset")
    out = await aggregate_battery_devices([FakeProvider([a]), FakeProvider([b])])
    assert {d.id for d in out} == {a.id, b.id}


@pytest.mark.asyncio
async def test_aggregate_isolates_provider_failure():
    a = DeviceRecord(id="logitech:g502-x-plus", name="G502 X PLUS", percent=80, kind="mouse")
    out = await aggregate_battery_devices([FakeProvider(error=RuntimeError("boom")), FakeProvider([a])])
    assert out == [a]
