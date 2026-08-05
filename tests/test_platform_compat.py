from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
                             os.path.join("/nonexistent/default", "cc-switch.db"))

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
            self.assertEqual(result, os.path.expanduser("~/my-db/cc-switch.db"))


class WindowEffectTests(unittest.TestCase):
    @patch.object(pc, "SYSTEM", "linux")
    def test_mac_frost_skipped_on_linux(self):
        self.assertFalse(pc.try_mac_frost(MagicMock()))

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_frost_degrades_when_pyobjc_missing(self):
        with patch("builtins.__import__", side_effect=ImportError("no pyobjc")):
            self.assertFalse(pc.try_mac_frost(MagicMock()))

    @patch.object(pc, "SYSTEM", "linux")
    def test_mac_panel_skipped_on_linux(self):
        self.assertFalse(pc.make_mac_panel(MagicMock()))

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_panel_degrades_when_pyobjc_missing(self):
        with patch("builtins.__import__", side_effect=ImportError("no pyobjc")):
            self.assertFalse(pc.make_mac_panel(MagicMock()))

    @patch.object(pc, "SYSTEM", "win32")
    @patch.object(pc, "try_windows_acrylic", return_value=True)
    def test_apply_effects_uses_acrylic_on_windows(self, mock_acrylic):
        self.assertTrue(pc.apply_window_effects(MagicMock()))
        mock_acrylic.assert_called_once()

    @patch.object(pc, "SYSTEM", "linux")
    @patch.object(pc, "try_windows_acrylic")
    @patch.object(pc, "try_mac_frost")
    def test_apply_effects_false_on_linux(self, mock_frost, mock_acrylic):
        self.assertFalse(pc.apply_window_effects(MagicMock()))
        mock_frost.assert_not_called()
        mock_acrylic.assert_not_called()


def _fake_appkit(window=None, **constants):
    """构造可注入 sys.modules 的 fake AppKit 模块。

    try_mac_frost / make_mac_panel 内部执行 `import AppKit`，会命中
    sys.modules 中已注入的 fake（CI Windows runner 无 pyobjc，不能真 import）。
    """
    defaults = {
        "NSVisualEffectMaterialHUDWindow": 13,
        "NSVisualEffectBlendingModeBehindWindow": 0,
        "NSVisualEffectStateActive": 1,
        "NSViewWidthSizable": 2,
        "NSViewHeightSizable": 16,
        "NSWindowAbove": 1,
        "NSFloatingWindowLevel": 3,
        "NSWindowCollectionBehaviorCanJoinAllSpaces": 1,
    }
    defaults.update(constants)
    app = SimpleNamespace(**defaults)
    app.NSApp = MagicMock(return_value=SimpleNamespace(
        windows=lambda: [window] if window else []))
    app.NSVisualEffectView = MagicMock()
    return app


def _fake_window(title="TokenTicker", visible=True):
    win = MagicMock()
    win.title.return_value = title
    win.isVisible.return_value = visible
    win.contentView.return_value = MagicMock()
    win.collectionBehavior.return_value = 0
    return win


class MacFrostAppKitTests(unittest.TestCase):
    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_frost_adds_effect_view_when_window_found(self):
        win = _fake_window()
        appkit = _fake_appkit(win)
        effect = appkit.NSVisualEffectView.alloc.return_value.initWithFrame_.return_value
        root = MagicMock()
        root.title.return_value = "TokenTicker"
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertTrue(pc.try_mac_frost(root))
        effect.setMaterial_.assert_called_once_with(13)
        effect.setBlendingMode_.assert_called_once_with(0)
        effect.setState_.assert_called_once_with(1)
        effect.setAutoresizingMask_.assert_called_once_with(2 | 16)
        win.contentView().addSubview_positioned_relativeTo_.assert_called_once_with(
            effect, 1, None)

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_frost_false_when_window_not_found(self):
        appkit = _fake_appkit(None)
        root = MagicMock()
        root.title.return_value = "TokenTicker"
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertFalse(pc.try_mac_frost(root))

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_frost_matches_first_visible_when_title_empty(self):
        win = _fake_window(title="other", visible=True)
        appkit = _fake_appkit(win)
        root = MagicMock()
        root.title.return_value = ""
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertTrue(pc.try_mac_frost(root))

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_frost_false_when_no_visible_window_and_title_empty(self):
        win = _fake_window(title="other", visible=False)
        appkit = _fake_appkit(win)
        root = MagicMock()
        root.title.return_value = ""
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertFalse(pc.try_mac_frost(root))

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_frost_false_when_effect_fails(self):
        win = _fake_window()
        appkit = _fake_appkit(win)
        effect = appkit.NSVisualEffectView.alloc.return_value.initWithFrame_.return_value
        effect.setMaterial_.side_effect = Exception("boom")
        root = MagicMock()
        root.title.return_value = "TokenTicker"
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertFalse(pc.try_mac_frost(root))


class MacPanelAppKitTests(unittest.TestCase):
    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_panel_sets_floating_level_and_behavior(self):
        win = _fake_window()
        win.collectionBehavior.return_value = 8
        appkit = _fake_appkit(win)
        root = MagicMock()
        root.title.return_value = "TokenTicker"
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertTrue(pc.make_mac_panel(root))
        win.setLevel_.assert_called_once_with(3)
        win.setCollectionBehavior_.assert_called_once_with(8 | 1)
        win.makeKeyAndOrderFront_.assert_called_once_with(None)

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_panel_false_when_window_not_found(self):
        appkit = _fake_appkit(None)
        root = MagicMock()
        root.title.return_value = "TokenTicker"
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertFalse(pc.make_mac_panel(root))

    @patch.object(pc, "SYSTEM", "darwin")
    def test_mac_panel_false_when_set_level_fails(self):
        win = _fake_window()
        appkit = _fake_appkit(win)
        win.setLevel_.side_effect = Exception("boom")
        root = MagicMock()
        root.title.return_value = "TokenTicker"
        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertFalse(pc.make_mac_panel(root))


if __name__ == "__main__":
    unittest.main()
