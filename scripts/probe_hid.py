"""Quick HID probe for Barracuda / Logitech."""

from __future__ import annotations

import hid

KEYWORDS = (
    "razer",
    "barracuda",
    "macronix",
    "g502",
    "lightspeed",
    "headset",
    "dongle",
    "2.4",
)


def main() -> None:
    items = list(hid.enumerate())
    print(f"total={len(items)}")
    interesting = []
    for info in items:
        vid = int(info.get("vendor_id") or 0)
        pid = int(info.get("product_id") or 0)
        product = info.get("product_string") or ""
        manuf = info.get("manufacturer_string") or ""
        blob = f"{product} {manuf}".lower()
        if vid in (0x1532, 0x046D) or any(k in blob for k in KEYWORDS):
            interesting.append(info)
    print(f"interesting={len(interesting)}")
    for info in sorted(
        interesting,
        key=lambda i: (i.get("vendor_id") or 0, i.get("product_id") or 0, i.get("usage_page") or 0),
    ):
        vid = int(info.get("vendor_id") or 0)
        pid = int(info.get("product_id") or 0)
        page = int(info.get("usage_page") or 0)
        usage = int(info.get("usage") or 0)
        print(
            f"VID=0x{vid:04X} PID=0x{pid:04X} "
            f"prod={info.get('product_string')!r} manuf={info.get('manufacturer_string')!r} "
            f"page=0x{page:04X} usage=0x{usage:04X}"
        )


if __name__ == "__main__":
    main()
