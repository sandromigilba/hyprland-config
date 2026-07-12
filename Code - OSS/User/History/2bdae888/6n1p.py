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
        
        # Dimensi jendela utama
        self.root.geometry("950x460")
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
        
        # Komponen Canvas untuk Grafis Carousel
        self.canvas = tk.Canvas(root, bg="#1e1e2e", highlightthickness=0, width=950, height=330)
        self.canvas.pack(pady=15)
        
        # Label Nama File Gambar aktif
        self.label_name = tk.Label(root, text="", bg="#1e1e2e", fg="#bd93f9", font=("JetBrains Mono", 12, "bold"))
        self.label_name.pack()
        
        # Label Petunjuk Navigasi
        self.label_hint = tk.Label(root, text="   Navigasi: Panah Kiri / Kanan  |  Pilih: Enter  |  Keluar: Esc ", 
                                   bg="#282a36", fg="#6272a4", font=("JetBrains Mono", 10), pady=5, padx=10)
        self.label_hint.pack(pady=15)
        
        # Sistem Navigasi Keyboard
        self.root.bind("<Right>", self.geser_kanan)
        self.root.bind("<Left>", self.geser_kiri)
        self.root.bind("<Return>", self.eksekusi_wallpaper)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self.render_carousel()
        
    def get_thumbnail(self, path, size, redup=False):
        # Memasukkan status 'redup' ke dalam key cache agar tidak bentrok
        if (path, size, redup) in self.img_cache:
            return self.img_cache[(path, size, redup)]
        try:
            img = Image.open(path)
            img.thumbnail(size)
            
            # Jika gambar di samping, kurangi kecerahannya menjadi 35% agar terlihat redup/gelap
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
        
        # Indexing kartu kiri, tengah (aktif), dan kanan
        idx_center = self.current_idx
        idx_left = (self.current_idx - 1) % total
        idx_right = (self.current_idx + 1) % total
        
        # Dimensi thumbnail kartu
        size_center = (420, 260)
        size_samping = (220, 140)
        
        # 1. Gambar Sisi Kiri (Dipasang redup=True)
        img_left = self.get_thumbnail(self.wallpapers[idx_left], size_samping, redup=True)
        if img_left:
            self.canvas.create_image(160, 165, image=img_left)
            
        # 2. Gambar Sisi Kanan (Dipasang redup=True)
        img_right = self.get_thumbnail(self.wallpapers[idx_right], size_samping, redup=True)
        if img_right:
            self.canvas.create_image(790, 165, image=img_right)
            
        # 3. Gambar Utama Tengah (Aktif + Highlight Border Ungu)
        img_center = self.get_thumbnail(self.wallpapers[idx_center], size_center, redup=False)
        if img_center:
            w, h = img_center.width(), img_center.height()
            # Gambar bingkai border ungu di belakang gambar aktif
            self.canvas.create_rectangle(475 - w//2 - 6, 165 - h//2 - 6, 475 + w//2 + 6, 165 + h//2 + 6, 
                                         outline="#bd93f9", width=4)
            self.canvas.create_image(475, 165, image=img_center)
        
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
        # Jalankan awww dengan efek grow mendarat dari tengah
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