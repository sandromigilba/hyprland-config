#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import tkinter as tk
from tkinter import messagebox
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps

# =========================================================
# CONFIG
# =========================================================
WALLPAPER_DIR = os.path.expanduser("~/Pictures/wallpapers")
STATE_FILE = os.path.expanduser("~/.cache/awww/wallpaper")
VALID_EXT = (".png", ".jpg", ".jpeg", ".webp")

WALLPAPER_CMD = "awww" if shutil.which("awww") else "swww"

BG_COLOR = "#1e1e2e"
ACCENT_COLOR = "#bd93f9"
MUTED_COLOR = "#6272a4"
FONT_MAIN = ("JetBrains Mono", 13, "bold")
FONT_HINT = ("JetBrains Mono", 10)

WIN_W, WIN_H = 950, 460
X_LEFT, X_CENTER, X_RIGHT = 160, 475, 790
Y_CENTER = 180
SPACING = 315

SIZE_CENTER = (360, 220)
SIZE_SIDE = (180, 110)

RESAMPLE_FAST = Image.Resampling.BOX


class FastImageLoader:
    def __init__(self, max_workers=3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, path, size, mode, callback):
        self.executor.submit(self._process, path, size, mode, callback)

    def _process(self, path, size, mode, callback):
        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")
                if mode == "bg":
                    img = img.resize((80, 40), RESAMPLE_FAST).filter(ImageFilter.GaussianBlur(3))
                    img = ImageEnhance.Brightness(img).enhance(0.25)
                    img = img.resize((WIN_W, WIN_H), RESAMPLE_FAST)
                else:
                    img = ImageOps.fit(img, size, method=RESAMPLE_FAST)
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)
                callback(img)
        except Exception as e:
            print(f"[ERROR] Process error: {e}", file=sys.stderr)

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)


class WallpaperCarousel:
    def __init__(self, root):
        self.root = root
        self.root.title("Wallpaper Manager")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        pos_x = (self.root.winfo_screenwidth() - WIN_W) // 2
        pos_y = (self.root.winfo_screenheight() - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{pos_x}+{pos_y}")

        # Flag keselamatan saat aplikasi ditutup
        self.is_running = True

        # 1. BACA DAFTAR WALLPAPER & NORMALISASI PATH RIGID
        self.wallpapers = []
        if os.path.exists(WALLPAPER_DIR):
            raw_files = sorted([
                f for f in os.listdir(WALLPAPER_DIR)
                if f.lower().endswith(VALID_EXT)
            ])
            self.wallpapers = [
                os.path.abspath(os.path.realpath(os.path.join(WALLPAPER_DIR, f)))
                for f in raw_files
            ]

        if not self.wallpapers:
            self.root.withdraw()
            messagebox.showwarning("Error", f"Tidak ada gambar di: {WALLPAPER_DIR}")
            self._close_app()
            return

        self.img_cache = {}
        self.active_refs = {}  # Mencegah Garbage Collector menghapus objek PhotoImage
        self.loader = FastImageLoader()
        self.is_animating = False

        # 2. CARI INDEKS WALLPAPER YANG SEDANG AKTIF / TERAKHIR DIPASANG
        self.current_idx = self._get_active_index()

        # Canvas UI
        self.canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_item = self.canvas.create_image(X_CENTER, WIN_H // 2)
        self.left_item = self.canvas.create_image(X_LEFT, Y_CENTER)
        self.right_item = self.canvas.create_image(X_RIGHT, Y_CENTER)
        self.center_item = self.canvas.create_image(X_CENTER, Y_CENTER)
        self.border_item = self.canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=4)
        
        self.text_item = self.canvas.create_text(X_CENTER, 365, fill=ACCENT_COLOR, font=FONT_MAIN)
        self.canvas.create_text(
            X_CENTER, 415,
            text="← → / H L Navigate  |  Enter Select  |  Esc Exit",
            fill=MUTED_COLOR, font=FONT_HINT
        )

        self._render_static()
        self._load_current_views()

        # Key Bindings
        for k in ("<Right>", "l", "L", "j", "J"): root.bind(k, lambda e: self._navigate(1))
        for k in ("<Left>", "h", "H", "k", "K"): root.bind(k, lambda e: self._navigate(-1))
        root.bind("<Button-4>", lambda e: self._navigate(-1))
        root.bind("<Button-5>", lambda e: self._navigate(1))
        root.bind("<Return>", self._apply_wallpaper)
        root.bind("<Escape>", lambda e: self._close_app())
        root.protocol("WM_DELETE_WINDOW", self._close_app)

    def _get_active_index(self):
        active_target = None
        try:
            res = subprocess.run([WALLPAPER_CMD, "query"], capture_output=True, text=True, timeout=0.8)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().splitlines():
                    parts = line.split(":")
                    candidate = parts[-1].strip().strip("\"'")
                    if candidate.lower().endswith(VALID_EXT):
                        active_target = candidate
                        break
        except Exception:
            pass

        if not active_target and os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    active_target = f.read().strip()
            except Exception:
                pass

        if not active_target:
            return 0

        target_realpath = os.path.abspath(os.path.realpath(os.path.expanduser(active_target)))
        target_basename = os.path.basename(target_realpath)

        for idx, path in enumerate(self.wallpapers):
            if path == target_realpath:
                return idx

        for idx, path in enumerate(self.wallpapers):
            if os.path.basename(path) == target_basename:
                return idx

        return 0

    def _load_current_views(self):
        n = len(self.wallpapers)
        slots = [
            (self.wallpapers[self.current_idx], SIZE_CENTER, "normal", self.center_item),
            (self.wallpapers[(self.current_idx - 1) % n], SIZE_SIDE, "dim", self.left_item),
            (self.wallpapers[(self.current_idx + 1) % n], SIZE_SIDE, "dim", self.right_item),
            (self.wallpapers[self.current_idx], (WIN_W, WIN_H), "bg", self.bg_item)
        ]

        for path, size, mode, canvas_item in slots:
            key = (path, size, mode)
            if key in self.img_cache:
                self._update_canvas_item(canvas_item, self.img_cache[key])
            else:
                self.loader.submit(
                    path, size, mode,
                    lambda img, k=key, ci=canvas_item: self._apply_to_canvas(k, img, ci)
                )

    def _apply_to_canvas(self, key, pil_img, canvas_item):
        if not self.is_running:
            return

        def update():
            if not self.is_running:
                return
            tk_img = ImageTk.PhotoImage(pil_img)
            self.img_cache[key] = tk_img
            self._update_canvas_item(canvas_item, tk_img)

        try:
            self.root.after(0, update)
        except Exception:
            pass

    def _update_canvas_item(self, canvas_item, tk_img):
        self.canvas.itemconfig(canvas_item, image=tk_img)
        self.active_refs[canvas_item] = tk_img

    def _render_static(self):
        self.canvas.coords(self.left_item, X_LEFT, Y_CENTER)
        self.canvas.coords(self.center_item, X_CENTER, Y_CENTER)
        self.canvas.coords(self.right_item, X_RIGHT, Y_CENTER)

        self.canvas.coords(
            self.border_item,
            X_CENTER - SIZE_CENTER[0]//2 - 6, Y_CENTER - SIZE_CENTER[1]//2 - 6,
            X_CENTER + SIZE_CENTER[0]//2 + 6, Y_CENTER + SIZE_CENTER[1]//2 + 6
        )
        name = os.path.basename(self.wallpapers[self.current_idx])
        self.canvas.itemconfig(self.text_item, text=name[:47] + "..." if len(name) > 50 else name)

    def _navigate(self, direction):
        if self.is_animating: return
        self.is_animating = True
        self._animate(direction, 0)

    def _animate(self, direction, step):
        if not self.is_running:
            return

        steps = 5
        if step <= steps:
            offset = SPACING * direction * (step / steps)
            self.canvas.coords(self.left_item, X_LEFT - offset, Y_CENTER)
            self.canvas.coords(self.center_item, X_CENTER - offset, Y_CENTER)
            self.canvas.coords(self.right_item, X_RIGHT - offset, Y_CENTER)
            self.root.after(8, lambda: self._animate(direction, step + 1))
        else:
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self._render_static()
            self._load_current_views()
            self.is_animating = False

    def _apply_wallpaper(self, _=None):
        if self.is_animating: return
        target = self.wallpapers[self.current_idx]

        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f: f.write(target)
        except Exception:
            pass

        subprocess.Popen(
            [WALLPAPER_CMD, "img", target, "--transition-type", "grow", "--transition-pos", "center"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._close_app()

    def _close_app(self):
        """Metode pembersihan yang aman dari memory leak dan exception thread."""
        self.is_running = False
        if hasattr(self, 'loader'):
            self.loader.shutdown()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = WallpaperCarousel(root)
    if hasattr(app, "wallpapers") and app.wallpapers:
        root.mainloop()