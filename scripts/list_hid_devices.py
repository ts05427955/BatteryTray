"""Print VID/PID/product for connected HID devices (Barracuda / LIGHTSPEED discovery)."""

from __future__ import annotations

try:
    import hid
except ImportError:
    print("hid is not installed; pip install hid")
    raise SystemExit(1)


def main() -> None:
    for info in hid.enumerate():
        vid = int(info.get("vendor_id") or 0)
        pid = int(info.get("product_id") or 0)
        product = info.get("product_string") or ""
        page = int(info.get("usage_page") or 0)
        usage = int(info.get("usage") or 0)
        print(
            f"VID=0x{vid:04X} PID=0x{pid:04X} product={product!r} "
            f"usage_page=0x{page:04X} usage=0x{usage:04X}"
        )


if __name__ == "__main__":
    main()
