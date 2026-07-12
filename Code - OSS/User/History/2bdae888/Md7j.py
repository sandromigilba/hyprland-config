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
        self.is_animating = False
        
        # Canvas utama
        self.canvas = tk.Canvas(root, bg="#1e1e2e", highlightthickness=0, width=950, height=460)
        self.canvas.pack(fill="both", expand=True)
        
        # Posisi jangkar statis
        self.x_left, self.x_center, self.x_right = 160, 475, 790
        self.y_center = 180
        
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
        """
        progress: nilai float dari 0.0 sampai 1.0 sepanjang durasi transisi
        direction: -1 jika bergeser ke kiri (panah kiri), 1 jika bergeser ke kanan (panah kanan)
        """
        self.canvas.delete("all")
        total = len(self.wallpapers)
        
        # 1. Kalkulasi interpolasi indeks untuk penentuan background container
        # Background berganti mulus di pertengahan jalan slide
        if progress < 0.5:
            bg_idx = self.current_idx
        else:
            bg_idx = (self.current_idx + direction) % total
            
        bg_img = self.get_processed_img(self.wallpapers[bg_idx], (950, 460), mode="bg")
        if bg_img:
            self.canvas.create_image(475, 230, image=bg_img)
            
        # Definisikan ukuran target
        w_c, h_c = 360, 220  # Ukuran tengah (Besar)
        w_s, h_s = 180, 110  # Ukuran samping (Kecil)
        
        # Jarak tempuh perpindahan antar pos jangkar
        step_x = 315 * direction * progress
        
        # Urutan rendering elemen dari luar ke dalam agar tumpukan (layering) visual tidak kacau
        # Kita pasang 4 indeks demi kelancaran transisi siklik melingkar
        indices = [
            (self.current_idx - 2 * direction) % total,
            (self.current_idx - direction) % total,
            (self.current_idx + direction) % total,
            (self.current_idx + 2 * direction) % total,
            self.current_idx
        ]
        
        # Hilangkan duplikasi indeks agar performa tetap maksimal
        render_queue = []
        for idx in indices:
            if idx not in render_queue:
                render_queue.insert(0, idx)
                
        # Selalu prioritaskan indeks target masa depan berada di paling atas susunan layer
        target_idx = (self.current_idx + direction) % total
        if direction != 0 and target_idx in render_queue:
            render_queue.remove(target_idx)
            render_queue.append(target_idx)
        if self.current_idx in render_queue:
            render_queue.remove(self.current_idx)
            render_queue.append(self.current_idx)

        for idx in render_queue:
            # Tentukan posisi default awal gambar sebelum ada pergeseran animasi
            if idx == self.current_idx:
                x_start, size_start, center_state = self.x_center, (w_c, h_c), "current"
            elif idx == (self.current_idx - 1) % total:
                x_start, size_start, center_state = self.x_left, (w_s, h_s), "left"
            elif idx == (self.current_idx + 1) % total:
                x_start, size_start, center_state = self.x_right, (w_s, h_s), "right"
            elif idx == (self.current_idx - 2) % total and direction == -1:
                x_start, size_start, center_state = self.x_left - 315, (w_s, h_s), "outer_left"
            elif idx == (self.current_idx + 2) % total and direction == 1:
                x_start, size_start, center_state = self.x_right + 315, (w_s, h_s), "outer_right"
            else:
                continue
                
            # Hitung pergeseran posisi X baru secara real-time
            x_now = x_start - step_x
            
            # ─── TRIK DYNAMIC RESIZING ───
            # Hitung transformasi ukuran lebar (w) & tinggi (h) secara kontinu berdasarkan rasio progress
            if center_state == "current" and direction != 0:
                # Gambar tengah yang beralih bergerak keluar (mengecil)
                w = int(w_c - (w_c - w_s) * progress)
                h = int(h_c - (h_c - h_s) * progress)
                mode = "dim" if progress > 0.5 else "normal"
            elif ((center_state == "left" and direction == -1) or (center_state == "right" and direction == 1)) and direction != 0:
                # Gambar samping yang beralih bergerak masuk ke tengah (membesar)
                w = int(w_s + (w_c - w_s) * progress)
                h = int(h_s + (h_c - h_s) * progress)
                mode = "normal" if progress > 0.5 else "dim"
            else:
                # Gambar konstan di area pinggiran tetap kecil
                w, h = w_s, h_s
                mode = "dim"
                
            img = self.get_processed_img(self.wallpapers[idx], (w, h), mode=mode)
            if img:
                # ─── BINGKAI UNGU IKUT MELUNCUR ───
                if (center_state == "current" and progress < 0.5 and direction != 0) or \
                   (((center_state == "left" and direction == -1) or (center_state == "right" and direction == 1)) and progress >= 0.5):
                    self.canvas.create_rectangle(x_now - w//2 - 6, self.y_center - h//2 - 6, 
                                                 x_now + w//2 + 6, self.y_center + h//2 + 6, 
                                                 outline="#bd93f9", width=4)
                
                # Jika posisi diam mutlak (tidak sedang mencet keyboard)
                if direction == 0 and idx == self.current_idx:
                    self.canvas.create_rectangle(x_now - w//2 - 6, self.y_center - h//2 - 6, 
                                                 x_now + w//2 + 6, self.y_center + h//2 + 6, 
                                                 outline="#bd93f9", width=4)
                    
                self.canvas.create_image(x_now, self.y_center, image=img)
                
        # 3. Text Overlay
        self.canvas.create_text(475, 365, text=os.path.basename(self.wallpapers[bg_idx]), 
                                fill="#bd93f9", font=("JetBrains Mono", 13, "bold"))
        self.canvas.create_text(475, 415, text=" Navigasi: Panah Kiri/Kanan | Pilih: Enter | Keluar: Esc ", 
                                fill="#6272a4", font=("JetBrains Mono", 10))

    def animate_slide(self, direction, step=0):
        total_steps = 18 # Kunci kehalusan frame rate transisi
        if step <= total_steps:
            # ─── INTERPOLASI EASE-IN-OUT (SINUSOIDAL) ───
            # Mengganti linear ke kurva melambat alami di garis finish
            ratio = step / total_steps
            progress = 0.5 * (1.0 - math.cos(ratio * math.pi))
            
            self.render_carousel(progress=progress, direction=direction)
            self.root.after(10, lambda: self.animate_slide(direction, step + 1))
        else:
            # Selesai animasi, mutasi indeks dasar asli
            self.current_idx = (self.current_idx + direction) % len(self.wallpapers)
            self.render_carousel(progress=0.0, direction=0)
            self.is_animating = False

    def geser_kanan(self, event):
        if self.is_animating: return
        self.is_animating = True
        self.animate_slide(direction=1) # Maju 1 langkah indeks ke kanan
        
    def geser_kiri(self, event):
        if self.is_animating: return
        self.is_animating = True
        self.animate_slide(direction=-1) # Mundur 1 langkah indeks ke kiri
        
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