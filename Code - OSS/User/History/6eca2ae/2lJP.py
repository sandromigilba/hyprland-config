#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox,
    QComboBox, QMessageBox, QListWidget,
    QLineEdit
)

CONFIG_PATH = Path.home() / ".config/waybar/config"


class WaybarConfigManager(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Waybar Safe Config + WiFi Manager")
        self.resize(650, 550)

        self.load_config()

        layout = QVBoxLayout()

        # ================= WAYBAR =================
        layout.addWidget(QLabel("=== Waybar Config (SAFE MODE) ==="))

        self.position = QComboBox()
        self.position.addItems(["top", "bottom"])
        self.position.setCurrentText(self.config.get("position", "top"))

        self.height = QSpinBox()
        self.height.setRange(20, 100)
        self.height.setValue(self.config.get("height", 42))

        self.spacing = QSpinBox()
        self.spacing.setRange(0, 50)
        self.spacing.setValue(self.config.get("spacing", 10))

        layout.addWidget(self.position)
        layout.addWidget(self.height)
        layout.addWidget(self.spacing)

        self.save_btn = QPushButton("Save (Safe Patch)")
        self.save_btn.clicked.connect(self.save_config_safe)

        self.restart_btn = QPushButton("Restart Waybar")
        self.restart_btn.clicked.connect(self.restart_waybar)

        layout.addWidget(self.save_btn)
        layout.addWidget(self.restart_btn)

        # ================= WIFI =================
        layout.addWidget(QLabel("=== WiFi Manager ==="))

        self.wifi_list = QListWidget()
        self.wifi_list.setMinimumHeight(200)
        layout.addWidget(self.wifi_list)

        btn_row = QHBoxLayout()

        self.scan_btn = QPushButton("Scan WiFi")
        self.scan_btn.clicked.connect(self.scan_wifi)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_wifi)

        btn_row.addWidget(self.scan_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("WiFi Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.setLayout(layout)

        # ================= STYLE (rounded 30px) =================
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 14px;
            }

            QComboBox, QSpinBox, QLineEdit, QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 30px;
                padding: 10px;
            }

            QPushButton {
                background-color: #2a2a2a;
                border-radius: 30px;
                padding: 10px;
            }

            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)

    # ================= SAFE LOAD =================
    def load_config(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                text = f.read()

            # remove //
            clean_lines = []
            for line in text.splitlines():
                if "//" in line:
                    line = line.split("//")[0]
                clean_lines.append(line)

            self.config = json.loads("\n".join(clean_lines))

        except Exception:
            # fallback aman
            self.config = {
                "position": "top",
                "height": 42,
                "spacing": 10
            }

    # ================= SAFE SAVE (PATCH ONLY) =================
    def save_config_safe(self):
        try:
            # backup dulu
            backup = CONFIG_PATH.with_suffix(".bak")
            backup.write_text(CONFIG_PATH.read_text())

            # update ONLY small fields
            self.config["position"] = self.position.currentText()
            self.config["height"] = self.height.value()
            self.config["spacing"] = self.spacing.value()

            # validate JSON dulu
            json.dumps(self.config)

            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4)

            QMessageBox.information(self, "OK", "Saved safely (backup created)")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ================= WAYBAR =================
    def restart_waybar(self):
        subprocess.run(["pkill", "waybar"])
        subprocess.Popen(["waybar"])

    # ================= WIFI =================
    def scan_wifi(self):
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi", "list"],
            capture_output=True,
            text=True
        )

        self.wifi_list.clear()
        seen = set()

        for line in result.stdout.splitlines():
            if ":" in line:
                ssid, signal = line.split(":")[:2]
                if ssid:
                    seen.add(f"{ssid} ({signal}%)")

        for s in sorted(seen):
            self.wifi_list.addItem(s)

    def connect_wifi(self):
        item = self.wifi_list.currentItem()

        if not item:
            QMessageBox.warning(self, "Warning", "Pilih WiFi dulu")
            return

        ssid = item.text().split(" (")[0]
        password = self.password_input.text()

        if not password:
            QMessageBox.warning(self, "Warning", "Password kosong")
            return

        result = subprocess.run(
            ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            QMessageBox.information(self, "OK", f"Connected {ssid}")
        else:
            QMessageBox.critical(self, "Error", result.stderr)


if __name__ == "__main__":
    app = QApplication([])
    win = WaybarConfigManager()
    win.show()
    app.exec()