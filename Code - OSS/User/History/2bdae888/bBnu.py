#!/usr/bin/env python3
import os
import sys
import math
import subprocess
import tkinter as tk
from collections import OrderedDict
from PIL import Image, ImageTk, ImageEnhance, ImageFilter

# =========================
# KONFIGURASI JALUR
# =========================
WALLPAPER_DIR = os.path.expanduser("~/Pictures")
STATE_FILE    = os.path.expanduser("~/.cache/awww/wallpaper")
VALID_EXT     = ('.png', '.jpg', '.jpeg', '.webp')

# =========================
# KONSTANTA UI
# =========================
BG_COLOR     = "#1e1e2e"
ACCENT_COLOR = "#bd93f9"
MUTED_COLOR  = "#6272a4"
FONT_MAIN    = ("JetBrains Mono", 13, "bold")
FONT_HINT    = ("JetBrains Mono", 10)

WIN_W, WIN_H    = 950, 460
X_LEFT          = 160
X_CENTER        = 475
X_RIGHT         = 790
Y_CENTER        = 180
SPACING         = 315
SIZE_CENTER     = (360, 220)
SIZE_SIDE       = (180, 110)
CACHE_MAX       = 40          # Batas LRU cache (item)
ANIM_STEPS      = 14          # Jumlah frame animasi geser
ANIM_DELAY_MS   = 10          # Delay antar frame (ms)


class LRUImageCache:
    """
    Cache LRU sederhana untuk PhotoImage.
    Menghapus entri terlama satu per satu (bukan clear total)
    agar PhotoImage yang sedang dipakai Canvas tidak di-GC.
    """
    def __init__(self, maxsize: int = CACHE_MAX):
        self._store: OrderedDict[tuple, ImageTk.PhotoImage] = OrderedDict()
        self._max   = maxsize

    def get(self, key: tuple):
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def set(self, key: tuple, value: ImageTk.PhotoImage):
        if key in self._store:
            self._store.move_to_end(key)
        else:
            while len(self._store) >= self._max:
                self._store.popitem(last=False)
        self._store[key] = value

    def clear(self):
        self._store.clear()


class WallpaperCarousel:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Wallpaper Picker")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        # ─── OPTIMASI POSISI: PRESISI DI TENGAH MONITOR ───
        # Ambil resolusi monitor saat ini
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # Hitung koordinat jangkar tengah secara absolut
        pos_x = (screen_w // 2) - (WIN_W // 2)
        pos_y = (screen_h // 2) - (WIN_H // 2)
        
        # Kunci geometri sebelum update_idletasks berjalan
        self.root.geometry(f"{WIN_W}x{WIN_H}+{pos_x}+{pos_y}")
        self.root.update_idletasks()

        # Muat daftar wallpaper
        self.wallpapers: list[str] = sorted(
            os.path.join(WALLPAPER_DIR, f)
            for f in os.listdir(WALLPAPER_DIR)
            if f.lower().endswith(VALID_EXT)
        )
        if not self.wallpapers:
            print("[wallpaper_picker] Tidak ada wallpaper di:", WALLPAPER_DIR, file=sys.stderr)
            sys.exit(1)

        self.current_idx: int  = self._load_active_index()
        self._cache            = LRUImageCache(CACHE_MAX)
        self.active_images: list[ImageTk.PhotoImage] = []   # Mencegah GC prematur
        self.is_animating: bool = False

        # Canvas utama
        self.canvas = tk.Canvas(
            root, bg=BG_COLOR, highlightthickness=0,
            width=WIN_W, height=WIN_H
        )
        self.canvas.pack(fill="both", expand=True)

        self._render_carousel()

        # Key bindings
        self.root.bind("<Right>",  self._geser_kanan)
        self.root.bind("<Left>",   self._geser_kiri)
        self.root.bind("<Return>", self._eksekusi_wallpaper)
        self.root.bind("<Escape>", lambda _: self.root.destroy())

    # =========================================================
    # UTILITAS
    # =========================================================

    def _load_active_index(self) -> int:
        """Baca indeks wallpaper aktif dari STATE_FILE. Fallback ke 0 jika gagal."""
        try:
            with open(STATE_FILE, "r") as f:
                path = f.read().strip()
            return self.wallpapers.index(path)
        except (FileNotFoundError, OSError):
            return 0
        except ValueError:
            return 0

    def _get_processed_img(
        self,
        path: str,
        size: tuple[int, int],
        mode: str = "normal"
    ) -> ImageTk.PhotoImage | None:
        """
        Kembalikan PhotoImage dari cache, atau proses dan simpan ke cache.
        mode: 'normal' | 'dim' | 'bg'
        """
        key = (path, size, mode)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")

                if mode == "bg":
                    img = img.resize((95, 46),     resample=Image.Resampling.BILINEAR)
                    img = img.filter(ImageFilter.GaussianBlur(3))
                    img = ImageEnhance.Brightness(img).enhance(0.3)
                    img = img.resize((WIN_W, WIN_H), resample=Image.Resampling.BILINEAR)
                else:
                    img = img.resize(size, resample=Image.Resampling.BILINEAR)
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)

                tk_img = ImageTk.PhotoImage(img)
                self._cache.set(key, tk_img)
                return tk_img

        except (OSError, SyntaxError, ValueError) as exc:
            print(f"[wallpaper_picker] Gagal memproses {path}: {exc}", file=sys.stderr)
            return None

    # =========================================================
    # RENDERING
    # =========================================================

    def _build_render_queue(
        self, direction: int, progress: float
    ) -> list[tuple[int, float, tuple[int, int], str]]:
        n   = len(self.wallpapers)
        ci  = self.current_idx
        mid = progress >= 0.5       

        if direction == 1:
            return [
                ((ci + 2) % n, X_RIGHT + SPACING,   SIZE_SIDE,   "dim"),
                ((ci - 1) % n, X_LEFT  - SPACING,   SIZE_SIDE,   "dim"),   
                ((ci - 1) % n, X_LEFT,              SIZE_SIDE,   "dim"),
                (ci,           X_CENTER,
                    SIZE_SIDE   if mid else SIZE_CENTER,
                    "dim"       if mid else "normal"),
                ((ci + 1) % n, X_RIGHT,
                    SIZE_CENTER if mid else SIZE_SIDE,
                    "normal"    if mid else "dim"),
            ]
        elif direction == -1:
            return [
                ((ci - 2) % n, X_LEFT  - SPACING,   SIZE_SIDE,   "dim"),
                ((ci + 1) % n, X_RIGHT + SPACING,   SIZE_SIDE,   "dim"),   
                ((ci + 1) % n, X_RIGHT,              SIZE_SIDE,   "dim"),
                (ci,           X_CENTER,
                    SIZE_SIDE   if mid else SIZE_CENTER,
                    "dim"       if mid else "normal"),
                ((ci - 1) % n, X_LEFT,
                    SIZE_CENTER if mid else SIZE_SIDE,
                    "normal"    if mid else "dim"),
            ]
        else:
            return [
                ((ci - 1) % n, X_LEFT,   SIZE_SIDE,   "dim"),
                ((ci + 1) % n, X_RIGHT,  SIZE_SIDE,   "dim"),
                (ci,           X_CENTER, SIZE_CENTER, "normal"),
            ]

    def _active_idx(self, direction: int, progress: float) -> int:
        n = len(self.wallpapers)
        if direction != 0 and progress >= 0.5:
            return (self.current_idx + direction) % n
        return self.current_idx

    def _render_carousel(self, progress: float = 0.0, direction: int = 0):
        self.canvas.delete("all")
        self.active_images.clear()

        # Latar blur
        bg_idx = self._active_idx(direction, progress)
        bg_img = self._get_processed_img(self.wallpapers[bg_idx], (WIN_W, WIN_H), mode="bg")
        if bg_img:
            self.canvas.create_image(X_CENTER, WIN_H // 2, image=bg_img)
            self.active_images.append(bg_img)

        offset_x = SPACING * direction * progress
        queue    = self._build_render_queue(direction, progress)

        for idx, x_base, size, mode in queue:
            img = self.get_processed_img(self.wallpapers[idx], size, mode=mode)
            if img is None:
                continue

            x_now = x_base - offset_x
            self.canvas.create_image(x_now, Y_CENTER, image=img)
            self.active_images.append(img)

            if idx == bg_idx:
                w, h = size
                self.canvas.create_rectangle(
                    x_now - w // 2 - 6, Y_CENTER - h // 2 - 6,
                    x_now + w // 2 + 6, Y_CENTER + h // 2 + 6,
                    outline=ACCENT_COLOR, width=4
                )

        # Label nama file & hint navigasi
        name_text = os.path.basename(self.wallpapers[bg_idx])
        self.canvas.create_text(X_CENTER, 365, text=name_text,
                                fill=ACCENT_COLOR, font=FONT_MAIN)
        self.canvas.create_text(X_CENTER, 415,
                                text=" Navigasi: ← → | Pilih: Enter | Keluar: Esc ",
                                fill=MUTED_COLOR, font=FONT_HINT)

    # =========================================================
    # ANIMASI
    # =========================================================

    def _animate_slide(self, direction: int, step: int = 0):
        if step <= ANIM_STEPS:
            ratio    = step / ANIM_STEPS
            progress = 0.5 * (1.0 - math.cos(ratio * math.pi))   
            self._render_carousel(progress=progress, direction=direction)
            self.root.after(ANIM_DELAY_MS, lambda: self._animate_slide(direction, step + 1))
        else:
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self._render_carousel()
            self.is_animating = False

    # =========================================================
    # EVENT HANDLERS
    # =========================================================

    def _geser_kanan(self, _event=None):
        if self.is_animating:
            return
        self.is_animating = True
        self._animate_slide(direction=1)

    def _geser_kiri(self, _event=None):
        if self.is_animating:
            return
        self.is_animating = True
        self._animate_slide(direction=-1)

    def _eksekusi_wallpaper(self, _event=None):
        if self.is_animating:
            return
        target = self.wallpapers[self.current_idx]

        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                f.write(target)
        except OSError as exc:
            print(f"[wallpaper_picker] Gagal menyimpan state: {exc}", file=sys.stderr)

        subprocess.Popen(
            ["awww", "img", target,
             "--transition-type", "grow",
             "--transition-pos",  "center"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app  = WallpaperCarousel(root)
    
    # TIPS HYPRLAND: Jika kamu ingin jendela picker ini melayang murni tanpa titlebar bawaan OS
    # Silakan hapus tanda komentar '#' pada baris di bawah ini:
    # root.overrideredirect(True)
    
    root.mainloop()