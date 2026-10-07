# BatteryTray

Shows device battery levels as Windows tray icons. Each device gets a circular ring, a mouse/headset glyph, and the percent. Hover for the device name and percent; right-click for **Refresh now** or **Quit**. The app rescans every 60 seconds.

**BatteryTray v1.0.1** — created by Marco

## What is supported

- **BLE Battery Service** — devices that expose GATT `0x180F` / Battery Level `0x2A19`
- **Logitech G502 X PLUS** — battery via G Hub WebSocket (`localhost:9010`), then HID++ if needed
- **Scyrox V8** — HID via 2.4G dongle (VID `0x3554`, PIDs `0xF5F7` / `0xF5F4` / `0xF5F6`). Wake the mouse if it is sleeping.
- **Razer Barracuda X 2.4** — **not supported** for battery (Synapse omits it; HID probes can disconnect the headset, so BatteryTray does not open that dongle).
- **HyperX Cloud II Wireless** (Cloud 2) — HID via the 2.4G dongle (Kingston `0951:1718` and HP `03F0:018B` / `0D93` / `0696`). Supports both legacy and HP/DTS packet formats. Wired-only Cloud II has no battery. Power the headset on; if NGENUITY is open and the icon is missing, quit NGENUITY and hit **Refresh now**.
- **Tray visibility (Windows 11)** — the app sets `IsPromoted` so icons prefer the taskbar over the `^` overflow. You can also: drag the icon from `^` onto the taskbar, or **Settings → Personalization → Taskbar → Other system tray icons**.

**Not guaranteed:** only the models above are targeted. Other Logitech/Razer 2.4 GHz or BLE products may not appear.

**Bluetooth off:** 2.4 GHz / G Hub / HID readings are kept; turning Bluetooth off no longer clears those tray icons (BLE-only devices may still be unavailable).

## Setup

```
python -m pip install -r requirements.txt
```

Requires `websockets` (G Hub) and `hid` (HID++ / Razer HID). Both are pinned in `requirements.txt`.

## Run

```
python main.py
```

Start **Logitech G Hub** if you use a G502 X PLUS.

## Tray

- Circular ring + large mouse/headset glyph
- Color: **green** ≥50%, **yellow** 20–49%, **red** <20%
- Starts with Windows (right-click tray → uncheck **Start with Windows** to disable)
- Hover tooltip shows `{name} — {percent}%`
- Right-click: **Refresh now** / **Quit**
- If no devices are found and there is nothing to show from 2.4G providers, a status icon may appear (e.g. Bluetooth unavailable for BLE-only setups)

## Tests

```
python -m pytest -v
```

Automated tests use mocks; no physical dongle required.

## Manual smoke (optional)

1. G Hub running, Razer software as usual, Bluetooth off — run `python main.py`
2. Confirm G502 icon when G Hub reports battery
3. Confirm Scyrox V8 icon with the 2.4G dongle plugged in and the mouse awake
4. Try **Refresh now** and **Quit** (Barracuda audio should stay connected)

## Build exe for friends

On your PC:

```
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Output: `dist\BatteryTray.exe`

Send that one file. Friends do **not** need Python.

Notes:

- Windows SmartScreen may say “Windows protected your PC” → **More info** → **Run anyway** (unsigned app).
- For G502 they should install/run **Logitech G Hub**.
- Tray icon: right-click → **Start with Windows** / **Quit**.
- First launch may take a few seconds while Windows unpacks the one-file exe.
