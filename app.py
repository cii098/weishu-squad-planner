# -*- coding: utf-8 -*-
"""
卫戍协议 · 小队规划器
仿云顶之弈的阵容/盟约（羁绊）规划工具，支持窗口置顶与小窗模式。
数据来源：PRTS Wiki / 游戏数据表（卫戍协议·规程 序列Ⅰ）
"""
import json
import os
import re
import sys
import time
import ctypes
import tkinter as tk
import tkinter.font as tkfont

# 打包成 exe 后：数据在临时解包目录，配置写在 exe 同目录
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    DATA_FILE = os.path.join(getattr(sys, "_MEIPASS", APP_DIR), "data.json")
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FILE = os.path.join(APP_DIR, "data.json")
CONFIG_FILE = os.path.join(APP_DIR, "settings.json")

MAX_TEAM = 9
CARD_H = 50          # 干员卡片高度（画布绘制）

# ---------------- 配色 ----------------
BG = "#0a1013"
PANEL = "#101a1e"
PANEL_2 = "#0d1619"
CARD = "#15232a"
CARD_HOVER = "#1b2f37"
CARD_ON = "#123a35"
BORDER = "#1e3138"
BORDER_ON = "#2ee6c0"
TEXT = "#dbe7ea"
MUTED = "#7a929b"
ACCENT = "#2ee6c0"
GOLD = "#e8b339"
WARN = "#e8703a"
KEY = "#010203"   # 悬浮球透明键控色

RANK_COLOR = {1: "#9aa6ab", 2: "#46efbc", 3: "#33c9da",
              4: "#f6c60f", 5: "#e88c1a", 6: "#ef4444"}
RANK_NAME = {1: "Ⅰ", 2: "Ⅱ", 3: "Ⅲ", 4: "Ⅳ", 5: "Ⅴ", 6: "Ⅵ"}

FONT = "Microsoft YaHei UI"


def clean(s):
    if not s:
        return ""
    s = re.sub(r"<@[^>]*>", "", s)
    s = s.replace("</>", "").replace("<", "").replace(">", "")
    return s.strip()


class Tooltip:
    """鼠标悬停提示"""

    def __init__(self, widget, get_text, wrap=300):
        self.widget = widget
        self.get_text = get_text
        self.wrap = wrap
        self.tip = None
        self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _=None):
        self._cancel()
        self.job = self.widget.after(420, self._show)

    def _cancel(self):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None

    def _show(self):
        text = self.get_text()
        if not text:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes("-topmost", True)
        try:
            self.tip.attributes("-disabled", True)   # 不接收鼠标，避免挡住点击
        except tk.TclError:
            pass
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip.wm_geometry(f"+{x}+{y}")
        f = tk.Frame(self.tip, bg=BORDER_ON, padx=1, pady=1)
        f.pack()
        tk.Label(f, text=text, bg="#0d1a1d", fg=TEXT, font=(FONT, 9),
                 justify="left", wraplength=self.wrap, padx=10, pady=8).pack()

    def _hide(self, _=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None


class DarkSelect(tk.Frame):
    """深色下拉选择器（自绘弹出列表，避免 Windows 原生菜单的浅色外观）"""

    def __init__(self, parent, values, on_change=None, width=10):
        bg = parent["bg"]
        super().__init__(parent, bg=bg)
        self.on_change = on_change
        self.values = list(values)
        self.value = self.values[0] if self.values else ""
        self.popup = None
        self._outside = None
        self.mb = tk.Label(self, text=f" {self.value} ▾ ", bg=PANEL, fg=TEXT,
                           font=(FONT, 9), padx=4, pady=4, width=width,
                           anchor="w", cursor="hand2",
                           highlightthickness=1, highlightbackground=BORDER)
        self.mb.pack(fill="x")
        self.mb.bind("<ButtonRelease-1>", self._open)
        self.mb.bind("<Enter>", lambda e: self.mb.configure(bg=CARD_HOVER,
                                                            highlightbackground=BORDER_ON))
        self.mb.bind("<Leave>", lambda e: self.mb.configure(bg=PANEL,
                                                            highlightbackground=BORDER))
        self.set_values(self.values)

    def set_values(self, values):
        self.values = list(values)
        if not self.values:
            self.values = [""]
        if self.value not in self.values:
            self.value = self.values[0]
        self.mb.configure(text=f" {self.value} ▾ ")

    def _open(self, _=None):
        if time.time() - getattr(self, "_closed_at", 0) < 0.15:
            return
        self._close()
        root = self.winfo_toplevel()
        self.popup = tk.Toplevel(root)
        self.popup.wm_overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(bg=BORDER_ON)

        wrap = tk.Frame(self.popup, bg=PANEL, padx=1, pady=1)
        wrap.pack(fill="both", expand=True)

        height = min(10, len(self.values))
        lb = tk.Listbox(wrap, bg=PANEL, fg=TEXT, selectbackground="#1f4a45",
                        selectforeground=ACCENT, activestyle="none",
                        font=(FONT, 9), bd=0, highlightthickness=0,
                        width=max(10, self.mb.cget("width")), height=height,
                        exportselection=False)
        for v in self.values:
            lb.insert("end", v)
        if self.value in self.values:
            lb.selection_set(self.values.index(self.value))
            lb.see(self.values.index(self.value))
        lb.pack(side="left", fill="both", expand=True)

        need_sb = len(self.values) > height
        if need_sb:
            sb = DarkScrollbar(wrap, command=lb.yview, bg=PANEL)
            sb.pack(side="right", fill="y")
            lb.configure(yscrollcommand=sb.set)

        x = self.mb.winfo_rootx()
        y = self.mb.winfo_rooty() + self.mb.winfo_height()
        w = max(self.mb.winfo_width(), lb.winfo_reqwidth() + (10 if need_sb else 0))
        h = lb.winfo_reqheight()
        if y + h > root.winfo_screenheight() - 60:
            y = self.mb.winfo_rooty() - h - 2
        self.popup.wm_geometry(f"{w}x{h}+{x}+{y}")

        def pick(_=None):
            sel = lb.curselection()
            if sel:
                v = self.values[sel[0]]
                self._close()
                self._pick(v)

        lb.bind("<ButtonRelease-1>", pick)
        lb.bind("<Return>", pick)
        lb.bind("<Escape>", lambda e: self._close())
        lb.focus_set()

        self._outside = lambda e: None if (self.popup and str(e.widget).startswith(str(self.popup))) else self._close()
        root.bind_all("<ButtonPress-1>", self._outside, add="+")

    def _close(self):
        self._closed_at = time.time()
        if self._outside:
            try:
                self.winfo_toplevel().unbind_all("<ButtonPress-1>")
            except tk.TclError:
                pass
            self._outside = None
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def _pick(self, v):
        self.value = v
        self.mb.configure(text=f" {v} ▾ ")
        if self.on_change:
            self.on_change(v)

    def get(self):
        return self.value

    def set(self, v):
        self.value = v
        self.mb.configure(text=f" {v} ▾ ")


class DarkScrollbar(tk.Canvas):
    """深色细滚动条：圆角滑块，悬停/拖动时高亮"""

    def __init__(self, parent, command, width=9, bg=BG):
        super().__init__(parent, width=width, bg=bg, highlightthickness=0,
                         bd=0, cursor="hand2")
        self.command = command
        self.first, self.last = 0.0, 1.0
        self._hover = False
        self._drag_off = None
        self._drag_h = 0
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", lambda e: self._on_release())

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self._redraw()

    def _thumb(self):
        h = max(self.winfo_height(), 1)
        if self.last - self.first >= 0.999:
            return None
        top = int(self.first * h)
        bottom = int(self.last * h)
        if bottom - top < 28:
            mid = (top + bottom) // 2
            top, bottom = mid - 14, mid + 14
            if top < 0:
                top, bottom = 0, 28
            if bottom > h:
                top, bottom = h - 28, h
        return top + 1, bottom - 1

    def _on_enter(self, _):
        self._hover = True
        self._redraw()

    def _on_leave(self, _):
        self._hover = False
        self._redraw()

    def _on_press(self, e):
        th = self._thumb()
        if th and th[0] <= e.y <= th[1]:
            self._drag_off = (e.y - th[0]) / max(1, th[1] - th[0])
            self._drag_h = th[1] - th[0]
            self._redraw()
            return
        self._drag_off = None
        if th:
            self.command("scroll", 1 if e.y > th[1] else -1, "pages")

    def _on_drag(self, e):
        if self._drag_off is None:
            return
        h = max(self.winfo_height(), 1)
        top = (e.y - self._drag_off * self._drag_h) / h
        self.command("moveto", min(max(0.0, top), 1.0))

    def _on_release(self):
        self._drag_off = None
        self._redraw()

    def _redraw(self):
        self.delete("all")
        h = self.winfo_height()
        w = self.winfo_width()
        if h < 12 or w < 3:
            return
        self.create_rectangle(w // 2, 2, w // 2 + 1, h - 2, fill="#101a1e", outline="")
        th = self._thumb()
        if not th:
            return
        if self._drag_off is not None:
            color = ACCENT
        elif self._hover:
            color = "#3c6068"
        else:
            color = "#27424a"
        self._round_rect(1, th[0], w - 1, th[1], min(4, (w - 2) // 2), color)

    def _round_rect(self, x1, y1, x2, y2, r, fill):
        r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
               x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
               x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.create_polygon(pts, smooth=True, fill=fill, outline="")


class Planner:
    def __init__(self, root):
        self.root = root
        self.data = json.load(open(DATA_FILE, encoding="utf-8"))
        self.ops = self.data["operators"]
        self.bonds = {b["id"]: b for b in self.data["bonds"]}
        self.op_by_id = {o["id"]: o for o in self.ops}

        self.f_name = tkfont.Font(root=root, family=FONT, size=10, weight="bold")
        self.f_rank = tkfont.Font(root=root, family=FONT, size=9, weight="bold")
        self.f_bond = tkfont.Font(root=root, family=FONT, size=8)

        self.team = []                 # 干员 id 列表，按上场顺序
        self.tier_filter = set()       # 空 = 全部；单选
        self.bond_filter = None
        self.keyword = ""
        self.open_bonds = set()        # 已展开详情的盟约
        self.compact = False
        self.normal_geo = "1010x730"
        self._load_window_size()
        self._pool_items = {}         # 干员 id -> 卡片图元
        self._pool_order = []         # [(干员 id, y0, y1)]
        self._hover_oid = None
        self._tip_win = None
        self._tip_job = None
        self._bond_rows = {}
        self.pool_cols = 2
        self._pool_canvas_w = 0
        self._bond_canvas_w = 0
        self._pool_job = None
        self._pool_live_ts = 0.0
        self._resizing = False
        self._pending_pool = False
        self._click_op_id = None
        self._click_ts = 0.0
        self._bond_click_id = None
        self._bond_click_ts = 0.0
        self._maxed = False
        self._restore_geo = self.normal_geo
        self._drag_origin = None
        self.ball = None

        self._setup_window()
        self._build_topbar()
        self._build_main()
        self._build_resize_grip()
        self.render_pool()
        self.render_team()
        self.render_bonds()
        self._bind_keys()

    # ---------------- 窗口 ----------------
    def _setup_window(self):
        self.root.title("卫戍协议 · 小队规划器")
        self.root.configure(bg=BG)
        self.root.geometry(self.normal_geo)
        self.root.minsize(380, 480)
        self.root.overrideredirect(True)      # 去掉系统白色标题栏
        self.root.attributes("-topmost", True)
        self.root.bind("<Map>", self._on_root_map)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_window_size(self):
        """读取上次调整的窗口大小"""
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                d = json.load(f)
            w, h = int(d["w"]), int(d["h"])
        except Exception:
            return
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if w < 860 or h < 620:
            return
        self.normal_geo = f"{min(w, sw)}x{min(h, sh)}"

    def _save_window_size(self):
        try:
            if self.compact:
                geo = self.normal_geo
            elif self._maxed:
                geo = self._restore_geo
            else:
                geo = self.root.geometry()
            m = re.match(r"(\d+)x(\d+)", geo)
            if not m:
                return
            w, h = int(m.group(1)), int(m.group(2))
            if w < 860 or h < 620:
                return
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"w": w, "h": h}, f)
        except Exception:
            pass

    def _on_close(self):
        self._save_window_size()
        self.root.destroy()

    def _on_root_map(self, e):
        if e.widget is self.root:
            self.root.after(10, self._reapply_borderless)

    def _reapply_borderless(self):
        """从最小化恢复后重新隐藏系统标题栏"""
        try:
            if self.root.state() == "normal" and not self.root.overrideredirect():
                self.root.overrideredirect(True)
                self.root.attributes("-topmost", self.topmost_var.get())
        except tk.TclError:
            pass

    def minimize_window(self):
        # Windows 下无边框窗口无法直接最小化，临时恢复边框再图标化
        try:
            self.root.overrideredirect(False)
            self.root.iconify()
        except tk.TclError:
            pass

    def _work_area(self):
        try:
            import ctypes.wintypes as wt
            r = wt.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):
                return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:
            pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def toggle_max(self):
        if self._maxed:
            self.root.geometry(self._restore_geo)
            self._maxed = False
        else:
            self._restore_geo = self.root.geometry()
            x, y, w, h = self._work_area()
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self._maxed = True

    def _drag_start(self, e):
        self._drag_origin = (e.x_root, e.y_root,
                             self.root.winfo_x(), self.root.winfo_y())

    def _drag_move(self, e):
        if not self._drag_origin or self._maxed:
            return
        sx, sy, wx, wy = self._drag_origin
        self.root.geometry(f"+{wx + e.x_root - sx}+{wy + e.y_root - sy}")

    def _bind_drag(self, *widgets):
        for w in widgets:
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<Double-Button-1>", lambda e: self.toggle_max())

    def _build_resize_grip(self):
        g = tk.Canvas(self.root, width=14, height=14, bg=BG,
                      highlightthickness=0, bd=0,
                      cursor="bottom_right_corner")
        g.place(relx=1.0, rely=1.0, anchor="se")
        for d in (5, 9, 13):
            g.create_line(14 - d, 14, 14, 14 - d, fill="#2a3f46")
        g.bind("<ButtonPress-1>", self._resize_start)
        g.bind("<B1-Motion>", self._resize_drag)
        g.bind("<ButtonRelease-1>", self._resize_release)
        self.grip = g

    def _resize_start(self, e):
        self._resize_origin = (e.x_root, e.y_root,
                               self.root.winfo_width(), self.root.winfo_height())
        self._resize_last = 0.0
        self._resize_final = None
        self._resizing = True
        self._pending_pool = False
        self._pool_live_ts = 0.0

    def _resize_drag(self, e):
        if not self._resize_origin:
            return
        self._resize_final = (e.x_root, e.y_root)
        now = time.time()
        # 限制到 ~25fps，避免每个鼠标事件都触发整套重排
        if now - self._resize_last < 0.04:
            return
        self._resize_last = now
        self._apply_resize(e.x_root, e.y_root)

    def _resize_release(self, e):
        if self._resize_origin and self._resize_final:
            self._apply_resize(*self._resize_final)
        self._resize_origin = None
        self._resize_final = None
        self._resizing = False
        self._maxed = False
        if self._pending_pool:
            self._pending_pool = False
            if self._pool_job:
                try:
                    self.root.after_cancel(self._pool_job)
                except Exception:
                    pass
                self._pool_job = None
            self.root.after_idle(self.render_pool)
        self.root.after(150, self._save_window_size)

    def _apply_resize(self, xr, yr):
        sx, sy, w, h = self._resize_origin
        nw = max(860, w + xr - sx)
        nh = max(620, h + yr - sy)
        self.root.geometry(f"{nw}x{nh}")
        self._maxed = False

    def _bind_keys(self):
        self.root.bind("<Control-t>", lambda e: self.toggle_topmost())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Escape>", lambda e: self.clear_filters())
        self.root.bind_all("<MouseWheel>", self._on_wheel_global, add="+")
        self.root.bind("<ButtonPress-1>", self._defocus_search, add="+")

    def _defocus_search(self, e):
        """点击搜索框以外的地方时取消其焦点/选中状态"""
        w = e.widget
        if w is self.search_entry or str(w).startswith(str(self.search_entry)):
            return
        if self.root.focus_get() is self.search_entry:
            self.root.focus_set()

    def toggle_topmost(self):
        v = not self.topmost_var.get()
        self.topmost_var.set(v)
        self.root.attributes("-topmost", v)

    # ---------------- 顶栏 ----------------
    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=PANEL_2, height=56)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=PANEL_2)
        left.pack(side="left", padx=14)
        self.title_lbl = tk.Label(left, text="卫戍协议", bg=PANEL_2, fg=GOLD,
                                  font=(FONT, 13, "bold"))
        self.title_lbl.pack(side="left")
        self.subtitle = tk.Label(left, text=" 小队规划器", bg=PANEL_2, fg=TEXT,
                                 font=(FONT, 11))
        self.subtitle.pack(side="left")

        right = tk.Frame(bar, bg=PANEL_2)
        right.pack(side="right", padx=(12, 8))

        # 窗口控制（替代系统白色标题栏，三个按钮等宽等高）
        self.close_btn = self._winbtn(right, "close", self._on_close, danger=True)
        self.close_btn.pack(side="right")
        self.max_btn = self._winbtn(right, "max", self.toggle_max)
        self.max_btn.pack(side="right")
        self.min_btn = self._winbtn(right, "min", self.minimize_window)
        self.min_btn.pack(side="right")

        self.topmost_var = tk.BooleanVar(value=True)
        self.topmost_chk = tk.Checkbutton(
            right, text="置顶", variable=self.topmost_var,
            command=lambda: self.root.attributes("-topmost", self.topmost_var.get()),
            bg=PANEL_2, fg=TEXT, activebackground=PANEL_2,
            activeforeground=ACCENT, selectcolor="#0b2b27",
            font=(FONT, 9), bd=0, highlightthickness=0,
            cursor="hand2")
        self.topmost_chk.pack(side="right", padx=(10, 4))
        self.compact_btn = self._btn(right, "小窗", self.toggle_compact, padx=10)
        self.compact_btn.pack(side="right", padx=4)
        self.ball_btn = self._btn(right, "悬浮球", self.toggle_ball, padx=10)
        self.ball_btn.pack(side="right", padx=4)

        self._bind_drag(bar, left, self.title_lbl, self.subtitle)

        tk.Frame(self.root, bg=BORDER, height=1).pack(side="top", fill="x")

    def _btn(self, parent, text, cmd, padx=12, bg=PANEL, fg=TEXT, width=None):
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=(FONT, 9),
                     padx=padx, pady=4, cursor="hand2", width=width,
                     highlightthickness=1, highlightbackground=BORDER)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.configure(bg=CARD_HOVER, fg=ACCENT,
                                                highlightbackground=BORDER_ON))
        b.bind("<Leave>", lambda e: b.configure(bg=bg, fg=fg,
                                                highlightbackground=BORDER))
        return b

    def _winbtn(self, parent, kind, cmd, danger=False):
        """自绘窗口按钮：三个按钮等宽等高，图标统一 12px 视觉尺寸"""
        size = 28
        c = tk.Canvas(parent, width=size, height=size, bg=PANEL_2,
                      highlightthickness=0, bd=0, cursor="hand2")
        items = []
        if kind == "min":
            items.append(c.create_line(8, 14, 20, 14, fill=MUTED, width=1.6))
        elif kind == "max":
            items.append(c.create_rectangle(9, 9, 19, 19, outline=MUTED, width=1.4))
        else:
            items.append(c.create_line(9, 9, 19, 19, fill=MUTED, width=1.6))
            items.append(c.create_line(19, 9, 9, 19, fill=MUTED, width=1.6))

        def paint(bg, fg):
            c.configure(bg=bg)
            for it in items:
                if c.type(it) == "line":
                    c.itemconfigure(it, fill=fg)
                else:
                    c.itemconfigure(it, outline=fg)

        c.bind("<ButtonPress-1>", lambda e: cmd())
        c.bind("<Enter>", lambda e: paint("#a8382b" if danger else CARD_HOVER,
                                          "#ffffff" if danger else TEXT))
        c.bind("<Leave>", lambda e: paint(PANEL_2, MUTED))
        return c

    def _placeholder(self, entry, text):
        entry.insert(0, text)
        entry.configure(fg=MUTED)

        def on_focus_in(e):
            if entry.get() == text:
                entry.delete(0, "end")
                entry.configure(fg=TEXT)

        def on_focus_out(e):
            if not entry.get():
                entry.insert(0, text)
                entry.configure(fg=MUTED)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry._placeholder = text

    def _on_search(self):
        if not hasattr(self, "pool_canvas"):
            return
        val = self.search_var.get().strip()
        self.keyword = "" if val == getattr(self.search_entry, "_placeholder", "") else val
        self.render_pool()

    # ---------------- 主区域 ----------------
    def _build_main(self):
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="top", fill="both", expand=True)
        self.main.rowconfigure(0, weight=1)
        self.main.columnconfigure(0, weight=1, minsize=420)
        self.main.columnconfigure(1, weight=0, minsize=410)

        # 左：干员池
        self.pool_frame = tk.Frame(self.main, bg=BG)
        self.pool_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=8)
        self.pool_frame.rowconfigure(1, weight=1)
        self.pool_frame.columnconfigure(0, weight=1)

        head = tk.Frame(self.pool_frame, bg=BG)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(head, text="干员池", bg=BG, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(side="left", padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search())
        self.search_entry = tk.Entry(head, textvariable=self.search_var,
                                     bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                                     relief="flat", font=(FONT, 9), width=9,
                                     highlightthickness=1, highlightbackground=BORDER,
                                     highlightcolor=BORDER_ON)
        self.search_entry.pack(side="left", ipady=3, padx=(0, 6))
        self._placeholder(self.search_entry, "搜索干员")

        # 盟约筛选
        bond_names = ["全部盟约"] + [b["name"] for b in self.data["bonds"]]
        self.bond_select = DarkSelect(head, bond_names,
                                      on_change=self._on_bond_selected, width=7)
        self.bond_select.pack(side="left", padx=(0, 6))

        # 等级筛选
        self.tier_btns = {}
        for t in range(1, 7):
            b = tk.Label(head, text=RANK_NAME[t], bg=PANEL, fg=RANK_COLOR[t],
                         font=(FONT, 9, "bold"), width=2, pady=3, cursor="hand2",
                         highlightthickness=1, highlightbackground=BORDER)
            b.pack(side="left", padx=0)
            b.bind("<Button-1>", lambda e, t=t: self._toggle_tier(t))
            self.tier_btns[t] = b

        self.pool_canvas = tk.Canvas(self.pool_frame, bg=BG, width=1, height=1,
                                     highlightthickness=0, bd=0)
        self.pool_canvas.grid(row=1, column=0, sticky="nsew")
        self.pool_scroll = DarkScrollbar(self.pool_frame,
                                         command=self.pool_canvas.yview, bg=BG)
        self.pool_scroll.grid(row=1, column=1, sticky="ns", padx=(2, 0))
        self.pool_canvas.configure(yscrollcommand=self.pool_scroll.set)
        self.pool_canvas.bind("<Configure>", self._on_pool_resize)
        self.pool_canvas.bind("<Motion>", self._on_pool_motion)
        self.pool_canvas.bind("<Leave>", self._on_pool_leave)
        self.pool_canvas.bind("<ButtonPress-1>", self._on_pool_click)
        self.pool_canvas.bind("<Double-Button-1>", self._on_pool_click)

        # 右：阵容 + 盟约
        self.team_frame = tk.Frame(self.main, bg=BG)
        self.team_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=8)
        self.team_frame.columnconfigure(0, weight=1)
        self.team_frame.rowconfigure(2, weight=1)

        thead = tk.Frame(self.team_frame, bg=BG)
        thead.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(thead, text="上场阵容", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(side="left")
        self.team_count = tk.Label(thead, text="0 / 9", bg=BG, fg=ACCENT,
                                   font=(FONT, 10, "bold"))
        self.team_count.pack(side="left", padx=8)
        self.clear_btn = self._btn(thead, "清空", self.clear_team, padx=9, bg=BG)
        self.clear_btn.pack(side="left", padx=(4, 0))
        self.slots_frame = tk.Frame(self.team_frame, bg=BG)
        self.slots_frame.grid(row=1, column=0, sticky="new")
        for i in range(3):
            self.slots_frame.columnconfigure(i, weight=1, uniform="slot")
        self.team_frame.bind("<Configure>", self._on_team_resize)

        # 盟约列表（每行可展开详情，支持同时展开多个）
        self.bond_panel = tk.Frame(self.team_frame, bg=BG)
        self.bond_panel.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        self.bond_panel.rowconfigure(1, weight=1)
        self.bond_panel.columnconfigure(0, weight=1)

        bhead = tk.Frame(self.bond_panel, bg=BG)
        bhead.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Label(bhead, text="盟约", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(side="left")
        self.bond_count = tk.Label(bhead, text="", bg=BG, fg=ACCENT, font=(FONT, 9))
        self.bond_count.pack(side="left", padx=8)
        tk.Label(bhead, text="●核心 ○附加", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(side="right")

        self.bond_canvas = tk.Canvas(self.bond_panel, bg=BG, width=1, height=1,
                                     highlightthickness=0, bd=0)
        self.bond_canvas.grid(row=1, column=0, sticky="nsew")
        self.bond_scroll = DarkScrollbar(self.bond_panel,
                                         command=self.bond_canvas.yview, bg=BG)
        self.bond_scroll.grid(row=1, column=1, sticky="ns", padx=(2, 0))
        self.bond_canvas.configure(yscrollcommand=self.bond_scroll.set)
        self.bond_inner = tk.Frame(self.bond_canvas, bg=BG)
        self.bond_win = self.bond_canvas.create_window((0, 0), window=self.bond_inner, anchor="nw")
        self.bond_inner.bind("<Configure>", lambda e: self.bond_canvas.configure(
            scrollregion=self.bond_canvas.bbox("all")))
        self.bond_canvas.bind("<Configure>", self._on_bond_resize)

    def _on_team_resize(self, e):
        """让 9 个阵容格子保持正方形并铺满面板宽度（限制上限避免反过来撑宽面板）"""
        cell = min(130, max(72, (e.width - 18) // 3))
        if cell == getattr(self, "_slot_cell", None):
            return
        self._slot_cell = cell
        for w in self.slots_frame.grid_slaves():
            w.configure(width=cell, height=cell)

    def _on_pool_resize(self, e):
        if e.width == self._pool_canvas_w:
            return
        self._pool_canvas_w = e.width
        cols = max(2, min(6, (e.width - 12) // 230))
        changed = cols != self.pool_cols
        self.pool_cols = cols
        if self._resizing:
            # 拖动过程中实时跟随：列数变化立即重排，其余按约 8fps 节流重排
            now = time.time()
            if changed or now - self._pool_live_ts > 0.12:
                self._pool_live_ts = now
                self.render_pool()
            self._pending_pool = True
            return
        if self._pool_job:
            try:
                self.root.after_cancel(self._pool_job)
            except Exception:
                pass
        self._pool_job = self.root.after(20, self._rerender_pool)

    def _rerender_pool(self):
        self._pool_job = None
        self.render_pool()

    def _on_bond_resize(self, e):
        if e.width == self._bond_canvas_w:
            return
        self._bond_canvas_w = e.width
        self.bond_canvas.itemconfigure(self.bond_win, width=e.width)
        wrap = max(240, e.width - 36)
        for rec in self._bond_rows.values():
            rec["body"].configure(wraplength=wrap)

    def _on_wheel_global(self, e):
        if not e.delta:
            return
        w = self.root.winfo_containing(e.x_root, e.y_root)
        path = w
        while path is not None:
            try:
                if path.winfo_class() == "Listbox":
                    return
            except Exception:
                break
            path = getattr(path, "master", None)
        for canvas, sb in ((self.pool_canvas, self.pool_scroll),
                           (self.bond_canvas, self.bond_scroll)):
            if not canvas.winfo_exists() or canvas.winfo_width() < 2:
                continue
            hit = False
            for widget in (canvas, sb):
                if not widget.winfo_exists() or widget.winfo_width() < 2:
                    continue
                x0, y0 = widget.winfo_rootx(), widget.winfo_rooty()
                if x0 <= e.x_root <= x0 + widget.winfo_width() and \
                        y0 <= e.y_root <= y0 + widget.winfo_height():
                    hit = True
                    break
            if hit:
                self._cancel_pool_tip()
                canvas.yview_scroll(int(-e.delta / 120), "units")
                return "break"

    # ---------------- 干员池 ----------------
    def _toggle_tier(self, t):
        if t in self.tier_filter:
            self.tier_filter.clear()
        else:
            self.tier_filter = {t}
        self._paint_tier_buttons()
        self.render_pool()

    def _paint_tier_buttons(self):
        for t, b in self.tier_btns.items():
            if t in self.tier_filter:
                b.configure(bg=RANK_COLOR[t], fg="#07100f", highlightbackground=RANK_COLOR[t])
            else:
                b.configure(bg=PANEL, fg=RANK_COLOR[t], highlightbackground=BORDER)

    def _on_bond_selected(self, name):
        if name == "全部盟约":
            self.bond_filter = None
        else:
            self.bond_filter = next((b["id"] for b in self.bonds.values()
                                     if b["name"] == name), None)
        self.render_pool()

    def clear_filters(self):
        self.tier_filter.clear()
        self._paint_tier_buttons()
        self.bond_filter = None
        self.bond_select.set("全部盟约")
        self.search_var.set("")
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, getattr(self.search_entry, "_placeholder", ""))
        self.search_entry.configure(fg=MUTED)
        self.keyword = ""
        self.render_pool()

    def _filtered_ops(self):
        kw = self.keyword.lower()
        out = []
        for o in self.ops:
            if self.tier_filter and o["rank"] not in self.tier_filter:
                continue
            if self.bond_filter and self.bond_filter not in o["bonds"]:
                continue
            if kw:
                hay = o["name"].lower() + o["profession"] + " ".join(
                    self.bonds[b]["name"] for b in o["bonds"] if b in self.bonds)
                if kw not in hay:
                    continue
            out.append(o)
        out.sort(key=lambda o: (o["rank"], o["name"]))
        return out

    def render_pool(self):
        c = self.pool_canvas
        c.delete("all")
        self._pool_items = {}
        self._pool_order = []
        self._hover_oid = None
        self._cancel_pool_tip()
        ops = self._filtered_ops()
        w = self._pool_canvas_w or c.winfo_width()
        if w < 40:
            w = 560
        if not ops:
            c.create_text(w // 2, 40, text="没有符合条件的干员",
                          fill=MUTED, font=(FONT, 9))
            c.configure(scrollregion=(0, 0, w, 80))
            return
        cols = self.pool_cols
        gap = 6
        card_w = max(120.0, (w - gap * (cols + 1)) / cols)
        rows = (len(ops) + cols - 1) // cols
        for i, op in enumerate(ops):
            row, col = divmod(i, cols)
            x = gap + col * (card_w + gap)
            y = gap + row * (CARD_H + gap)
            self._draw_card(op, x, y, card_w)
        c.configure(scrollregion=(0, 0, w, gap + rows * (CARD_H + gap)))

    def _draw_card(self, op, x, y, w):
        c = self.pool_canvas
        oid = op["id"]
        on = oid in self.team
        rect = c.create_rectangle(x, y, x + w, y + CARD_H,
                                  fill=CARD_ON if on else CARD,
                                  outline=BORDER_ON if on else BORDER)
        c.create_rectangle(x + 1, y + 1, x + 5, y + CARD_H - 1,
                           fill=RANK_COLOR[op["rank"]], outline="")
        name = c.create_text(x + 11, y + 16, anchor="w",
                             text=self._fit_text(op["name"], self.f_name, w - 48),
                             fill=RANK_COLOR[op["rank"]], font=self.f_name)
        c.create_text(x + w - 9, y + 16, anchor="e", text=RANK_NAME[op["rank"]],
                      fill=RANK_COLOR[op["rank"]], font=self.f_rank)
        bond_txt = " · ".join(self.bonds[b]["name"] for b in op["bonds"] if b in self.bonds)
        bond = c.create_text(x + 11, y + 36, anchor="w",
                             text=self._fit_text(bond_txt, self.f_bond, w - 22),
                             fill=ACCENT if on else "#5f7d86", font=self.f_bond)
        self._pool_items[oid] = {"rect": rect, "name": name, "bond": bond}
        self._pool_order.append((oid, x, y, x + w, y + CARD_H))

    def _fit_text(self, text, font, maxw):
        if font.measure(text) <= maxw:
            return text
        while text and font.measure(text + "…") > maxw:
            text = text[:-1]
        return text + "…"

    def _paint_pool_card(self, oid):
        it = self._pool_items.get(oid)
        if not it:
            return
        on = oid in self.team
        hover = oid == self._hover_oid
        bg = CARD_ON if on else (CARD_HOVER if hover else CARD)
        c = self.pool_canvas
        c.itemconfigure(it["rect"], fill=bg,
                        outline=BORDER_ON if (on or hover) else BORDER)
        c.itemconfigure(it["bond"], fill=ACCENT if on else "#5f7d86")

    def _sync_cards(self):
        for oid in list(self._pool_items):
            self._paint_pool_card(oid)

    def _pool_op_at(self, x, y):
        cx = self.pool_canvas.canvasx(x)
        cy = self.pool_canvas.canvasy(y)
        for oid, x0, y0, x1, y1 in self._pool_order:
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                return self.op_by_id[oid]
        return None

    def _on_pool_click(self, e):
        op = self._pool_op_at(e.x, e.y)
        self._cancel_pool_tip()
        if op:
            self._click_op(op)

    def _on_pool_motion(self, e):
        op = self._pool_op_at(e.x, e.y)
        oid = op["id"] if op else None
        if oid != self._hover_oid:
            old = self._hover_oid
            self._hover_oid = oid
            if old:
                self._paint_pool_card(old)
            if oid:
                self._paint_pool_card(oid)
            self._schedule_pool_tip(op)
        self.pool_canvas.configure(cursor="hand2" if op else "")

    def _on_pool_leave(self, _=None):
        old = self._hover_oid
        self._hover_oid = None
        if old:
            self._paint_pool_card(old)
        self._cancel_pool_tip()

    def _schedule_pool_tip(self, op):
        self._cancel_pool_tip()
        if not op:
            return
        self._tip_job = self.root.after(420, lambda o=op: self._show_pool_tip(o))

    def _cancel_pool_tip(self):
        if self._tip_job:
            try:
                self.root.after_cancel(self._tip_job)
            except Exception:
                pass
            self._tip_job = None
        if self._tip_win:
            self._tip_win.destroy()
            self._tip_win = None

    def _show_pool_tip(self, op):
        self._tip_job = None
        x, y = self.root.winfo_pointerxy()
        win = tk.Toplevel(self.root)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-disabled", True)
        except tk.TclError:
            pass
        win.wm_geometry(f"+{x + 14}+{y + 16}")
        f = tk.Frame(win, bg=BORDER_ON, padx=1, pady=1)
        f.pack()
        tk.Label(f, text=self._op_tip(op), bg="#0d1a1d", fg=TEXT, font=(FONT, 9),
                 justify="left", wraplength=280, padx=10, pady=8).pack()
        self._tip_win = win

    def _op_tip(self, op):
        lines = [f"{op['name']}  {RANK_NAME[op['rank']]}阶 · {op['profession']}"]
        lines.append("盟约：" + "、".join(self.bonds[b]["name"] for b in op["bonds"] if b in self.bonds))
        if op.get("traitType"):
            lines.append(f"特质：{op['traitType']}")
        if op.get("trait"):
            lines.append(clean(op["trait"]))
        return "\n".join(lines)

    # ---------------- 阵容 ----------------
    def _click_op(self, op):
        """带时间防抖的点击入口：快速连点（被系统识别为双击）也只触发一次。"""
        now = time.time()
        if op["id"] == self._click_op_id and now - self._click_ts < 0.18:
            return
        self._click_op_id = op["id"]
        self._click_ts = now
        self.toggle_op(op)

    def toggle_op(self, op):
        oid = op["id"]
        if oid in self.team:
            self.team.remove(oid)
        else:
            if len(self.team) >= MAX_TEAM:
                self._flash_count()
                return
            self.team.append(oid)
        rec = self._pool_items.get(oid)
        if rec:
            self._paint_pool_card(oid)
        self.render_team()
        self.render_bonds()

    def _flash_count(self):
        self.team_count.configure(fg=WARN)
        self.root.after(600, lambda: self.team_count.configure(fg=ACCENT))

    def clear_team(self):
        if not self.team:
            return
        self.team.clear()
        self._sync_cards()
        self.render_team()
        self.render_bonds()

    def render_team(self):
        for w in self.slots_frame.winfo_children():
            w.destroy()
        self.team_count.configure(text=f"{len(self.team)} / {MAX_TEAM}")

        for idx in range(MAX_TEAM):
            r, c = divmod(idx, 3)
            size = getattr(self, "_slot_cell", 92)
            slot = tk.Frame(self.slots_frame, bg=PANEL, width=size, height=size,
                            highlightthickness=1,
                            highlightbackground=BORDER)
            slot.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            slot.grid_propagate(False)
            slot.columnconfigure(0, weight=1)

            if idx < len(self.team):
                op = self.op_by_id[self.team[idx]]
                slot.configure(bg=CARD, cursor="hand2")
                tk.Frame(slot, bg=RANK_COLOR[op["rank"]], height=3).grid(
                    row=0, column=0, sticky="ew")
                tk.Label(slot, text=op["name"], bg=CARD, fg=RANK_COLOR[op["rank"]],
                         font=(FONT, 10, "bold"), anchor="w").grid(
                    row=1, column=0, sticky="ew", padx=8, pady=(4, 0))
                tk.Label(slot, text=RANK_NAME[op["rank"]],
                         bg=CARD, fg=RANK_COLOR[op["rank"]], font=(FONT, 8),
                         anchor="w").grid(row=2, column=0, sticky="ew", padx=8)
                btxt = " · ".join(self.bonds[b]["name"] for b in op["bonds"] if b in self.bonds)
                tk.Label(slot, text=btxt, bg=CARD, fg=MUTED, font=(FONT, 8),
                         anchor="w").grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))
                for w in slot.winfo_children() + [slot]:
                    w.bind("<ButtonPress-1>", lambda e, o=op: self._click_op(o))
                    w.bind("<Double-Button-1>", lambda e, o=op: self._click_op(o))
                Tooltip(slot, lambda o=op: self._op_tip(o), wrap=280)
            else:
                tk.Label(slot, text="+", bg=PANEL, fg="#31474f",
                         font=(FONT, 16)).place(relx=0.5, rely=0.5, anchor="center")

    # ---------------- 盟约 ----------------
    def _bond_stats(self):
        stats = {}
        for bid in self.bonds:
            members = [self.op_by_id[o] for o in self.team if bid in self.op_by_id[o]["bonds"]]
            if not members:
                continue
            cnt = len(members)
            bond = self.bonds[bid]
            bonus = 0
            if bid == "maniShip":
                eff = cnt
            elif bond["type"] == "core" and "maniShip" in self.team:
                mani = sum(1 for o in self.team if "maniShip" in self.op_by_id[o]["bonds"])
                bonus = 1 if mani else 0
                eff = cnt + bonus
            else:
                eff = cnt
            if bid == "soloShip" and cnt > 1:
                active = False
            else:
                active = eff >= bond["threshold"]
            stats[bid] = {"cnt": cnt, "eff": eff, "bonus": bonus,
                          "active": active, "members": members}
        return stats

    def render_bonds(self):
        for w in self.bond_inner.winfo_children():
            w.destroy()
        self._bond_rows = {}
        stats = self._bond_stats()
        active_n = sum(1 for s in stats.values() if s["active"])
        self.bond_count.configure(text=f"{active_n} 激活")

        if not stats:
            tk.Label(self.bond_inner, text="上场干员后显示相关盟约",
                     bg=BG, fg=MUTED, font=(FONT, 9)).pack(pady=14)
            return

        order = sorted(stats.items(),
                       key=lambda kv: (not kv[1]["active"],
                                       -kv[1]["eff"] / self.bonds[kv[0]]["threshold"],
                                       self.bonds[kv[0]]["name"]))
        for bid, st in order:
            self._make_bond_row(bid, st)

    def _make_bond_row(self, bid, st):
        bond = self.bonds[bid]
        active = st["active"]
        bg = "#0f2b27" if active else "#0e181c"
        fg = ACCENT if active else "#8ba1a8"
        box = tk.Frame(self.bond_inner, bg=bg, highlightthickness=1,
                       highlightbackground="#1d4a44" if active else "#152329")
        box.pack(fill="x", pady=(0, 4))

        head = tk.Frame(box, bg=bg, cursor="hand2")
        head.pack(fill="x")
        head.columnconfigure(1, weight=1)

        dot = tk.Label(head, text="●" if bond["type"] == "core" else "○",
                       bg=bg,
                       fg=(GOLD if bond["type"] == "core" else "#5c8f88") if active
                       else ("#6d5f3f" if bond["type"] == "core" else "#3f5a59"),
                       font=(FONT, 9))
        dot.grid(row=0, column=0, padx=(7, 2), pady=5)

        name = tk.Label(head, text=bond["name"], bg=bg, fg=fg,
                        font=(FONT, 9, "bold" if active else "normal"), anchor="w")
        name.grid(row=0, column=1, sticky="ew")

        if bid == "soloShip" and st["cnt"] > 1:
            cnt_txt = f"{st['cnt']} 失效"
        elif st["bonus"]:
            cnt_txt = f"{st['cnt']}+1/{bond['threshold']}"
        else:
            cnt_txt = f"{st['cnt']}/{bond['threshold']}"
        cnt = tk.Label(head, text=cnt_txt, bg=bg, fg=ACCENT if active else "#6a8188",
                       font=(FONT, 9, "bold" if active else "normal"), padx=5)
        cnt.grid(row=0, column=2, sticky="e")

        opened = bid in self.open_bonds
        flt = tk.Label(head, text="筛选", bg=bg,
                       fg=ACCENT if self.bond_filter == bid else ("#8ba1a8" if active else "#6a8188"),
                       font=(FONT, 8), padx=5, cursor="hand2",
                       highlightthickness=1,
                       highlightbackground=BORDER_ON if self.bond_filter == bid
                       else ("#1d4a44" if active else "#152329"))
        flt.grid(row=0, column=3, padx=(0, 4))
        flt.bind("<ButtonPress-1>", lambda e, b=bid: self._quick_filter_bond(b))
        flt.bind("<Enter>", lambda e, w=flt: w.configure(fg=ACCENT,
                                                          highlightbackground=BORDER_ON))
        flt.bind("<Leave>", lambda e, w=flt, b=bid: self._paint_filter_btn(w, b))

        tri = tk.Label(head, text="▾" if opened else "▸", bg=bg,
                       fg=ACCENT if opened else "#4c666e", font=(FONT, 8))
        tri.grid(row=0, column=4, padx=(2, 8))

        body = tk.Label(box, text=self._bond_detail_text(bid, st), bg=bg,
                        fg=TEXT if active else "#a9bcc3", font=(FONT, 8),
                        justify="left", anchor="nw",
                        wraplength=max(240, self.bond_canvas.winfo_width() - 36))
        if opened:
            body.pack(fill="x", padx=10, pady=(0, 7))

        self._bond_rows[bid] = {"tri": tri, "body": body, "flt": flt,
                                "active": active}
        for w in (head, dot, name, cnt, tri, body):
            w.bind("<ButtonPress-1>", lambda e, b=bid: self._toggle_bond(b))
        Tooltip(head, lambda b=bid: self._bond_tip(b), wrap=320)

    def _bond_detail_text(self, bid, st):
        bond = self.bonds[bid]
        txt = ("〔核心盟约〕" if bond["type"] == "core" else "〔附加盟约〕") + bond["desc"]
        if bond["bonus"]:
            txt += "\n" + bond["bonus"]
        if st:
            txt += "\n成员：" + "、".join(o["name"] for o in st["members"])
        return txt

    def _bond_tip(self, bid):
        bond = self.bonds[bid]
        st = self._bond_stats().get(bid)
        txt = f"【{bond['name']}】需要 {bond['threshold']} 名\n{bond['desc']}"
        if bond["bonus"]:
            txt += f"\n\n{bond['bonus']}"
        if st:
            txt += "\n\n成员：" + "、".join(o["name"] for o in st["members"])
        return txt

    def _toggle_bond(self, bid):
        now = time.time()
        if bid == self._bond_click_id and now - self._bond_click_ts < 0.2:
            return
        self._bond_click_id = bid
        self._bond_click_ts = now
        if bid in self.open_bonds:
            self.open_bonds.discard(bid)
        else:
            self.open_bonds.add(bid)
        rec = self._bond_rows.get(bid)
        if not rec:
            return
        opened = bid in self.open_bonds
        rec["tri"].configure(text="▾" if opened else "▸",
                             fg=ACCENT if opened else "#4c666e")
        if opened:
            rec["body"].pack(fill="x", padx=10, pady=(0, 7))
        else:
            rec["body"].pack_forget()

    def _quick_filter_bond(self, bid):
        """点击盟约行的「筛选」：干员池只显示该盟约干员，再点一次取消"""
        if self.bond_filter == bid:
            self.bond_filter = None
            self.bond_select.set("全部盟约")
        else:
            self.bond_filter = bid
            self.bond_select.set(self.bonds[bid]["name"])
        self.render_pool()
        for b, rec in self._bond_rows.items():
            self._paint_filter_btn(rec["flt"], b)

    def _paint_filter_btn(self, w, bid):
        rec = self._bond_rows.get(bid, {})
        active = rec.get("active", False)
        sel = self.bond_filter == bid
        w.configure(bg="#0f2b27" if active else "#0e181c",
                    fg=ACCENT if sel else ("#8ba1a8" if active else "#6a8188"),
                    highlightbackground=BORDER_ON if sel
                    else ("#1d4a44" if active else "#152329"))

    # ---------------- 悬浮球 ----------------
    def toggle_ball(self):
        if self.ball:
            self.restore_from_ball()
        else:
            self.to_ball()

    def _ball_corner_pos(self, size):
        """按窗口所处象限，把悬浮球放到窗口对应的那个角"""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        wx, wy = self.root.winfo_x(), self.root.winfo_y()
        ww, wh = self.root.winfo_width(), self.root.winfo_height()
        if ww < 100:
            ww, wh = 1010, 730
        left = wx + ww // 2 < sw // 2
        top = wy + wh // 2 < sh // 2
        bx = wx + 12 if left else wx + ww - size - 12
        by = wy + 12 if top else wy + wh - size - 12
        bx = min(max(0, bx), sw - size)
        by = min(max(0, by), sh - size)
        return bx, by

    def to_ball(self):
        size = 64
        bx, by = self._ball_corner_pos(size)

        ball = tk.Toplevel(self.root)
        ball.wm_overrideredirect(True)
        ball.attributes("-topmost", True)
        ball.attributes("-alpha", 0.84)
        ball.configure(bg=KEY)
        ball.geometry(f"{size}x{size}+{bx}+{by}")
        try:
            ball.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass

        cv = tk.Canvas(ball, width=size, height=size, bg=KEY, highlightthickness=0)
        cv.pack()
        cv.create_oval(3, 3, size - 3, size - 3, fill="#0f2724",
                       outline=ACCENT, width=2)
        cv.create_text(size // 2, size // 2 - 5, text="卫", fill=GOLD,
                       font=(FONT, 17, "bold"))
        cv.create_text(size // 2, size - 13, text=f"{len(self.team)}/{MAX_TEAM}",
                       fill=ACCENT, font=(FONT, 7, "bold"))

        self.ball = ball
        self._ball_start = None
        self._ball_moved = False
        for w in (ball, cv):
            w.bind("<ButtonPress-1>", self._ball_press)
            w.bind("<B1-Motion>", self._ball_drag)
            w.bind("<ButtonRelease-1>", self._ball_release)
            w.bind("<Button-3>", self._ball_menu)
            w.bind("<Enter>", lambda e: ball.attributes("-alpha", 1.0))
            w.bind("<Leave>", lambda e: ball.attributes("-alpha", 0.84))
        ball.update_idletasks()
        self.root.withdraw()
        # 部分情况下窗口首次映射会被系统挪位，映射后再校正一次
        ball.after(80, lambda: ball.winfo_exists() and
                   ball.geometry(f"{size}x{size}+{bx}+{by}"))

    def _ball_press(self, e):
        self._ball_start = (e.x_root, e.y_root,
                            self.ball.winfo_x(), self.ball.winfo_y())
        self._ball_moved = False

    def _ball_drag(self, e):
        if not self._ball_start:
            return
        sx, sy, wx, wy = self._ball_start
        dx, dy = e.x_root - sx, e.y_root - sy
        if abs(dx) > 3 or abs(dy) > 3:
            self._ball_moved = True
        self.ball.geometry(f"+{wx + dx}+{wy + dy}")

    def _ball_release(self, e):
        if not self._ball_moved:
            self.restore_from_ball()

    def _ball_menu(self, e):
        m = tk.Menu(self.ball, tearoff=0, bg=PANEL, fg=TEXT,
                    activebackground="#1f4a45", activeforeground=ACCENT,
                    bd=1, relief="solid", font=(FONT, 9))
        m.add_command(label="展开窗口", command=self.restore_from_ball)
        m.add_separator()
        m.add_command(label="退出程序", command=self._on_close)
        m.tk_popup(e.x_root, e.y_root)

    def restore_from_ball(self):
        if self.ball:
            self.ball.destroy()
            self.ball = None
        self.root.deiconify()
        self.root.attributes("-topmost", self.topmost_var.get())
        self.root.lift()
        self.root.focus_force()

    # ---------------- 小窗模式 ----------------
    def toggle_compact(self):
        self.compact = not self.compact
        if self.compact:
            if not self._maxed:
                self.normal_geo = self.root.geometry()
            self.subtitle.pack_forget()
            self.compact_btn.configure(text="还原")
            self.pool_frame.grid_remove()
            self.grip.place_forget()
            self.team_frame.grid_configure(row=0, column=0, columnspan=2,
                                           padx=(6, 6), pady=(6, 6))
            self.main.columnconfigure(0, weight=1)
            self.main.columnconfigure(1, weight=0, minsize=0)
            self.main.rowconfigure(0, weight=1)
            self.main.rowconfigure(1, weight=0)
            for i in range(3):
                self.slots_frame.columnconfigure(i, weight=1, uniform="slot")
            self.root.minsize(380, 480)
            self.root.geometry("420x680")
            self._maxed = False
        else:
            self.team_frame.grid_configure(row=0, column=1, columnspan=1,
                                           padx=(5, 10), pady=8)
            self.pool_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=8)
            self.subtitle.pack(side="left")
            self.compact_btn.configure(text="小窗")
            self.grip.place(relx=1.0, rely=1.0, anchor="se")
            self.main.columnconfigure(0, weight=1, minsize=420)
            self.main.columnconfigure(1, weight=0, minsize=410)
            self.main.rowconfigure(0, weight=1)
            self.main.rowconfigure(1, weight=0)
            self.root.geometry(self.normal_geo)
        self.root.update_idletasks()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    Planner(root)
    root.mainloop()


if __name__ == "__main__":
    main()
