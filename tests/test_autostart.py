from unittest.mock import MagicMock, patch

from autostart import VALUE_NAME, launch_command, set_enabled


def test_launch_command_points_at_main_py():
    cmd = launch_command()
    assert "main.py" in cmd
    assert cmd.startswith('"')
    assert VALUE_NAME == "BatteryTray"


def test_launch_command_frozen_uses_exe_only():
    with patch("autostart._is_frozen", return_value=True):
        with patch("autostart.sys.executable", r"C:\Apps\BatteryTray.exe"):
            cmd = launch_command()
    assert cmd == r'"C:\Apps\BatteryTray.exe"'
    assert "main.py" not in cmd


def test_set_enabled_uses_winreg_delete_value_function():
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
    mock_winreg.HKEY_CURRENT_USER = object()
    mock_winreg.KEY_SET_VALUE = 2
    mock_winreg.REG_SZ = 1
    mock_winreg.DeleteValue.side_effect = FileNotFoundError

    with patch.dict("sys.modules", {"winreg": mock_winreg}):
        with patch("autostart.sys.platform", "win32"):
            set_enabled(True)

    assert mock_winreg.DeleteValue.call_count >= 1
    mock_winreg.SetValueEx.assert_called()
    # Must be winreg.DeleteValue(key, name), not key.DeleteValue(...)
    mock_key.DeleteValue.assert_not_called()
