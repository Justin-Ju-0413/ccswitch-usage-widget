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
