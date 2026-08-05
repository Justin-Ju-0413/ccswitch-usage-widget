# TokenTicker macOS 跨平台适配 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 TokenTicker 在 macOS 上「装上就能用」（字体/毛玻璃/窗口交互/DB 路径/自启动/打包），Windows 行为保持不变。

**Architecture:** 新增 `platform_compat.py` 适配层集中平台差异（字体、窗口特效、NSPanel、DB 探测），`ccswitch_widget.py` 仅通过适配层调用平台能力；macOS 自启动/打包用独立 shell 脚本；CI 增加 macOS 作业。

**Tech Stack:** Python 3.8+ / Tkinter / customtkinter / 可选 pyobjc-framework-Cocoa / PyInstaller / GitHub Actions

**Spec:** `docs/superpowers/specs/2026-08-05-macos-cross-platform-design.md`

## Global Constraints

- Python 3.8 兼容（不用 walrus、match、dict union、f-string 调试符）
- 测试框架：unittest（`python -m unittest discover -s tests -v`），不用 pytest
- Windows 路径行为不得改变（`setup_autostart.ps1`、`publish.ps1`、`try_acrylic` 语义）
- pyobjc 是可选依赖：所有 pyobjc/Cocoa 代码必须 try-import，失败静默降级返回 False
- 平台判定统一用 `sys.platform`（'darwin' / 'win32' / 'linux'），便于单测 patch
- 新增/修改文件的 Python 代码必须过 `py_compile`
- 所有提交 push 到 `feat/macos-cross-platform` 分支（main 受保护）

---

### Task 1: platform_compat 骨架 + 字体选择

**Files:**
- Create: `platform_compat.py`
- Test: `tests/test_platform_compat.py`

**Interfaces:**
- Produces: `SYSTEM`（str，=sys.platform）、`is_macos()`、`is_windows()`、`FONT_CANDIDATES`（dict）、`select_font(system=None, available=None) -> str|None`、`resolve_font(root) -> str|None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_platform_compat.py`:

```python
from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_platform_compat -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'platform_compat'`

- [ ] **Step 3: Write minimal implementation**

Create `platform_compat.py`:

```python
#!/usr/bin/env python3
"""TokenTicker 平台适配层：字体 / 窗口特效 / DB 路径探测 / macOS 窗口行为。"""
import json
import os
import sys

SYSTEM = sys.platform

FONT_CANDIDATES = {
    "darwin": ["PingFang SC", "SF Pro Text", "Helvetica Neue"],
    "win32": ["Segoe UI"],
    "linux": ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans"],
}

DEFAULT_CC_SWITCH_DIR = os.path.expanduser("~/.cc-switch")


def is_macos():
    return SYSTEM == "darwin"


def is_windows():
    return SYSTEM == "win32"


def select_font(system=None, available=None):
    """返回候选字体列表中第一个可用者；available 为空表示无 Tk 环境。

    返回 None 表示没有可用候选（调用方应保留默认字体）。
    """
    candidates = FONT_CANDIDATES.get(system or SYSTEM, [])
    if available is not None:
        avail = set(available or [])
        for name in candidates:
            if name in avail:
                return name
        return None
    return candidates[0] if candidates else None


def resolve_font(root):
    """在有 Tk root 时用 tkfont.families() 探测字体。"""
    import tkinter.font as tkfont
    return select_font(available=tkfont.families(root))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_platform_compat -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add platform_compat.py tests/test_platform_compat.py
git commit -m "feat: add platform compat layer with font selection"
git push origin feat/macos-cross-platform
```

---

### Task 2: DB 路径探测

**Files:**
- Create: `platform_compat.py` (append)
- Test: `tests/test_platform_compat.py` (append)

**Interfaces:**
- Consumes: `DEFAULT_CC_SWITCH_DIR`
- Produces: `db_candidates(cfg, cc_switch_dir=DEFAULT_CC_SWITCH_DIR) -> list[str]`、`resolve_db_path(cfg, cc_switch_dir=DEFAULT_CC_SWITCH_DIR) -> str`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_platform_compat.py`:

```python
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
```

Add imports at top of the test file (merge with existing import block):

```python
import json
import os
import tempfile
from pathlib import Path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_platform_compat -v`
Expected: FAIL with `AttributeError: module 'platform_compat' has no attribute 'db_candidates'`

- [ ] **Step 3: Write minimal implementation**

Append to `platform_compat.py`:

```python
def _read_cc_switch_custom_dir(cc_switch_dir):
    """从 CC Switch 的 settings.json 读取自定义配置目录；解析失败返回 None。"""
    try:
        with open(os.path.join(cc_switch_dir, "settings.json"), encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    for key in ("customConfigDir", "config_dir", "custom_config_dir", "configDirectory"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return os.path.expanduser(value)
    return None


def db_candidates(cfg, cc_switch_dir=DEFAULT_CC_SWITCH_DIR):
    """返回有序的数据库候选路径（用于探测与报错展示）。"""
    candidates = []
    manual = (cfg.get("db_path") or "").strip()
    if manual:
        candidates.append(os.path.expanduser(manual))
    custom = _read_cc_switch_custom_dir(cc_switch_dir)
    if custom:
        candidates.append(os.path.join(custom, "cc-switch.db"))
    candidates.append(os.path.join(cc_switch_dir, "cc-switch.db"))
    return candidates


def resolve_db_path(cfg, cc_switch_dir=DEFAULT_CC_SWITCH_DIR):
    """按优先级返回第一个存在的数据库文件，否则返回默认路径。"""
    candidates = db_candidates(cfg, cc_switch_dir)
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[-1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_platform_compat -v`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add platform_compat.py tests/test_platform_compat.py
git commit -m "feat: resolve cc-switch db path across platforms"
git push origin feat/macos-cross-platform
```

---

### Task 3: 主文件接入字体 / DB / 设置窗口路径输入

**Files:**
- Modify: `ccswitch_widget.py`
- Test: `tests/test_widget.py` (append)
- Test: `tests/test_platform_compat.py` (no change)

**Interfaces:**
- Consumes: `pc.select_font`, `pc.resolve_font`, `pc.resolve_db_path`, `pc.db_candidates`
- Produces: `widget.resolve_runtime(root, cfg) -> str`（更新模块级 `DB` 与 `F`，返回 DB 路径）；设置窗口新增 `db_path` 字段

- [ ] **Step 1: Write the failing test**

Append to `tests/test_widget.py`:

```python
class RuntimeResolutionTests(unittest.TestCase):
    def test_resolve_runtime_updates_db_and_font(self):
        with patch.object(widget.pc, "resolve_db_path", return_value="/tmp/x/cc-switch.db"), \
             patch.object(widget.pc, "resolve_font", return_value="PingFang SC"):
            widget.resolve_runtime(MagicMock(), {"db_path": "/tmp/x/cc-switch.db"})
        self.assertEqual(widget.DB, "/tmp/x/cc-switch.db")
        self.assertEqual(widget.F, "PingFang SC")

    def test_resolve_runtime_keeps_default_font_when_unresolvable(self):
        with patch.object(widget.pc, "resolve_db_path", return_value="/tmp/y/cc-switch.db"), \
             patch.object(widget.pc, "resolve_font", return_value=None):
            widget.resolve_runtime(MagicMock(), {})
        self.assertEqual(widget.F, "Segoe UI")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widget -v`
Expected: FAIL with `AttributeError: module 'ccswitch_widget' has no attribute 'resolve_runtime'`

- [ ] **Step 3: Write minimal implementation**

In `ccswitch_widget.py`:

Add import (top, after existing imports):

```python
import platform_compat as pc
```

Keep the module-level `DB = os.path.expanduser("~/.cc-switch/cc-switch.db")` line 11 **unchanged** — `load_config()` is defined later in the file, so calling it at module level would raise NameError. The resolved path is applied at runtime via `resolve_runtime` (called from `main()` in Task 5 and `apply_config` below). Tests that `patch.object(widget, "DB", ...)` keep working unchanged.

Add after `save_config`:

```python
def resolve_runtime(root, cfg):
    """将模块级 DB/F 更新为当前平台与配置的解析结果；返回 DB 路径。"""
    global DB, F
    DB = pc.resolve_db_path(cfg)
    font = pc.resolve_font(root)
    if font:
        F = font
    return DB
```

Add `db_path` field to `SettingsWindow.__init__` — insert after the `c4` card block (after line 316), before the save button:

```python
        c5 = card(win)
        ctk.CTkLabel(c5, text="数据库路径", fg_color="transparent", text_color=t["text"], font=(F, 13)).pack(side="left", padx=16, pady=14)
        self.db_var = tk.StringVar(value=cfg.get("db_path", ""))
        db_row = ctk.CTkFrame(c5, fg_color="transparent")
        db_row.pack(side="right", padx=16, pady=10)
        ctk.CTkEntry(db_row, textvariable=self.db_var, fg_color=t["card2"], text_color=t["text"],
                     border_color=t["border"], width=200, height=30, font=(F, 12)).pack(side="left")
        ctk.CTkButton(db_row, text="浏览…", command=self._pick_db, fg_color=t["card2"],
                      text_color=t["text"], hover_color=t["border"], font=(F, 12),
                      width=70, height=30).pack(side="left", padx=(6, 0))

    def _pick_db(self):
        from tkinter import filedialog
        picked = filedialog.askopenfilename(parent=self.win, title="选择 cc-switch.db",
                                            filetypes=[("SQLite", "*.db"), ("All files", "*")])
        if picked:
            self.db_var.set(picked)
```

In `SettingsWindow.save` (line 321-328), add before `save_config(self.cfg)`:

```python
        self.cfg["db_path"] = self.db_var.get().strip() or None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_widget tests.test_platform_compat -v`
Expected: PASS (19 tests)

- [ ] **Step 5: Verify Windows legacy behavior is untouched**

Run: `python3 -m py_compile ccswitch_widget.py platform_compat.py`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add ccswitch_widget.py tests/test_widget.py
git commit -m "feat: wire platform compat into main app (font, db path, settings)"
git push origin feat/macos-cross-platform
```

---

### Task 4: macOS 毛玻璃 + NSPanel 窗口交互

**Files:**
- Modify: `platform_compat.py` (append)
- Test: `tests/test_platform_compat.py` (append)

**Interfaces:**
- Consumes: `is_macos()`
- Produces: `try_mac_frost(root) -> bool`、`try_windows_acrylic(root) -> bool`（自 ccswitch_widget 迁入，逻辑不变）、`make_mac_panel(root, title=None) -> bool`、`apply_window_effects(root) -> bool`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_platform_compat.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_platform_compat -v`
Expected: FAIL with `AttributeError: module 'platform_compat' has no attribute 'try_mac_frost'`

- [ ] **Step 3: Write minimal implementation**

Append to `platform_compat.py`:

```python
def try_windows_acrylic(root):
    """Windows DWM Acrylic（原 ccswitch_widget.try_acrylic 迁入，行为不变）。"""
    try:
        import ctypes
        from ctypes import windll, byref, c_int, sizeof
        root.update_idletasks()
        hwnd = windll.user32.GetParent(root.winfo_id())
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), sizeof(c_int))
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, byref(c_int(1)), sizeof(c_int))

        class MARGINS(ctypes.Structure):
            _fields_ = [("cxLeftWidth", c_int), ("cxRightWidth", c_int),
                        ("cyTopHeight", c_int), ("cyBottomHeight", c_int)]
        windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(MARGINS(-1, -1, -1, -1)))
        return True
    except Exception:
        return False


def try_mac_frost(root):
    """macOS 毛玻璃（NSVisualEffectView，可选 pyobjc）；失败静默返回 False。"""
    if not is_macos():
        return False
    try:
        from ctypes import c_void_p
        import objc
        from Cocoa import (NSVisualEffectView, NSVisualEffectMaterialHudWindow,
                           NSVisualEffectBlendingModeBehindWindow,
                           NSVisualEffectStateActive, NSViewWidthSizable,
                           NSViewHeightSizable)
    except Exception:
        return False
    try:
        ns_view = objc.objc_object(c_void_p=root.winfo_id())
        effect = NSVisualEffectView.alloc().initWithFrame_(ns_view.bounds())
        effect.setMaterial_(NSVisualEffectMaterialHudWindow)
        effect.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect.setState_(NSVisualEffectStateActive)
        effect.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        ns_view.addSubview_positioned_relativeTo_(effect, objc.NSWindowAbove, None)
        return True
    except Exception:
        return False


def make_mac_panel(root, title=None):
    """将 macOS 无边框窗口提升为可交互的浮动 NSPanel；失败返回 False。"""
    if not is_macos():
        return False
    try:
        import objc
        from ctypes import c_void_p
        from Cocoa import (NSApp, NSFloatingWindowLevel,
                           NSWindowCollectionBehaviorCanJoinAllSpaces)
    except Exception:
        return False
    try:
        win_id = root.winfo_id()
        target = None
        for window in NSApp().windows():
            if window.contentView() is not None and \
               int(window.contentView().self()) == int(win_id):
                target = window
                break
        if target is None:
            return False
        target.setLevel_(NSFloatingWindowLevel)
        target.setCollectionBehavior_(target.collectionBehavior() |
                                      NSWindowCollectionBehaviorCanJoinAllSpaces)
        target.makeKeyAndOrderFront_(None)
        return True
    except Exception:
        return False


def apply_window_effects(root):
    """系统级窗口特效入口：macOS 毛玻璃 → Windows Acrylic → False（降级 alpha）。"""
    if is_macos():
        return try_mac_frost(root)
    if is_windows():
        return try_windows_acrylic(root)
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_platform_compat -v`
Expected: PASS (23 tests)

- [ ] **Step 5: Commit**

```bash
git add platform_compat.py tests/test_platform_compat.py
git commit -m "feat: add mac frosted glass and borderless panel window behavior"
git push origin feat/macos-cross-platform
```

---

### Task 5: 主文件窗口初始化接入 macOS 行为

**Files:**
- Modify: `ccswitch_widget.py`
- Test: `tests/test_widget.py` (append)

**Interfaces:**
- Consumes: `pc.is_macos()`, `pc.is_windows()`, `pc.make_mac_panel(root)`, `pc.apply_window_effects(root)`, `pc.db_candidates(cfg)`
- Produces: `widget.apply_window_flags(root, effects, cfg, is_win=pc.is_windows())`（纯决策函数，可单测）

- [ ] **Step 1: Write the failing test**

Append to `tests/test_widget.py`:

```python
class WindowFlagTests(unittest.TestCase):
    def setUp(self):
        self.root = MagicMock()

    def test_effects_on_windows_sets_transparentcolor(self):
        widget.apply_window_flags(self.root, True, {}, is_win=True)
        self.root.configure.assert_called_with(fg_color=widget.TRANSP)
        self.root.wm_attributes.assert_called_with("-transparentcolor", widget.TRANSP)

    def test_effects_on_macos_skips_transparentcolor(self):
        widget.apply_window_flags(self.root, True, {}, is_win=False)
        self.root.wm_attributes.assert_not_called()

    def test_no_effects_sets_alpha_and_window_bg(self):
        widget.apply_window_flags(self.root, False, {"alpha": 0.7, "theme": "Mocha"}, is_win=False)
        self.root.wm_attributes.assert_called_with("-alpha", 0.7)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widget -v`
Expected: FAIL with `AttributeError: module 'ccswitch_widget' has no attribute 'apply_window_flags'`

- [ ] **Step 3: Write minimal implementation**

In `ccswitch_widget.py`:

1. Delete the `try_acrylic` function (lines 331-344) — logic moved to `pc.try_windows_acrylic` in Task 4.

2. Add `apply_window_flags` after `_lbl`:

```python
def apply_window_flags(root, effects, cfg, is_win=pc.is_windows()):
    """按特效启用状态设置窗口透明相关属性。effects=True 表示毛玻璃/亚克力已启用。"""
    theme = THEMES[cfg["theme"]]
    if effects:
        root.configure(fg_color=TRANSP)
        if is_win:
            root.wm_attributes("-transparentcolor", TRANSP)
    else:
        root.wm_attributes("-alpha", cfg["alpha"])
        root.configure(fg_color=theme["win"])
```

3. Rework `App.__init__` window setup block (lines 354-362) from:

```python
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        self.acrylic = try_acrylic(root)
        if self.acrylic:
            root.configure(fg_color=TRANSP)
            root.wm_attributes("-transparentcolor", TRANSP)
        else:
            root.wm_attributes("-alpha", cfg["alpha"])
            root.configure(fg_color=self.theme["win"])
```

to:

```python
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        if pc.is_macos():
            pc.make_mac_panel(root)
        self.acrylic = pc.apply_window_effects(root)
        apply_window_flags(root, self.acrylic, cfg)
```

4. In `App.apply_config` (line 455), the window background reset in `_build_ui` uses `TRANSP if self.acrylic else t["win"]` — no change needed. But `apply_config` must re-resolve the DB path after settings change. Add at the top of `apply_config`, before `self._build_ui()`:

```python
        resolve_runtime(self.root, new_cfg)
```

5. Rework `main()` (lines 504-511) to set title, resolve runtime, and give better error:

```python
def main():
    cfg = load_config()
    root = ctk.CTk()
    root.title("TokenTicker")
    if pc.is_macos():
        pc.make_mac_panel(root)
    resolve_runtime(root, cfg)
    if not os.path.exists(DB):
        searched = "\n".join(pc.db_candidates(cfg))
        print(f"找不到 cc-switch.db: {DB}\n已探测以下位置:\n{searched}\n"
              "请先安装并运行 CC Switch(https://github.com/farion1231/cc-switch)。",
              file=sys.stderr)
        sys.exit(1)
    App(root, cfg)
    root.mainloop()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_widget tests.test_platform_compat -v`
Expected: PASS (28 tests)

- [ ] **Step 5: Verify syntax**

Run: `python3 -m py_compile ccswitch_widget.py platform_compat.py`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add ccswitch_widget.py tests/test_widget.py
git commit -m "feat: apply mac window behavior in app initialization"
git push origin feat/macos-cross-platform
```

---

### Task 6: macOS 开机自启脚本

**Files:**
- Create: `setup_autostart.sh`
- Modify: `.gitignore` (no change needed — verify `*.db` already covers db)

**Interfaces:**
- Produces: shell script with `setup_autostart.sh`（默认安装）和 `setup_autostart.sh --uninstall`（卸载）

- [ ] **Step 1: Write the script**

Create `setup_autostart.sh`:

```bash
#!/usr/bin/env bash
# TokenTicker macOS 开机自启（LaunchAgent）。用法:
#   ./setup_autostart.sh          # 安装
#   ./setup_autostart.sh --uninstall  # 卸载
set -euo pipefail

LABEL="com.tokenticker.widget"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$LABEL.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--uninstall" ]]; then
    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
    fi
    rm -f "$PLIST_PATH"
    echo "已卸载开机自启: $PLIST_PATH"
    exit 0
fi

APP_PATH="/Applications/TokenTicker.app/Contents/MacOS/TokenTicker"
if [[ -x "$APP_PATH" ]]; then
    PROGRAM="$APP_PATH"
    PROGRAM_ARGS=()
else
    PYTHON_BIN="$(command -v python3 || true)"
    if [[ -z "$PYTHON_BIN" ]]; then
        echo "错误: 未找到 python3，且 /Applications/TokenTicker.app 不存在" >&2
        exit 1
    fi
    PROGRAM="$PYTHON_BIN"
    PROGRAM_ARGS=("$SCRIPT_DIR/ccswitch_widget.py")
fi

mkdir -p "$LAUNCH_AGENTS_DIR"
cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROGRAM</string>
PLIST

if [[ ${#PROGRAM_ARGS[@]} -gt 0 ]]; then
    for arg in "${PROGRAM_ARGS[@]}"; do
        printf '        <string>%s</string>\n' "$arg" >> "$PLIST_PATH"
    done
fi

cat >> "$PLIST_PATH" <<PLIST
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH" >/dev/null
launchctl load "$PLIST_PATH"
echo "已安装开机自启: $PLIST_PATH"
echo "程序: $PROGRAM"
```

Note: `PROGRAM_ARGS` is empty for the `.app` path; the guarded loop avoids emitting an empty `<string/>` element under bash 3.2 (macOS default).

- [ ] **Step 2: Verify syntax and plist validity**

Run:
```bash
bash -n setup_autostart.sh
# macOS 本机:
./setup_autostart.sh --uninstall && ./setup_autostart.sh && plutil -p ~/Library/LaunchAgents/com.tokenticker.widget.plist
```
Expected: `bash -n` exit 0; plutil 输出含 Label/ProgramArguments/RunAtLoad

- [ ] **Step 3: Commit**

```bash
git add setup_autostart.sh
git commit -m "feat: add macos launchagent autostart script"
git push origin feat/macos-cross-platform
```

---

### Task 7: macOS 打包脚本 + CI macOS 作业

**Files:**
- Create: `publish_mac.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `requirements.txt` (add optional-dep comment)

**Interfaces:**
- Produces: `publish_mac.sh`（本地打包 .app + sha256，不推送）；CI `verify-macos` 与 `package-smoke-macos` 作业

- [ ] **Step 1: Write the script**

Create `publish_mac.sh`:

```bash
#!/usr/bin/env bash
# 本地构建 TokenTicker macOS release candidate。本脚本绝不推送或发布 Release。
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="$(command -v python3)"
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" -m PyInstaller --clean --onefile --windowed --name TokenTicker \
    --collect-all customtkinter --osx-bundle-identifier com.tokenticker.widget \
    ccswitch_widget.py

BINARY="dist/TokenTicker.app/Contents/MacOS/TokenTicker"
if [[ ! -x "$BINARY" ]]; then
    echo "缺少构建产物: $BINARY" >&2
    exit 1
fi
HASH="$(shasum -a 256 "$BINARY" | awk '{print $1}')"
printf '%s  TokenTicker\n' "$HASH" > "dist/TokenTicker.app.sha256"

echo "artifact = dist/TokenTicker.app"
echo "sha256   = $HASH"
echo "Release remains local until tag and GitHub Release authorization is granted."
```

- [ ] **Step 2: Verify script syntax**

Run: `bash -n publish_mac.sh`
Expected: exit 0

- [ ] **Step 3: Add CI jobs**

Modify `.github/workflows/ci.yml` — append after the existing `package-smoke` job:

```yaml
  verify-macos:
    runs-on: macos-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - run: python3 -m pip install -r requirements.txt
      - run: python3 -m unittest discover -s tests -v
      - run: python3 -m py_compile ccswitch_widget.py platform_compat.py
      - name: Parse shell scripts
        run: |
          for f in setup_autostart.sh publish_mac.sh; do
            bash -n "$f"
          done

  package-smoke-macos:
    runs-on: macos-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - run: python3 -m pip install -r requirements.txt pyinstaller
      - run: ./publish_mac.sh
      - uses: actions/upload-artifact@v4
        with:
          name: TokenTicker-macos-candidate
          path: |
            dist/TokenTicker.app
            dist/TokenTicker.app.sha256
          if-no-files-found: error
          retention-days: 7
```

- [ ] **Step 4: Update requirements.txt**

Replace the single line `customtkinter>=5.2,<6` with:

```
customtkinter>=5.2,<6
# macOS 可选毛玻璃效果: pip install pyobjc-framework-Cocoa
```

- [ ] **Step 5: Commit**

```bash
git add publish_mac.sh .github/workflows/ci.yml requirements.txt
git commit -m "ci: add macos verification and packaging smoke jobs"
git push origin feat/macos-cross-platform
```

---

### Task 8: README / CHANGELOG 更新

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: 全部已完成功能

- [ ] **Step 1: Update CHANGELOG.md**

Replace the top of `CHANGELOG.md` (the `## 1.6.3 - Unreleased` section) with:

```markdown
# Changelog

## 1.7.0 - Unreleased

- 跨平台适配：macOS 字体自适应（PingFang SC / SF Pro Text）、毛玻璃（可选 pyobjc，自动降级半透明）、无边框窗口交互（NSPanel）
- 数据库路径自适应：手动指定 → CC Switch 自定义配置目录 → 默认路径
- macOS 开机自启（setup_autostart.sh，LaunchAgent）与打包（publish_mac.sh，PyInstaller .app）
- CI 增加 macOS 验证与打包冒烟作业

## 1.6.3

- Improve minimum text sizing and readability.
- Resolve startup shortcut paths from the checked-out repository instead of a developer-specific directory.
- Replace the one-time repository publishing script with a local test, package, and SHA-256 workflow.
- Add database-query, utility, PowerShell parse, and packaging CI checks.
```

(Keep the original 1.6.3 bullets verbatim; only the section header changes from `1.6.3 - Unreleased` to `1.6.3`.)

- [ ] **Step 2: Update README.md**

1. Change the platform badge row (line 12) to:

```markdown
  <img src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/macOS-000000?style=flat-square&logo=apple&logoColor=white" alt="macOS" />
```

2. Replace the "已知限制" first bullet (line 117):

```markdown
- 仅 Windows 测试通过（Segoe UI 字体；macOS / Linux 需改字体）
```

with:

```markdown
- Windows / macOS 均支持（macOS 需 macOS 12+；毛玻璃需 `pip install pyobjc-framework-Cocoa`，未安装自动降级半透明）
```

3. Replace the "前置要求" section (lines 55-57) to add macOS:

```markdown
### 前置要求
- 已安装并运行 [CC Switch](https://github.com/farion1231/cc-switch) **v3.13+**
- Python 3.8+（macOS 建议 Python 3.12 + Tk）

### macOS 可选毛玻璃

```bash
pip install pyobjc-framework-Cocoa
```

未安装时窗口自动使用半透明效果，功能不受影响。
```

4. Replace the "开机自启（Windows）" section (lines 74-80) with a combined section:

```markdown
### 开机自启

**Windows:** 运行 `setup_autostart.ps1` 创建开机自启 + 桌面快捷方式：

```powershell
powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
```

**macOS:** 运行 `setup_autostart.sh` 安装 LaunchAgent：

```bash
./setup_autostart.sh          # 安装
./setup_autostart.sh --uninstall  # 卸载
```

### 打包成 app（macOS，可选）

```bash
./publish_mac.sh
```

输出 `dist/TokenTicker.app` 与校验和；脚本不会推送代码或创建 GitHub Release。
```

- [ ] **Step 3: Verify all tests still pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (28 tests)

- [ ] **Step 4: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document macos support in readme and changelog"
git push origin feat/macos-cross-platform
```

---

## 本机验证（macOS，Task 5 完成后）

```bash
cd /var/folders/wv/wn0ncfs160q9p3s73zpryyx00000gn/T/opencode/ccswitch-usage-widget
python3 -m unittest discover -s tests -v
python3 ccswitch_widget.py   # 人工检查: 显示/刷新/右键菜单/设置/拖动/毛玻璃
```

检查项：
- 字体为 PingFang SC（非豆腐块）
- 无边框、置顶、可拖动
- 右键菜单与设置窗口可交互（NSPanel 生效）
- 毛玻璃或半透明降级正常
- 数据来自 `~/.cc-switch/cc-switch.db`

## 最终交付

- [ ] PR #2 内所有任务提交完成
- [ ] macOS 本机人工验证通过
- [ ] CI（Windows + macOS）全绿
