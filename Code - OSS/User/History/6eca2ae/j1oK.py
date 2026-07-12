#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox,
    QComboBox, QMessageBox
)

CONFIG_PATH = Path.home() / ".config/waybar/config"


class WaybarConfigManager(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Waybar Config Manager")
        self.resize(500, 300)

        self.load_config()

        layout = QVBoxLayout()

        # Position
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position"))

        self.position = QComboBox()
        self.position.addItems(["top", "bottom"])
        self.position.setCurrentText(self.config.get("position", "top"))

        pos_layout.addWidget(self.position)
        layout.addLayout(pos_layout)

        # Height
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height"))

        self.height = QSpinBox()
        self.height.setRange(20, 100)
        self.height.setValue(self.config.get("height", 42))

        height_layout.addWidget(self.height)
        layout.addLayout(height_layout)

        # Spacing
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Spacing"))

        self.spacing = QSpinBox()
        self.spacing.setRange(0, 50)
        self.spacing.setValue(self.config.get("spacing", 10))

        spacing_layout.addWidget(self.spacing)
        layout.addLayout(spacing_layout)

        # Save button
        self.save_btn = QPushButton("Save Config")
        self.save_btn.clicked.connect(self.save_config)

        # Restart button
        self.restart_btn = QPushButton("Restart Waybar")
        self.restart_btn.clicked.connect(self.restart_waybar)

        layout.addWidget(self.save_btn)
        layout.addWidget(self.restart_btn)

        self.setLayout(layout)

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                text = f.read()

            # hapus komentar //
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

            QMessageBox.information(
                self,
                "Success",
                "Config saved successfully"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

    def restart_waybar(self):
        subprocess.run(["pkill", "waybar"])
        subprocess.Popen(["waybar"])

        QMessageBox.information(
            self,
            "Waybar",
            "Waybar restarted"
        )


if __name__ == "__main__":
    app = QApplication([])
    win = WaybarConfigManager()
    win.show()
    app.exec()