from __future__ import annotations

from PIL import Image, ImageDraw

from models import DeviceKind

# Kept for kind coverage tests / future tints. Ring color is battery-level only.
KIND_COLORS: dict[DeviceKind, tuple[int, int, int]] = {
    "headset": (80, 200, 90),
    "mouse": (80, 200, 90),
    "controller": (80, 200, 90),
    "other": (80, 200, 90),
}

GREEN = (50, 205, 80, 255)
YELLOW = (240, 190, 40, 255)
RED = (230, 60, 55, 255)
TRACK = (70, 74, 80, 255)
GLYPH_BG = (22, 24, 28, 255)

# Font Awesome Free computer-mouse (v7), viewBox 0 0 640 640.
# https://fontawesome.com/license/free
_FA_MOUSE_VB = 640


def battery_color(percent: int) -> tuple[int, int, int, int]:
    if percent >= 50:
        return GREEN
    if percent >= 20:
        return YELLOW
    return RED


def _draw_ring(draw: ImageDraw.ImageDraw, size: int, percent: int, color: tuple[int, int, int, int]) -> None:
    pad = 1
    bbox = (pad, pad, size - pad - 1, size - pad - 1)
    width = max(4, size // 6)
    draw.ellipse(bbox, fill=GLYPH_BG)
    draw.arc(bbox, 0, 360, fill=TRACK, width=width)
    if percent <= 0:
        return
    end = -90 + 360 * min(percent, 100) / 100
    draw.arc(bbox, -90, end, fill=color, width=width)


def _fa_mouse_mask(pixel_size: int) -> Image.Image:
    """Rasterize the FA mouse path into an alpha mask."""
    vb = _FA_MOUSE_VB
    hi = 256
    mask = Image.new("L", (hi, hi), 0)
    d = ImageDraw.Draw(mask)
    s = hi / vb

    def box(x0: float, y0: float, x1: float, y1: float) -> tuple[float, float, float, float]:
        return (x0 * s, y0 * s, x1 * s, y1 * s)

    # Outer body from SVG path (rounded rect ~ radius 88).
    d.rounded_rectangle(box(128, 64, 512, 576), radius=88 * s, fill=255)
    # Center slit between left/right buttons (SVG leaves 304..336 empty).
    d.rectangle(box(304, 96, 336, 288), fill=0)
    if pixel_size == hi:
        return mask
    return mask.resize((pixel_size, pixel_size), Image.Resampling.LANCZOS)


def _paste_colored_mask(
    image: Image.Image,
    mask: Image.Image,
    fill: tuple[int, int, int, int],
    box: tuple[int, int],
) -> None:
    layer = Image.new("RGBA", mask.size, fill)
    image.paste(layer, box, mask)


def _draw_mouse(image: Image.Image, size: int, fill: tuple[int, int, int, int]) -> None:
    # Fill most of the ring interior so the FA mouse stays readable at tray scale.
    glyph = int(size * 0.72)
    mask = _fa_mouse_mask(glyph)
    x = (size - glyph) // 2
    y = (size - glyph) // 2
    _paste_colored_mask(image, mask, fill, (x, y))


def _draw_headset(draw: ImageDraw.ImageDraw, size: int, fill: tuple[int, int, int, int]) -> None:
    cx, cy = size / 2, size / 2 + size * 0.02
    width = max(4, size // 8)
    band = (cx - size * 0.34, cy - size * 0.38, cx + size * 0.34, cy + size * 0.22)
    draw.arc(band, 200, 340, fill=fill, width=width)
    cup_w, cup_h = size * 0.20, size * 0.30
    for dx in (-size * 0.28, size * 0.28):
        draw.rounded_rectangle(
            (cx + dx - cup_w / 2, cy - cup_h * 0.10, cx + dx + cup_w / 2, cy + cup_h * 0.70),
            radius=size * 0.06,
            fill=fill,
        )


def _draw_controller(draw: ImageDraw.ImageDraw, size: int, fill: tuple[int, int, int, int]) -> None:
    cx, cy = size / 2, size / 2
    draw.rounded_rectangle(
        (cx - size * 0.36, cy - size * 0.16, cx + size * 0.36, cy + size * 0.20),
        radius=size * 0.12,
        fill=fill,
    )
    r = size * 0.07
    draw.ellipse((cx - size * 0.18 - r, cy - r, cx - size * 0.18 + r, cy + r), fill=GLYPH_BG)
    draw.ellipse((cx + size * 0.18 - r, cy - r, cx + size * 0.18 + r, cy + r), fill=GLYPH_BG)


def _draw_kind_glyph(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    kind: DeviceKind,
    size: int,
    fill: tuple[int, int, int, int],
) -> None:
    if kind == "headset":
        _draw_headset(draw, size, fill)
    elif kind == "controller":
        _draw_controller(draw, size, fill)
    else:
        _draw_mouse(image, size, fill)


def make_battery_icon(percent: int, kind: DeviceKind, size: int = 128) -> Image.Image:
    percent = max(0, min(100, int(percent)))
    color = battery_color(percent)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    _draw_ring(draw, size, percent, color)
    _draw_kind_glyph(image, draw, kind, size, color)
    return image


def make_status_icon(label: str = "BT", size: int = 128) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    _draw_ring(draw, size, 0, GREEN)
    cx, cy, r = size / 2, size / 2, size * 0.14
    draw.ellipse((cx - r, cy - r * 1.5, cx + r, cy - r * 0.1), fill=(220, 220, 225, 255))
    draw.rectangle((cx - r * 0.38, cy, cx + r * 0.38, cy + r * 1.5), fill=(220, 220, 225, 255))
    return image
