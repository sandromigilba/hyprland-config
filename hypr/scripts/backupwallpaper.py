#!/usr/bin/env python3

import os
import sys
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
WALLPAPER_DIR = os.path.expanduser("~/Pictures/wallpapers")
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

MAX_CACHE = 64
THREAD_WORKERS = 4

# =========================================================
# THREADED IMAGE PROCESSOR
# =========================================================
class ThreadedImageLoader:
    def __init__(self, max_workers=THREAD_WORKERS):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, path, size, mode, session_id, callback):
        # Jalankan pekerjaan manipulasi PIL di thread terpisah
        self.executor.submit(self._process_image, path, size, mode, session_id, callback)

    def _process_image(self, path, size, mode, session_id, callback):
        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")
                
                if mode == "bg":
                    # Downsample mikro + fast blur untuk latar belakang super ringan
                    thumb = img.resize((120, 60), Image.Resampling.BILINEAR)
                    thumb = thumb.filter(ImageFilter.GaussianBlur(4))
                    img = ImageEnhance.Brightness(thumb).enhance(0.25)
                    img = img.resize((WIN_W, WIN_H), Image.Resampling.BILINEAR)
                else:
                    img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)
                
                callback(img, session_id)
        except Exception as e:
            print(f"[ERROR] Processing failed for {path}: {e}", file=sys.stderr)

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
        self.root.title("Wallpaper Manager")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = (screen_w // 2) - (WIN_W // 2)
        pos_y = (screen_h // 2) - (WIN_H // 2)
        self.root.geometry(f"{WIN_W}x{WIN_H}+{pos_x}+{pos_y}")

        # 1. BACA SELURUH WALLPAPER DENGAN NORMALISASI PATH RIGID
        try:
            raw_files = sorted([
                f for f in os.listdir(WALLPAPER_DIR)
                if f.lower().endswith(VALID_EXT)
            ])
            self.wallpapers = [
                os.path.abspath(os.path.realpath(os.path.join(WALLPAPER_DIR, f)))
                for f in raw_files
            ]
        except OSError:
            self.wallpapers = []

        if not self.wallpapers:
            print("[ERROR] No wallpapers found in Pictures/wallpapers", file=sys.stderr)
            sys.exit(1)

        # 2. CARI INDEKS WALLPAPER AKTIF SAAT INI
        self.current_idx = self._load_active_index()
        
        self.cache = LRUCache()
        self.loader = ThreadedImageLoader()
        self.is_animating = False
        self.session_id = 0

        self.canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_item = self.canvas.create_image(X_CENTER, WIN_H // 2)
        self.left_item = self.canvas.create_image(X_LEFT, Y_CENTER)
        self.right_item = self.canvas.create_image(X_RIGHT, Y_CENTER)
        self.center_item = self.canvas.create_image(X_CENTER, Y_CENTER)
        
        self.border_item = self.canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=4)
        self.text_item = self.canvas.create_text(X_CENTER, 365, fill=ACCENT_COLOR, font=FONT_MAIN)
        self.hint_item = self.canvas.create_text(X_CENTER, 415, text="← → Navigate | Enter Select | Esc Exit", fill=MUTED_COLOR, font=FONT_HINT)

        self.active_refs = {}

        self._render_static()
        self._prefetch_surroundings()

        root.bind("<Right>", self._slide_right)
        root.bind("<Left>", self._slide_left)
        root.bind("<Return>", self._apply_wallpaper)
        root.bind("<Escape>", lambda e: self._on_close())
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_active_index(self):
        """Mencari indeks wallpaper aktif dengan pencocokan Multi-Stage (Path & Basename)."""
        active_target = None

        # Tahap 1: Coba ambil path dari daemon awww
        try:
            result = subprocess.run(
                ["awww", "query"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    for token in line.split():
                        cleaned_token = token.strip("\"'")
                        if cleaned_token.lower().endswith(VALID_EXT):
                            active_target = cleaned_token
                            break
                    if active_target:
                        break
        except Exception:
            pass

        # Tahap 2: Fallback ke STATE_FILE jika awww query tidak memberikan hasil
        if not active_target and os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    active_target = f.read().strip()
            except Exception:
                pass

        if not active_target:
            return 0

        # Normalisasi target yang ditemukan
        target_realpath = os.path.abspath(os.path.realpath(os.path.expanduser(active_target)))
        target_basename = os.path.basename(target_realpath)

        # Tahap 3A: Pencocokan Path Asli (Exact Realpath Match)
        for idx, path in enumerate(self.wallpapers):
            if path == target_realpath:
                return idx

        # Tahap 3B: Pencocokan Nama File Saja (Basename Fallback Match)
        # Sangat berguna jika file baru masuk / path folder menggunakan alias
        for idx, path in enumerate(self.wallpapers):
            if os.path.basename(path) == target_basename:
                return idx

        return 0

    # =====================================================
    # LAZY LOADING & RENDER ENGINE
    # =====================================================
    def _prefetch_surroundings(self):
        """Memuat gambar slot Tengah, Kiri, Kanan, dan Background."""
        self.session_id += 1
        n = len(self.wallpapers)
        c_idx = self.current_idx

        slots = [
            (self.wallpapers[c_idx], SIZE_CENTER, "normal", self.center_item),
            (self.wallpapers[(c_idx - 1) % n], SIZE_SIDE, "dim", self.left_item),
            (self.wallpapers[(c_idx + 1) % n], SIZE_SIDE, "dim", self.right_item),
            (self.wallpapers[c_idx], (WIN_W, WIN_H), "bg", self.bg_item)
        ]

        for path, size, mode, canvas_item in slots:
            self._request_image(path, size, mode, canvas_item, self.session_id)

    def _request_image(self, path, size, mode, canvas_item, session_id):
        key = (path, size, mode)
        cached_img = self.cache.get(key)
        
        if cached_img:
            self._set_canvas_image(canvas_item, cached_img)
            return

        def on_load(pil_img, sid):
            # Abaikan jika session sudah kadaluarsa (user sudah geser lagi)
            if sid != self.session_id:
                return
            self.root.after(0, lambda: self._safe_ui_update(key, pil_img, canvas_item, sid))

        self.loader.submit(path, size, mode, session_id, on_load)

    def _safe_ui_update(self, key, pil_img, canvas_item, session_id):
        if session_id != self.session_id:
            return
        try:
            if pil_img:
                tk_img = ImageTk.PhotoImage(pil_img)
                self.cache.set(key, tk_img)
                self._set_canvas_image(canvas_item, tk_img)
        except Exception:
            pass

    def _set_canvas_image(self, canvas_item, tk_img):
        self.canvas.itemconfig(canvas_item, image=tk_img)
        self.active_refs[canvas_item] = tk_img

    def _render_static(self):
        """Reset posisi koordinat canvas ke posisi awal."""
        self.canvas.coords(self.left_item, X_LEFT, Y_CENTER)
        self.canvas.coords(self.center_item, X_CENTER, Y_CENTER)
        self.canvas.coords(self.right_item, X_RIGHT, Y_CENTER)

        self.canvas.coords(
            self.border_item, 
            X_CENTER - SIZE_CENTER[0]//2 - 6, Y_CENTER - SIZE_CENTER[1]//2 - 6,
            X_CENTER + SIZE_CENTER[0]//2 + 6, Y_CENTER + SIZE_CENTER[1]//2 + 6
        )
        
        filename = os.path.basename(self.wallpapers[self.current_idx])
        if len(filename) > 50:
            filename = filename[:47] + "..."

        self.canvas.itemconfig(self.text_item, text=filename)

    # =====================================================
    # ANIMATION ENGINE (EASE-OUT CUBIC)
    # =====================================================
    def _animate(self, direction, step=0):
        ANIM_STEPS = 8   # Langkah lebih sedikit untuk rasa lebih responsif
        ANIM_DELAY = 10  # Delay interval (ms)
        
        if step <= ANIM_STEPS:
            t = step / ANIM_STEPS
            progress = 1 - (1 - t) ** 3  # Cubic Ease-Out
            
            offset_x = SPACING * direction * progress
            
            self.canvas.coords(self.left_item, X_LEFT - offset_x, Y_CENTER)
            self.canvas.coords(self.center_item, X_CENTER - offset_x, Y_CENTER)
            self.canvas.coords(self.right_item, X_RIGHT - offset_x, Y_CENTER)
            
            self.root.after(ANIM_DELAY, lambda: self._animate(direction, step + 1))
        else:
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

        # Panggil daemon awww untuk menerapkan wallpaper
        subprocess.Popen(
            ["awww", "img", target, "--transition-type", "grow", "--transition-pos", "center"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        
        self._on_close()

    def _on_close(self):
        self.loader.shutdown()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WallpaperCarousel(root)
    root.mainloop()