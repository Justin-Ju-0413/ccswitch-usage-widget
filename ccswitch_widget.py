#!/usr/bin/env python3
"""TokenTicker v1.6.2 - 液态玻璃 + DWM Acrylic,字体最小 12pt"""
import sqlite3, os, datetime, sys, json
from collections import defaultdict
import customtkinter as ctk
import tkinter as tk

__version__ = "1.6.2"
ctk.set_appearance_mode("dark")

DB = os.path.expanduser("~/.cc-switch/cc-switch.db")
CONFIG_DIR = os.path.expanduser("~/.ccswitch-widget")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
F = "Segoe UI"
TRANSP = '#010101'

THEMES = {
    "Mocha": {"win":"#181825","card":"#1e1e2e","card2":"#313244","border":"#45475a","text":"#cdd6f4","sub":"#a6adc8","dim":"#6c7086","green":"#a6e3a1","yellow":"#f9e2af","red":"#f38ba8","blue":"#89b4fa","mauve":"#cba6f7","teal":"#94e2d5"},
    "Latte": {"win":"#e6e9ef","card":"#eff1f5","card2":"#ccd0da","border":"#bcc0cc","text":"#4c4f69","sub":"#6c6f85","dim":"#9ca0b0","green":"#40a02b","yellow":"#df8e1d","red":"#d20f39","blue":"#1e66f5","mauve":"#8839ef","teal":"#179299"},
    "Nord":  {"win":"#242933","card":"#2e3440","card2":"#3b4252","border":"#4c566a","text":"#d8dee9","sub":"#a3b1c2","dim":"#7b8497","green":"#a3be8c","yellow":"#ebcb8b","red":"#bf616a","blue":"#81a1c1","mauve":"#b48ead","teal":"#8fbcbb"},
}

DEFAULT_CONFIG = {"refresh_ms":30000, "alpha":0.88, "theme":"Mocha", "default_range":"24h", "win_w":520, "win_h":1020}

RANGES = {
    "5m":  {"seconds":300,   "bucket":30,    "n":10, "label":"5m"},
    "15m": {"seconds":900,   "bucket":60,    "n":15, "label":"15m"},
    "30m": {"seconds":1800,  "bucket":120,   "n":15, "label":"30m"},
    "1h":  {"seconds":3600,  "bucket":300,   "n":12, "label":"1h"},
    "24h": {"seconds":86400, "bucket":3600,  "n":24, "label":"24h"},
    "7d":  {"seconds":604800,"bucket":86400, "n":7,  "label":"7d"},
}

TOK_EXPR = "input_tokens+output_tokens+cache_read_tokens+cache_creation_tokens"
GRP = "CASE WHEN app_type LIKE 'claude%' THEN 'Claude' ELSE 'Codex' END"


def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if cfg.get("theme") not in THEMES:
        cfg["theme"] = "Mocha"
    if cfg.get("default_range") not in RANGES:
        cfg["default_range"] = "24h"
    return cfg


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def fmt_tok(n):
    if not n:
        return "0"
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def cost_color(amt, t):
    if amt is None:
        return t["text"]
    if amt >= 50:
        return t["red"]
    if amt >= 20:
        return t["yellow"]
    return t["green"]


def query(range_key):
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=3)
    con.execute("PRAGMA busy_timeout=3000")
    now = datetime.datetime.now()
    now_ts = int(now.timestamp())
    h24 = now_ts - 86400
    ms = int(datetime.datetime(now.year, now.month, 1).timestamp())
    today_total = con.execute(
        f"SELECT ROUND(SUM(CAST(total_cost_usd AS REAL)),4), SUM({TOK_EXPR}) "
        "FROM proxy_request_logs WHERE created_at>=?", (h24,)).fetchone()
    today_rows = con.execute(
        f"SELECT {GRP} g, model, ROUND(SUM(CAST(total_cost_usd AS REAL)),4), SUM({TOK_EXPR}) "
        "FROM proxy_request_logs WHERE created_at>=? GROUP BY 1,2 "
        "ORDER BY 1, SUM(CAST(total_cost_usd AS REAL)) DESC", (h24,)).fetchall()
    month_total = con.execute(
        f"SELECT ROUND(SUM(CAST(total_cost_usd AS REAL)),4), SUM({TOK_EXPR}) "
        "FROM proxy_request_logs WHERE created_at>=?", (ms,)).fetchone()
    month_rows = con.execute(
        f"SELECT {GRP} g, model, ROUND(SUM(CAST(total_cost_usd AS REAL)),4), SUM({TOK_EXPR}) "
        "FROM proxy_request_logs WHERE created_at>=? GROUP BY 1,2 "
        "ORDER BY 1, SUM(CAST(total_cost_usd AS REAL)) DESC", (ms,)).fetchall()
    rg = RANGES[range_key]
    start = now_ts - rg["seconds"]
    chart_rows = con.execute(
        f"SELECT (? - created_at)/{rg['bucket']} b, CAST(total_cost_usd AS REAL) cost "
        "FROM proxy_request_logs WHERE created_at>=? ORDER BY b, created_at", (now_ts, start)).fetchall()
    cur = con.execute(
        "SELECT app_type, name FROM providers WHERE is_current=1 "
        "AND app_type IN ('claude','codex') ORDER BY app_type").fetchall()
    latest = con.execute(
        "SELECT p.name, l.model FROM proxy_request_logs l "
        "LEFT JOIN providers p ON l.provider_id=p.id AND l.app_type=p.app_type "
        "ORDER BY l.created_at DESC LIMIT 1").fetchone()
    con.close()
    per = defaultdict(list)
    for b, cost in chart_rows:
        if b is not None and 0 <= b < rg["n"]:
            per[int(b)].append(cost or 0.0)
    candles = []
    for i in range(rg["n"]):
        b = rg["n"] - 1 - i
        cs = per.get(b, [])
        if cs:
            candles.append((cs[0], max(cs), min(cs), cs[-1]))
        else:
            candles.append((0.0, 0.0, 0.0, 0.0))
    return dict(today=today_total, today_rows=today_rows, month=month_total,
                month_rows=month_rows, candles=candles, range_key=range_key,
                providers=cur, latest=latest)


def _lbl(parent, text, theme, key, font, width=None, anchor="w", color=None):
    c = color if color is not None else theme[key]
    kw = dict(text=text, fg_color="transparent", text_color=c, font=font, anchor=anchor, height=30)
    if width is not None:
        kw["width"] = width
    return ctk.CTkLabel(parent, **kw)


class UsageTable:
    def __init__(self, parent, theme, title, big_font=17):
        self.t = theme
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=16, pady=(10, 2))
        r = ctk.CTkFrame(wrap, fg_color="transparent")
        r.pack(fill="x")
        _lbl(r, title, theme, "dim", (F, 13), 70, "w").pack(side="left")
        self.cost = _lbl(r, "$0.00", theme, "green", (F, big_font, "bold"))
        self.cost.pack(side="left")
        self.tok = _lbl(r, "", theme, "blue", (F, 13))
        self.tok.pack(side="right")
        self.body = ctk.CTkFrame(wrap, fg_color="transparent")
        self.body.pack(fill="x", pady=(4, 8))

    def update(self, total, rows):
        t = self.t
        self.cost.configure(text=f"${total[0] or 0:.2f}", text_color=cost_color(total[0] or 0, t))
        self.tok.configure(text=fmt_tok(total[1]) + " tokens")
        for w in self.body.winfo_children():
            w.destroy()
        h = ctk.CTkFrame(self.body, fg_color="transparent")
        h.pack(fill="x", pady=(0, 2))
        _lbl(h, "名称", t, "dim", (F, 12), 190, "w").pack(side="left")
        _lbl(h, "Token", t, "dim", (F, 12), 90, "e").pack(side="left", padx=(4, 0))
        _lbl(h, "花费", t, "dim", (F, 12), None, "e").pack(side="right")
        for agent in ("Claude", "Codex"):
            arows = [r for r in rows if r[0] == agent]
            ac = sum((r[2] or 0) for r in arows)
            at = sum((r[3] or 0) for r in arows)
            self._agent_row(agent, at, ac)
            for r in arows[:3]:
                self._sub_row(r[1], r[3] or 0, r[2])

    def _agent_row(self, agent, tok, cost):
        t = self.t
        col = t["mauve"] if agent == "Claude" else t["teal"]
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=1)
        _lbl(row, "● " + agent, t, None, (F, 13, "bold"), 190, "w", color=col).pack(side="left")
        _lbl(row, fmt_tok(tok), t, "sub", (F, 12), 90, "e").pack(side="left", padx=(4, 0))
        _lbl(row, f"${cost or 0:.2f}", t, None, (F, 13, "bold"), None, "e", color=cost_color(cost or 0, t)).pack(side="right")

    def _sub_row(self, model, tok, cost):
        t = self.t
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", padx=(20, 0))
        _lbl(row, "└ " + (model or "?")[:16], t, "sub", (F, 12), 190, "w").pack(side="left")
        _lbl(row, fmt_tok(tok), t, "dim", (F, 12), 90, "e").pack(side="left", padx=(4, 0))
        _lbl(row, f"${cost or 0:.2f}", t, None, (F, 12), None, "e", color=cost_color(cost or 0, t)).pack(side="right")


class CandleChart:
    def __init__(self, parent, theme):
        self.t = theme
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=16, pady=(2, 10))
        self.canvas = tk.Canvas(wrap, bg=theme["card"], highlightthickness=0, height=160)
        self.canvas.pack(fill="x", pady=(2, 0))
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.candles, self.range_key = [], "24h"

    def update(self, candles, range_key):
        self.candles, self.range_key = candles, range_key
        self.draw()

    def draw(self):
        c = self.canvas
        t = self.t
        c.configure(bg=t["card"])
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return
        ml, mb, mt, mr = 50, 20, 24, 8
        cw = w - ml - mr
        ch = h - mt - mb
        base_y = mt + ch
        n = len(self.candles) or 1
        max_h = max((cd[1] for cd in self.candles), default=0.0)
        max_h = max(max_h, 0.0001)
        bw = cw / n
        body_w = max(2, bw / 3)
        for i in range(1, 4):
            y = mt + ch * i // 4
            c.create_line(ml, y, ml + cw, y, fill=t["border"], dash=(1, 3))
        c.create_text(ml - 4, mt, text=f"${max_h:.4f}", fill=t["dim"], font=(F, 12), anchor="ne")
        c.create_text(ml - 4, base_y, text="$0", fill=t["dim"], font=(F, 12), anchor="se")
        if len(self.candles) >= 2:
            first_c = self.candles[0][3]
            last_c = self.candles[-1][3]
            if first_c > 0:
                change = (last_c - first_c) / first_c * 100
                arrow = "▲" if change >= 0 else "▼"
                color = t["red"] if change >= 0 else t["green"]
                c.create_text(ml + cw, 12, text=f"{arrow} {abs(change):.1f}%", fill=color, font=(F, 13, "bold"), anchor="ne")
            else:
                c.create_text(ml + cw, 12, text="- 0.0%", fill=t["dim"], font=(F, 13), anchor="ne")
        for i, (o, hi, lo, cl) in enumerate(self.candles):
            x = ml + i * bw + bw / 2
            y_h = base_y - hi / max_h * ch
            y_l = base_y - lo / max_h * ch
            y_o = base_y - o / max_h * ch
            y_c = base_y - cl / max_h * ch
            color = t["red"] if cl >= o else t["green"]
            c.create_line(x, y_h, x, y_l, fill=color, width=1)
            top = min(y_o, y_c)
            bot = max(y_o, y_c)
            if bot - top < 2:
                bot = top + 2
            c.create_rectangle(x - body_w, top, x + body_w, bot, fill=color, outline=color)
            if i == n - 1:
                c.create_rectangle(x - bw / 2, y_h - 3, x + bw / 2, y_l + 3, outline=t["yellow"], width=1)
        bk = RANGES[self.range_key]["bucket"]
        unit = "s" if bk < 60 else ("m" if bk < 3600 else ("h" if bk < 86400 else "d"))
        div = 1 if unit == "s" else (60 if unit == "m" else (3600 if unit == "h" else 86400))
        step = max(1, n // 6)
        for i in range(n):
            if i == n - 1:
                lbl = "now"
            elif i % step == 0:
                lbl = f"-{(n - 1 - i) * bk // div}{unit}"
            else:
                lbl = None
            if lbl:
                c.create_text(ml + i * bw + bw / 2, base_y + 12, text=lbl, fill=t["dim"], font=(F, 12))


class SettingsWindow:
    def __init__(self, parent, cfg, theme, on_apply):
        self.cfg = dict(cfg)
        self.on_apply = on_apply
        t = theme
        win = ctk.CTkToplevel(parent, fg_color=t["win"])
        win.title("TokenTicker 设置")
        win.geometry("420x440")
        win.transient(parent)
        win.wm_attributes("-topmost", True)
        win.lift()
        win.focus_force()
        win.grab_set()
        self.win = win

        def card(parent):
            f = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=12, border_width=1, border_color=t["border"])
            f.pack(fill="x", padx=18, pady=8)
            return f

        c1 = card(win)
        ctk.CTkLabel(c1, text="刷新间隔", fg_color="transparent", text_color=t["text"], font=(F, 13)).pack(side="left", padx=16, pady=14)
        self.refresh_var = tk.StringVar(value=str(cfg["refresh_ms"] // 1000))
        ctk.CTkOptionMenu(c1, variable=self.refresh_var, values=["5", "10", "30", "60", "120", "300"],
                          fg_color=t["card2"], button_color=t["mauve"], text_color=t["text"],
                          width=110, height=30, font=(F, 12)).pack(side="right", padx=16, pady=12)
        ctk.CTkLabel(c1, text="秒", fg_color="transparent", text_color=t["dim"], font=(F, 12)).pack(side="right", padx=(0, 16))

        c2 = card(win)
        ctk.CTkLabel(c2, text="透明度", fg_color="transparent", text_color=t["text"], font=(F, 13)).pack(side="left", padx=16, pady=14)
        self.alpha_var = tk.DoubleVar(value=cfg["alpha"])
        ctk.CTkSlider(c2, variable=self.alpha_var, from_=0.6, to=1.0, number_of_steps=8,
                      button_color=t["mauve"], progress_color=t["card2"], width=160).pack(side="right", padx=16, pady=14)

        c3 = card(win)
        ctk.CTkLabel(c3, text="主题", fg_color="transparent", text_color=t["text"], font=(F, 13)).pack(side="left", padx=16, pady=14)
        self.theme_var = tk.StringVar(value=cfg["theme"])
        ctk.CTkOptionMenu(c3, variable=self.theme_var, values=list(THEMES.keys()),
                          fg_color=t["card2"], button_color=t["mauve"], text_color=t["text"],
                          width=140, height=30, font=(F, 12)).pack(side="right", padx=16, pady=12)

        c4 = card(win)
        ctk.CTkLabel(c4, text="默认范围", fg_color="transparent", text_color=t["text"], font=(F, 13)).pack(side="left", padx=16, pady=14)
        self.range_var = tk.StringVar(value=cfg["default_range"])
        ctk.CTkOptionMenu(c4, variable=self.range_var, values=list(RANGES.keys()),
                          fg_color=t["card2"], button_color=t["mauve"], text_color=t["text"],
                          width=140, height=30, font=(F, 12)).pack(side="right", padx=16, pady=12)

        tk.Button(win, text="保存", command=self.save, bg=t["mauve"], fg=t["win"],
                  font=(F, 13, "bold"), padx=24, relief="flat").pack(pady=18)

    def save(self):
        self.cfg["refresh_ms"] = int(self.refresh_var.get()) * 1000
        self.cfg["alpha"] = self.alpha_var.get()
        self.cfg["theme"] = self.theme_var.get()
        self.cfg["default_range"] = self.range_var.get()
        save_config(self.cfg)
        self.on_apply(self.cfg)
        self.win.destroy()


def try_acrylic(root):
    try:
        import ctypes
        from ctypes import windll, byref, c_int, sizeof
        root.update_idletasks()
        hwnd = windll.user32.GetParent(root.winfo_id())
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), sizeof(c_int))
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, byref(c_int(1)), sizeof(c_int))
        class MARGINS(ctypes.Structure):
            _fields_ = [("cxLeftWidth", c_int), ("cxRightWidth", c_int), ("cyTopHeight", c_int), ("cyBottomHeight", c_int)]
        windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(MARGINS(-1, -1, -1, -1)))
        return True
    except Exception:
        return False


class App:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.theme = THEMES[cfg["theme"]]
        self.range_key = cfg["default_range"]
        self._after_id = None
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        self.acrylic = try_acrylic(root)
        if self.acrylic:
            root.configure(fg_color=TRANSP)
            root.wm_attributes("-transparentcolor", TRANSP)
        else:
            root.wm_attributes("-alpha", cfg["alpha"])
            root.configure(fg_color=self.theme["win"])
        sw = root.winfo_screenwidth()
        root.geometry(f"{cfg['win_w']}x{cfg['win_h']}+{sw-cfg['win_w']-20}+20")
        self._build_ui()
        self.refresh()
        self._schedule()

    def _card(self, pady=(4, 4)):
        t = self.theme
        return ctk.CTkFrame(self.root, fg_color=t["card"], corner_radius=16,
                            border_width=1, border_color=t["border"])

    def _build_ui(self):
        t = self.theme
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(fg_color=TRANSP if self.acrylic else t["win"])

        hc = self._card((10, 4))
        hc.pack(fill="x", padx=10, pady=(10, 4))
        hdr = ctk.CTkFrame(hc, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(14, 2))
        ctk.CTkLabel(hdr, text="█ TokenTicker", fg_color="transparent", text_color=t["mauve"],
                     font=(F, 18, "bold")).pack(side="left")
        self.clock = ctk.CTkLabel(hdr, text="", fg_color="transparent", text_color=t["dim"], font=(F, 13))
        self.clock.pack(side="right")
        ctk.CTkLabel(hc, text=f"你的 AI 用量行情终端  ·  v{__version__}", fg_color="transparent",
                     text_color=t["dim"], font=(F, 12)).pack(fill="x", padx=18, pady=(0, 12))

        uc = self._card((4, 4))
        uc.pack(fill="x", padx=10, pady=4)
        self.today = UsageTable(uc, t, "近24h", 17)
        ctk.CTkFrame(uc, fg_color=t["border"], height=1).pack(fill="x", padx=18, pady=2)
        self.month = UsageTable(uc, t, "本月", 16)

        cc = self._card((4, 4))
        cc.pack(fill="x", padx=10, pady=4)
        rbtn = ctk.CTkFrame(cc, fg_color="transparent")
        rbtn.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(rbtn, text="花费 K 线", fg_color="transparent", text_color=t["dim"],
                     font=(F, 13, "bold")).pack(side="left")
        self.range_buttons = {}
        for key in RANGES:
            active = (key == self.range_key)
            b = ctk.CTkButton(rbtn, text=RANGES[key]["label"], command=lambda k=key: self.set_range(k),
                              fg_color=t["mauve"] if active else t["card2"],
                              text_color=t["win"] if active else t["sub"],
                              hover_color=t["card2"], corner_radius=6,
                              font=(F, 12, "bold"), width=44, height=28, border_width=0)
            b.pack(side="right", padx=2)
            self.range_buttons[key] = b
        self.chart = CandleChart(cc, t)
        leg = ctk.CTkFrame(cc, fg_color="transparent")
        leg.pack(fill="x", padx=18, pady=(0, 12))
        ctk.CTkLabel(leg, text="█涨", fg_color="transparent", text_color=t["red"], font=(F, 12)).pack(side="left")
        ctk.CTkLabel(leg, text="█跌", fg_color="transparent", text_color=t["green"], font=(F, 12)).pack(side="left", padx=(4, 12))
        ctk.CTkLabel(leg, text="▢", fg_color="transparent", text_color=t["yellow"], font=(F, 12)).pack(side="left")
        ctk.CTkLabel(leg, text="当前", fg_color="transparent", text_color=t["dim"], font=(F, 12)).pack(side="left", padx=(2, 0))

        fc = self._card((4, 10))
        fc.pack(fill="x", padx=10, pady=(4, 10))
        self.api_label = ctk.CTkLabel(fc, text="", fg_color="transparent", text_color=t["dim"],
                                      font=(F, 12), anchor="w")
        self.api_label.pack(fill="x", padx=18, pady=(14, 0))
        self.latest = ctk.CTkLabel(fc, text="", fg_color="transparent", text_color=t["dim"],
                                   font=(F, 12), anchor="w")
        self.latest.pack(fill="x", padx=18, pady=(2, 14))

        self.menu = tk.Menu(self.root, tearoff=0, bg=t["card"], fg=t["text"],
                            activebackground=t["card2"], activeforeground=t["text"], borderwidth=0,
                            font=(F, 12))
        self.menu.add_command(label="立即刷新", command=self.refresh)
        self.menu.add_command(label="设置…", command=self.open_settings)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.root.destroy)
        self.root.bind_all("<Button-1>", self.start_drag)
        self.root.bind_all("<B1-Motion>", self.do_drag)
        self.root.bind_all("<Button-3>", self.popup)
        self.root.bind_all("<Escape>", lambda e: self.root.destroy())
        self._sx = self._sy = self._ox = self._oy = 0

    def set_range(self, key):
        self.range_key = key
        t = self.theme
        for k, b in self.range_buttons.items():
            active = (k == key)
            b.configure(fg_color=t["mauve"] if active else t["card2"],
                        text_color=t["win"] if active else t["sub"])
        self.refresh()

    def open_settings(self):
        SettingsWindow(self.root, self.cfg, self.theme, self.apply_config)

    def apply_config(self, new_cfg):
        self.cfg = new_cfg
        self.theme = THEMES[new_cfg["theme"]]
        self.range_key = new_cfg["default_range"]
        if not self.acrylic:
            self.root.wm_attributes("-alpha", new_cfg["alpha"])
        self._build_ui()
        self.refresh()
        self._schedule()

    def _schedule(self):
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(self.cfg["refresh_ms"], self.loop)

    def loop(self):
        self.refresh()
        self._schedule()

    def refresh(self):
        try:
            d = query(self.range_key)
        except Exception as e:
            self.clock.configure(text="出错")
            self.latest.configure(text=str(e)[:40])
            return
        self.today.update(d["today"], d["today_rows"])
        self.month.update(d["month"], d["month_rows"])
        self.chart.update(d["candles"], d["range_key"])
        api = " · ".join(n for _, n in d["providers"]) if d["providers"] else ""
        self.api_label.configure(text="API: " + api if api else "")
        l = d["latest"]
        if l and l[0]:
            self.latest.configure(text=f"最近: {l[0]} · {l[1] or '?'}")
        elif l:
            self.latest.configure(text=f"最近: {l[1] or ''}")
        self.clock.configure(text=datetime.datetime.now().strftime("%H:%M:%S"))

    def popup(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def start_drag(self, e):
        self._sx, self._sy = e.x_root, e.y_root
        self._ox, self._oy = self.root.winfo_x(), self.root.winfo_y()

    def do_drag(self, e):
        self.root.geometry(f"+{self._ox + e.x_root - self._sx}+{self._oy + e.y_root - self._sy}")


def main():
    if not os.path.exists(DB):
        print(f"找不到 cc-switch.db: {DB}\n请先安装并运行 CC Switch(https://github.com/farion1231/cc-switch)。", file=sys.stderr)
        sys.exit(1)
    cfg = load_config()
    root = ctk.CTk()
    App(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
