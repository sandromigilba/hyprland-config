#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance

# Konfigurasi Jalur Folder Gambar
WALLPAPER_DIR = os.path.expanduser("~/Pictures")
VALID_EXT = ('.png', '.jpg', '.jpeg', '.webp')

class WallpaperCarousel:
    def __init__(self, root):
        self.root = root
        self.root.title("Awww Wallpaper Picker")
        self.root.configure(bg="#1e1e2e") # Warna tema Dracula Gelap
        
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
        self.wallpapers = [os.path.join(WALLPAPER_DIR, f) for f in os.listdir(WALLPAPER_DIR) 
                           if f.lower().endswith(VALID_EXT)]
        self.wallpapers.sort()
        
        if not self.wallpapers:
            print("Waduh, tidak ada foto (.png/.jpg/.webp) di folder ~/Pictures!")
            sys.exit(1)
            
        self.current_idx = 0
        self.img_cache = {} # Mencegah bug gambar hilang akibat garbage collector Python
        
        # ─── 2. TRIK MARGIN AUTO: WRAPPER UTAMA ───
        # Kotak pembungkus yang menyedot sisa ruang window agar posisi konten simetris di tengah
        self.main_container = tk.Frame(root, bg="#1e1e2e")
        self.main_container.pack(expand=True)
        
        # Komponen Canvas masuk ke main_container (tinggi disesuaikan ke 310 agar tidak sesak)
        self.canvas = tk.Canvas(self.main_container, bg="#1e1e2e", highlightthickness=0, width=950, height=310)
        self.canvas.pack(pady=(0, 10)) # margin-bottom: 10px
        
        # Label Nama File Gambar aktif masuk ke main_container
        self.label_name = tk.Label(self.main_container, text="", bg="#1e1e2e", fg="#bd93f9", font=("JetBrains Mono", 12, "bold"))
        self.label_name.pack(pady=5)
        
        # Label Petunjuk Navigasi masuk ke main_container
        self.label_hint = tk.Label(self.main_container, text="   Navigasi: Panah Kiri / Kanan  |  Pilih: Enter  |  Keluar: Esc ", 
                                   bg="#282a36", fg="#6272a4", font=("JetBrains Mono", 10), pady=6, padx=12)
        self.label_hint.pack(pady=(10, 0)) # margin-top: 10px
        
        # Sistem Navigasi Keyboard
        self.root.bind("<Right>", self.geser_kanan)
        self.root.bind("<Left>", self.geser_kiri)
        self.root.bind("<Return>", self.eksekusi_wallpaper)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self.render_carousel()
        
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
        
        idx_center = self.current_idx
        idx_left = (self.current_idx - 1) % total
        idx_right = (self.current_idx + 1) % total
        
        size_center = (420, 260)
        size_samping = (220, 140)
        
        # Koordinat Y diubah ke 155 agar presisi di tengah Canvas berbobot 310px
        y_center = 155 
        
        # 1. Gambar Sisi Kiri (Redup)
        img_left = self.get_thumbnail(self.wallpapers[idx_left], size_samping, redup=True)
        if img_left:
            self.canvas.create_image(160, y_center, image=img_left)
            
        # 2. Gambar Sisi Kanan (Redup)
        img_right = self.get_thumbnail(self.wallpapers[idx_right], size_samping, redup=True)
        if img_right:
            self.canvas.create_image(790, y_center, image=img_right)
            
        # 3. Gambar Utama Tengah (Aktif + Highlight Border Ungu)
        img_center = self.get_thumbnail(self.wallpapers[idx_center], size_center, redup=False)
        if img_center:
            w, h = img_center.width(), img_center.height()
            self.canvas.create_rectangle(475 - w//2 - 6, y_center - h//2 - 6, 475 + w//2 + 6, y_center + h//2 + 6, 
                                         outline="#bd93f9", width=4)
            self.canvas.create_image(475, y_center, image=img_center)
        
        # Perbarui Teks Nama File
        nama_file = os.path.basename(self.wallpapers[idx_center])
        self.label_name.config(text=nama_file)
        
    def geser_kanan(self, event):
        self.current_idx = (self.current_idx + 1) % len(self.wallpapers)
        self.render_carousel()
        
    def geser_kiri(self, event):
        self.current_idx = (self.current_idx - 1) % len(self.wallpapers)
        self.render_carousel()
        
    def eksekusi_wallpaper(self, event):
        target_wall = self.wallpapers[self.current_idx]
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