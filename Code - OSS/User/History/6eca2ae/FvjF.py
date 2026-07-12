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

        self.setWindowTitle("Waybar Config + WiFi Manager")
        self.resize(600, 550)

        self.load_config()

        layout = QVBoxLayout()

        # ================= WAYBAR CONFIG =================
        layout.addWidget(QLabel("=== Waybar Config ==="))

        self.position = QComboBox()
        self.position.addItems(["top", "bottom"])
        self.position.setCurrentText(self.config.get("position", "top"))

        self.height = QSpinBox()
        self.height.setRange(20, 100)
        self.height.setValue(self.config.get("height", 42))

        self.spacing = QSpinBox()
        self.spacing.setRange(0, 50)
        self.spacing.setValue(self.config.get("spacing", 10))

        self.save_btn = QPushButton("Save Waybar Config")
        self.save_btn.clicked.connect(self.save_config)

        self.restart_btn = QPushButton("Restart Waybar")
        self.restart_btn.clicked.connect(self.restart_waybar)

        layout.addWidget(self.position)
        layout.addWidget(self.height)
        layout.addWidget(self.spacing)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.restart_btn)

        # ================= WIFI =================
        layout.addWidget(QLabel("WiFi Manager"))

        self.wifi_list = QListWidget()
        self.wifi_list.setMinimumHeight(220)
        layout.addWidget(self.wifi_list)

        self.scan_btn = QPushButton("Scan WiFi")
        self.scan_btn.clicked.connect(self.scan_wifi)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_wifi)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.scan_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Masukkan password WiFi")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.setLayout(layout)

        # ================= UI STYLE (ROUNDED 30px) =================
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 14px;
            }

            QLabel {
                font-weight: bold;
                margin-top: 10px;
            }

            QComboBox, QSpinBox, QLineEdit, QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 30px;
                padding: 10px;
                color: white;
            }

            QListWidget {
                padding: 10px;
            }

            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 30px;
                padding: 10px;
            }

            QPushButton:hover {
                background-color: #3a3a3a;
            }

            QPushButton:pressed {
                background-color: #555;
            }
        """)

    # ================= WAYBAR =================
    def load_config(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                text = f.read()

            lines = []
            for line in text.splitlines():
                if "//" in line:
                    line = line.split("//")[0]
                lines.append(line)

            self.config = json.loads("\n".join(lines))

        except Exception:
            self.config = {}

    def save_config(self):
        self.config["position"] = self.position.currentText()
        self.config["height"] = self.height.value()
        self.config["spacing"] = self.spacing.value()

        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4)

            QMessageBox.information(self, "Success", "Saved")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

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
            QMessageBox.warning(self, "Warning", "Masukkan password")
            return

        result = subprocess.run(
            ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            QMessageBox.information(self, "Success", f"Connected {ssid}")
        else:
            QMessageBox.critical(self, "Error", result.stderr)


if __name__ == "__main__":
    app = QApplication([])
    win = WaybarConfigManager()
    win.show()
    app.exec()