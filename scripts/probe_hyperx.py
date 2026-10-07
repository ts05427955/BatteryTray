"""Diagnose HyperX Cloud II Wireless on a friend's PC.

Run with the 2.4G dongle plugged in and the headset powered on:
  python scripts\\probe_hyperx.py > hyperx_probe.txt

Send hyperx_probe.txt back. Scyrox working means hidapi is fine;
this isolates whether HyperX is missing, open-fails, or reply decode fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hid

from providers.hyperx import (
    PRODUCT_IDS,
    VENDOR_IDS,
    _battery_request,
    _battery_request_dts,
    _decode_battery_reply,
    _is_candidate,
    _name_looks_like_cloud_ii,
)


def _hex(data: list[int], n: int = 20) -> str:
    return " ".join(f"{b:02X}" for b in data[:n])


def main() -> None:
    infos = list(hid.enumerate())
    print(f"total_hid={len(infos)}")

    interesting = []
    for info in infos:
        vid = int(info.get("vendor_id") or 0)
        pid = int(info.get("product_id") or 0)
        product = str(info.get("product_string") or "")
        if vid in VENDOR_IDS or _name_looks_like_cloud_ii(product) or "hyperx" in product.lower():
            interesting.append(info)

    print(f"hyperx_family={len(interesting)}")
    if not interesting:
        print("NO HyperX/Kingston/HP Cloud dongle found.")
        print("Check: 2.4G dongle plugged (not 3.5mm-only Cloud II), headset ON.")
        return

    for info in interesting:
        vid = int(info.get("vendor_id") or 0)
        pid = int(info.get("product_id") or 0)
        page = int(info.get("usage_page") or 0)
        usage = int(info.get("usage") or 0)
        product = info.get("product_string") or ""
        cand = _is_candidate(info)
        in_pid = pid in PRODUCT_IDS
        print(
            f"\n--- VID=0x{vid:04X} PID=0x{pid:04X} "
            f"page=0x{page:04X} usage=0x{usage:04X} "
            f"prod={product!r} candidate={cand} known_pid={in_pid}"
        )
        if not cand:
            print("  skip (not treated as Cloud II Wireless candidate)")
            continue

        path = info.get("path")
        dev = hid.device()
        try:
            dev.open_path(path)
            print("  open: OK")
        except Exception as exc:
            print(f"  open: FAIL {exc}")
            continue

        try:
            try:
                ir = list(dev.get_input_report(6, 62) or [])
                print(f"  get_input_report(6): {_hex(ir)} len={len(ir)}")
            except Exception as exc:
                print(f"  get_input_report(6): err {exc}")

            for label, req in (("legacy", _battery_request()), ("dts", _battery_request_dts())):
                print(f"  TX[{label}] {_hex(req)}")
                try:
                    n = dev.write(req)
                    print(f"  write[{label}] -> {n}")
                except Exception as exc:
                    print(f"  write[{label}] err: {exc}")
                    try:
                        n = dev.send_feature_report([0, *req])
                        print(f"  feature[{label}] -> {n}")
                    except Exception as exc2:
                        print(f"  feature[{label}] err: {exc2}")
                        continue
                for i in range(5):
                    try:
                        data = list(dev.read(255, timeout_ms=400))
                    except TypeError:
                        data = list(dev.read(255) or [])
                    except Exception as exc:
                        print(f"  RX[{label}:{i}] err: {exc}")
                        break
                    if not data:
                        print(f"  RX[{label}:{i}] (empty)")
                        continue
                    pct = _decode_battery_reply(data)
                    print(f"  RX[{label}:{i}] {_hex(data)} len={len(data)} decode={pct}")
                    if pct is not None:
                        print(f"  SUCCESS percent={pct}")
                        break
        finally:
            try:
                dev.close()
            except Exception:
                pass

    print("\ndone")


if __name__ == "__main__":
    main()
