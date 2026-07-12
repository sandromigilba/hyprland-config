#!/usr/bin/env python3
import tkinter as tk
import subprocess
import os

class SidebarControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("HyprControlPanel")
        self.root.configure(bg="#1e1e2e") # Dracula Base
        
        # Ukuran sidebar kanan
        lebar = 320
        tinggi = 900
        lebar_layar = self.root.winfo_screenwidth()
        tinggi_layar = self.root.winfo_screenheight()
        
        # Taruh pas di pojok kanan layar
        pos_x = lebar_layar - lebar - 10
        pos_y = (tinggi_layar // 2) - (tinggi // 2)
        
        self.root.geometry(f"{lebar}x{tinggi}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)
        
        # Close focus lost (jika klik di luar, sidebar otomatis menutup/hide)
        self.root.bind("<FocusOut>", lambda e: self.root.destroy())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # ─── UI ELEMENTS ───
        title = tk.Label(root, text="󱗼 CONTROL PANEL", bg="#1e1e2e", fg="#bd93f9", font=("JetBrains Mono", 16, "bold"))
        title.pack(pady=30)

        # Slider Volume
        tk.Label(root, text="󰕾 Volume", bg="#1e1e2e", fg="#a6e3a1", font=("JetBrains Mono", 11)).pack(anchor="w", padx=30)
        self.vol_slider = tk.Scale(root, from_=100, to=0, orient="vertical", length=150, bg="#1e1e2e", fg="#cdd6f4", 
                                   troughcolor="#313244", activebackground="#bd93f9", highlightthickness=0, command=self.set_volume)
        self.vol_slider.set(self.get_volume())
        self.vol_slider.pack(pady=10)

        # Slider Brightness
        tk.Label(root, text="󰃟 Brightness", bg="#1e1e2e", fg="#f9e2af", font=("JetBrains Mono", 11)).pack(anchor="w", padx=30)
        self.bright_slider = tk.Scale(root, from_=100, to=10, orient="vertical", length=150, bg="#1e1e2e", fg="#cdd6f4", 
                                     troughcolor="#313244", activebackground="#bd93f9", highlightthickness=0, command=self.set_brightness)
        self.bright_slider.set(self.get_brightness())
        self.bright_slider.pack(pady=10)

        # Quick Buttons (Power/Reload)
        btn_frame = tk.Frame(root, bg="#1e1e2e")
        btn_frame.pack(side="bottom", pady=40)

        tk.Button(btn_frame, text=" 󰑓 Reload ", bg="#313244", fg="#cdd6f4", font=("JetBrains Mono", 10), 
                  command=self.reload_hyprland, relief="flat", padx=10, pady=5).grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text="  Power ", bg="#f38ba8", fg="#11111b", font=("JetBrains Mono", 10, "bold"), 
                  command=self.power_menu, relief="flat", padx=10, pady=5).grid(row=0, column=1, padx=10)

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

    def reload_hyprland(self):
        subprocess.run(["hyprctl", "reload"])
        self.root.destroy()

    def power_menu(self):
        subprocess.run(["wlogout", "-b", "6"])
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SidebarControlPanel(root)
    # Membuat window tetap stand-alone tanpa window decoration atas bawaan OS
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.focus_force()
    root.mainloop()