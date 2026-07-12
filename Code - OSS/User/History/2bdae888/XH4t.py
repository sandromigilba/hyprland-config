#!/usr/bin/env python3

import os
import sys
import math
import threading
import queue
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

MAX_CACHE = 32
THREAD_WORKERS = 4

# =========================================================
# THREADED IMAGE PROCESSOR
# =========================================================

class ThreadedImageLoader:
    def __init__(self, max_workers=THREAD_WORKERS):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending = {}

    def submit(self, path, size, mode, callback):
        key = (path, size, mode)
        if key in self.pending:
            return
        
        future = self.executor.submit(self._process_image, path, size, mode)
        self.pending[key] = future
        future.add_done_callback(lambda f, k=key, cb=callback: self._handle_result(f, k, cb))

    def _process_image(self, path, size, mode):
        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")
                
                if mode == "bg":
                    # Optimized blur pipeline
                    thumb = img.resize((128, 64), Image.Resampling.BILINEAR)
                    thumb = thumb.filter(ImageFilter.GaussianBlur(2))
                    img = ImageEnhance.Brightness(thumb).enhance(0.25)
                    img = img.resize((WIN_W, WIN_H), Image.Resampling.BILINEAR)
                else:
                    img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)

                return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"[ERROR] Processing failed for {path}: {e}")
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
# LRU CACHE (THREAD-SAFE-ish)
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

        # =================================================
        # CANVAS SETUP
        # =================================================
        self.canvas = tk.Canvas(
            root, width=WIN_W, height=WIN_H, 
            bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # =================================================
        # CANVAS ITEMS (Pre-created)
        # =================================================
        self.bg_item = self.canvas.create_image(X_CENTER, WIN_H // 2)
        self.left_item = self.canvas.create_image(X_LEFT, Y_CENTER)
        self.right_item = self.canvas.create_image(X_RIGHT, Y_CENTER)
        self.center_item = self.canvas.create_image(X_CENTER, Y_CENTER)
        
        self.border_item = self.canvas.create_rectangle(
            0, 0, 0, 0, 
            outline=ACCENT_COLOR, width=4
        )
        self.text_item = self.canvas.create_text(
            X_CENTER, 365, 
            fill=ACCENT_COLOR, font=FONT_MAIN
        )
        self.hint_item = self.canvas.create_text(
            X_CENTER, 415, 
            text="← → Navigate | Enter Select | Esc Exit", 
            fill=MUTED_COLOR, font=FONT_HINT
        )

        # Placeholders for loaded images
        self._images = {"left": None, "center": None, "right": None, "bg": None}

        # =================================================
        # STARTUP PRE-FETCH
        # =================================================
        self._prefetch_surroundings()
        
        # Render initial state
        self._render_static()
        self.root.update_idletasks()

        # =================================================
        # KEYBINDS
        # =================================================
        root.bind("<Right>", self._slide_right)
        root.bind("<Left>", self._slide_left)
        root.bind("<Return>", self._apply_wallpaper)
        root.bind("<Escape>", lambda e: root.destroy())

        # Cleanup handler
        root.protocol("WM_DELETE_WINDOW", lambda: (self.loader.shutdown(), root.destroy()))

    def _load_active_index(self):
        try:
            with open(STATE_FILE, "r") as f:
                path = f.read().strip()
            return self.wallpapers.index(path)
        except (OSError, ValueError):
            return 0

    # =====================================================
    # PREFETCH LOGIC
    # =====================================================
    def _prefetch_surroundings(self):
        n = len(self.wallpapers)
        indices = [
            (self.current_idx, SIZE_CENTER, "normal"),
            ((self.current_idx - 1) % n, SIZE_SIDE, "dim"),
            ((self.current_idx + 1) % n, SIZE_SIDE, "dim"),
            (self.current_idx, (WIN_W, WIN_H), "bg"),
        ]

        for idx, size, mode in indices:
            self._request_image(self.wallpapers[idx], size, mode)

    def _request_image(self, path, size, mode):
        key = (path, size, mode)
        
        # Check cache first
        cached = self.cache.get(key)
        if cached:
            self._on_image_loaded(key, cached, mode)
            return

        # Callback wrapper
        def on_load(img, k=key, m=mode):
            if img:
                self.cache.set(k, img)
                self._on_image_loaded(k, img, m)

        self.loader.submit(path, size, mode, on_load)

    def _on_image_loaded(self, key, img, mode):
        # Safely update UI in main thread
        def update():
            try:
                path, size, mode = key
                
                if mode == "bg":
                    self._images["bg"] = img
                    self.canvas.itemconfig(self.bg_item, image=img)
                elif mode == "normal":
                    self._images["center"] = img
                    self.canvas.itemconfig(self.center_item, image=img)
                elif mode == "dim":
                    # Determine if left or right based on center image
                    center_key = (self.wallpapers[self.current_idx], SIZE_CENTER, "normal")
                    if key[0] == self.wallpapers[(self.current_idx - 1) % len(self.wallpapers)]:
                        self._images["left"] = img
                        self.canvas.itemconfig(self.left_item, image=img)
                    else:
                        self._images["right"] = img
                        self.canvas.itemconfig(self.right_item, image=img)
            except Exception:
                pass

        self.root.after(0, update)

    # =====================================================
    # STATIC RENDER (Initial Display)
    # =====================================================
    def _render_static(self):
        n = len(self.wallpapers)
        c_idx = self.current_idx
        l_idx = (c_idx - 1) % n
        r_idx = (c_idx + 1) % n

        self.canvas.coords(self.border_item, 
            X_CENTER - SIZE_CENTER[0]//2 - 6, 
            Y_CENTER - SIZE_CENTER[1]//2 - 6,
            X_CENTER + SIZE_CENTER[0]//2 + 6, 
            Y_CENTER + SIZE_CENTER[1]//2 + 6
        )
        
        filename = os.path.basename(self.wallpapers[c_idx])
        self.canvas.itemconfig(self.text_item, text=filename)

    # =====================================================
    # ANIMATION ENGINE
    # =====================================================
    def _animate(self, direction, step=0):
        ANIM_STEPS = 14
        ANIM_DELAY = 10
        
        if step <= ANIM_STEPS:
            # Ease-out cubic math for smooth deceleration
            t = step / ANIM_STEPS
            progress = 1 - (1 - t) ** 3
            
            # Interpolate offset
            offset_x = SPACING * direction * progress
            
            # Border position logic
            if progress < 0.5:
                # Border stays with center initially
                border_x = X_CENTER - offset_x
            else:
                # Border transitions to target position
                border_x = (X_CENTER - SPACING * direction) - offset_x + (SPACING * direction * (progress - 0.5) * 2)
            
            # Update positions
            self.canvas.coords(self.left_item, X_LEFT - offset_x, Y_CENTER)
            self.canvas.coords(self.center_item, X_CENTER - offset_x, Y_CENTER)
            self.canvas.coords(self.right_item, X_RIGHT - offset_x, Y_CENTER)
            
            # Update border
            bx = border_x
            by = Y_CENTER
            self.canvas.coords(self.border_item,
                bx - SIZE_CENTER[0]//2 - 6,
                by - SIZE_CENTER[1]//2 - 6,
                bx + SIZE_CENTER[0]//2 + 6,
                by + SIZE_CENTER[1]//2 + 6
            )
            
            self.root.after(ANIM_DELAY, lambda: self._animate(direction, step + 1))
        else:
            # Animation complete - update index and prefetch new surroundings
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self._prefetch_surroundings()
            self._render_static()
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

        # Save state
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                f.write(target)
        except Exception as e:
            print(f"[ERROR] Saving state: {e}")

        # Apply wallpaper
        subprocess.Popen(
            ["awww", "img", target, "--transition-type", "grow", "--transition-pos", "center"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        
        # Exit gracefully
        self.loader.shutdown()
        self.root.destroy()

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    root = tk.Tk()
    # root.overrideredirect(True) # Uncomment for borderless on Hyprland
    app = WallpaperCarousel(root)
    root.mainloop()