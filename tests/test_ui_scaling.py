"""Tests for the renderer's virtual-resolution viewport calculations."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import pygame


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import WINDOW_HEIGHT, WINDOW_WIDTH
from ui import Renderer


class ViewportTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.renderer = Renderer.__new__(Renderer)

    def tearDown(self) -> None:
        pygame.quit()

    def test_logical_size_fills_original_window(self) -> None:
        self.renderer._update_viewport((WINDOW_WIDTH, WINDOW_HEIGHT))

        self.assertEqual(self.renderer.scale, 1)
        self.assertEqual(self.renderer.viewport.size, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.assertEqual(self.renderer.viewport.topleft, (0, 0))

    def test_widescreen_window_is_uniformly_scaled_and_centered(self) -> None:
        self.renderer._update_viewport((1920, 1080))

        self.assertAlmostEqual(self.renderer.scale, 1080 / WINDOW_HEIGHT)
        self.assertEqual(self.renderer.viewport.size, (1015, 1080))
        self.assertEqual(self.renderer.viewport.topleft, (452, 0))

    def test_small_window_dimensions_are_safe(self) -> None:
        self.renderer._update_viewport((0, -10))

        self.assertEqual(self.renderer.window_size, (1, 1))
        self.assertEqual(self.renderer.viewport.size, (1, 1))
        self.assertEqual(self.renderer.viewport.topleft, (0, 0))

    def test_mouse_conversion_rejects_letterbox_and_maps_viewport(self) -> None:
        self.renderer._update_viewport((1920, 1080))

        self.assertIsNone(self.renderer.to_logical_pos((100, 100)))
        self.assertEqual(self.renderer.to_logical_pos(self.renderer.viewport.topleft), (0, 0))

        center = self.renderer.viewport.center
        logical_center = self.renderer.to_logical_pos(center)
        self.assertIsNotNone(logical_center)
        self.assertLessEqual(abs(logical_center[0] - WINDOW_WIDTH // 2), 1)
        self.assertLessEqual(abs(logical_center[1] - WINDOW_HEIGHT // 2), 1)


if __name__ == "__main__":
    unittest.main()
