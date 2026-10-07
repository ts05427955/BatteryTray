from unittest.mock import MagicMock, patch

from models import DeviceRecord
from tray_app import TrayApp


def _dev(id_: str = "AA:BB", name: str = "Test Mouse", pct: int = 87) -> DeviceRecord:
    return DeviceRecord(id=id_, name=name, percent=pct, kind="mouse")


def test_menu_labels_include_about():
    app = TrayApp(on_refresh=lambda: None, on_quit=lambda: None)
    titles = [item.text for item in app._menu()]
    assert titles == [
        "Refresh now",
        "Start with Windows",
        "About",
        "Quit",
    ]


@patch("tray_app.threading.Thread")
def test_about_menu_schedules_dialog_thread(mock_thread):
    app = TrayApp(on_refresh=lambda: None, on_quit=lambda: None)
    app._show_about()
    mock_thread.assert_called_once()
    kwargs = mock_thread.call_args.kwargs
    assert kwargs.get("daemon") is True
    assert mock_thread.call_args.kwargs.get("target") is not None or mock_thread.call_args.args


@patch("tray_app.threading.Thread")
@patch("tray_app.pystray.Icon")
def test_empty_devices_shows_status_icon(mock_icon_cls, mock_thread):
    mock_icon_cls.return_value = MagicMock()
    app = TrayApp(on_refresh=lambda: None, on_quit=lambda: None)
    app.apply_devices([], bluetooth_error=None)

    assert mock_icon_cls.call_count == 1
    args, kwargs = mock_icon_cls.call_args
    title = args[2] if len(args) > 2 else kwargs.get("title")
    assert title == "No battery devices found"
    mock_thread.assert_called()


@patch("tray_app.threading.Thread")
@patch("tray_app.pystray.Icon")
def test_device_tooltip_uses_em_dash_percent(mock_icon_cls, mock_thread):
    mock_icon_cls.return_value = MagicMock()
    app = TrayApp(on_refresh=lambda: None, on_quit=lambda: None)
    app.apply_devices([_dev()], bluetooth_error=None)

    args, kwargs = mock_icon_cls.call_args
    title = args[2] if len(args) > 2 else kwargs.get("title")
    assert title == "Test Mouse — 87%"


@patch("tray_app.threading.Thread")
@patch("tray_app.pystray.Icon")
def test_bluetooth_error_uses_status_tooltip(mock_icon_cls, mock_thread):
    mock_icon_cls.return_value = MagicMock()
    app = TrayApp(on_refresh=lambda: None, on_quit=lambda: None)
    app.apply_devices([], bluetooth_error="Bluetooth is off or unavailable")

    args, kwargs = mock_icon_cls.call_args
    title = args[2] if len(args) > 2 else kwargs.get("title")
    assert title == "Bluetooth is off or unavailable"
