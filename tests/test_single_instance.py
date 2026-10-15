from unittest.mock import MagicMock, patch

import pytest

from single_instance import SingleInstanceLock, try_acquire_single_instance


def test_try_acquire_returns_lock_when_mutex_created():
    fake_kernel = MagicMock()
    fake_kernel.CreateMutexW.return_value = 12345
    fake_kernel.GetLastError.return_value = 0  # created new

    with patch("single_instance.sys.platform", "win32"):
        with patch("single_instance.ctypes.windll.kernel32", fake_kernel):
            lock = try_acquire_single_instance("BatteryTray")
    assert isinstance(lock, SingleInstanceLock)
    assert lock.acquired is True
    fake_kernel.CreateMutexW.assert_called_once()


def test_try_acquire_returns_none_when_already_exists():
    fake_kernel = MagicMock()
    fake_kernel.CreateMutexW.return_value = 12345
    fake_kernel.GetLastError.return_value = 183  # ERROR_ALREADY_EXISTS

    with patch("single_instance.sys.platform", "win32"):
        with patch("single_instance.ctypes.windll.kernel32", fake_kernel):
            lock = try_acquire_single_instance("BatteryTray")
    assert lock is None
    fake_kernel.CloseHandle.assert_called_once_with(12345)


def test_lock_release_closes_handle():
    fake_kernel = MagicMock()
    lock = SingleInstanceLock(handle=99, _kernel=fake_kernel)
    lock.release()
    fake_kernel.CloseHandle.assert_called_once_with(99)
    lock.release()  # idempotent
    assert fake_kernel.CloseHandle.call_count == 1
