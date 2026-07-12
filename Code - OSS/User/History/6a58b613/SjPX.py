#!/usr/bin/env python3

import os
import sys
import json
import time
import socket
import threading
import subprocess

MAX_LEN = 30
PAUSE_TIME = 10.0
SCROLL_DELAY = 0.2

class WindowScroller:
    def __init__(self):
        self.title = ""
        self.display = ""
        self.offset = 0
        self.changed = True
        self.running = True
        self.lock = threading.Lock()

    def set_title(self, title):
        with self.lock:
            if title != self.title:
                self.title = title.strip()
                self.offset = 0
                self.changed = True

    def output(self, text):
        print(json.dumps({"text": text}), flush=True)
        
    def marquee(self):
        while self.running:
            with self.lock:
                title = self.title if self.title else "Desktop"

            if len(title) <= MAX_LEN:
                self.output(title)
                time.sleep(0.5)
                continue

            if self.changed:
                self.output(title[:MAX_LEN] + "...")
                self.changed = False
                time.sleep(PAUSE_TIME)
                continue

            scroll = title + "   "
            if self.offset >= len(scroll):
                self.offset = 0
                self.changed = True
                continue

            doubled = scroll + scroll
            text = doubled[self.offset:self.offset + MAX_LEN]
            self.output(text)
            self.offset += 1
            time.sleep(SCROLL_DELAY)
            
    def get_socket():
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")

    if not runtime or not sig:
        print("Hyprland environment not found.", file=sys.stderr)
        sys.exit(1)

    return f"{runtime}/hypr/{sig}/.socket2.sock"


def listen(scroller):
    sock_path = get_socket()

    while True:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(sock_path)

            while True:
                data = sock.recv(4096)
                if not data:
                    break

                for line in data.decode(errors="ignore").splitlines():
                    if line.startswith("activewindow>>"):
                        parts = line.split(">>", 1)[1].split(",", 1)

                        if len(parts) == 2:
                            title = parts[1]
                        else:
                            title = ""

                        scroller.set_title(title)

        except Exception:
            time.sleep(1)

    def initial_title():
    try:
        result = subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return data.get("title", "")
    except Exception:
        return ""


def main():
    scroller = WindowScroller()
    scroller.set_title(initial_title())

    threading.Thread(
        target=listen,
        args=(scroller,),
        daemon=True,
    ).start()

    try:
        scroller.marquee()
    except KeyboardInterrupt:
        scroller.running = False


if __name__ == "__main__":
    main()