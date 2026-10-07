from version import ABOUT_TEXT, APP_NAME, AUTHOR, VERSION


def test_app_identity():
    assert APP_NAME == "BatteryTray"
    assert VERSION == "1.0.1"
    assert AUTHOR == "Marco"
    assert ABOUT_TEXT == "BatteryTray v1.0.1 — created by Marco"
