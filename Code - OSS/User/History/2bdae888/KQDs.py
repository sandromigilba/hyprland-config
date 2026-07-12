#!/usr/bin/env python3

import os
import sys
import math
import threading
import subprocess
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from PIL import (
    Image,
    ImageTk,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)

# =========================================================
# PATH CONFIG
# =========================================================
WALLPAPER_DIR = os.path.expanduser("~/Pictures")
STATE_FILE = os.path.expanduser("~/.cache/awww/wallpaper")
VALID_EXT = (".png", ".jpg", ".jpeg", ".webp")

# =========================================================
# UI CONFIG
# =========================================================
BG_COLOR = "#1e1e2e"
ACCENT_COLOR = "#bd93f9"
MUTED_COLOR = "#6272a4"

FONT_MAIN = ("JetBrains Mono", 13, "bold")
FONT_HINT = ("JetBrains Mono", 10)

WIN_W = 950
WIN_H = 460

X_LEFT = 160
X_CENTER = 475
X_RIGHT = 790
Y_CENTER = 180

SPACING = 315

SIZE_CENTER = (360, 220)
SIZE_SIDE = (180, 110)

MAX_CACHE = 48
THREAD_WORKERS = 4

# =========================================================
# THREADED IMAGE PROCESSOR (PURE PIL DATA ONLY)
# =========================================================
class ThreadedImageLoader:
    def __init__(self, max_workers=THREAD_WORKERS):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending = {}

    def submit(self, path, size, mode, callback):
        key = (path, size, mode)
        if key in self.pending:
            return
        
        # Kirim pekerjaan murni manipulasi data gambar PIL
        future = self.executor.submit(self._process_image, path, size, mode)
        self.pending[key] = future
        future.add_done_callback(lambda f, k=key, cb=callback: self._handle_result(f, k, cb))

    def _process_image(self, path, size, mode):
        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")
                
                if mode == "bg":
                    # Pipeline blur mikro super ringan
                    thumb = img.resize((95, 46), Image.Resampling.BILINEAR)
                    thumb = thumb.filter(ImageFilter.GaussianBlur(3))
                    img = ImageEnhance.Brightness(thumb).enhance(0.3)
                    img = img.resize((WIN_W, WIN_H), Image.Resampling.BILINEAR)
                else:
                    img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)
                return img # Kembalikan PIL.Image murni, bukan PhotoImage
        except Exception as e:
            print(f"[ERROR] Processing failed for {path}: {e}", file=sys.stderr)
            return None

    def _handle_result(self, future, key, callback):
        try:
            result = future.result()
            if key in self.pending:
                del self.pending[key]
            if result:
                callback(result)
        except Exception:
            pass

    def shutdown(self):
        self.executor.shutdown(wait=False)

# =========================================================
# LRU CACHE
# =========================================================
class LRUCache:
    def __init__(self, maxsize=MAX_CACHE):
        self.maxsize = maxsize
        self.store = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.store:
                self.store.move_to_end(key)
                return self.store[key]
        return None

    def set(self, key, value):
        with self.lock:
            if key in self.store:
                self.store.move_to_end(key)
            else:
                while len(self.store) >= self.maxsize:
                    self.store.popitem(last=False)
            self.store[key] = value

# =========================================================
# MAIN APP
# =========================================================
class WallpaperCarousel:
    def __init__(self, root):
        self.root = root
        self.root.title("Wallpaper Picker")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = (screen_w // 2) - (WIN_W // 2)
        pos_y = (screen_h // 2) - (WIN_H // 2)
        self.root.geometry(f"{WIN_W}x{WIN_H}+{pos_x}+{pos_y}")

        try:
            self.wallpapers = sorted([
                os.path.join(WALLPAPER_DIR, f)
                for f in os.listdir(WALLPAPER_DIR)
                if f.lower().endswith(VALID_EXT)
            ])
        except OSError:
            self.wallpapers = []

        if not self.wallpapers:
            print("[ERROR] No wallpapers found in Pictures", file=sys.stderr)
            sys.exit(1)

        self.current_idx = self._load_active_index()
        self.cache = LRUCache()
        self.loader = ThreadedImageLoader()
        self.is_animating = False

        self.canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Inisialisasi Pool Jendela ID Canvas
        self.bg_item = self.canvas.create_image(X_CENTER, WIN_H // 2)
        self.left_item = self.canvas.create_image(X_LEFT, Y_CENTER)
        self.right_item = self.canvas.create_image(X_RIGHT, Y_CENTER)
        self.center_item = self.canvas.create_image(X_CENTER, Y_CENTER)
        
        self.border_item = self.canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=4)
        self.text_item = self.canvas.create_text(X_CENTER, 365, fill=ACCENT_COLOR, font=FONT_MAIN)
        self.hint_item = self.canvas.create_text(X_CENTER, 415, text="← → Navigate | Enter Select | Esc Exit", fill=MUTED_COLOR, font=FONT_HINT)

        # Pengunci Referensi Memori (Anti-GC)
        self.active_refs = []

        # Tampilkan Awal
        self._render_static()
        self._prefetch_surroundings()

        root.bind("<Right>", self._slide_right)
        root.bind("<Left>", self._slide_left)
        root.bind("<Return>", self._apply_wallpaper)
        root.bind("<Escape>", lambda e: root.destroy())
        root.protocol("WM_DELETE_WINDOW", lambda: (self.loader.shutdown(), root.destroy()))

    def _load_active_index(self):
        try:
            with open(STATE_FILE, "r") as f:
                path = f.read().strip()
            return self.wallpapers.index(path)
        except (OSError, ValueError):
            return 0

    # =====================================================
    # LAZY LOADING & ENGINE CACHE
    # =====================================================
    def _prefetch_surroundings(self):
        """Memuat 3 gambar aktif + 1 background secara cerdas"""
        n = len(self.wallpapers)
        c_idx = self.current_idx

        # Gunakan pemetaan slot penugasan yang kaku (Anti-Tertukar)
        slots = [
            (self.wallpapers[c_idx], SIZE_CENTER, "normal", self.center_item),
            (self.wallpapers[(c_idx - 1) % n], SIZE_SIDE, "dim", self.left_item),
            (self.wallpapers[(c_idx + 1) % n], SIZE_SIDE, "dim", self.right_item),
            (self.wallpapers[c_idx], (WIN_W, WIN_H), "bg", self.bg_item)
        ]

        for path, size, mode, canvas_item in slots:
            self._request_image(path, size, mode, canvas_item)

    def _request_image(self, path, size, mode, canvas_item):
        key = (path, size, mode)
        cached = self.cache.get(key)
        
        if cached:
            self.canvas.itemconfig(canvas_item, image=cached)
            return

        def on_load(pil_img, k=key, target=canvas_item):
            # Konversi PIL.Image murni ke ImageTk.PhotoImage WAJIB di Main Thread
            self.root.after(0, lambda: self._safe_ui_update(k, pil_img, target))

        self.loader.submit(path, size, mode, on_load)

    def _safe_ui_update(self, key, pil_img, canvas_item):
        try:
            if pil_img:
                tk_img = ImageTk.PhotoImage(pil_img)
                self.cache.set(key, tk_img)
                self.canvas.itemconfig(canvas_item, image=tk_img)
                
                # Jaga agar referensi tidak dibersihkan Garbage Collector
                self.active_refs.append(tk_img)
                if len(self.active_refs) > 16:
                    self.active_refs.pop(0)
        except Exception:
            pass

    def _render_static(self):
        """Reset koordinat murni ke titik awal semula"""
        self.canvas.coords(self.left_item, X_LEFT, Y_CENTER)
        self.canvas.coords(self.center_item, X_CENTER, Y_CENTER)
        self.canvas.coords(self.right_item, X_RIGHT, Y_CENTER)

        self.canvas.coords(self.border_item, 
            X_CENTER - SIZE_CENTER[0]//2 - 6, Y_CENTER - SIZE_CENTER[1]//2 - 6,
            X_CENTER + SIZE_CENTER[0]//2 + 6, Y_CENTER + SIZE_CENTER[1]//2 + 6
        )
        
        filename = os.path.basename(self.wallpapers[self.current_idx])
        self.canvas.itemconfig(self.text_item, text=filename)

    # =====================================================
    # ANIMATION ENGINE (EASE-OUT CUBIC)
    # =====================================================
    def _animate(self, direction, step=0):
        ANIM_STEPS = 12
        ANIM_DELAY = 12
        
        if step <= ANIM_STEPS:
            t = step / ANIM_STEPS
            progress = 1 - (1 - t) ** 3  # Deceleration Ease-Out
            
            offset_x = SPACING * direction * progress
            border_x = X_CENTER - offset_x if progress < 0.5 else (X_CENTER - SPACING * direction) - offset_x + (SPACING * direction * (progress - 0.5) * 2)
            
            # Geser koordinat murni objek penampung
            self.canvas.coords(self.left_item, X_LEFT - offset_x, Y_CENTER)
            self.canvas.coords(self.center_item, X_CENTER - offset_x, Y_CENTER)
            self.canvas.coords(self.right_item, X_RIGHT - offset_x, Y_CENTER)
            
            self.canvas.coords(self.border_item,
                border_x - SIZE_CENTER[0]//2 - 6, Y_CENTER - SIZE_CENTER[1]//2 - 6,
                border_x + SIZE_CENTER[0]//2 + 6, Y_CENTER + SIZE_CENTER[1]//2 + 6
            )
            
            self.root.after(ANIM_DELAY, lambda: self._animate(direction, step + 1))
        else:
            # Selesai animasi: mutasi indeks, reset koordinat awal, lalu muat gambar baru
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self._render_static()
            self._prefetch_surroundings()
            self.is_animating = False

    def _slide_right(self, _=None):
        if self.is_animating: return
        self.is_animating = True
        self._animate(1)

    def _slide_left(self, _=None):
        if self.is_animating: return
        self.is_animating = True
        self._animate(-1)

    def _apply_wallpaper(self, _=None):
        if self.is_animating: return
        target = self.wallpapers[self.current_idx]

        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                f.write(target)
        except Exception as e:
            print(f"[ERROR] Saving state: {e}")

        subprocess.Popen(
            ["awww", "img", target, "--transition-type", "grow", "--transition-pos", "center"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        
        self.loader.shutdown()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # root.overrideredirect(True) # Pasang borderless untuk Hyprland jika siap
    app = WallpaperCarousel(root)
    root.mainloop()