#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
import math
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
        self.active_images = [] # Mencegah Garbage Collector menghapus gambar aktif
        self.is_animating = False
        
        # Canvas utama
        self.canvas = tk.Canvas(root, bg="#1e1e2e", highlightthickness=0, width=950, height=460)
        self.canvas.pack(fill="both", expand=True)
        
        # Konfigurasi Posisi dan Dimensi Kartu (Statis agar Ringan)
        self.x_left, self.x_center, self.x_right = 160, 475, 790
        self.y_center = 180
        self.spacing = 315
        
        self.size_center = (360, 220)
        self.size_samping = (180, 110)
        
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
        cache_key = (path, size, mode)
        if cache_key in self.img_cache: 
            return self.img_cache[cache_key]
        
        try:
            with Image.open(path) as raw_img:
                img = raw_img.convert("RGB")
                if mode == "bg":
                    img = img.resize((95, 46), resample=Image.Resampling.BILINEAR)
                    img = img.filter(ImageFilter.GaussianBlur(3))
                    img = ImageEnhance.Brightness(img).enhance(0.3)
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

    def render_carousel(self, progress=0.0, direction=0):
        self.canvas.delete("all")
        self.active_images.clear()
        total = len(self.wallpapers)
        
        # Penentuan latar belakang kontainer
        bg_idx = (self.current_idx + direction) % total if progress >= 0.5 else self.current_idx
        bg_img = self.get_processed_img(self.wallpapers[bg_idx], (950, 460), mode="bg")
        if bg_img:
            self.canvas.create_image(475, 230, image=bg_img)
            self.active_images.append(bg_img)
            
        # Hitung geseran koordinat X murni
        offset_x = self.spacing * direction * progress
        
        # Siapkan daftar indeks yang akan digambar di layar berdasarkan arah transisi
        if direction == 1: # Geser Kanan (Maju)
            render_queue = [
                ((self.current_idx + 2) % total, self.x_right + self.spacing, self.size_samping, "dim"),
                ((self.current_idx - 1) % total, self.x_left, self.size_samping, "dim"),
                ((self.current_idx + 1) % total, self.x_right, self.size_center if progress >= 0.5 else self.size_samping, "normal" if progress >= 0.5 else "dim"),
                (self.current_idx, self.x_center, self.size_samping if progress >= 0.5 else self.size_center, "dim" if progress >= 0.5 else "normal")
            ]
        elif direction == -1: # Geser Kiri (Mundur)
            render_queue = [
                ((self.current_idx - 2) % total, self.x_left - self.spacing, self.size_samping, "dim"),
                ((self.current_idx + 1) % total, self.x_right, self.size_samping, "dim"),
                ((self.current_idx - 1) % total, self.x_left, self.size_center if progress >= 0.5 else self.size_samping, "normal" if progress >= 0.5 else "dim"),
                (self.current_idx, self.x_center, self.size_samping if progress >= 0.5 else self.size_center, "dim" if progress >= 0.5 else "normal")
            ]
        else: # Diam Mapan
            render_queue = [
                ((self.current_idx - 1) % total, self.x_left, self.size_samping, "dim"),
                ((self.current_idx + 1) % total, self.x_right, self.size_samping, "dim"),
                (self.current_idx, self.x_center, self.size_center, "normal")
            ]

        # Gambar aset gambar statis dari cache
        for idx, x_base, size, mode in render_queue:
            img = self.get_processed_img(self.wallpapers[idx], size, mode=mode)
            if img:
                x_now = x_base - offset_x
                self.canvas.create_image(x_now, self.y_center, image=img)
                self.active_images.append(img)
                
                # Gambar bingkai border ungu hanya pada elemen utama yang sedang aktif/dituju
                if (direction == 0 and idx == self.current_idx) or \
                   (direction != 0 and progress >= 0.5 and idx == (self.current_idx + direction) % total) or \
                   (direction != 0 and progress < 0.5 and idx == self.current_idx):
                    w, h = size
                    self.canvas.create_rectangle(x_now - w//2 - 6, self.y_center - h//2 - 6, 
                                                 x_now + w//2 + 6, self.y_center + h//2 + 6, 
                                                 outline="#bd93f9", width=4)
                
        # 3. Text Overlay
        self.canvas.create_text(475, 365, text=os.path.basename(self.wallpapers[bg_idx]), 
                                fill="#bd93f9", font=("JetBrains Mono", 13, "bold"))
        self.canvas.create_text(475, 415, text=" Navigasi: Panah Kiri/Kanan | Pilih: Enter | Keluar: Esc ", 
                                fill="#6272a4", font=("JetBrains Mono", 10))

    def animate_slide(self, direction, step=0):
        total_steps = 12 # Dipangkas ke 12 frame agar animasi melesat instan & responsif
        if step <= total_steps:
            ratio = step / total_steps
            # Efek Ease-In-Out Sinusoidal Murni
            progress = 0.5 * (1.0 - math.cos(ratio * math.pi))
            
            self.render_carousel(progress=progress, direction=direction)
            self.root.after(12, lambda: self.animate_slide(direction, step + 1))
        else:
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self.render_carousel(progress=0.0, direction=0)
            self.is_animating = False

    def geser_kanan(self, event):
        if self.is_animating: return
        self.is_animating = True
        self.animate_slide(direction=1)
        
    def geser_kiri(self, event):
        if self.is_animating: return
        self.is_animating = True
        self.animate_slide(direction=-1)
        
    def eksekusi_wallpaper(self, event):
        if self.is_animating: return
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