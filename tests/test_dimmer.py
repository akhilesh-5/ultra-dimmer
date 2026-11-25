"""Unit and Win32 prototype verification tests for Ultra Dimmer."""

import ctypes
import os
import py_compile
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from dimmer_engine import (  # noqa: E402
    MAGCOLOREFFECT,
    MagnificationDimmer,
    kernel32,
    mag,
    user32,
)


class TestDimmerEngine(unittest.TestCase):
    """Validate pure color-matrix math, bounds, ctypes prototypes, and assets."""

    def test_clamp_percent_bounds(self) -> None:
        self.assertEqual(MagnificationDimmer.clamp_percent(-15), 5)
        self.assertEqual(MagnificationDimmer.clamp_percent(0), 5)
        self.assertEqual(MagnificationDimmer.clamp_percent(5), 5)
        self.assertEqual(MagnificationDimmer.clamp_percent(42), 42)
        self.assertEqual(MagnificationDimmer.clamp_percent(100), 100)
        self.assertEqual(MagnificationDimmer.clamp_percent(140), 100)

    def test_build_matrix_diagonal_and_identity(self) -> None:
        for factor in (0.05, 0.25, 0.50, 1.00):
            eff = MagnificationDimmer.build_matrix(factor)
            self.assertIsInstance(eff, MAGCOLOREFFECT)
            vals = list(eff.transform)
            self.assertEqual(len(vals), 25)
            for row in range(5):
                for col in range(5):
                    val = vals[row * 5 + col]
                    if row == col and row < 3:
                        self.assertAlmostEqual(val, factor, places=5)
                    elif row == col:
                        self.assertAlmostEqual(val, 1.0, places=5)
                    else:
                        self.assertAlmostEqual(val, 0.0, places=5)

    def test_ctypes_prototypes_configured(self) -> None:
        self.assertEqual(ctypes.sizeof(MAGCOLOREFFECT), 25 * ctypes.sizeof(ctypes.c_float))
        self.assertIsNotNone(mag.MagSetFullscreenColorEffect.argtypes)
        self.assertIsNotNone(mag.MagGetFullscreenColorEffect.argtypes)
        self.assertIsNotNone(user32.IsIconic.argtypes)
        self.assertIsNotNone(user32.SetWindowPos.argtypes)
        self.assertIsNotNone(kernel32.CreateMutexW.argtypes)

    def test_assets_and_source_compile(self) -> None:
        ico_path = os.path.join(REPO_ROOT, "assets", "ultra_dimmer.ico")
        self.assertTrue(os.path.isfile(ico_path), "Missing assets/ultra_dimmer.ico")
        self.assertGreater(os.path.getsize(ico_path), 1000)

        for rel in (
            os.path.join("src", "dimmer_engine.py"),
            os.path.join("src", "ultra_dimmer.pyw"),
            os.path.join("assets", "generate_icon.py"),
        ):
            py_compile.compile(os.path.join(REPO_ROOT, rel), doraise=True)


if __name__ == "__main__":
    unittest.main()
