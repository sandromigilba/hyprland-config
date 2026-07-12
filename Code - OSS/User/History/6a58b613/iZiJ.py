#!/usr/bin/env python3

import json
import os
import socket
import threading
import time

MAX_LEN = 30
PAUSE = 10
SPEED = 0.20


class Marquee:

    def __init__(self):
        self.title = "Desktop"
        self.offset = 0
        self.pause = True
        self.lock = threading.Lock()

    def set_title(self, title):
        title = title.strip()

        if not title:
            title = "Desktop"

        with self.lock:
            if title != self.title:
                self.title = title
                self.offset = 0
                self.pause = True

    def current(self):
        with self.lock:
            title = self.title
            offset = self.offset
            pause = self.pause

        if len(title) <= MAX_LEN:
            return title

        if pause:
            return title[:MAX_LEN] + "..."

        scroll = title + "     "
        scroll = scroll + scroll

        return scroll[offset:offset + MAX_LEN]

    def tick(self):
        with self.lock:

            if len(self.title) <= MAX_LEN:
                return False

            if self.pause:
                self.pause = False
                return True

            self.offset += 1

            if self.offset >= len(self.title) + 5:
                self.offset = 0
                self.pause = True
                return True

        return False


marquee = Marquee()

def print_json(text):
    print(json.dumps({"text": text}), flush=True)


def get_socket_path():
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")

    if not runtime or not signature:
        raise RuntimeError("Hyprland is not running")

    return f"{runtime}/hypr/{signature}/.socket2.sock"


def handle_event(line):
    if not line.startswith("activewindow>>"):
        return

    try:
        payload = line.split(">>", 1)[1]
        parts = payload.split(",", 1)

        if len(parts) != 2:
            return

        window_class, window_title = parts
        marquee.set_title(window_title)

    except Exception:
        pass


def ipc_loop():
    sock_path = get_socket_path()

    while True:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(sock_path)

            buffer = ""

            while True:
                data = sock.recv(4096)

                if not data:
                    break

                buffer += data.decode(errors="ignore")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    handle_event(line)

        except Exception:
            time.sleep(1)

def render_loop():
    while True:
        text = marquee.current()
        print_json(text)

        changed = marquee.tick()

        if len(text) <= MAX_LEN:
            time.sleep(0.5)
            continue

        if changed:
            time.sleep(PAUSE)
        else:
            time.sleep(SPEED)


def main():
    threading.Thread(
        target=ipc_loop,
        daemon=True,
    ).start()

    render_loop()


if __name__ == "__main__":
    main()