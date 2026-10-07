from models import classify_kind


def test_classify_headset():
    assert classify_kind("WH-1000XM5 Headphones") == "headset"
    assert classify_kind("Galaxy Buds2") == "headset"


def test_classify_mouse():
    assert classify_kind("MX Master Mouse") == "mouse"


def test_classify_controller():
    assert classify_kind("Xbox Wireless Controller") == "controller"
    assert classify_kind("DualSense Pad") == "controller"


def test_classify_other():
    assert classify_kind("Unknown Thing") == "other"
    assert classify_kind("") == "other"
