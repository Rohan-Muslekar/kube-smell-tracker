#!/usr/bin/env python3
"""Run a shell command from the repo root and save its output as a terminal-style PNG.

Usage: python3 results/render.py OUT.png 'COMMAND'
Needs Pillow (pip install pillow). Only used to make the images in results/screenshots/;
the pipeline itself is standard library only.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ("DejaVuSansMono.ttf", "/usr/share/fonts/google-noto-vf/NotoSansMono[wght].ttf",
         "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf", "Menlo.ttc", "Consolas.ttf")
SIZE, PAD, BAR = 16, 20, 34
BG, FG, PROMPT, BAR_BG = "#1e1e2e", "#cdd6f4", "#a6e3a1", "#313244"


def font():
    for name in FONTS:
        try:
            return ImageFont.truetype(name, SIZE)
        except OSError:
            continue
    return ImageFont.load_default(SIZE)


def main():
    out, command = Path(sys.argv[1]), sys.argv[2]
    run = subprocess.run(["bash", "-c", command], cwd=ROOT, capture_output=True, text=True)
    lines = (run.stdout + run.stderr).rstrip("\n").expandtabs(4).splitlines()
    f = font()
    char_w = f.getlength("M")
    line_h = int(SIZE * 1.45)
    width = int(PAD * 2 + char_w * max(len(l) for l in ["$ " + command, *lines]))
    height = BAR + PAD * 2 + line_h * (len(lines) + 1)
    img = Image.new("RGB", (max(width, 480), height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, BAR], fill=BAR_BG)
    for i, color in enumerate(("#f38ba8", "#f9e2af", "#a6e3a1")):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=color)
    y = BAR + PAD
    d.text((PAD, y), "$ " + command, font=f, fill=PROMPT)
    for line in lines:
        y += line_h
        d.text((PAD, y), line, font=f, fill=FG)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"{out} ({img.width}x{img.height}, exit {run.returncode})")


if __name__ == "__main__":
    main()
