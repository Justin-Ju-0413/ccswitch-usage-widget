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
    return select_font(available=set(tkfont.families(root)))


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
    """按优先级返回数据库路径：手动配置优先；否则返回第一个存在的候选；都不存在时返回默认路径。"""
    manual = (cfg.get("db_path") or "").strip()
    if manual:
        return os.path.expanduser(manual)
    candidates = db_candidates(cfg, cc_switch_dir)
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[-1]


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


def make_mac_panel(root):
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
