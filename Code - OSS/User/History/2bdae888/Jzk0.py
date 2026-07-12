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
        
        # ─── 1. KALKULASI MARGIN WINDOW AGAR PAS DI TENGAH MONITOR ───
        lebar = 950
        tinggi = 460
        lebar_layar = self.root.winfo_screenwidth()
        tinggi_layar = self.root.winfo_screenheight()
        
        posisi_x = (lebar_layar // 2) - (lebar // 2)
        posisi_y = (tinggi_layar // 2) - (tinggi // 2)
        
        self.root.geometry(f"{lebar}x{tinggi}+{posisi_x}+{posisi_y}")
        self.root.resizable(False, False)
        
        # Scan semua gambar di folder ~/Pictures
        self.wallpapers = sorted([os.path.join(WALLPAPER_DIR, f) for f in os.listdir(WALLPAPER_DIR) 
                                  if f.lower().endswith(VALID_EXT)])
        
        if not self.wallpapers:
            print("Waduh, tidak ada foto (.png/.jpg/.webp) di folder ~/Pictures!")
            sys.exit(1)
            
        # ─── 2. DETEKSI WALLPAPER AKTIF ───
        self.current_idx = self.load_active_index()
        self.img_cache = {}
        
        # ─── 3. TRIK MARGIN AUTO: WRAPPER UTAMA ───
        self.main_container = tk.Frame(root, bg="#1e1e2e")
        self.main_container.pack(expand=True)
        
        self.canvas = tk.Canvas(self.main_container, bg="#1e1e2e", highlightthickness=0, width=950, height=310)
        self.canvas.pack(pady=(0, 10))
        
        self.label_name = tk.Label(self.main_container, text="", bg="#1e1e2e", fg="#bd93f9", font=("JetBrains Mono", 12, "bold"))
        self.label_name.pack(pady=5)
        
        self.label_hint = tk.Label(self.main_container, text="   Navigasi: Panah Kiri / Kanan  |  Pilih: Enter  |  Keluar: Esc ", 
                                   bg="#282a36", fg="#6272a4", font=("JetBrains Mono", 10), pady=6, padx=12)
        self.label_hint.pack(pady=(10, 0))
        
        # Sistem Navigasi Keyboard
        self.root.bind("<Right>", self.geser_kanan)
        self.root.bind("<Left>", self.geser_kiri)
        self.root.bind("<Return>", self.eksekusi_wallpaper)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self.render_carousel()

    def load_active_index(self):
        """Membaca file state untuk menentukan wallpaper mana yang aktif."""
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
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(0.35)
                
            tk_img = ImageTk.PhotoImage(img)
            self.img_cache[(path, size, redup)] = tk_img
            return tk_img
        except:
            return None

    def render_carousel(self):
        self.canvas.delete("all")
        total = len(self.wallpapers)
        y_center = 155
        
        # Indeks kartu
        idx_center = self.current_idx
        idx_left = (self.current_idx - 1) % total
        idx_right = (self.current_idx + 1) % total
        
        size_center = (420, 260)
        size_samping = (220, 140)
        
        # Render Kiri, Kanan, Tengah
        # Urutan: (idx, x_pos, size, is_center)
        for idx, x_pos, size, is_center in [(idx_left, 160, size_samping, False), 
                                           (idx_right, 790, size_samping, False),
                                           (idx_center, 475, size_center, True)]:
            img = self.get_thumbnail(self.wallpapers[idx], size, redup=not is_center)
            if img:
                if is_center:
                    w, h = img.width(), img.height()
                    self.canvas.create_rectangle(x_pos - w//2 - 6, y_center - h//2 - 6, 
                                                 x_pos + w//2 + 6, y_center + h//2 + 6, 
                                                 outline="#bd93f9", width=4)
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
        
        # 1. Simpan ke file state agar terbaca saat aplikasi dibuka kembali
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(target_wall)
            
        # 2. Jalankan awww
        subprocess.run(["awww", "img", target_wall, 
                        "--transition-type", "grow", 
                        "--transition-pos", "center", 
                        "--transition-fps", "75",
                        "--transition-step", "90"])
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WallpaperCarousel(root)
    root.mainloop()