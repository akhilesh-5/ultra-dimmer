# Ultra Dimmer

Sub-zero display brightness controller for Windows 10/11 (**5% – 100%**).

Hardware laptop brightness sliders typically stop at a manufacturer floor (5%–10% backlight duty cycle) so the LED panel stays readable. In dark rooms, even `0%` Windows brightness can feel glaring. **Ultra Dimmer** lowers perceived screen output smoothly from **100% down to 5%** across every surface on screen—desktop, apps, Taskbar, Start Menu, and `Alt+Tab` switcher—without modifying drivers, firmware, or Windows Night Light.

---

## Architecture & How It Works

### Why Naive Approaches Break on Windows 11
1. **Transparent Overlay Windows (`WS_EX_LAYERED | WS_EX_TRANSPARENT`)**:
   * Windows 11 places the **Taskbar** and **`Alt+Tab` Task Switcher** in higher DWM system Z-order bands (`ZBID_SYSTEM_TOOLS`) than standard `HWND_TOPMOST` windows (`ZBID_DESKTOP`), leaving an un-dimmed bright strip along the taskbar and bright flashes while switching windows.
2. **GDI Hardware Gamma Ramps (`SetDeviceGammaRamp`)**:
   * Modern display drivers clamp gamma gain endpoints at **50%** (rejecting values below 0.50) and reset hardware LUTs whenever the monitor sleeps or locks.

### The Native Solution: Windows DWM Magnification API (`Magnification.dll`)
Ultra Dimmer uses Microsoft’s official `MagSetFullscreenColorEffect` compositor transform:

```text
[ Desktop / Apps / Taskbar / Start Menu / Alt+Tab Switcher ]
                            │
                            ▼
        DWM Compositor Output (Magnification.dll)
     5×5 RGB Scaling Matrix: diag(f, f, f, 1.0, 1.0)
             (f = 1.00 normal  ──►  0.05 ultra dark)
                            │
                            ▼
          GPU LUT / Night Light / ICC Profile Preserved
```

* **Uniform Full-Screen Coverage**: Dims apps, Taskbar, Start Menu, notifications, and `Alt+Tab` seamlessly with zero Z-order seams and zero overlay windows capturing mouse input.
* **True Linear Range (100% → 5%)**: Bypassing the 50% driver clamp gives smooth, distinct steps all the way down to `5%`.
* **Preserves Night Light & Calibration**: Leaves hardware `GetDeviceGammaRamp` tables untouched so Windows Night Light and color profiles stack normally.
* **Self-Healing Across Sleep / Lock Screen**: A lightweight 1.5 s check verifies `MagGetFullscreenColorEffect` and automatically restores the active dim level after monitor power-off, UAC prompts, or `Win+L` unlock.
* **Normal Desktop App Window**: Uses Per-Monitor DPI awareness, a dedicated `AppUserModelID`, and `WS_EX_APPWINDOW` so the control window appears cleanly in the Taskbar and `Alt+Tab` without hanging over other tabs. A Win32 mutex enforces single-instance launches.

---

## Repository Structure

```text
ultra-dimmer/
├── src/
│   ├── dimmer_engine.py     # Win32 Magnification API wrapper, DPI setup, & prototypes
│   └── ultra_dimmer.pyw     # Tkinter UI, global hotkeys, & single-instance mutex
├── assets/
│   ├── generate_icon.py     # Reproducible Pillow multi-size icon generator
│   └── ultra_dimmer.ico     # Custom crescent moon application icon
├── tests/
│   └── test_dimmer.py       # Unit, prototype, icon, and compilation checks
├── install.ps1 / .bat       # Creates Desktop & Start Menu shortcuts (no auto-start)
├── uninstall.ps1 / .bat     # Stops running instance & removes shortcuts cleanly
├── requirements.txt         # Runtime stdlib notes + optional Pillow dev dependency
└── LICENSE                  # MIT License
```

---

## Installation (Windows 10 / 11)

### Prerequisites
* Windows 10 or Windows 11 (x64)
* Python 3.10+ with **Tkinter** (`tcl/tk`, included in standard Python & Microsoft Store Python 3.11)

### Quick Install
1. Clone the repository:
   ```powershell
   git clone https://github.com/akhilesh-5/ultra-dimmer.git
   cd ultra-dimmer
   ```
2. Run the one-click installer (**Double-click `install.bat`** or run in PowerShell):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install.ps1
   ```
   This creates shortcuts on your **Desktop** and in the **Start Menu** (`Ultra Dimmer`).
   *Note: Ultra Dimmer does **not** add itself to Windows Startup—it runs only when you launch it.*

### Run Directly Without Shortcuts
```powershell
pythonw src\ultra_dimmer.pyw
```

### Uninstall
Double-click `uninstall.bat` or run:
```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```
This stops any active instance (restoring 100% display brightness) and deletes all shortcuts.

---

## Controls & Global Hotkeys

* **Launch Default**: Opens at **100% brightness** so you can reduce it explicitly to your preference.
* **Quick Presets**: `10% Ultra` · `25% Night` · `50% Dim` · `100% Normal`
* **Global Hotkeys** (work from any window or minimized state):

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + Alt + Down` | Decrease brightness by `5%` |
| `Ctrl + Alt + Up` | Increase brightness by `5%` |
| `Ctrl + Alt + D` | Toggle window visibility (Show / Minimize) |
| `Ctrl + Alt + 0` | Reset brightness immediately to `100%` |
| `Esc` *(focused)* | Minimize control window to Taskbar |

---

## Safety, Eye Health & Resource Usage

* **Hardware & OS Safe**: Uses documented Microsoft Accessibility APIs (`Magnification.dll`). Does not flash firmware, modify BIOS/ACPI backlight registers, alter registry keys, or block native `Fn` brightness keys. Closing the app automatically resets the transform to `1.0`.
* **Eye Health**: Matching display brightness to dark-room ambient lighting reduces pupil strain without introducing hardware PWM strobing flicker.
* **Lightweight**: Event-driven global hotkeys (`GetMessageW`) use **0.0% idle CPU** and ~**45 MB RAM**.

---

## Running Tests

```powershell
python -m unittest discover -s tests -v
```
