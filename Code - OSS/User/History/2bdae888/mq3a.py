```python
#!/usr/bin/env python3

import os
import sys
import math
import subprocess
import tkinter as tk

from PIL import (
    Image,
    ImageTk,
    ImageEnhance,
    ImageFilter
)

# =========================
# CONFIG
# =========================

WALLPAPER_DIR = os.path.expanduser("~/Pictures")
STATE_FILE = os.path.expanduser("~/.cache/awww/wallpaper")

VALID_EXT = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
)

WINDOW_W = 950
WINDOW_H = 460

BG_COLOR = "#1e1e2e"
ACCENT = "#bd93f9"
TEXT_SUB = "#6272a4"

CENTER_W = 360
CENTER_H = 220

SIDE_W = 180
SIDE_H = 110

SPACING = 315

FPS_DELAY = 16
TOTAL_STEPS = 18


class WallpaperCarousel:

    def __init__(self, root):

        self.root = root

        self.root.title("Awww Wallpaper Picker")
        self.root.configure(bg=BG_COLOR)

        pos_x = (self.root.winfo_screenwidth() // 2) - (WINDOW_W // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (WINDOW_H // 2)

        self.root.geometry(
            f"{WINDOW_W}x{WINDOW_H}+{pos_x}+{pos_y}"
        )

        self.root.resizable(False, False)

        # =========================
        # LOAD WALLPAPERS
        # =========================

        try:
            self.wallpapers = sorted([
                os.path.join(WALLPAPER_DIR, f)
                for f in os.listdir(WALLPAPER_DIR)
                if f.lower().endswith(VALID_EXT)
            ])

        except FileNotFoundError:
            print(f"Directory not found: {WALLPAPER_DIR}")
            sys.exit(1)

        if not self.wallpapers:
            print("No wallpapers found.")
            sys.exit(1)

        # =========================
        # STATE
        # =========================

        self.current_idx = self.load_active_index()

        self.img_cache = {}

        # prevent tkinter image gc
        self.active_images = []

        self.is_animating = False

        # =========================
        # CANVAS
        # =========================

        self.canvas = tk.Canvas(
            root,
            width=WINDOW_W,
            height=WINDOW_H,
            bg=BG_COLOR,
            highlightthickness=0
        )

        self.canvas.pack(fill="both", expand=True)

        # =========================
        # POSITIONS
        # =========================

        self.x_left = 160
        self.x_center = 475
        self.x_right = 790

        self.y_center = 180

        # =========================
        # INITIAL RENDER
        # =========================

        self.render_carousel()

        # =========================
        # BINDS
        # =========================

        self.root.bind("<Right>", self.geser_kanan)
        self.root.bind("<Left>", self.geser_kiri)

        self.root.bind("<Return>", self.eksekusi_wallpaper)

        self.root.bind(
            "<Escape>",
            lambda e: self.root.destroy()
        )

    # =========================================================
    # LOAD ACTIVE INDEX
    # =========================================================

    def load_active_index(self):

        if os.path.exists(STATE_FILE):

            try:
                with open(STATE_FILE, "r") as f:
                    path = f.read().strip()

                if path in self.wallpapers:
                    return self.wallpapers.index(path)

            except Exception as e:
                print(f"Failed reading state file: {e}")

        return 0

    # =========================================================
    # IMAGE PROCESSING
    # =========================================================

    def get_processed_img(self, path, size, mode="normal"):

        # reduce cache explosion
        size = (
            round(size[0] / 10) * 10,
            round(size[1] / 10) * 10
        )

        cache_key = (path, size, mode)

        if cache_key in self.img_cache:
            return self.img_cache[cache_key]

        try:

            with Image.open(path) as raw_img:

                img = raw_img.convert("RGB")

                # =========================
                # BACKGROUND
                # =========================

                if mode == "bg":

                    img = img.resize(
                        (95, 46),
                        Image.Resampling.BILINEAR
                    )

                    img = img.filter(
                        ImageFilter.GaussianBlur(3)
                    )

                    img = ImageEnhance.Brightness(img).enhance(0.3)

                    img = img.resize(
                        (WINDOW_W, WINDOW_H),
                        Image.Resampling.BILINEAR
                    )

                # =========================
                # NORMAL IMAGE
                # =========================

                else:

                    img.thumbnail(size, Image.Resampling.LANCZOS)

                    canvas_img = Image.new(
                        "RGB",
                        size,
                        BG_COLOR
                    )

                    paste_x = (size[0] - img.width) // 2
                    paste_y = (size[1] - img.height) // 2

                    canvas_img.paste(img, (paste_x, paste_y))

                    img = canvas_img

                    if mode == "dim":
                        img = ImageEnhance.Brightness(img).enhance(0.35)

                tk_img = ImageTk.PhotoImage(img)

                self.img_cache[cache_key] = tk_img

                return tk_img

        except Exception as e:

            print(f"Failed loading image {path}")
            print(e)

            return None

    # =========================================================
    # RENDER
    # =========================================================

    def render_carousel(self, progress=0.0, direction=0):

        self.canvas.delete("all")

        # prevent image gc
        self.active_images.clear()

        total = len(self.wallpapers)

        # =========================
        # BACKGROUND
        # =========================

        if progress < 0.5:
            bg_idx = self.current_idx
        else:
            bg_idx = (self.current_idx + direction) % total

        bg_img = self.get_processed_img(
            self.wallpapers[bg_idx],
            (WINDOW_W, WINDOW_H),
            mode="bg"
        )

        if bg_img:

            self.active_images.append(bg_img)

            self.canvas.create_image(
                WINDOW_W // 2,
                WINDOW_H // 2,
                image=bg_img
            )

        # =========================
        # MOVEMENT
        # =========================

        step_x = -SPACING * direction * progress

        # =========================
        # DRAW ORDER
        # =========================

        render_items = []

        for idx in range(total):

            if idx == self.current_idx:

                x_start = self.x_center
                state = "current"

            elif idx == (self.current_idx - 1) % total:

                x_start = self.x_left
                state = "left"

            elif idx == (self.current_idx + 1) % total:

                x_start = self.x_right
                state = "right"

            elif idx == (self.current_idx - 2) % total and direction == -1:

                x_start = self.x_left - SPACING
                state = "outer_left"

            elif idx == (self.current_idx + 2) % total and direction == 1:

                x_start = self.x_right + SPACING
                state = "outer_right"

            else:
                continue

            x_now = x_start + step_x

            # =========================
            # SIZE INTERPOLATION
            # =========================

            if state == "current" and direction != 0:

                w = int(
                    CENTER_W - (CENTER_W - SIDE_W) * progress
                )

                h = int(
                    CENTER_H - (CENTER_H - SIDE_H) * progress
                )

                mode = "dim" if progress > 0.5 else "normal"

            elif (
                (
                    state == "left"
                    and direction == -1
                )
                or
                (
                    state == "right"
                    and direction == 1
                )
            ) and direction != 0:

                w = int(
                    SIDE_W + (CENTER_W - SIDE_W) * progress
                )

                h = int(
                    SIDE_H + (CENTER_H - SIDE_H) * progress
                )

                mode = "normal" if progress > 0.5 else "dim"

            else:

                w = SIDE_W
                h = SIDE_H

                mode = "dim"

            render_items.append({
                "idx": idx,
                "x": x_now,
                "w": w,
                "h": h,
                "state": state,
                "mode": mode
            })

        # =========================
        # LAYER ORDER
        # =========================

        layer_order = [
            "outer_left",
            "outer_right",
            "left",
            "right",
            "current"
        ]

        render_items.sort(
            key=lambda x: layer_order.index(x["state"])
        )

        # =========================
        # DRAW IMAGES
        # =========================

        for item in render_items:

            idx = item["idx"]

            x = item["x"]
            w = item["w"]
            h = item["h"]

            state = item["state"]
            mode = item["mode"]

            img = self.get_processed_img(
                self.wallpapers[idx],
                (w, h),
                mode
            )

            if not img:
                continue

            self.active_images.append(img)

            # =========================
            # BORDER
            # =========================

            should_draw_border = False

            if direction == 0 and idx == self.current_idx:
                should_draw_border = True

            elif (
                state == "current"
                and progress < 0.5
                and direction != 0
            ):
                should_draw_border = True

            elif (
                (
                    state == "left"
                    and direction == -1
                )
                or
                (
                    state == "right"
                    and direction == 1
                )
            ) and progress >= 0.5:

                should_draw_border = True

            if should_draw_border:

                self.canvas.create_rectangle(
                    x - w // 2 - 6,
                    self.y_center - h // 2 - 6,

                    x + w // 2 + 6,
                    self.y_center + h // 2 + 6,

                    outline=ACCENT,
                    width=4
                )

            self.canvas.create_image(
                x,
                self.y_center,
                image=img
            )

        # =========================
        # TEXT
        # =========================

        self.canvas.create_text(
            WINDOW_W // 2,
            365,
            text=os.path.basename(
                self.wallpapers[bg_idx]
            ),
            fill=ACCENT,
            font=("JetBrains Mono", 13, "bold")
        )

        self.canvas.create_text(
            WINDOW_W // 2,
            415,
            text=" Navigasi: ← → | Pilih: Enter | Keluar: Esc ",
            fill=TEXT_SUB,
            font=("JetBrains Mono", 10)
        )

    # =========================================================
    # ANIMATION
    # =========================================================

    def animate_slide(self, direction, step=0):

        if step <= TOTAL_STEPS:

            ratio = step / TOTAL_STEPS

            # smooth ease in/out
            progress = 0.5 * (
                1.0 - math.cos(ratio * math.pi)
            )

            self.render_carousel(
                progress=progress,
                direction=direction
            )

            self.root.after(
                FPS_DELAY,
                lambda: self.animate_slide(
                    direction,
                    step + 1
                )
            )

        else:

            self.current_idx = (
                self.current_idx + direction
            ) % len(self.wallpapers)

            self.render_carousel()

            self.is_animating = False

    # =========================================================
    # NAVIGATION
    # =========================================================

    def geser_kanan(self, event=None):

        if self.is_animating:
            return

        self.is_animating = True

        self.animate_slide(direction=1)

    def geser_kiri(self, event=None):

        if self.is_animating:
            return

        self.is_animating = True

        self.animate_slide(direction=-1)

    # =========================================================
    # APPLY WALLPAPER
    # =========================================================

    def eksekusi_wallpaper(self, event=None):

        if self.is_animating:
            return

        target = self.wallpapers[self.current_idx]

        os.makedirs(
            os.path.dirname(STATE_FILE),
            exist_ok=True
        )

        try:

            with open(STATE_FILE, "w") as f:
                f.write(target)

        except Exception as e:

            print(f"Failed writing state file: {e}")

        try:

            subprocess.run([
                "awww",
                "img",
                target,

                "--transition-type",
                "grow",

                "--transition-pos",
                "center"
            ], check=True)

        except FileNotFoundError:

            print("awww is not installed.")

        except subprocess.CalledProcessError as e:

            print(f"awww failed: {e}")

        self.root.destroy()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = WallpaperCarousel(root)

    root.mainloop()
```
