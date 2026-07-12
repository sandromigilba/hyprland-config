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
        self.is_animating = False # Mencegah spam klik saat animasi berjalan
        
        # Canvas utama sebagai container utama
        self.canvas = tk.Canvas(root, bg="#1e1e2e", highlightthickness=0, width=950, height=460)
        self.canvas.pack(fill="both", expand=True)
        
        # Koordinat X konstan untuk posisi diam awal
        self.x_left, self.x_center, self.x_right = 160, 475, 790
        self.y_center = 180
        
        # Setup gambar awal
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
        """Mode: 'normal' (thumbnail), 'dim' (sampingan), 'bg' (downsampled blur ekstrim)"""
        cache_key = (path, size, mode)
        if cache_key in self.img_cache: 
            return self.img_cache[cache_key]
        
        try:
            with Image.open(path) as raw_img:
                img = raw_img.convert("RGB")
                if mode == "bg":
                    # Downsample ke resolusi mikro untuk mempercepat komputasi blur container
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

    def render_carousel(self, offset_x=0, temp_idx=None):
        """Merender komponen dengan offset X opsional untuk kebutuhan animasi"""
        self.canvas.delete("all")
        total = len(self.wallpapers)
        
        # Jika sedang transisi, gunakan indeks sementara untuk background
        idx_active = temp_idx if temp_idx is not None else self.current_idx
        
        # 1. Render Background Blur Container (Selalu mengikuti wallpaper aktif/target)
        bg_img = self.get_processed_img(self.wallpapers[idx_active], (950, 460), mode="bg")
        if bg_img:
            self.canvas.create_image(475, 230, image=bg_img)
            
        # 2. Ukuran gambar yang sudah dikecilkan (Lebih ringkas & proporsional)
        size_center = (360, 220)
        size_samping = (180, 110)
        
        idx_center = idx_active
        idx_left = (idx_active - 1) % total
        idx_right = (idx_active + 1) % total
        
        # Jika geser kanan/kiri ekstrem, render ekstra 1 gambar di ujung luar luar jangkauan untuk transisi mulus
        items = [
            ((idx_left - 1) % total, self.x_left - 315 + offset_x, size_samping, False), # Cadangan kiri
            (idx_left, self.x_left + offset_x, size_samping, False),
            (idx_center, self.x_center + offset_x, size_center, True),
            (idx_right, self.x_right + offset_x, size_samping, False),
            ((idx_right + 1) % total, self.x_right + 315 + offset_x, size_samping, False) # Cadangan kanan
        ]
        
        for idx, x, size, is_center in items:
            # Gunakan versi 'dim' saat bergeser, nanti di-highlight ulang saat animasi selesai
            mode = "normal" if (is_center and offset_x == 0) else "dim"
            img = self.get_processed_img(self.wallpapers[idx], size, mode=mode)
            if img:
                if is_center and offset_x == 0:
                    w, h = img.width(), img.height()
                    self.canvas.create_rectangle(x - w//2 - 6, self.y_center - h//2 - 6, 
                                                 x + w//2 + 6, self.y_center + h//2 + 6, 
                                                 outline="#bd93f9", width=4)
                self.canvas.create_image(x, self.y_center, image=img)
                
        # 3. Text Overlay
        self.canvas.create_text(475, 365, text=os.path.basename(self.wallpapers[idx_center]), 
                                fill="#bd93f9", font=("JetBrains Mono", 13, "bold"))
        self.canvas.create_text(475, 415, text=" Navigasi: Panah Kiri/Kanan | Pilih: Enter | Keluar: Esc ", 
                                fill="#6272a4", font=("JetBrains Mono", 10))

    def animate_slide(self, target_offset, step=0, direction="left"):
        """Menggeser posisi gambar secara berkala hingga mencapai target pixel"""
        total_steps = 15 # Total frame animasi (makin kecil makin cepat)
        if step < total_steps:
            # Menggunakan interpolasi linear sederhana untuk pergerakan
            current_offset = (target_offset / total_steps) * (step + 1)
            
            # Tentukan indeks visual mana yang harus mendominasi background selama transisi
            total = len(self.wallpapers)
            visual_idx = (self.current_idx + (1 if direction == "right" else -1)) % total
            
            self.render_carousel(offset_x=int(current_offset), temp_idx=visual_idx)
            self.root.after(12, lambda: self.animate_slide(target_offset, step + 1, direction))
        else:
            # Selesai animasi, kunci posisi asli ke indeks baru
            total = len(self.wallpapers)
            if direction == "right":
                self.current_idx = (self.current_idx + 1) % total
            else:
                self.current_idx = (self.current_idx - 1) % total
                
            self.render_carousel()
            self.is_animating = False

    def geser_kanan(self, event):
        if self.is_animating: return
        self.is_animating = True
        # Bergeser ke kiri sebesar jarak antar kartu (-315px) untuk efek meluncur ke kanan
        self.animate_slide(-315, step=0, direction="right")
        
    def geser_kiri(self, event):
        if self.is_animating: return
        self.is_animating = True
        # Bergeser ke kanan sebesar jarak antar kartu (+315px) untuk efek meluncur ke kiri
        self.animate_slide(315, step=0, direction="left")
        
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