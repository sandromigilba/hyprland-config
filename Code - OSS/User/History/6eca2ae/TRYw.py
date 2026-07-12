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
        self.resize(600, 500)

        self.load_config()

        layout = QVBoxLayout()

        # ================= WAYBAR CONFIG =================
        layout.addWidget(QLabel("=== Waybar Config ==="))

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position"))

        self.position = QComboBox()
        self.position.addItems(["top", "bottom"])
        self.position.setCurrentText(self.config.get("position", "top"))
        pos_layout.addWidget(self.position)
        layout.addLayout(pos_layout)

        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height"))

        self.height = QSpinBox()
        self.height.setRange(20, 100)
        self.height.setValue(self.config.get("height", 42))
        height_layout.addWidget(self.height)
        layout.addLayout(height_layout)

        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Spacing"))

        self.spacing = QSpinBox()
        self.spacing.setRange(0, 50)
        self.spacing.setValue(self.config.get("spacing", 10))
        spacing_layout.addWidget(self.spacing)
        layout.addLayout(spacing_layout)

        self.save_btn = QPushButton("Save Waybar Config")
        self.save_btn.clicked.connect(self.save_config)

        self.restart_btn = QPushButton("Restart Waybar")
        self.restart_btn.clicked.connect(self.restart_waybar)

        layout.addWidget(self.save_btn)
        layout.addWidget(self.restart_btn)

        # ================= WIFI SECTION =================
        layout.addWidget(QLabel("\n=== WiFi Manager ==="))

        self.wifi_list = QListWidget()
        layout.addWidget(self.wifi_list)

        btn_layout = QHBoxLayout()

        self.scan_btn = QPushButton("Scan WiFi")
        self.scan_btn.clicked.connect(self.scan_wifi)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_wifi)

        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.connect_btn)

        layout.addLayout(btn_layout)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("WiFi Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.setLayout(layout)

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

            clean_json = "\n".join(lines)
            self.config = json.loads(clean_json)

        except Exception:
            self.config = {}

    def save_config(self):
        self.config["position"] = self.position.currentText()
        self.config["height"] = self.height.value()
        self.config["spacing"] = self.spacing.value()

        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4)

            QMessageBox.information(self, "Success", "Config saved")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def restart_waybar(self):
        subprocess.run(["pkill", "waybar"])
        subprocess.Popen(["waybar"])

        QMessageBox.information(self, "Waybar", "Restarted")

    # ================= WIFI =================
    def scan_wifi(self):
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi", "list"],
                capture_output=True,
                text=True
            )

            self.wifi_list.clear()

            networks = set()

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                ssid = line.split(":")[0].strip()
                signal = line.split(":")[1].strip() if ":" in line else "0"

                if ssid:
                    networks.add(f"{ssid} ({signal}%)")

            for net in sorted(networks):
                self.wifi_list.addItem(net)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def connect_wifi(self):
        selected = self.wifi_list.currentItem()

        if not selected:
            QMessageBox.warning(self, "Warning", "Pilih WiFi dulu")
            return

        ssid = selected.text().split(" (")[0]
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
            QMessageBox.information(self, "Success", f"Connected to {ssid}")
        else:
            QMessageBox.critical(self, "Error", result.stderr)


if __name__ == "__main__":
    app = QApplication([])
    win = WaybarConfigManager()
    win.show()
    app.exec()