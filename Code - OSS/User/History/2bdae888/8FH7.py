#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance, ImageFilter

# Konfigurasi Jalur
WALLPAPER_DIR = os.path.expanduser("~/Pictures")
STATE_FILE = os.path.expanduser("~/.cache/awww/wallpaper")
VALID_EXT = ('.png', '.jpg', '.jpeg', '.webp')

class WallpaperCarousel:
    def __init__(self, root):
        self.root = root
        self.root.title("Awww Wallpaper Picker")
        self.root.configure(bg="#1e1e2e")
        
        lebar, tinggi = 950, 460
        pos_x = (self.root.winfo_screenwidth() // 2) - (lebar // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (tinggi // 2)
        self.root.geometry(f"{lebar}x{tinggi}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)
        
        self.wallpapers = sorted([os.path.join(WALLPAPER_DIR, f) for f in os.listdir(WALLPAPER_DIR) 
                                  if f.lower().endswith(VALID_EXT)])
        if not self.wallpapers: 
            sys.exit(1)
            
        self.current_idx = self.load_active_index()
        self.img_cache = {}
        
        # Canvas utama sebagai container utama
        self.canvas = tk.Canvas(root, bg="#1e1e2e", highlightthickness=0, width=950, height=460)
        self.canvas.pack(fill="both", expand=True)
        
        # Layout UI
        self.render_carousel()
        
        self.root.bind("<Right>", self.geser_kanan)
        self.root.bind("<Left>", self.geser_kiri)
        self.root.bind("<Return>", self.eksekusi_wallpaper)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def load_active_index(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                path = f.read().strip()
                return self.wallpapers.index(path) if path in self.wallpapers else 0
        return 0
        
    def get_processed_img(self, path, size, mode="normal"):
        """Mode: 'normal' (thumbnail), 'dim' (sampingan), 'bg' (downsampled blur)"""
        cache_key = (path, size, mode)
        if cache_key in self.img_cache: 
            return self.img_cache[cache_key]
        
        try:
            # Gunakan penanganan context manager agar file handle langsung ditutup setelah dibaca
            with Image.open(path) as raw_img:
                img = raw_img.convert("RGB")
                
                if mode == "bg":
                    # TRIK UTAMA: Perkecil ke resolusi mikro (10%) untuk kalkulasi instan
                    img = img.resize((95, 46), resample=Image.Resampling.BILINEAR)
                    img = img.filter(ImageFilter.GaussianBlur(3)) # Radius kecil karena gambar sudah kecil
                    img = ImageEnhance.Brightness(img).enhance(0.3)
                    # Kembalikan ke ukuran window asli
                    img = img.resize((950, 460), resample=Image.Resampling.BILINEAR)
                else:
                    img = img.resize(size, resample=Image.Resampling.BILINEAR)
                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)
                    
                tk_img = ImageTk.PhotoImage(img)
                self.img_cache[cache_key] = tk_img
                return tk_img
        except: 
            return None

    def render_carousel(self):
        self.canvas.delete("all")
        total = len(self.wallpapers)
        
        # Bersihkan cache berkala agar RAM tidak bengkak saat scrolling lama
        if len(self.img_cache) > 15:
            self.img_cache.clear()
            
        # 1. Render Background (Container Preview Super Ringan)
        bg_img = self.get_processed_img(self.wallpapers[self.current_idx], (950, 460), mode="bg")
        if bg_img:
            self.canvas.create_image(475, 230, image=bg_img)
        
        # 2. Render Carousel
        y_center = 180
        idx_left = (self.current_idx - 1) % total
        idx_right = (self.current_idx + 1) % total
        
        for idx, x, size, is_center in [(idx_left, 160, (220, 140), False),
                                        (idx_right, 790, (220, 140), False),
                                        (self.current_idx, 475, (420, 260), True)]:
            img = self.get_processed_img(self.wallpapers[idx], size, mode="normal" if is_center else "dim")
            if img:
                if is_center:
                    # Gambar border penanda
                    self.canvas.create_rectangle(475-210-6, y_center-130-6, 475+210+6, y_center+130+6, outline="#bd93f9", width=4)
                self.canvas.create_image(x, y_center, image=img)
        
        # 3. Text Overlay
        self.canvas.create_text(475, 360, text=os.path.basename(self.wallpapers[self.current_idx]), 
                                fill="#bd93f9", font=("JetBrains Mono", 14, "bold"))
        self.canvas.create_text(475, 410, text=" Navigasi: Panah | Pilih: Enter | Esc: Keluar ", 
                                fill="#6272a4", font=("JetBrains Mono", 10))

    def geser_kanan(self, event):
        self.current_idx = (self.current_idx + 1) % len(self.wallpapers)
        self.render_carousel()
        
    def geser_kiri(self, event):
        self.current_idx = (self.current_idx - 1) % len(self.wallpapers)
        self.render_carousel()
        
    def eksekusi_wallpaper(self, event):
        target = self.wallpapers[self.current_idx]
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f: 
            f.write(target)
        subprocess.run(["awww", "img", target, "--transition-type", "grow", "--transition-pos", "center"])
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WallpaperCarousel(root)
    root.mainloop()