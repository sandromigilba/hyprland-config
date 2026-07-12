#!/usr/bin/env python3

import subprocess
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox,
    QComboBox, QMessageBox, QListWidget,
    QLineEdit
)

from PyQt6.QtCore import Qt

CONFIG_PATH = Path.home() / ".config/waybar/config"


class WaybarConfigManager(QWidget):
    def __init__(self):
        super().__init__()

        # ================= WINDOW STYLE (OVERLAY) =================
        self.setWindowTitle("Waybar Overlay Manager")
        self.resize(380, 520)

        # floating overlay look
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        layout = QVBoxLayout()

        # ================= WAYBAR =================
        layout.addWidget(QLabel("Waybar Safe Editor"))

        self.position = QComboBox()
        self.position.addItems(["top", "bottom"])

        self.height = QSpinBox()
        self.height.setRange(20, 100)

        self.spacing = QSpinBox()
        self.spacing.setRange(0, 50)

        self.load_current_values()

        layout.addWidget(self.position)
        layout.addWidget(self.height)
        layout.addWidget(self.spacing)

        btn_row = QHBoxLayout()

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_waybar_safe)

        self.restart_btn = QPushButton("Restart")
        self.restart_btn.clicked.connect(self.restart_waybar)

        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.restart_btn)

        layout.addLayout(btn_row)

        # ================= WIFI =================
        layout.addWidget(QLabel("WiFi Manager"))

        self.wifi_list = QListWidget()
        self.wifi_list.setMinimumHeight(180)
        layout.addWidget(self.wifi_list)

        wifi_btns = QHBoxLayout()

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self.scan_wifi)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_wifi)

        wifi_btns.addWidget(self.scan_btn)
        wifi_btns.addWidget(self.connect_btn)

        layout.addLayout(wifi_btns)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("WiFi Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.setLayout(layout)

        # ================= CENTER =================
        self.center()

        # ================= STYLE =================
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 13px;
                border-radius: 20px;
            }

            QLabel {
                font-weight: bold;
                margin-top: 6px;
            }

            QComboBox, QSpinBox, QLineEdit, QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 20px;
                padding: 8px;
            }

            QPushButton {
                background-color: #2a2a2a;
                border-radius: 20px;
                padding: 8px;
            }

            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)

    # ================= CENTER WINDOW =================
    def center(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()

        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2

        self.move(x, y)

    # ================= LOAD CONFIG =================
    def load_current_values(self):
        try:
            text = CONFIG_PATH.read_text()

            def find(key, default):
                match = re.search(rf'"{key}"\s*:\s*("?)([^",\n]+)\1', text)
                return match.group(2) if match else default

            self.position.setCurrentText(find("position", "top"))

            try:
                self.height.setValue(int(find("height", 42)))
            except:
                self.height.setValue(42)

            try:
                self.spacing.setValue(int(find("spacing", 10)))
            except:
                self.spacing.setValue(10)

        except Exception:
            self.position.setCurrentText("top")
            self.height.setValue(42)
            self.spacing.setValue(10)

    # ================= SAFE PATCH =================
    def patch_field(self, key, value):
        text = CONFIG_PATH.read_text()

        if isinstance(value, str):
            pattern = rf'"{key}"\s*:\s*"(.*?)"'
            replacement = f'"{key}": "{value}"'
        else:
            pattern = rf'"{key}"\s*:\s*[0-9]+'
            replacement = f'"{key}": {value}'

        new_text = re.sub(pattern, replacement, text)
        CONFIG_PATH.write_text(new_text)

    def save_waybar_safe(self):
        try:
            backup = CONFIG_PATH.with_suffix(".bak")
            backup.write_text(CONFIG_PATH.read_text())

            self.patch_field("position", self.position.currentText())
            self.patch_field("height", self.height.value())
            self.patch_field("spacing", self.spacing.value())

            QMessageBox.information(self, "OK", "Saved safely")

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