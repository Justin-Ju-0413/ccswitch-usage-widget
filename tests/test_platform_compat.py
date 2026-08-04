from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 显式加载 tkinter.font 子模块：unittest.mock.patch("tkinter.font")
# 只会 import 父模块 tkinter，而 tkinter/__init__.py 不会自动加载 font。
import tkinter.font  # noqa: F401

import platform_compat as pc


class FontSelectionTests(unittest.TestCase):
    def test_macos_candidates_priority(self):
        with patch.object(pc, "SYSTEM", "darwin"):
            self.assertEqual(pc.select_font(available={"Helvetica Neue"}),
                             "Helvetica Neue")
            self.assertEqual(pc.select_font(available={"PingFang SC", "SF Pro Text"}),
                             "PingFang SC")

    def test_windows_uses_segoe_ui(self):
        with patch.object(pc, "SYSTEM", "win32"):
            self.assertEqual(pc.select_font(available={"Segoe UI"}), "Segoe UI")

    def test_linux_candidates(self):
        with patch.object(pc, "SYSTEM", "linux"):
            self.assertEqual(pc.select_font(available={"WenQuanYi Micro Hei"}),
                             "WenQuanYi Micro Hei")

    def test_no_match_returns_none(self):
        self.assertIsNone(pc.select_font(system="darwin", available={"Arial"}))

    def test_no_tk_returns_first_candidate(self):
        with patch.object(pc, "SYSTEM", "darwin"):
            self.assertEqual(pc.select_font(), "PingFang SC")

    def test_unknown_platform_returns_none(self):
        self.assertIsNone(pc.select_font(system="plan9", available=[]))


class PlatformDetectionTests(unittest.TestCase):
    @patch.object(pc, "SYSTEM", "darwin")
    def test_is_macos(self):
        self.assertTrue(pc.is_macos())

    @patch.object(pc, "SYSTEM", "win32")
    def test_is_windows(self):
        self.assertTrue(pc.is_windows())


class ResolveFontTests(unittest.TestCase):
    @patch("platform_compat.select_font")
    def test_resolve_font_queries_tk_families(self, mock_select):
        mock_root = MagicMock()
        with patch("tkinter.font") as mock_tkfont:
            mock_tkfont.families.return_value = ["Arial", "PingFang SC"]
            pc.resolve_font(mock_root)
        mock_tkfont.families.assert_called_once_with(mock_root)
        mock_select.assert_called_once_with(available={"Arial", "PingFang SC"})

    @patch("platform_compat.select_font", return_value=None)
    def test_resolve_font_none_when_no_match(self, _mock_select):
        with patch("tkinter.font") as mock_tkfont:
            mock_tkfont.families.return_value = []
            self.assertIsNone(pc.resolve_font(MagicMock()))


class DbPathTests(unittest.TestCase):
    def test_manual_db_path_takes_priority(self):
        with patch.object(pc, "DEFAULT_CC_SWITCH_DIR", "/nonexistent/default"):
            cfg = {"db_path": "/tmp/manual/cc-switch.db"}
            self.assertEqual(pc.db_candidates(cfg)[0], "/tmp/manual/cc-switch.db")
            self.assertEqual(pc.resolve_db_path(cfg, cc_switch_dir="/nonexistent/default"),
                             "/tmp/manual/cc-switch.db")

    def test_custom_dir_from_cc_switch_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cc_dir = home / ".cc-switch"
            cc_dir.mkdir()
            custom = home / "icloud-sync"
            custom.mkdir()
            (custom / "cc-switch.db").touch()
            (cc_dir / "settings.json").write_text(
                json.dumps({"customConfigDir": str(custom)}), encoding="utf-8")
            result = pc.resolve_db_path({}, cc_switch_dir=str(cc_dir))
            self.assertEqual(result, str(custom / "cc-switch.db"))

    def test_default_path_when_no_override(self):
        with patch.object(pc, "DEFAULT_CC_SWITCH_DIR", "/nonexistent/default"):
            self.assertEqual(pc.resolve_db_path({}, cc_switch_dir="/nonexistent/default"),
                             "/nonexistent/default/cc-switch.db")

    def test_broken_settings_json_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            cc_dir = Path(tmp)
            (cc_dir / "settings.json").write_text("{not json", encoding="utf-8")
            result = pc.resolve_db_path({}, cc_switch_dir=str(cc_dir))
            self.assertEqual(result, str(cc_dir / "cc-switch.db"))

    def test_tilde_in_manual_path_is_expanded(self):
        with patch.object(pc, "DEFAULT_CC_SWITCH_DIR", "/nonexistent/default"):
            result = pc.resolve_db_path({"db_path": "~/my-db/cc-switch.db"},
                                        cc_switch_dir="/nonexistent/default")
            self.assertEqual(result, os.path.join(os.path.expanduser("~"), "my-db/cc-switch.db"))


if __name__ == "__main__":
    unittest.main()
