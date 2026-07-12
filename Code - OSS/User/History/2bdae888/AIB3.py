#!/usr/bin/env python3

import os
import sys
import math
import subprocess
import tkinter as tk

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

CACHE_MAX = 24  # Ditingkatkan sedikit untuk menampung cache BG + Thumbs sekaligus
ANIM_STEPS = 14  # 14 frame terasa lebih responsif pada monitor refresh rate tinggi
ANIM_DELAY_MS = 10

# =========================================================
# IMAGE CACHE (LRU)
# =========================================================

class LRUImageCache:
    def __init__(self, maxsize=CACHE_MAX):
        self.maxsize = maxsize
        self.store = OrderedDict()

    def get(self, key):
        if key in self.store:
            self.store.move_to_end(key)
            return self.store[key]
        return None

    def set(self, key, value):
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

        # =================================================
        # CENTER WINDOW
        # =================================================
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = (screen_w // 2) - (WIN_W // 2)
        pos_y = (screen_h // 2) - (WIN_H // 2)
        self.root.geometry(f"{WIN_W}x{WIN_H}+{pos_x}+{pos_y}")

        # =================================================
        # LOAD WALLPAPERS
        # =================================================
        try:
            self.wallpapers = sorted(
                os.path.join(WALLPAPER_DIR, f)
                for f in os.listdir(WALLPAPER_DIR)
                if f.lower().endswith(VALID_EXT)
            )
        except OSError:
            self.wallpapers = []

        if not self.wallpapers:
            print("[wallpaper_picker] Wallpaper tidak ditemukan di Pictures", file=sys.stderr)
            sys.exit(1)

        self.current_idx = self._load_active_index()
        self.cache = LRUImageCache()
        self.is_animating = False

        # =================================================
        # CANVAS
        # =================================================
        self.canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # =================================================
        # INITIALIZE POOLED CANVAS ITEMS
        # =================================================
        self.bg_item = self.canvas.create_image(X_CENTER, WIN_H // 2)
        self.left_item = self.canvas.create_image(X_LEFT, Y_CENTER)
        self.right_item = self.canvas.create_image(X_RIGHT, Y_CENTER)
        self.center_item = self.canvas.create_image(X_CENTER, Y_CENTER) # Urutan z-index: center paling atas
        
        self.border_item = self.canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=4)
        self.text_item = self.canvas.create_text(X_CENTER, 365, fill=ACCENT_COLOR, font=FONT_MAIN)
        self.hint_item = self.canvas.create_text(X_CENTER, 415, text=" ← → Navigate | Enter Select | Esc Exit ", fill=MUTED_COLOR, font=FONT_HINT)

        self.active_refs = []
        self._render()

        # =================================================
        # KEYBINDS
        # =================================================
        root.bind("<Right>", self._slide_right)
        root.bind("<Left>", self._slide_left)
        root.bind("<Return>", self._apply_wallpaper)
        root.bind("<Escape>", lambda _: root.destroy())

    def _load_active_index(self):
        try:
            with open(STATE_FILE, "r") as f:
                path = f.read().strip()
            return self.wallpapers.index(path)
        except Exception:
            return 0

    # =====================================================
    # OPTIMIZED IMAGE PROCESSING (Z-INDEX & LAZY CACHE)
    # =====================================================
    def _get_processed_img(self, path, size, mode="normal"):
        key = (path, size, mode)
        cached = self.cache.get(key)
        if cached:
            return cached

        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")
                
                if mode == "bg":
                    # Pemrosesan background dipindahkan ke sini secara Lazy-load (RAM Aman!)
                    img = img.resize((95, 46), Image.Resampling.BILINEAR)
                    img = img.filter(ImageFilter.GaussianBlur(3))
                    img = ImageEnhance.Brightness(img).enhance(0.30)
                    img = img.resize((WIN_W, WIN_H), Image.Resampling.BILINEAR)
                else:
                    img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)

                tk_img = ImageTk.PhotoImage(img)
                self.cache.set(key, tk_img)
                return tk_img
        except Exception as e:
            print(f"Error processing {path}: {e}")
            return None

    # =====================================================
    # RENDER ENGINE
    # =====================================================
    def _render(self, progress=0.0, direction=0):
        self.active_refs.clear()
        n = len(self.wallpapers)

        offset_x = SPACING * direction * progress

        # Penentuan index visual dasar statis sepanjang pergeseran animasi
        base_idx = self.current_idx
        left_idx = (base_idx - 1) % n
        right_idx = (base_idx + 1) % n

        # Index target masa depan untuk dynamic highlight text & bg swap
        target_idx = (base_idx + direction) % n if progress >= 0.5 else base_idx

        # =================================================
        # 1. LIVE BACKGROUND BLUR (DIBACA DARI CACHE LRU)
        # =================================================
        bg = self._get_processed_img(self.wallpapers[target_idx], (WIN_W, WIN_H), "bg")
        if bg:
            self.canvas.itemconfig(self.bg_item, image=bg)
            self.active_refs.append(bg)

        # =================================================
        # 2. THE IMAGES (UKURAN TETAP KONSISTEN SAAT BERGESER)
        # =================================================
        left_img = self._get_processed_img(self.wallpapers[left_idx], SIZE_SIDE, "dim")
        center_img = self._get_processed_img(self.wallpapers[base_idx], SIZE_CENTER, "normal")
        right_img = self._get_processed_img(self.wallpapers[right_idx], SIZE_SIDE, "dim")

        self.active_refs.extend([left_img, center_img, right_img])

        # Atur gambar ke item pool
        self.canvas.itemconfig(self.left_item, image=left_img)
        self.canvas.itemconfig(self.center_item, image=center_img)
        self.canvas.itemconfig(self.right_item, image=right_img)

        # Geser posisi koordinat X secara kontinu
        self.canvas.coords(self.left_item, X_LEFT - offset_x, Y_CENTER)
        self.canvas.coords(self.center_item, X_CENTER - offset_x, Y_CENTER)
        self.canvas.coords(self.right_item, X_RIGHT - offset_x, Y_CENTER)

        # =================================================
        # 3. KOTAK BORDER & OVERLAY TEXT
        # =================================================
        # Fokus border meluncur dinamis mengikuti arah perpindahan
        border_target_x = X_CENTER if progress < 0.5 else (X_CENTER - SPACING * direction)
        bx = border_target_x - offset_x
        bw, bh = SIZE_CENTER if progress < 0.5 else SIZE_CENTER # Menjaga dimensi border konsisten
        
        self.canvas.coords(self.border_item, bx - bw // 2 - 6, Y_CENTER - bh // 2 - 6, bx + bw // 2 + 6, Y_CENTER + bh // 2 + 6)
        self.canvas.itemconfig(self.text_item, text=os.path.basename(self.wallpapers[target_idx]))

    # =====================================================
    # ANIMATION ENGINE
    # =====================================================
    def _animate(self, direction, step=0):
        if step <= ANIM_STEPS:
            ratio = step / ANIM_STEPS
            progress = 0.5 * (1.0 - math.cos(ratio * math.pi))
            self._render(progress=progress, direction=direction)
            self.root.after(ANIM_DELAY_MS, lambda: self._animate(direction, step + 1))
        else:
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self._render()
            self.is_animating = False

    # =====================================================
    # EVENTS
    # =====================================================
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
            print(e)

        subprocess.Popen(
            ["awww", "img", target, "--transition-type", "grow", "--transition-pos", "center"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # root.overrideredirect(True) # Uncomment untuk borderless murni di Hyprland
    app = WallpaperCarousel(root)
    root.mainloop()