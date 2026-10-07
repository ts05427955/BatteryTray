from icon_factory import KIND_COLORS, GREEN, RED, YELLOW, battery_color, make_battery_icon, make_status_icon


def test_battery_icon_size_and_mode():
    img = make_battery_icon(87, "mouse", size=64)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_battery_icon_100_percent():
    img = make_battery_icon(100, "headset", size=64)
    assert img.size == (64, 64)


def test_kind_colors_cover_all_kinds():
    for kind in ("headset", "mouse", "controller", "other"):
        assert kind in KIND_COLORS


def test_status_icon():
    img = make_status_icon("BT", size=64)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_battery_color_green_yellow_red():
    assert battery_color(100) == GREEN
    assert battery_color(50) == GREEN
    assert battery_color(49) == YELLOW
    assert battery_color(20) == YELLOW
    assert battery_color(19) == RED
    assert battery_color(0) == RED


def test_mouse_icon_draws_ring_progress():
    empty = make_battery_icon(0, "mouse", size=64)
    full = make_battery_icon(100, "mouse", size=64)
    mid_x, top_y = 32, 4
    assert sum(full.getpixel((mid_x, top_y))[:3]) > sum(empty.getpixel((mid_x, top_y))[:3])
    assert full.getpixel((mid_x, top_y))[1] > full.getpixel((mid_x, top_y))[0]


def test_mouse_glyph_has_fa_style_body_and_button_slit():
    img = make_battery_icon(90, "mouse", size=128)
    # Body center should be green-filled (mouse silhouette).
    assert img.getpixel((64, 78))[1] > 150
    # Button slit near top-center should stay dark (gap between L/R buttons).
    slit = img.getpixel((64, 48))
    assert slit[1] < 120
