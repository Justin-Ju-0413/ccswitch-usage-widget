#!/usr/bin/env python3
"""CC Switch 用量桌面悬浮窗 v1.3.0

单窗口:用量表格(近24h/本月)+ 花费 K 线图(5m/15m/30m/1h/24h/7d)+ 设置页面。
K 线 OHLC = 每桶内请求花费的首/最大/最小/末。只读 ~/.cc-switch/cc-switch.db。
"""
import sqlite3, os, datetime, sys, json
from collections import defaultdict
import tkinter as tk
from tkinter import ttk

__version__ = "1.4.0"

DB = os.path.expanduser("~/.cc-switch/cc-switch.db")
CONFIG_DIR = os.path.expanduser("~/.ccswitch-widget")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
F = "Segoe UI"

THEMES = {
    "Mocha": {"bg":"#1e1e2e","surface":"#313244","text":"#cdd6f4","sub":"#a6adc8","dim":"#6c7086","green":"#a6e3a1","yellow":"#f9e2af","red":"#f38ba8","blue":"#89b4fa","mauve":"#cba6f7","teal":"#94e2d5"},
    "Latte": {"bg":"#eff1f5","surface":"#ccd0da","text":"#4c4f69","sub":"#6c6f85","dim":"#9ca0b0","green":"#40a02b","yellow":"#df8e1d","red":"#d20f39","blue":"#1e66f5","mauve":"#8839ef","teal":"#179299"},
    "Nord":  {"bg":"#2e3440","surface":"#3b4252","text":"#d8dee9","sub":"#a3b1c2","dim":"#7b8497","green":"#a3be8c","yellow":"#ebcb8b","red":"#bf616a","blue":"#81a1c1","mauve":"#b48ead","teal":"#8fbcbb"},
}

DEFAULT_CONFIG = {"refresh_ms":30000, "alpha":0.95, "theme":"Mocha", "default_range":"24h", "win_w":440, "win_h":700}

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


class UsageTable:
    def __init__(self, parent, theme, title, big_font=13):
        self.t = theme
        wrap = tk.Frame(parent, bg=theme["bg"])
        wrap.pack(fill="x", padx=14, pady=(4, 0))
        r = tk.Frame(wrap, bg=theme["bg"])
        r.pack(fill="x")
        tk.Label(r, text=title, fg=theme["dim"], bg=theme["bg"], font=(F, 9), width=6, anchor="w").pack(side="left")
        self.cost = tk.Label(r, text="$0.00", fg=theme["green"], bg=theme["bg"], font=(F, big_font, "bold"))
        self.cost.pack(side="left")
        self.tok = tk.Label(r, text="", fg=theme["blue"], bg=theme["bg"], font=(F, 9))
        self.tok.pack(side="right")
        self.body = tk.Frame(wrap, bg=theme["bg"])
        self.body.pack(fill="x", pady=(6, 0))

    def update(self, total, rows):
        t = self.t
        self.cost.config(text=f"${total[0] or 0:.2f}", fg=cost_color(total[0] or 0, t))
        self.tok.config(text=fmt_tok(total[1]) + " tokens")
        for w in self.body.winfo_children():
            w.destroy()
        h = tk.Frame(self.body, bg=t["bg"])
        h.pack(fill="x", pady=(0, 3))
        tk.Label(h, text="", bg=t["bg"], width=2).pack(side="left")
        tk.Label(h, text="名称", fg=t["dim"], bg=t["bg"], font=(F, 7), width=16, anchor="w").pack(side="left")
        tk.Label(h, text="Token", fg=t["dim"], bg=t["bg"], font=(F, 7), width=8, anchor="e").pack(side="left", padx=(4, 0))
        tk.Label(h, text="花费", fg=t["dim"], bg=t["bg"], font=(F, 7), anchor="e").pack(side="right")
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
        row = tk.Frame(self.body, bg=t["bg"])
        row.pack(fill="x", pady=1)
        tk.Label(row, text="●", fg=col, bg=t["bg"], font=(F, 8), width=2).pack(side="left")
        tk.Label(row, text=agent, fg=t["text"], bg=t["bg"], font=(F, 9, "bold"), width=16, anchor="w").pack(side="left")
        tk.Label(row, text=fmt_tok(tok), fg=t["sub"], bg=t["bg"], font=(F, 8), width=8, anchor="e").pack(side="left", padx=(4, 0))
        tk.Label(row, text=f"${cost or 0:.2f}", fg=cost_color(cost or 0, t), bg=t["bg"], font=(F, 9, "bold")).pack(side="right")

    def _sub_row(self, model, tok, cost):
        t = self.t
        row = tk.Frame(self.body, bg=t["bg"])
        row.pack(fill="x", padx=(16, 0))
        tk.Label(row, text="└", fg=t["dim"], bg=t["bg"], font=(F, 8), width=2).pack(side="left")
        tk.Label(row, text=(model or "?")[:18], fg=t["sub"], bg=t["bg"], font=(F, 8), width=16, anchor="w").pack(side="left")
        tk.Label(row, text=fmt_tok(tok), fg=t["dim"], bg=t["bg"], font=(F, 8), width=8, anchor="e").pack(side="left", padx=(4, 0))
        tk.Label(row, text=f"${cost or 0:.2f}", fg=cost_color(cost or 0, t), bg=t["bg"], font=(F, 8)).pack(side="right")


class CandleChart:
    """花费 K 线图:每桶 OHLC = 桶内请求花费的首/最大/最小/末。涨红跌绿,当前黄框。"""
    def __init__(self, parent, theme):
        self.t = theme
        wrap = tk.Frame(parent, bg=theme["bg"])
        wrap.pack(fill="x", padx=14, pady=(4, 0))
        self.canvas = tk.Canvas(wrap, bg=theme["bg"], highlightthickness=0, height=160)
        self.canvas.pack(fill="x", pady=(2, 0))
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.candles, self.range_key = [], "24h"

    def update(self, candles, range_key):
        self.candles, self.range_key = candles, range_key
        self.draw()

    def draw(self):
        c = self.canvas
        t = self.t
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return
        ml, mb, mt, mr = 40, 16, 20, 8
        cw = w - ml - mr
        ch = h - mt - mb
        base_y = mt + ch
        n = len(self.candles) or 1
        max_h = max((cd[1] for cd in self.candles), default=0.0)
        max_h = max(max_h, 0.0001)
        bw = cw / n
        body_w = max(2, bw / 3)
        # 网格
        for i in range(1, 4):
            y = mt + ch * i // 4
            c.create_line(ml, y, ml + cw, y, fill=t["surface"], dash=(1, 3))
        # Y 标签
        c.create_text(ml - 4, mt, text=f"${max_h:.4f}", fill=t["dim"], font=(F, 7), anchor="ne")
        c.create_text(ml - 4, base_y, text="$0", fill=t["dim"], font=(F, 7), anchor="se")
        c.create_text(ml - 4, mt + ch // 2, text=f"${max_h/2:.4f}", fill=t["dim"], font=(F, 7), anchor="e")
        # 涨跌幅(最后 close vs 第一 close)
        if len(self.candles) >= 2:
            first_c = self.candles[0][3]
            last_c = self.candles[-1][3]
            if first_c > 0:
                change = (last_c - first_c) / first_c * 100
                arrow = "▲" if change >= 0 else "▼"
                color = t["red"] if change >= 0 else t["green"]
                c.create_text(ml + cw, 8, text=f"{arrow} {abs(change):.1f}%", fill=color, font=(F, 8, "bold"), anchor="ne")
            else:
                c.create_text(ml + cw, 8, text="- 0.0%", fill=t["dim"], font=(F, 8), anchor="ne")
        # K 线
        for i, (o, hi, lo, cl) in enumerate(self.candles):
            x = ml + i * bw + bw / 2
            y_h = base_y - hi / max_h * ch
            y_l = base_y - lo / max_h * ch
            y_o = base_y - o / max_h * ch
            y_c = base_y - cl / max_h * ch
            color = t["red"] if cl >= o else t["green"]
            # 影线
            c.create_line(x, y_h, x, y_l, fill=color, width=1)
            # 实体
            top = min(y_o, y_c)
            bot = max(y_o, y_c)
            if bot - top < 2:
                bot = top + 2
            c.create_rectangle(x - body_w, top, x + body_w, bot, fill=color, outline=color)
            # 当前 K 线黄框
            if i == n - 1:
                c.create_rectangle(x - bw / 2, y_h - 3, x + bw / 2, y_l + 3, outline=t["yellow"], width=1)
        # X 标签
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
                c.create_text(ml + i * bw + bw / 2, base_y + 8, text=lbl, fill=t["dim"], font=(F, 7))


class SettingsWindow:
    def __init__(self, parent, cfg, theme, on_apply):
        self.cfg = dict(cfg)
        self.on_apply = on_apply
        t = theme
        win = tk.Toplevel(parent)
        win.title("设置")
        win.configure(bg=t["bg"])
        win.geometry("340x340")
        win.transient(parent)
        win.wm_attributes("-topmost", True)
        win.lift()
        win.focus_force()
        win.grab_set()
        self.win = win

        def row(label, widget_cls, **kw):
            f = tk.Frame(win, bg=t["bg"])
            f.pack(fill="x", padx=14, pady=8)
            tk.Label(f, text=label, fg=t["text"], bg=t["bg"], font=(F, 9)).pack(side="left")
            w = widget_cls(f, **kw)
            w.pack(side="right")
            return w

        self.refresh_var = tk.IntVar(value=cfg["refresh_ms"] // 1000)
        row("刷新间隔(秒)", tk.Spinbox, from_=5, to=600, textvariable=self.refresh_var, width=6)
        self.alpha_var = tk.DoubleVar(value=cfg["alpha"])
        sc = tk.Scale(win, from_=0.6, to=1.0, resolution=0.05, orient="horizontal",
                      variable=self.alpha_var, bg=t["bg"], fg=t["text"], highlightthickness=0,
                      troughcolor=t["surface"], length=140)
        f2 = tk.Frame(win, bg=t["bg"]); f2.pack(fill="x", padx=14, pady=8)
        tk.Label(f2, text="透明度", fg=t["text"], bg=t["bg"], font=(F, 9)).pack(side="left")
        sc.pack(side="right")
        self.theme_var = tk.StringVar(value=cfg["theme"])
        row("主题", ttk.Combobox, textvariable=self.theme_var, values=list(THEMES.keys()), width=12, state="readonly")
        self.range_var = tk.StringVar(value=cfg["default_range"])
        row("默认范围", ttk.Combobox, textvariable=self.range_var, values=list(RANGES.keys()), width=12, state="readonly")

        bf = tk.Frame(win, bg=t["bg"]); bf.pack(pady=12)
        tk.Button(bf, text="保存", command=self.save, bg=t["mauve"], fg=t["bg"], font=(F, 9, "bold"),
                  padx=16, relief="flat").pack()

    def save(self):
        self.cfg["refresh_ms"] = self.refresh_var.get() * 1000
        self.cfg["alpha"] = self.alpha_var.get()
        self.cfg["theme"] = self.theme_var.get()
        self.cfg["default_range"] = self.range_var.get()
        save_config(self.cfg)
        self.on_apply(self.cfg)
        self.win.destroy()


class App:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.theme = THEMES[cfg["theme"]]
        self.range_key = cfg["default_range"]
        self._after_id = None
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-alpha", cfg["alpha"])
        root.configure(bg=self.theme["bg"])
        sw = root.winfo_screenwidth()
        root.geometry(f"{cfg['win_w']}x{cfg['win_h']}+{sw-cfg['win_w']-20}+20")
        self._build_ui()
        self.refresh()
        self._schedule()

    def _build_ui(self):
        t = self.theme
        for w in self.root.winfo_children():
            w.destroy()
        outer = tk.Frame(self.root, bg=t["surface"])
        outer.pack(fill="both", expand=True)
        self.body = tk.Frame(outer, bg=t["bg"])
        self.body.pack(fill="both", expand=True, padx=1, pady=1)

        hdr = tk.Frame(self.body, bg=t["bg"])
        hdr.pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(hdr, text="█ TokenTicker", fg=t["mauve"], bg=t["bg"], font=(F, 13, "bold")).pack(side="left")
        self.clock = tk.Label(hdr, text="", fg=t["dim"], bg=t["bg"], font=(F, 9))
        self.clock.pack(side="right")
        tk.Label(self.body, text=f"你的 AI 用量行情终端  ·  v{__version__}", fg=t["dim"], bg=t["bg"], font=(F, 7)).pack(fill="x", padx=14, pady=(0, 4))

        self._sep(self.body, (4, 4))
        self.today = UsageTable(self.body, t, "近24h", 13)
        self._sep(self.body, (6, 0))
        self.month = UsageTable(self.body, t, "本月", 12)
        self._sep(self.body, (6, 0))

        rbtn = tk.Frame(self.body, bg=t["bg"])
        rbtn.pack(fill="x", padx=14, pady=(4, 0))
        tk.Label(rbtn, text="花费 K 线", fg=t["dim"], bg=t["bg"], font=(F, 8, "bold")).pack(side="left")
        self.range_buttons = {}
        for key in RANGES:
            active = (key == self.range_key)
            b = tk.Button(rbtn, text=RANGES[key]["label"], command=lambda k=key: self.set_range(k),
                          bg=t["mauve"] if active else t["surface"], fg=t["bg"] if active else t["sub"],
                          relief="flat", font=(F, 7, "bold"), padx=5, bd=0)
            b.pack(side="right", padx=1)
            self.range_buttons[key] = b
        self.chart = CandleChart(self.body, t)
        self._sep(self.body, (6, 0))

        self.api_label = tk.Label(self.body, text="", fg=t["dim"], bg=t["bg"], font=(F, 8), anchor="w")
        self.api_label.pack(fill="x", padx=14, pady=(4, 0))
        self.latest = tk.Label(self.body, text="", fg=t["dim"], bg=t["bg"], font=(F, 8), anchor="w")
        self.latest.pack(fill="x", padx=14, pady=(2, 4))
        leg = tk.Frame(self.body, bg=t["bg"])
        leg.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(leg, text="█涨", fg=t["red"], bg=t["bg"], font=(F, 8)).pack(side="left")
        tk.Label(leg, text="█跌", fg=t["green"], bg=t["bg"], font=(F, 8)).pack(side="left", padx=(4, 8))
        tk.Label(leg, text="▢", fg=t["yellow"], bg=t["bg"], font=(F, 8)).pack(side="left")
        tk.Label(leg, text="当前", fg=t["dim"], bg=t["bg"], font=(F, 8)).pack(side="left", padx=(2, 0))

        self.menu = tk.Menu(self.root, tearoff=0, bg=t["bg"], fg=t["text"], activebackground=t["surface"],
                            activeforeground=t["text"], borderwidth=0)
        self.menu.add_command(label="立即刷新", command=self.refresh)
        self.menu.add_command(label="设置…", command=self.open_settings)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.root.destroy)
        self.root.bind_all("<Button-1>", self.start_drag)
        self.root.bind_all("<B1-Motion>", self.do_drag)
        self.root.bind_all("<Button-3>", self.popup)
        self.root.bind_all("<Escape>", lambda e: self.root.destroy())
        self._sx = self._sy = self._ox = self._oy = 0

    def _sep(self, parent, pady):
        tk.Frame(parent, bg=self.theme["surface"], height=1).pack(fill="x", padx=14, pady=pady)

    def set_range(self, key):
        self.range_key = key
        t = self.theme
        for k, b in self.range_buttons.items():
            active = (k == key)
            b.config(bg=t["mauve"] if active else t["surface"], fg=t["bg"] if active else t["sub"])
        self.refresh()

    def open_settings(self):
        SettingsWindow(self.root, self.cfg, self.theme, self.apply_config)

    def apply_config(self, new_cfg):
        self.cfg = new_cfg
        self.theme = THEMES[new_cfg["theme"]]
        self.range_key = new_cfg["default_range"]
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
            self.clock.config(text="出错")
            self.latest.config(text=str(e)[:40])
            return
        self.today.update(d["today"], d["today_rows"])
        self.month.update(d["month"], d["month_rows"])
        self.chart.update(d["candles"], d["range_key"])
        api = " · ".join(n for _, n in d["providers"]) if d["providers"] else ""
        self.api_label.config(text="API: " + api if api else "")
        l = d["latest"]
        if l and l[0]:
            self.latest.config(text=f"最近: {l[0]} · {l[1] or '?'}")
        elif l:
            self.latest.config(text=f"最近: {l[1] or ''}")
        self.clock.config(text=datetime.datetime.now().strftime("%H:%M:%S"))

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
    root = tk.Tk()
    App(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
