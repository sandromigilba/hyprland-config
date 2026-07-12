#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import tkinter as tk

# =========================
# CONFIG & PALETTE (iOS Transparency & Bento Style)
# =========================
BG_COLOR = "#1e1e2e"       # Base latar belakang gelap
CARD_BG = "#2a2b3d"        # Kapsul abu-abu transparan ala iOS
TEXT_MAIN = "#cdd6f4"      # Teks utama
ACCENT_BLUE = "#007aff"    # Biru iOS aktif
ACCENT_YELLOW = "#ffcc00"  # Kuning slider cerah
MUTED = "#6272a4"          # Teks redup

WINDOW_W = 360
WINDOW_H = 600

class IOSCapsuleSlider(tk.Canvas):
    """Slider kustom berbentuk kapsul tebal vertikal ala iOS (Optimized Rendering)"""
    def __init__(self, parent, width, height, icon_text, icon_color, initial_val, callback):
        super().__init__(parent, width=width, height=height, bg=CARD_BG, highlightthickness=0)
        self.w = width
        self.h = height
        self.icon_text = icon_text
        self.icon_color = icon_color
        self.callback = callback
        self.value = initial_val / 100.0  # Konversi ke 0.0 - 1.0
        self.last_int_val = initial_val

        # Inisialisasi komponen bentuk sekali saja (Mencegah Overdraw)
        self.init_slider_components()
        
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Button-1>", self.on_drag)
        self.update_slider_view()

    def init_slider_components(self):
        """Membuat objek geometris statis di Canvas untuk dimanipulasi kemudian"""
        r = self.w // 2
        
        # 1. Background Kapsul Kosong (Statis)
        self.create_oval(0, 0, self.w, self.w*2, fill="#1c1c2e", outline="")
        self.create_oval(0, self.h - self.w*2, self.w, self.h, fill="#1c1c2e", outline="")
        self.create_rectangle(0, r, self.w, self.h - r, fill="#1c1c2e", outline="")

        # 2. Level Isi (Dinamis menggunakan tag 'fill_layer')
        self.fill_top_oval = self.create_oval(0, 0, self.w, self.w*2, fill=TEXT_MAIN, outline="", state="hidden")
        self.fill_rect = self.create_rectangle(0, self.h - r, self.w, self.h - r, fill=TEXT_MAIN, outline="", state="hidden")
        self.fill_bot_oval = self.create_oval(0, self.h - self.w*2, self.w, self.h, fill=TEXT_MAIN, outline="", state="hidden")

        # 3. Icon (Statis menggunakan tag 'icon')
        icon_y = self.h - r - 10
        self.icon_item = self.create_text(self.w // 2, icon_y, text=self.icon_text, fill=self.icon_color, font=("JetBrains Mono", 20, "bold"))

    def update_slider_view(self):
        """Mengubah tinggi fill layer secara efisien tanpa membuat ulang objek"""
        r = self.w // 2
        y_fill = self.h - (self.value * self.h)

        # Kelola visibilitas dan posisi fill layer secara bertahap
        if y_fill >= self.h:
            self.itemconfigure(self.fill_bot_oval, state="hidden")
            self.itemconfigure(self.fill_rect, state="hidden")
            self.itemconfigure(self.fill_top_oval, state="hidden")
        else:
            self.itemconfigure(self.fill_bot_oval, state="normal")
            
            if y_fill < self.h - r:
                self.itemconfigure(self.fill_rect, state="normal")
                self.coords(self.fill_rect, 0, max(r, y_fill), self.w, self.h - r)
            else:
                self.itemconfigure(self.fill_rows, state="hidden")

            if y_fill < r:
                self.itemconfigure(self.fill_top_oval, state="normal")
            else:
                self.itemconfigure(self.fill_top_oval, state="hidden")

        # Dynamic Color Shift untuk Ikon jika terendam cairan putih
        icon_y = self.h - r - 10
        txt_color = self.icon_color if y_fill > icon_y else "#11111b"
        self.itemconfigure(self.icon_item, fill=txt_color)

    def on_drag(self, event):
        val = (self.h - event.y) / self.h
        self.value = max(0.0, min(1.0, val))
        self.update_slider_view()
        
        # Throttling: Hanya panggil callback jika nilai integer-nya benar-benar berubah
        current_int_val = int(self.value * 100)
        if current_int_val != self.last_int_val:
            self.last_int_val = current_int_val
            self.callback(current_int_val)


class IPhoneControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("HyprOS_ControlCenter")
        self.root.configure(bg=BG_COLOR)

        lebar_layar = self.root.winfo_screenwidth()
        tinggi_layar = self.root.winfo_screenheight()
        pos_x = lebar_layar - WINDOW_W - 20
        pos_y = (tinggi_layar // 2) - (WINDOW_H // 2)

        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)

        self.root.bind("<FocusOut>", lambda e: self.root.destroy())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.main_container = tk.Frame(root, bg=BG_COLOR, padx=20, pady=20)
        self.main_container.pack(fill="both", expand=True)

        self.create_header()
        self.create_bento_grid()

    def create_header(self):
        header = tk.Frame(self.main_container, bg=BG_COLOR)
        header.pack(fill="x", pady=(0, 20))

        self.time_label = tk.Label(header, text="", bg=BG_COLOR, fg=TEXT_MAIN, font=("JetBrains Mono", 22, "bold"))
        self.time_label.pack(side="left")
        
        user_label = tk.Label(header, text="Control Center", bg=BG_COLOR, fg=MUTED, font=("JetBrains Mono", 10, "bold"))
        user_label.pack(side="right", ipady=5)
        
        self.update_clock()

    def update_clock(self):
        self.time_label.config(text=time.strftime("%H:%M"))
        self.root.after(1000, self.update_clock)

    def create_bento_grid(self):
        grid_frame = tk.Frame(self.main_container, bg=BG_COLOR)
        grid_frame.pack(fill="both", expand=True)
        
        grid_frame.columnconfigure(0, weight=1, uniform="kolom")
        grid_frame.columnconfigure(1, weight=1, uniform="kolom")

        # ─── BOX 1: KONEKTIVITAS ───
        conn_box = tk.Frame(grid_frame, bg=CARD_BG, padx=12, pady=12)
        conn_box.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        
        btn_wifi = tk.Label(conn_box, text="󰤨", bg=ACCENT_BLUE, fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=3, height=1)
        btn_wifi.grid(row=0, column=0, padx=6, pady=6)
        btn_wifi.bind("<Button-1>", lambda e: subprocess.Popen(["kitty", "-e", "nmtui"]))
        
        tk.Label(conn_box, text="󰀝", bg="#4a4a4a", fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=3, height=1).grid(row=0, column=1, padx=6, pady=6)
        tk.Label(conn_box, text="󰂯", bg=ACCENT_BLUE, fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=3, height=1).grid(row=1, column=0, padx=6, pady=6)
        tk.Label(conn_box, text="󰈀", bg="#4a4a4a", fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=3, height=1).grid(row=1, column=1, padx=6, pady=6)

        # ─── BOX 2: MEDIA PLAYER ───
        media_box = tk.Frame(grid_frame, bg=CARD_BG, padx=12, pady=12)
        media_box.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        
        tk.Label(media_box, text="Not Playing", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 11, "bold")).pack(anchor="w", pady=(5, 15))
        
        ctrl_frame = tk.Frame(media_box, bg=CARD_BG)
        ctrl_frame.pack(fill="x")
        tk.Label(ctrl_frame, text="󰒮", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14)).pack(side="left", expand=True)
        tk.Label(ctrl_frame, text="󰐊", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 16)).pack(side="left", expand=True)
        tk.Label(ctrl_frame, text="󰒭", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14)).pack(side="left", expand=True)

        # ─── BOX 3: TOGGLES TAMBAHAN ───
        toggle_box = tk.Frame(grid_frame, bg=BG_COLOR)
        toggle_box.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        
        tk.Label(toggle_box, text="󰘶", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=4, height=2).grid(row=0, column=0, padx=6, pady=6)
        tk.Label(toggle_box, text="󰂚", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=4, height=2).grid(row=0, column=1, padx=6, pady=6)
        
        focus_capsule = tk.Frame(toggle_box, bg=CARD_BG, padx=10, pady=8)
        focus_capsule.grid(row=1, column=0, columnspan=2, padx=6, pady=6, sticky="ew")
        tk.Label(focus_capsule, text="🌙 Focus", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 10, "bold")).pack(side="left")

        # ─── BOX 4 & 5: IOS SLIDERS (Jatah 2 Baris) ───
        slider_container = tk.Frame(grid_frame, bg=BG_COLOR)
        slider_container.grid(row=1, column=1, rowspan=2, padx=6, pady=6, sticky="nsew")
        
        self.bright_slider = IOSCapsuleSlider(slider_container, width=68, height=160, 
                                              icon_text="󰃟", icon_color=ACCENT_YELLOW, 
                                              initial_val=self.get_brightness(), callback=self.set_brightness)
        self.bright_slider.pack(side="left", expand=True, padx=4)

        self.vol_slider = IOSCapsuleSlider(slider_container, width=68, height=160, 
                                           icon_text="󰕾", icon_color=ACCENT_BLUE, 
                                           initial_val=self.get_volume(), callback=self.set_volume)
        self.vol_slider.pack(side="right", expand=True, padx=4)

        # ─── BOX 6: UTILITY SHORTCUTS ───
        util_box = tk.Frame(grid_frame, bg=BG_COLOR)
        util_box.grid(row=2, column=0, padx=0, pady=0, sticky="nsew")
        tk.Label(util_box, text="󰛨", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=4, height=2).grid(row=0, column=0, padx=6, pady=6)
        tk.Label(util_box, text="󰄀", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14), width=4, height=2).grid(row=0, column=1, padx=6, pady=6)

        # ─── FOOTER ROW: BATTERY & SHUTDOWN ───
        footer = tk.Frame(self.main_container, bg=BG_COLOR)
        footer.pack(side="bottom", fill="x", pady=(15, 0))

        bat_capacity = "100%"
        try:
            with open("/sys/class/power_supply/BAT0/capacity", "r") as f:
                bat_capacity = f"{f.read().strip()}%"
        except: pass

        bat_box = tk.Frame(footer, bg=CARD_BG, padx=12, pady=10)
        bat_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(bat_box, text=f"󰁹 {bat_capacity}", bg=CARD_BG, fg="#a6e3a1", font=("JetBrains Mono", 11, "bold")).pack(side="left")

        power_btn = tk.Button(footer, text="", bg="#f38ba8", fg="#11111b", font=("JetBrains Mono", 12, "bold"),
                              activebackground="#f38ba8", relief="flat", bd=0, width=4, height=2, command=self.trigger_power)
        power_btn.pack(side="right")

    # =========================================================
    # BACKEND OPTIMIZATION
    # =========================================================
    def get_volume(self):
        try:
            res = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]).decode()
            return int(float(res.split()[1]) * 100)
        except: return 50

    def set_volume(self, val):
        # Proteksi pengiriman sinyal audio yang valid ke WirePlumber
        subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{float(val)/100}"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def get_brightness(self):
        try:
            res = subprocess.check_output(["brightnessctl", "g"]).decode()
            max_b = subprocess.check_output(["brightnessctl", "m"]).decode()
            return int((int(res) / int(max_b)) * 100)
        except: return 100

    def set_brightness(self, val):
        # Menggunakan Popen agar eksekusi hardware backlight tidak memblokir UI thread Tkinter
        subprocess.Popen(["brightnessctl", "s", f"{val}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def trigger_power(self):
        self.root.destroy()
        subprocess.run(["wlogout", "-b", "6", "--protocol", "layer-shell"])


if __name__ == "__main__":
    root = tk.Tk()
    app = IPhoneControlPanel(root)
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.focus_force()
    root.mainloop()