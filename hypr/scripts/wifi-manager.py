#!/usr/bin/env python3

import sys
import subprocess

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer


# ============================================================
# NetworkManager helpers
# ============================================================

def nmcli(*args, timeout=5):
    """
    Jalankan nmcli dan kembalikan CompletedProcess.
    """
    return subprocess.run(
        ["nmcli", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def unescape_nmcli(value):
    """
    nmcli -t dapat melakukan escaping karakter.
    Tangani beberapa escape umum.
    """
    result = []
    escaped = False

    for char in value:
        if escaped:
            if char == ":":
                result.append(":")
            elif char == "\\":
                result.append("\\")
            elif char == "n":
                result.append("\n")
            else:
                result.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            result.append(char)

    if escaped:
        result.append("\\")

    return "".join(result)


def split_nmcli_line(line, expected_fields=2):
    """
    Split output nmcli -t sambil menangani escaped ':'.
    """
    fields = []
    current = []
    escaped = False

    for char in line:
        if escaped:
            current.append("\\")
            current.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == ":" and len(fields) < expected_fields - 1:
            fields.append("".join(current))
            current = []
        else:
            current.append(char)

    fields.append("".join(current))
    return [unescape_nmcli(field) for field in fields]


def enable_wifi_autoconnect(ssid):
    """
    Pastikan profile Wi-Fi disimpan dan NetworkManager akan
    melakukan reconnect otomatis jika koneksi terputus.

    Tidak ada timer/polling dari Python.
    NetworkManager sendiri yang menangani event disconnect.
    """
    try:
        # Aktifkan autoconnect.
        result = subprocess.run(
            [
                "nmcli",
                "connection",
                "modify",
                ssid,
                "connection.autoconnect",
                "yes",
                "connection.autoconnect-retries",
                "0",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return result.returncode == 0

    except (OSError, subprocess.SubprocessError):
        return False


# ============================================================
# WiFi status
# ============================================================

def get_wifi_status():
    """
    Mengambil status Wi-Fi aktif dari NetworkManager.

    Return:
        (connected: bool, ssid: str)
    """

    try:
        result = nmcli(
            "-t",
            "-e",
            "yes",
            "-f",
            "TYPE,STATE,CONNECTION",
            "device",
            timeout=3,
        )

        if result.returncode != 0:
            return False, ""

        for line in result.stdout.splitlines():
            parts = split_nmcli_line(line, 3)

            if len(parts) < 3:
                continue

            dev_type = parts[0].strip()
            state = parts[1].strip()
            connection = parts[2].strip()

            if dev_type == "wifi" and state == "connected":
                return True, connection

    except (subprocess.SubprocessError, OSError):
        pass

    return False, ""


# ============================================================
# WiFi status thread
# ============================================================

class WifiStatusThread(QThread):
    status_found = pyqtSignal(bool, str)

    def run(self):
        connected, ssid = get_wifi_status()
        self.status_found.emit(connected, ssid)


# ============================================================
# WiFi scan thread
# ============================================================

class WifiScanThread(QThread):
    networks_found = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, force_rescan=False):
        super().__init__()
        self.force_rescan = force_rescan

    def run(self):
        try:
            cmd = [
                "nmcli",
                "-t",
                "-e",
                "yes",
                "-f",
                "SSID,SIGNAL",
                "device",
                "wifi",
                "list",
            ]

            if self.force_rescan:
                cmd += ["--rescan", "yes"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                self.error_signal.emit(
                    result.stderr.strip()
                    or "Gagal melakukan scan Wi-Fi."
                )
                self.networks_found.emit([])
                return

            networks = {}

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                parts = split_nmcli_line(line, 2)

                if len(parts) < 2:
                    continue

                ssid = parts[0].strip()
                signal_text = parts[1].strip()

                if not ssid:
                    continue

                try:
                    signal = int(signal_text)
                except ValueError:
                    signal = 0

                # Jika SSID muncul beberapa kali,
                # gunakan signal tertinggi.
                if ssid not in networks:
                    networks[ssid] = signal
                else:
                    networks[ssid] = max(networks[ssid], signal)

            sorted_networks = sorted(
                networks.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )

            self.networks_found.emit(sorted_networks)

        except subprocess.TimeoutExpired:
            self.error_signal.emit("Scan Wi-Fi timeout.")
            self.networks_found.emit([])

        except (OSError, subprocess.SubprocessError) as exc:
            self.error_signal.emit(str(exc))
            self.networks_found.emit([])


# ============================================================
# WiFi connect thread
# ============================================================

class WifiConnectThread(QThread):
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, ssid, password):
        super().__init__()
        self.ssid = ssid
        self.password = password

    def run(self):
        try:
            cmd = [
                "nmcli",
                "device",
                "wifi",
                "connect",
                self.ssid,
            ]

            if self.password:
                cmd += [
                    "password",
                    self.password,
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Setelah berhasil, aktifkan NetworkManager
                # autoconnect tanpa perlu polling dari Python.
                enable_wifi_autoconnect(self.ssid)

                self.finished_signal.emit(
                    True,
                    self.ssid,
                    "",
                )
            else:
                error = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "Gagal terhubung ke Wi-Fi."
                )

                self.finished_signal.emit(
                    False,
                    self.ssid,
                    error,
                )

        except subprocess.TimeoutExpired:
            self.finished_signal.emit(
                False,
                self.ssid,
                "Koneksi Wi-Fi timeout.",
            )

        except (OSError, subprocess.SubprocessError) as exc:
            self.finished_signal.emit(
                False,
                self.ssid,
                str(exc),
            )


# ============================================================
# WiFi item
# ============================================================

class WifiItemWidget(QWidget):

    def __init__(self, ssid, signal, parent_overlay):
        super().__init__()

        self.ssid = ssid
        self.signal = signal
        self.parent_overlay = parent_overlay

        self.spinner_frames = [
            "⠋",
            "⠙",
            "⠹",
            "⠸",
            "⠼",
            "⠴",
            "⠦",
            "⠧",
            "⠇",
            "⠏",
        ]

        self.frame_idx = 0

        # Timer hanya untuk animasi tombol Connecting,
        # bukan untuk mengecek status Wi-Fi.
        self.loading_timer = QTimer(self)
        self.loading_timer.setInterval(100)
        self.loading_timer.timeout.connect(self.update_loading)

        self._build_ui()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(6)

        # ----------------------------------------------------
        # SSID row
        # ----------------------------------------------------

        header = QHBoxLayout()

        self.label = QLabel(self.ssid)

        self.label.setStyleSheet("""
            font-weight: bold;
            color: rgba(255, 255, 255, 0.95);
            background: transparent;
        """)

        signal_label = QLabel(f"{self.signal}%")

        signal_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.55);
            background: transparent;
            font-size: 11px;
        """)

        header.addWidget(self.label)
        header.addStretch()
        header.addWidget(signal_label)

        layout.addLayout(header)

        # ----------------------------------------------------
        # Password row
        # ----------------------------------------------------

        self.password_container = QWidget()

        password_layout = QHBoxLayout(self.password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(6)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password...")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(
            self.parent_overlay.connect_wifi
        )

        self.inline_connect_btn = QPushButton("Connect")
        self.inline_connect_btn.setObjectName("InlineConnectBtn")
        self.inline_connect_btn.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.inline_connect_btn.clicked.connect(
            self.parent_overlay.connect_wifi
        )

        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.inline_connect_btn)

        layout.addWidget(self.password_container)

        self.password_container.hide()

    # --------------------------------------------------------
    # Password
    # --------------------------------------------------------

    def show_password(self):
        self.password_container.show()
        self.password_input.setFocus()

    def hide_password(self):
        self.password_input.clear()
        self.password_container.hide()

    # --------------------------------------------------------
    # Loading
    # --------------------------------------------------------

    def start_loading(self):
        self.inline_connect_btn.setEnabled(False)
        self.password_input.setEnabled(False)

        self.frame_idx = 0
        self.inline_connect_btn.setText("⠋ Connecting...")
        self.loading_timer.start()

    def update_loading(self):
        icon = self.spinner_frames[
            self.frame_idx % len(self.spinner_frames)
        ]

        self.inline_connect_btn.setText(
            f"{icon} Connecting..."
        )

        self.frame_idx += 1

    def stop_loading(self):
        self.loading_timer.stop()
        self.inline_connect_btn.setEnabled(True)
        self.password_input.setEnabled(True)
        self.inline_connect_btn.setText("Connect")


# ============================================================
# Main Window
# ============================================================

class WifiManagerOverlay(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("WiFi Manager")

        # Ukuran overlay — dibuat sebagai konstanta seperti pada
        # Wallpaper Manager agar perhitungan posisi konsisten.
        WIN_W, WIN_H = 380, 460
        self.setFixedSize(WIN_W, WIN_H)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.active_widget = None

        self.status_thread = None
        self.scan_thread = None
        self.connect_thread = None

        self._closing = False

        self._build_ui()
        self.apply_style()

        # Center overlay seperti Wallpaper Manager:
        # hitung posisi X/Y dari ukuran layar dan ukuran window.
        # Pada X11 ini bekerja langsung; pada Wayland/Hyprland,
        # compositor tetap dapat mengambil alih posisi window.
        self.center_window()

        # Status hanya dicek sekali ketika aplikasi dibuka.
        # TIDAK ada timer untuk mengecek status setiap 5 detik.
        self.check_status()

        # Startup menggunakan cached scan, bukan force rescan.
        self.scan_wifi(False)

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.glass_box = QFrame()
        self.glass_box.setObjectName("GlassBox")

        container_layout = QVBoxLayout(self.glass_box)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(12)

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel("WiFi Manager")

        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.95);
        """)

        self.status_label = QLabel("Status: Checking...")

        self.status_label.setStyleSheet("""
            font-size: 11px;
            color: rgba(255, 255, 255, 0.6);
        """)

        title_box.addWidget(title)
        title_box.addWidget(self.status_label)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("CloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        container_layout.addLayout(header_layout)

        # ----------------------------------------------------
        # WiFi list
        # ----------------------------------------------------

        self.wifi_list = QListWidget()
        self.wifi_list.itemClicked.connect(
            self._on_wifi_selected
        )

        container_layout.addWidget(self.wifi_list)

        # ----------------------------------------------------
        # Refresh
        # ----------------------------------------------------

        self.scan_btn = QPushButton("Refresh Networks")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.refresh_wifi)

        container_layout.addWidget(self.scan_btn)

        main_layout.addWidget(self.glass_box)

    # ========================================================
    # Status (async)
    # ========================================================

    def check_status(self):
        if self.status_thread and self.status_thread.isRunning():
            return

        self.status_thread = WifiStatusThread()
        self.status_thread.status_found.connect(
            self._on_status_found
        )
        self.status_thread.finished.connect(
            self._status_thread_finished
        )
        self.status_thread.start()

    def _on_status_found(self, connected, ssid):
        if connected and ssid:
            self.status_label.setText(
                f"Status: Terhubung ke {ssid}"
            )

            self.status_label.setStyleSheet("""
                font-size: 11px;
                color: #50fa7b;
                font-weight: bold;
            """)

        else:
            self.status_label.setText(
                "Status: Tidak terhubung"
            )

            self.status_label.setStyleSheet("""
                font-size: 11px;
                color: #ff5555;
                font-weight: bold;
            """)

    def _status_thread_finished(self):
        self.status_thread = None

    # ========================================================
    # WiFi scan
    # ========================================================

    def scan_wifi(self, force_rescan=False):

        if self.scan_thread and self.scan_thread.isRunning():
            return

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText(
            "Scanning..." if force_rescan else "Loading..."
        )

        self.wifi_list.clear()
        self.active_widget = None

        self.scan_thread = WifiScanThread(force_rescan)

        self.scan_thread.networks_found.connect(
            self._on_scan_completed
        )

        self.scan_thread.error_signal.connect(
            self._on_scan_error
        )

        self.scan_thread.finished.connect(
            self._scan_thread_finished
        )

        self.scan_thread.start()

    def refresh_wifi(self):
        self.scan_wifi(True)

    def _on_scan_completed(self, networks):

        self.wifi_list.clear()

        if not networks:
            item = QListWidgetItem(
                "Tidak ada jaringan ditemukan."
            )

            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.wifi_list.addItem(item)
            return

        for ssid, signal in networks:
            item = QListWidgetItem()
            widget = WifiItemWidget(
                ssid,
                signal,
                self,
            )

            item.setSizeHint(widget.sizeHint())

            self.wifi_list.addItem(item)
            self.wifi_list.setItemWidget(
                item,
                widget,
            )

    def _on_scan_error(self, error):
        self.status_label.setText(
            "Status: Scan gagal"
        )

    def _scan_thread_finished(self):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText(
            "Refresh Networks"
        )

        self.scan_thread = None

        if self._closing:
            self._maybe_close()

    # ========================================================
    # WiFi selection
    # ========================================================

    def _on_wifi_selected(self, item):

        widget = self.wifi_list.itemWidget(item)

        if not widget:
            return

        if (
            self.active_widget
            and self.active_widget != widget
        ):
            self.active_widget.hide_password()

            for i in range(self.wifi_list.count()):
                old_item = self.wifi_list.item(i)

                if (
                    self.wifi_list.itemWidget(old_item)
                    == self.active_widget
                ):
                    old_item.setSizeHint(
                        self.active_widget.sizeHint()
                    )
                    break

        widget.show_password()
        item.setSizeHint(widget.sizeHint())

        self.active_widget = widget

    # ========================================================
    # Connect
    # ========================================================

    def connect_wifi(self):

        item = self.wifi_list.currentItem()

        if not item:
            return

        widget = self.wifi_list.itemWidget(item)

        if not widget:
            return

        ssid = widget.ssid
        password = widget.password_input.text()

        if (
            self.connect_thread
            and self.connect_thread.isRunning()
        ):
            return

        widget.start_loading()

        self.connect_thread = WifiConnectThread(
            ssid,
            password,
        )

        self.connect_thread.finished_signal.connect(
            lambda success, name, error:
            self._on_connect_finished(
                widget,
                item,
                success,
                name,
                error,
            )
        )

        self.connect_thread.finished.connect(
            self._connect_thread_finished
        )

        self.connect_thread.start()

    def _on_connect_finished(
        self,
        widget,
        item,
        success,
        ssid,
        error,
    ):

        widget.stop_loading()

        if success:

            self.status_label.setText(
                f"Status: Terhubung ke {ssid}"
            )

            self.status_label.setStyleSheet("""
                font-size: 11px;
                color: #50fa7b;
                font-weight: bold;
            """)

            widget.hide_password()
            item.setSizeHint(widget.sizeHint())

            # NetworkManager sudah diset:
            #
            # connection.autoconnect = yes
            # connection.autoconnect-retries = 0
            #
            # Jadi setelah Wi-Fi disconnect,
            # NetworkManager sendiri akan reconnect.
            # Tidak ada polling 5 detik dari Python.

            # Jangan QMessageBox.
            # Overlay terasa lebih ringan.
            self.close()

        else:
            QMessageBox.warning(
                self,
                "Gagal Koneksi",
                error,
            )

    def _connect_thread_finished(self):
        self.connect_thread = None

        if self._closing:
            self._maybe_close()

    # ========================================================
    # Keyboard
    # ========================================================

    def keyPressEvent(self, event):

        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return

        super().keyPressEvent(event)

    # ========================================================
    # Close handling
    #
    # Kalau ada thread background yang masih jalan, jangan
    # destroy window/app langsung (bisa crash/warning
    # "QThread destroyed while thread is still running").
    # Sembunyikan window dulu, lalu benar-benar close setelah
    # semua thread selesai.
    # ========================================================

    def closeEvent(self, event):

        active = [
            t
            for t in (
                self.status_thread,
                self.scan_thread,
                self.connect_thread,
            )
            if t and t.isRunning()
        ]

        if active:
            self._closing = True
            event.ignore()
            self.hide()
            return

        super().closeEvent(event)

    def _maybe_close(self):

        still_running = any(
            t and t.isRunning()
            for t in (
                self.status_thread,
                self.scan_thread,
                self.connect_thread,
            )
        )

        if not still_running:
            self.close()

    # ========================================================
    # Center overlay seperti Wallpaper Manager
    # ========================================================

    def center_window(self):

        screen = QApplication.primaryScreen()

        if not screen:
            return

        # Sama konsepnya dengan Wallpaper Manager:
        #   pos_x = (screen_width - WIN_W) // 2
        #   pos_y = (screen_height - WIN_H) // 2
        geometry = screen.geometry()

        x = geometry.x() + (
            geometry.width() - self.width()
        ) // 2

        y = geometry.y() + (
            geometry.height() - self.height()
        ) // 2

        self.setGeometry(
            x,
            y,
            self.width(),
            self.height()
        )

    # ========================================================
    # Styling
    # ========================================================

    def apply_style(self):

        self.setStyleSheet("""
            #GlassBox {
                background-color: rgba(25, 25, 35, 1);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 20px;
            }

            QWidget {
                color: rgba(255, 255, 255, 0.9);
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }

            QListWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 4px;
                outline: none;
            }

            QListWidget::item {
                border-radius: 8px;
                margin-bottom: 4px;
                background-color: rgba(255, 255, 255, 0.03);
            }

            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }

            QListWidget::item:selected {
                background-color: rgba(189, 147, 249, 0.2);
                border: 1px solid rgba(189, 147, 249, 0.4);
            }

            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 8px;
                padding: 6px 10px;
                color: #ffffff;
            }

            QLineEdit:focus {
                border: 1px solid rgba(189, 147, 249, 0.8);
                background-color: rgba(255, 255, 255, 0.15);
            }

            QLineEdit:disabled {
                background-color: rgba(255, 255, 255, 0.03);
                color: rgba(255, 255, 255, 0.3);
            }

            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 10px;
                padding: 8px 16px;
                font-weight: bold;
                color: rgba(255, 255, 255, 0.9);
            }

            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }

            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.45);
            }

            #InlineConnectBtn {
                background-color: rgba(189, 147, 249, 0.4);
                border: 1px solid rgba(189, 147, 249, 0.6);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                color: #ffffff;
            }

            #InlineConnectBtn:hover {
                background-color: rgba(189, 147, 249, 0.6);
                border: 1px solid rgba(189, 147, 249, 0.9);
            }

            #InlineConnectBtn:disabled {
                background-color: rgba(189, 147, 249, 0.2);
                border: 1px solid rgba(189, 147, 249, 0.3);
                color: rgba(255, 255, 255, 0.6);
            }

            #CloseBtn {
                background-color: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.5);
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }

            #CloseBtn:hover {
                color: #ff5555;
                background-color: transparent;
            }
        """)


# ============================================================
# Main
# ============================================================

def main():

    app = QApplication(sys.argv)

    # Penting untuk Hyprland/Wayland:
    # ini menentukan app_id window, dipakai untuk
    # match windowrulev2 di hyprland.conf.
    app.setDesktopFileName("wifi-manager")

    app.setQuitOnLastWindowClosed(True)

    window = WifiManagerOverlay()

    window.show()
    window.raise_()
    window.activateWindow()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


# ============================================================
# Catatan Hyprland (WAJIB dibaca)
# ============================================================
#
# Di X11, center_window() menghitung posisi overlay seperti
# Wallpaper Manager. Di Wayland/Hyprland, compositor dapat
# mengabaikan posisi yang diminta client. Karena itu rule
# "center" di bawah tetap disediakan sebagai fallback yang
# paling tepat untuk Hyprland.
#
# Tambahkan window rule ini di ~/.config/hypr/hyprland.conf
# (app_id "wifi-manager" cocok dengan app.setDesktopFileName):
#
#   windowrulev2 = float, class:^(wifi-manager)$
#   windowrulev2 = center, class:^(wifi-manager)$
#   windowrulev2 = size 380 460, class:^(wifi-manager)$
#   windowrulev2 = pin, class:^(wifi-manager)$
#   # opsional, biar berasa overlay ringan:
#   windowrulev2 = noborder, class:^(wifi-manager)$
#   windowrulev2 = noshadow, class:^(wifi-manager)$
#   windowrulev2 = animation slide, class:^(wifi-manager)$
#
# Kalau kamu launch scriptnya dari bind (misal buat toggle
# seperti rofi), pastikan hanya ada satu instance jalan
# (pakai pgrep/pkill di wrapper bash, atau exec-once) supaya
# tidak numpuk proses nmcli scan di background.
