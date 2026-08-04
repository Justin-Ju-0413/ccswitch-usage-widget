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
