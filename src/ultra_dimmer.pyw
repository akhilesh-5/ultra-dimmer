"""Ultra Dimmer - DPI-aware Windows desktop UI and global hotkey controller."""

import atexit
import os
import sys
import threading
import tkinter as tk
from ctypes import wintypes
import ctypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from dimmer_engine import (  # noqa: E402
    MagnificationDimmer,
    configure_win32_environment,
    kernel32,
    user32,
)

configure_win32_environment()

APP_TITLE = "Ultra Dimmer"
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
ICON_PATH = os.path.join(REPO_ROOT, "assets", "ultra_dimmer.ico")

SW_RESTORE = 9
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000
VK_DOWN = 0x28
VK_UP = 0x26
VK_D = 0x44
VK_0 = 0x30


class UltraDimmerApp:
    """Desktop control window paired with DWM Magnification dimming and global hotkeys."""

    def __init__(self) -> None:
        self.dimmer = MagnificationDimmer()
        atexit.register(self.cleanup)

        self.current_brightness = 40
        self.keep_on_top = False
        self.hotkey_thread_id = None
        self.hotkey_ready = threading.Event()
        self.is_closing = False

        self.build_ui()
        self.dimmer.set_brightness(self.current_brightness)

        self.schedule_monitor_check()
        self.hotkey_thread = threading.Thread(target=self.listen_hotkeys, daemon=True)
        self.hotkey_thread.start()

    def build_ui(self) -> None:
        """Build DPI-scaled Tkinter control panel with native Taskbar and Alt+Tab flags."""
        self.root = tk.Tk()
        self.root.title(APP_TITLE)

        try:
            scale = user32.GetDpiForSystem() / 96.0
        except Exception:
            scale = 1.0

        win_w = int(420 * scale)
        win_h = int(320 * scale)
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(win_w, win_h)
        self.root.resizable(False, False)
        self.root.configure(bg="#121318")

        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass

        # Behave like a normal desktop app (visible in Taskbar and Alt+Tab, not forced on top)
        self.root.attributes("-topmost", False)
        self.root.update_idletasks()
        hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style = (ex_style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        user32.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
        )

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Escape>", lambda _e: self.root.iconify())
        self.root.bind("<Up>", lambda _e: self.adjust_step(5))
        self.root.bind("<Right>", lambda _e: self.adjust_step(5))
        self.root.bind("<Down>", lambda _e: self.adjust_step(-5))
        self.root.bind("<Left>", lambda _e: self.adjust_step(-5))

        pad_x = int(20 * scale)
        pad_y = int(14 * scale)

        header = tk.Frame(self.root, bg="#1a1c24", height=int(52 * scale))
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🌙 Ultra Dimmer",
            fg="#e2e8f0",
            bg="#1a1c24",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left", padx=int(16 * scale), pady=int(10 * scale))

        self.val_badge = tk.Label(
            header,
            text=f"{self.current_brightness}%",
            fg="#38bdf8",
            bg="#0f172a",
            font=("Segoe UI", 11, "bold"),
            padx=int(12 * scale),
            pady=int(3 * scale),
            relief="flat",
        )
        self.val_badge.pack(side="right", padx=int(16 * scale))

        body = tk.Frame(self.root, bg="#121318", padx=pad_x, pady=pad_y)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Display Brightness Level (5% Ultra Dark – 100% Normal)",
            fg="#94a3b8",
            bg="#121318",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, int(8 * scale)))

        self.slider = tk.Scale(
            body,
            from_=5,
            to=100,
            orient="horizontal",
            showvalue=False,
            bg="#121318",
            troughcolor="#1e2230",
            activebackground="#38bdf8",
            highlightthickness=0,
            bd=0,
            sliderlength=int(24 * scale),
            width=int(18 * scale),
            sliderrelief="flat",
            command=self.on_slider_moved,
        )
        self.slider.set(self.current_brightness)
        self.slider.pack(fill="x", pady=(0, int(14 * scale)))

        btn_frame = tk.Frame(body, bg="#121318")
        btn_frame.pack(fill="x", pady=(0, int(14 * scale)))

        presets = [
            ("10% Ultra", 10, "#ef4444"),
            ("25% Night", 25, "#f59e0b"),
            ("50% Dim", 50, "#10b981"),
            ("100% Normal", 100, "#38bdf8"),
        ]

        for text, val, color in presets:
            tk.Button(
                btn_frame,
                text=text,
                font=("Segoe UI", 8, "bold"),
                fg="#f8fafc",
                bg="#1e2230",
                activeforeground="#ffffff",
                activebackground=color,
                bd=0,
                padx=int(6 * scale),
                pady=int(6 * scale),
                cursor="hand2",
                command=lambda v=val: self.set_brightness(v),
            ).pack(side="left", expand=True, fill="x", padx=2)

        opt_frame = tk.Frame(body, bg="#121318")
        opt_frame.pack(fill="x", pady=(0, int(14 * scale)))

        self.topmost_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            opt_frame,
            text="Keep window on top",
            variable=self.topmost_var,
            onvalue=True,
            offvalue=False,
            command=self.toggle_topmost,
            bg="#121318",
            fg="#94a3b8",
            activebackground="#121318",
            activeforeground="#e2e8f0",
            selectcolor="#1e2230",
            font=("Segoe UI", 8),
        ).pack(side="left")

        tk.Label(
            opt_frame,
            text="Hotkeys: Ctrl+Alt+Up/Down/D/0",
            fg="#64748b",
            bg="#121318",
            font=("Segoe UI", 8),
        ).pack(side="right")

        footer = tk.Frame(body, bg="#121318")
        footer.pack(fill="x", side="bottom")

        tk.Button(
            footer,
            text="Minimize to Taskbar",
            font=("Segoe UI", 9),
            fg="#e2e8f0",
            bg="#262b3d",
            activebackground="#38bdf8",
            activeforeground="#ffffff",
            bd=0,
            pady=int(7 * scale),
            cursor="hand2",
            command=self.root.iconify,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            footer,
            text="Reset & Exit",
            font=("Segoe UI", 9, "bold"),
            fg="#f87171",
            bg="#262b3d",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            bd=0,
            pady=int(7 * scale),
            padx=int(14 * scale),
            cursor="hand2",
            command=self.on_close,
        ).pack(side="right", padx=(4, 0))

        self.root.update_idletasks()
        final_w = max(win_w, self.root.winfo_reqwidth())
        final_h = max(win_h, self.root.winfo_reqheight() + int(8 * scale))
        self.root.geometry(f"{final_w}x{final_h}")
        self.root.minsize(final_w, final_h)

    def on_slider_moved(self, val: str) -> None:
        pct = self.dimmer.set_brightness(int(float(val)))
        self.current_brightness = pct
        self.val_badge.config(text=f"{pct}%")

    def set_brightness(self, val: int) -> None:
        self.slider.set(val)
        self.on_slider_moved(str(val))

    def adjust_step(self, delta: int) -> None:
        new_val = self.dimmer.clamp_percent(self.slider.get() + delta)
        self.set_brightness(new_val)

    def toggle_topmost(self) -> None:
        self.keep_on_top = self.topmost_var.get()
        self.root.attributes("-topmost", self.keep_on_top)

    def schedule_monitor_check(self) -> None:
        if self.is_closing:
            return
        try:
            self.dimmer.ensure_active()
        except Exception:
            pass
        self.root.after(1500, self.schedule_monitor_check)

    def listen_hotkeys(self) -> None:
        self.hotkey_thread_id = kernel32.GetCurrentThreadId()
        user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT, VK_DOWN)
        user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_ALT, VK_UP)
        user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_D)
        user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_0)
        self.hotkey_ready.set()

        msg = wintypes.MSG()
        while not self.is_closing:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                if hk_id == 1:
                    self.root.after(0, lambda: self.adjust_step(-5))
                elif hk_id == 2:
                    self.root.after(0, lambda: self.adjust_step(5))
                elif hk_id == 3:
                    self.root.after(0, self.toggle_window_visibility)
                elif hk_id == 4:
                    self.root.after(0, lambda: self.set_brightness(100))

        for hk_id in (1, 2, 3, 4):
            user32.UnregisterHotKey(None, hk_id)

    def toggle_window_visibility(self) -> None:
        hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        if user32.IsIconic(hwnd) or not self.root.winfo_viewable():
            self.root.deiconify()
            user32.ShowWindow(hwnd, SW_RESTORE)
            self.root.lift()
            user32.SetForegroundWindow(hwnd)
        else:
            self.root.iconify()

    def cleanup(self) -> None:
        if self.is_closing:
            return
        self.is_closing = True
        if self.hotkey_thread_id:
            try:
                user32.PostThreadMessageW(self.hotkey_thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        try:
            self.dimmer.restore_and_close()
        except Exception:
            pass

    def on_close(self) -> None:
        self.cleanup()
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = UltraDimmerApp()
    app.run()
