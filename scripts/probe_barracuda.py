"""Probe Razer Barracuda X 2.4 (1532:0552) vendor HID carefully.

Re-opens the device for each trial so a bad command does not brick the session.
"""

from __future__ import annotations

import time
from typing import Any

import hid

VID = 0x1532
PID = 0x0552
REPORT_LEN = 64


def _hex(data: list[int], n: int = 32) -> str:
    return " ".join(f"{b:02X}" for b in data[:n])


def _pkt(prefix: list[int]) -> list[int]:
    out = [0] * REPORT_LEN
    for i, b in enumerate(prefix):
        out[i] = b & 0xFF
    return out


def _vendor_path() -> Any | None:
    for info in hid.enumerate():
        if int(info.get("vendor_id") or 0) != VID:
            continue
        if int(info.get("product_id") or 0) != PID:
            continue
        if int(info.get("usage_page") or 0) != 0xFF00:
            continue
        if info.get("path"):
            return info.get("path")
    return None


def _open() -> hid.device | None:
    path = _vendor_path()
    if not path:
        return None
    dev = hid.device()
    try:
        dev.open_path(path)
        return dev
    except Exception as exc:
        print(f"open failed: {exc}")
        return None


def _close(dev: hid.device | None) -> None:
    if dev is None:
        return
    try:
        dev.close()
    except Exception:
        pass


def _read_all(dev: hid.device, *, timeout_ms: int = 400, max_reads: int = 6) -> list[list[int]]:
    out: list[list[int]] = []
    for _ in range(max_reads):
        try:
            data = list(dev.read(REPORT_LEN, timeout_ms=timeout_ms))
        except Exception:
            break
        if not data:
            if out:
                break
            continue
        out.append(data)
    return out


def _trial(label: str, packets: list[list[int]], *, handshake: bool = True) -> None:
    print(f"\n== {label} ==")
    dev = _open()
    if dev is None:
        print("open failed")
        return
    try:
        if handshake:
            hs = _pkt([0x01, 0x40, 0x00])
            print(f"TX {_hex(hs)}")
            n = dev.write(hs)
            print(f"write -> {n}")
            for rx in _read_all(dev, timeout_ms=250, max_reads=3):
                print(f"RX {_hex(rx)}")
            time.sleep(0.05)
        for req in packets:
            print(f"TX {_hex(req)}")
            try:
                n = dev.write(req)
                print(f"write -> {n}")
            except Exception as exc:
                print(f"write err: {exc}")
                continue
            for rx in _read_all(dev):
                print(f"RX {_hex(rx)}")
                interesting = [(i, b) for i, b in enumerate(rx) if 5 <= b <= 100]
                if interesting[:8]:
                    print(f"   bytes_in_5_100={interesting[:12]}")
            time.sleep(0.05)
    finally:
        _close(dev)


def main() -> None:
    path = _vendor_path()
    if not path:
        print("No Barracuda vendor interface (1532:0552 FF00)")
        return
    print(f"vendor path ok: {path!r}")

    # 1) Handshake only
    _trial("handshake only", [])

    # 2) Exact firmware-tool follow-up from Razer Insider logs
    ota = _pkt(
        [
            0x01,
            0x80,
            0x13,
            0x50,
            0x41,
            0x06,
            0x01,
            0x0D,
            0x00,
            0x25,
            0x34,
            0x12,
            0x5A,
            0x5A,
            0x01,
            0x00,
            0x00,
            0x00,
            0xF0,
        ]
    )
    _trial("firmware OTA ioctl packet", [ota])

    # 3) Short 01 80 status-ish probes (length in byte2)
    for length, payload in [
        (1, [0x00]),
        (1, [0x01]),
        (1, [0x02]),
        (1, [0x03]),
        (1, [0x04]),
        (1, [0x05]),
        (2, [0x00, 0x00]),
        (2, [0x01, 0x00]),
        (3, [0x50, 0x41, 0x01]),
        (3, [0x50, 0x41, 0x02]),
        (3, [0x50, 0x49, 0x01]),
        (4, [0x50, 0x41, 0x06, 0x01]),
        (5, [0x50, 0x41, 0x06, 0x01, 0x0D]),
    ]:
        body = [0x01, 0x80, length, *payload]
        _trial(f"01 80 len={length} payload={_hex(payload, 8)}", [_pkt(body)])

    # 4) Alternate command families seen in Macronix/YStech tools
    for cmd in (0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F):
        _trial(f"cmd family 01 {cmd:02X} 00", [_pkt([0x01, cmd, 0x00])])

    # 5) Passive listen (no TX) — some headsets push battery unsolicited
    print("\n== passive listen 3s ==")
    dev = _open()
    if dev:
        try:
            end = time.time() + 3
            while time.time() < end:
                for rx in _read_all(dev, timeout_ms=200, max_reads=1):
                    print(f"RX {_hex(rx)}")
        finally:
            _close(dev)

    print("\ndone")


if __name__ == "__main__":
    main()
