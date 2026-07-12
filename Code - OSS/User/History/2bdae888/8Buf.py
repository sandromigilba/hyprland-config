#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance

# Konfigurasi Jalur
WALLPAPER_DIR = os.path.expanduser("~/Pictures")
STATE_FILE = os.path.expanduser("~/.cache/awww/wallpaper")
VALID_EXT = ('.png', '.jpg', '.jpeg', '.webp')

class WallpaperCarousel:
    def __init__(self, root):
        self.root = root
        self.root.title("Awww Wallpaper Picker")
        self.root.configure(bg="#1e1e2e")
        
        # Kalkulasi Posisi Tengah
        lebar, tinggi = 950, 460
        pos_x = (self.root.winfo_screenwidth() // 2) - (lebar // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (tinggi // 2)
        self.root.geometry(f"{lebar}x{tinggi}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)
        
        # Scan Wallpaper
        self.wallpapers = sorted([os.path.join(WALLPAPER_DIR, f) for f in os.listdir(WALLPAPER_DIR) 
                                  if f.lower().endswith(VALID_EXT)])
        
        if not self.wallpapers:
            sys.exit(1)
            
        # Deteksi wallpaper aktif untuk auto-select
        self.current_idx = self.load_active_index()
        self.img_cache = {}
        
        # Main Container (Trik Margin Auto)
        self.main_container = tk.Frame(root, bg="#1e1e2e")
        self.main_container.pack(expand=True)
        
        self.canvas = tk.Canvas(self.main_container, bg="#1e1e2e", highlightthickness=0, width=950, height=310)
        self.canvas.pack(pady=(0, 10))
        
        self.label_name = tk.Label(self.main_container, text="", bg="#1e1e2e", fg="#bd93f9", font=("JetBrains Mono", 12, "bold"))
        self.label_name.pack(pady=5)
        
        self.label_hint = tk.Label(self.main_container, text="   Navigasi: Panah Kiri / Kanan  |  Pilih: Enter  |  Keluar: Esc ", 
                                   bg="#282a36", fg="#6272a4", font=("JetBrains Mono", 10), pady=6, padx=12)
        self.label_hint.pack(pady=(10, 0))
        
        # Bindings
        self.root.bind("<Right>", self.geser_kanan)
        self.root.bind("<Left>", self.geser_kiri)
        self.root.bind("<Return>", self.eksekusi_wallpaper)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self.render_carousel()

    def load_active_index(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                active_path = f.read().strip()
                if active_path in self.wallpapers:
                    return self.wallpapers.index(active_path)
        return 0

    def get_thumbnail(self, path, size, redup=False):
        if (path, size, redup) in self.img_cache:
            return self.img_cache[(path, size, redup)]
        try:
            img = Image.open(path)
            img.thumbnail(size)
            if redup:
                img = ImageEnhance.Brightness(img).enhance(0.35)
            tk_img = ImageTk.PhotoImage(img)
            self.img_cache[(path, size, redup)] = tk_img
            return tk_img
        except:
            return None

    def render_carousel(self):
        self.canvas.delete("all")
        total = len(self.wallpapers)
        y_center = 155
        
        # Indeks
        idx_center = self.current_idx
        idx_left = (self.current_idx - 1) % total
        idx_right = (self.current_idx + 1) % total
        
        # Render Kiri, Kanan, Tengah
        for idx, x_pos, size, is_center in [(idx_left, 160, (220, 140), False), 
                                           (idx_right, 790, (220, 140), False),
                                           (idx_center, 475, (420, 260), True)]:
            img = self.get_thumbnail(self.wallpapers[idx], size, redup=not is_center)
            if img:
                if is_center:
                    w, h = img.width(), img.height()
                    self.canvas.create_rectangle(x_pos - w//2 - 6, y_center - h//2 - 6, x_pos + w//2 + 6, y_center + h//2 + 6, outline="#bd93f9", width=4)
                self.canvas.create_image(x_pos, y_center, image=img)
        
        self.label_name.config(text=os.path.basename(self.wallpapers[idx_center]))
        
    def geser_kanan(self, event):
        self.current_idx = (self.current_idx + 1) % len(self.wallpapers)
        self.render_carousel()
        
    def geser_kiri(self, event):
        self.current_idx = (self.current_idx - 1) % len(self.wallpapers)
        self.render_carousel()
        
    def eksekusi_wallpaper(self, event):
        target_wall = self.wallpapers[self.current_idx]
        
        # 1. Tulis State
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(target_wall)
            
        # 2. Terapkan Wallpaper
        subprocess.run(["awww", "img", target_wall, "--transition-type", "grow", 
                        "--transition-pos", "center", "--transition-fps", "75", "--transition-step", "90"])
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WallpaperCarousel(root)
    root.mainloop()