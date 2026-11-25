"""Windows DWM Magnification API engine for compositor-level display dimming."""

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
mag = ctypes.windll.Magnification


class MAGCOLOREFFECT(ctypes.Structure):
    """Win32 5x5 RGBA + translation transformation matrix for Magnification API."""

    _fields_ = [("transform", ctypes.c_float * 25)]


def configure_win32_environment(app_user_model_id: str = "UltraDimmer.App.1") -> None:
    """Enable Per-Monitor DPI awareness and assign a dedicated Taskbar identity."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_user_model_id)
    except Exception:
        pass


def setup_prototypes() -> None:
    """Declare explicit 64-bit safe argtypes/restype for all Win32/Magnification calls."""
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND

    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL

    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    user32.GetDpiForSystem.argtypes = []
    user32.GetDpiForSystem.restype = wintypes.UINT

    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND

    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long

    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long

    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL

    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wintypes.BOOL

    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.GetMessageW.restype = ctypes.c_int

    user32.PostThreadMessageW.argtypes = [
        wintypes.DWORD,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.PostThreadMessageW.restype = wintypes.BOOL

    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL

    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL

    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE

    kernel32.GetCurrentThreadId.argtypes = []
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    mag.MagInitialize.argtypes = []
    mag.MagInitialize.restype = wintypes.BOOL

    mag.MagUninitialize.argtypes = []
    mag.MagUninitialize.restype = wintypes.BOOL

    mag.MagSetFullscreenColorEffect.argtypes = [ctypes.POINTER(MAGCOLOREFFECT)]
    mag.MagSetFullscreenColorEffect.restype = wintypes.BOOL

    mag.MagGetFullscreenColorEffect.argtypes = [ctypes.POINTER(MAGCOLOREFFECT)]
    mag.MagGetFullscreenColorEffect.restype = wintypes.BOOL


setup_prototypes()


class MagnificationDimmer:
    """Apply smooth 5%-100% display dimming across all UI layers via DWM Magnification.

    Unlike layered overlay windows (which sit below Windows 11's Taskbar and Alt+Tab bands)
    or GDI gamma ramps (which drivers clamp below 50% and reset on monitor sleep),
    MagSetFullscreenColorEffect scales RGB output post-composition across every screen region
    without affecting GPU gamma ramps or Night Light profiles.
    """

    MIN_PERCENT = 5
    MAX_PERCENT = 100

    def __init__(self) -> None:
        self.initialized = bool(mag.MagInitialize())
        self.current_factor = 1.0

    @classmethod
    def clamp_percent(cls, percent: int) -> int:
        """Clamp target brightness percentage within safe visible bounds [5, 100]."""
        return max(cls.MIN_PERCENT, min(cls.MAX_PERCENT, int(percent)))

    @staticmethod
    def build_matrix(factor: float) -> MAGCOLOREFFECT:
        """Construct a 5x5 color matrix scaling RGB channels linearly by factor."""
        eff = MAGCOLOREFFECT()
        vals = [
            factor, 0.0, 0.0, 0.0, 0.0,
            0.0, factor, 0.0, 0.0, 0.0,
            0.0, 0.0, factor, 0.0, 0.0,
            0.0, 0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 1.0,
        ]
        for idx, value in enumerate(vals):
            eff.transform[idx] = value
        return eff

    def _apply_factor(self, factor: float) -> bool:
        """Send target transform to Magnification API, reinitializing once on session reset."""
        if not self.initialized:
            self.initialized = bool(mag.MagInitialize())
        if not self.initialized:
            return False

        eff = self.build_matrix(factor)
        if mag.MagSetFullscreenColorEffect(ctypes.byref(eff)):
            return True

        # Re-initialize once if desktop transitions (e.g., Lock Screen or UAC) reset session
        mag.MagUninitialize()
        self.initialized = bool(mag.MagInitialize())
        if not self.initialized:
            return False
        return bool(mag.MagSetFullscreenColorEffect(ctypes.byref(eff)))

    def set_brightness(self, percent: int) -> int:
        """Set display brightness scale from 5% (0.05) to 100% (1.00) and return clamped value."""
        clamped = self.clamp_percent(percent)
        self.current_factor = clamped / 100.0
        self._apply_factor(self.current_factor)
        return clamped

    def ensure_active(self) -> None:
        """Verify DWM still holds our target transform and re-apply if reset after sleep/UAC."""
        if not self.initialized:
            self._apply_factor(self.current_factor)
            return

        cur = MAGCOLOREFFECT()
        ok = mag.MagGetFullscreenColorEffect(ctypes.byref(cur))
        if not ok or abs(cur.transform[0] - self.current_factor) > 0.01:
            self._apply_factor(self.current_factor)

    def restore_and_close(self) -> None:
        """Reset display transform back to identity (1.0) and release Magnification session."""
        if self.initialized:
            eff = self.build_matrix(1.0)
            mag.MagSetFullscreenColorEffect(ctypes.byref(eff))
            mag.MagUninitialize()
            self.initialized = False
