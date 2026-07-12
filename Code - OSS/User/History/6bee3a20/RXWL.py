#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import tkinter as tk
from PIL import Image, ImageTk

# =========================
# CONFIG & PALETTE (Catppuccin Macchiato/Dracula Style)
# =========================
BG_COLOR = "#1e1e2e"       # Base gelap
CARD_BG = "#313244"        # Kapsul widget
TEXT_MAIN = "#cdd6f4"      # Teks utama
ACCENT = "#bd93f9"         # Ungu ala iOS toggles
MUTED = "#6272a4"          # Teks redup

WINDOW_W = 340
WINDOW_H = 600

class IPhoneControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("HyprOS_ControlCenter")
        self.root.configure(bg=BG_COLOR)

        # Posisi di Sisi Kanan Layar
        lebar_layar = self.root.winfo_screenwidth()
        tinggi_layar = self.root.winfo_screenheight()
        pos_x = lebar_layar - WINDOW_W - 20
        pos_y = (tinggi_layar // 2) - (WINDOW_H // 2)

        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)

        # Auto-hide saat klik di luar panel
        self.root.bind("<FocusOut>", lambda e: self.root.destroy())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # Container Utama (Padding Luar)
        self.main_container = tk.Frame(root, bg=BG_COLOR, padx=15, pady=20)
        self.main_container.pack(fill="both", expand=True)

        # Jalankan Pembangun UI
        self.create_header_widgets()
        self.create_connectivity_card()
        self.create_media_sliders()
        self.create_footer_status()

    # =========================================================
    # 1. HEADER (JAM & STATUS SINGKAT)
    # =========================================================
    def create_header_widgets(self):
        header_frame = tk.Frame(self.main_container, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 15))

        # Jam Digital Besar ala iOS lockscreen
        self.time_label = tk.Label(header_frame, text="", bg=BG_COLOR, fg=TEXT_MAIN, font=("JetBrains Mono", 24, "bold"))
        self.time_label.pack(side="left")
        
        # Sapaan Master
        user_label = tk.Label(header_frame, text="Control Center", bg=BG_COLOR, fg=MUTED, font=("JetBrains Mono", 10, "bold"))
        user_label.pack(side="right", ipady=8)
        
        self.update_clock()

    def update_clock(self):
        waktu_sekarang = time.strftime("%H:%M")
        self.time_label.config(text=waktu_sekarang)
        self.root.after(1000, self.update_clock)

    # =========================================================
    # 2. CONNECTIVITY CARD (WIFI BLOCK)
    # =========================================================
    def create_connectivity_card(self):
        card = tk.Frame(self.main_container, bg=CARD_BG, padx=15, pady=15)
        card.pack(fill="x", pady=10)

        # Menggunakan susunan Grid internal di dalam Kapsul
        lbl_icon = tk.Label(card, text="󰤨", bg=CARD_BG, fg=ACCENT, font=("JetBrains Mono", 18))
        lbl_icon.grid(row=0, column=0, rowspan=2, padx=(0, 10))

        lbl_title = tk.Label(card, text="Wi-Fi Network", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 11, "bold"))
        lbl_title.grid(row=0, column=1, sticky="w")

        # Ambil nama SSID Wi-Fi aktif
        ssid = "Disconnected"
        try:
            res = subprocess.check_output(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"]).decode()
            for line in res.splitlines():
                if line.startswith("yes:"):
                    ssid = line.split(":")[1]
                    break
        except: pass

        self.lbl_ssid = tk.Label(card, text=ssid, bg=CARD_BG, fg=MUTED, font=("JetBrains Mono", 9))
        self.lbl_ssid.grid(row=1, column=1, sticky="w")
        
        # Tombol aksi toggle wifi settings (nmtui / nm-connection-editor)
        card.bind("<Button-1>", lambda e: subprocess.Popen(["kitty", "-e", "nmtui"]))

    # =========================================================
    # 3. SLIDERS CARD (AUDIO & BRIGHTNESS ALA IOS)
    # =========================================================
    def create_media_sliders(self):
        slider_card = tk.Frame(self.main_container, bg=BG_COLOR)
        slider_card.pack(fill="x", pady=10)

        # Kapsul Volume (Kiri)
        vol_frame = tk.Frame(slider_card, bg=CARD_BG, padx=15, pady=15)
        vol_frame.pack(side="left", fill="both", expand=True, padx=(0, 7))

        tk.Label(vol_frame, text="󰕾", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14)).pack()
        self.vol_slider = tk.Scale(vol_frame, from_=100, to=0, orient="vertical", length=140, bg=CARD_BG, fg=TEXT_MAIN,
                                   troughcolor=BG_COLOR, activebackground=ACCENT, highlightthickness=0, showvalue=False, command=self.set_volume)
        self.vol_slider.set(self.get_volume())
        self.vol_slider.pack(pady=5)
        tk.Label(vol_frame, text="Volume", bg=CARD_BG, fg=MUTED, font=("JetBrains Mono", 8)).pack()

        # Kapsul Kecerahan / Brightness (Kanan)
        bright_frame = tk.Frame(slider_card, bg=CARD_BG, padx=15, pady=15)
        bright_frame.pack(side="right", fill="both", expand=True, padx=(7, 0))

        tk.Label(bright_frame, text="󰃟", bg=CARD_BG, fg=TEXT_MAIN, font=("JetBrains Mono", 14)).pack()
        self.bright_slider = tk.Scale(bright_frame, from_=100, to=5, orient="vertical", length=140, bg=CARD_BG, fg=TEXT_MAIN,
                                      troughcolor=BG_COLOR, activebackground=ACCENT, highlightthickness=0, showvalue=False, command=self.set_brightness)
        self.bright_slider.set(self.get_brightness())
        self.bright_slider.pack(pady=5)
        tk.Label(bright_frame, text="Bright", bg=CARD_BG, fg=MUTED, font=("JetBrains Mono", 8)).pack()

    def get_volume(self):
        try:
            res = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]).decode()
            return int(float(res.split()[1]) * 100)
        except: return 50

    def set_volume(self, val):
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{float(val)/100}"])

    def get_brightness(self):
        try:
            res = subprocess.check_output(["brightnessctl", "g"]).decode()
            max_b = subprocess.check_output(["brightnessctl", "m"]).decode()
            return int((int(res) / int(max_b)) * 100)
        except: return 100

    def set_brightness(self, val):
        subprocess.run(["brightnessctl", "s", f"{val}%"], stdout=subprocess.DEVNULL)

    # =========================================================
    # 4. FOOTER (BATTERY CAPSULE & SHUTDOWN BUTTON)
    # =========================================================
    def create_footer_status(self):
        footer_frame = tk.Frame(self.main_container, bg=BG_COLOR)
        footer_frame.pack(side="bottom", fill="x", pady=(10, 0))

        # Kapsul Baterai
        bat_card = tk.Frame(footer_frame, bg=CARD_BG, padx=15, pady=12)
        bat_card.pack(side="left", fill="x", expand=True, padx=(0, 10))

        bat_capacity = "100%"
        try:
            with open("/sys/class/power_supply/BAT0/capacity", "r") as f:
                bat_capacity = f"{f.read().strip()}%"
        except: pass

        lbl_bat = tk.Label(bat_card, text=f"󰁹 {bat_capacity}", bg=CARD_BG, fg="#a6e3a1", font=("JetBrains Mono", 11, "bold"))
        lbl_bat.pack(side="left")

        # Kapsul Tombol Shutdown / Daya Resmi (iOS Red Circle Style)
        power_btn = tk.Button(footer_frame, text="", bg="#f38ba8", fg="#11111b", font=("JetBrains Mono", 14, "bold"),
                              activebackground="#f38ba8", relief="flat", bd=0, width=4, height=1, command=self.trigger_power)
        power_btn.pack(side="right")

    def trigger_power(self):
        self.root.destroy()
        subprocess.run(["wlogout", "-b", "6", "--protocol", "layer-shell"])


if __name__ == "__main__":
    root = tk.Tk()
    app = IPhoneControlPanel(root)
    
    # Kunci Window Decoration agar Floating Murni & Selalu di Atas
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.focus_force()
    
    root.mainloop()