"""High-frequency e-paper explainer: George narration (vo/, from narrate.py + timing.py) over
animated scenes. Frames drawn with PIL on all cores, encoded on the Apple media engine.

Usage: make.py out.mp4          render the video
       make.py stills            one PNG per scene into stills/
"""
import json
import math
import multiprocessing as mp
import pathlib
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
W, H, FPS, SR = 1920, 1080, 30, 24000
INTRO, GAP, OUTRO = 1.8, 0.35, 2.6

BG, CARD, INK, INK2, MUTED, RULE = "#ffffff", "#f4f6f9", "#111820", "#47515f", "#8a94a1", "#dce1e8"
PY, VIPER, RED, GREEN, PSRAM, SRAM, AMBER = (
    "#3b6fd6", "#14998a", "#d94141", "#1d8a4c", "#e8662a", "#2a7fb8", "#c99a06")

AV = "/System/Library/Fonts/Avenir Next.ttc"
_fonts = {}


def F(size, face="demi"):
    idx = {"bold": 0, "demi": 2, "med": 5, "reg": 7, "heavy": 8}[face]
    key = (size, face)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(AV, size, index=idx)
    return _fonts[key]


def M(size, bold=False):
    key = (size, "mono", bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size, index=1 if bold else 0)
    return _fonts[key]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def seg(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def rgb(c):
    if isinstance(c, tuple):
        return c
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(c1, c2, k):
    a, b = rgb(c1), rgb(c2)
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def fade(c, k):
    return mix(BG, c, max(0.0, min(1.0, k)))


def tint(c, k=0.15):
    return mix(BG, c, k)


def text(d, xy, s, font, fill=INK, anchor="la"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor)


def rbox(d, box, fill, r=14, outline=None, width=0):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def eyebrow(d, s, k=1.0):
    text(d, (W // 2, 105), s.upper(), M(28), fill=fade(MUTED, k), anchor="mm")


def arrow(d, a, b, fill=INK2, width=5, head=18):
    d.line((a, b), fill=fill, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    p1 = (b[0] - head * math.cos(ang - 0.45), b[1] - head * math.sin(ang - 0.45))
    p2 = (b[0] - head * math.cos(ang + 0.45), b[1] - head * math.sin(ang + 0.45))
    d.polygon([b, p1, p2], fill=fill)


def part_arrow(d, a, b, k, fill=INK2, width=5):
    if k <= 0:
        return
    e = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    arrow(d, a, e, fill=fill, width=width)


def dashed_v(d, x, y0, y1, fill, dash=14, width=4):
    y = y0
    while y < y1:
        d.line((x, y, x, min(y1, y + dash)), fill=fill, width=width)
        y += dash * 2


def node(d, box, title, sub=None, color=INK2, k=1.0, title_size=36):
    if k <= 0:
        return
    x0, y0, x1, y1 = box
    rbox(d, box, fade(tint(color, 0.12), k), r=16, outline=fade(color, k), width=4)
    cy = (y0 + y1) / 2 - (16 if sub else 0)
    text(d, ((x0 + x1) / 2, cy), title, F(title_size, "bold"), fill=fade(INK, k), anchor="mm")
    if sub:
        text(d, ((x0 + x1) / 2, cy + 40), sub, F(26, "med"), fill=fade(color, k), anchor="mm")


def load_bars(d, rows, t, x=520, y=250, w=1080, bh=70, gap=34, vmax=500, label_w=470,
              hundred=True):
    """rows: (label, value %, appear time, sublabel). Bars red over 100, green under."""
    xs = x + w * 100 / vmax
    if hundred:
        dashed_v(d, xs, y - 40, y + len(rows) * (bh + gap), INK2)
        text(d, (xs, y - 52), "100% = real time", F(26, "demi"), fill=INK2, anchor="ms")
    for i, row in enumerate(rows):
        label, v, at, sub = row[:4]
        k = seg(t, at, at + 0.9)
        if k <= 0:
            continue
        yy = y + i * (bh + gap)
        text(d, (x - 24, yy + bh / 2 - (12 if sub else 0)), label, F(32, "demi"),
             fill=fade(INK, k), anchor="rm")
        if sub:
            text(d, (x - 24, yy + bh / 2 + 22), sub, F(23, "med"), fill=fade(MUTED, k), anchor="rm")
        vv = v * k
        col = row[4] if len(row) > 4 else (RED if v > 100 else GREEN)
        bw = max(6, w * min(vv, vmax) / vmax)
        rbox(d, (x, yy, x + bw, yy + bh), fade(col, k), r=10)
        txt = f"{vv:.0f}%" if v >= 10 else f"{vv:.1f}%"
        f = F(44, "heavy")
        tb = d.textbbox((x + bw + 18, yy + bh / 2), txt, font=f, anchor="lm")
        d.rectangle((tb[0] - 6, tb[1] - 4, tb[2] + 6, tb[3] + 4), fill=BG)
        text(d, (x + bw + 18, yy + bh / 2), txt, f, fill=fade(col, k), anchor="lm")


# ---------------------------------------------------------------- scenes

PINK, INKBLK, PAPER, BLUE, PURPLE = "#e0457b", "#1b1f24", "#e9e6dc", "#2a7fb8", "#7a4fc9"

_ghost = Image.open(HERE / "ghost.png").convert("RGB").crop((300, 200, 1010, 690))
_ga = np.asarray(_ghost).astype(np.float32)
_ga = np.clip((_ga - _ga.min()) * (255 / max(1, np.percentile(_ga, 99.5) - _ga.min())), 0, 255)
GHOST = Image.fromarray(_ga.astype(np.uint8)).resize((780, 539))


def panel(d, box, k=1.0, fill=PAPER):
    x0, y0, x1, y1 = box
    rbox(d, (x0 - 34, y0 - 34, x1 + 34, y1 + 34), fade(PINK, k), r=22)
    d.rectangle(box, fill=fade(fill, k))


def pill(d, cx, cy, s, col, k=1.0, size=34):
    f = F(size, "bold")
    w = d.textlength(s, font=f)
    rbox(d, (cx - w / 2 - 30, cy - 34, cx + w / 2 + 30, cy + 34), fade(tint(col, .14), k), r=34)
    text(d, (cx, cy), s, f, fill=fade(col, k), anchor="mm")


def s_panel(d, t, T):
    eyebrow(d, "the panel")
    k1 = seg(t, 0, .7)
    panel(d, (300, 260, 900, 710), k1)
    text(d, (600, 485), "400 x 300", F(64, "heavy"), fill=fade(INK2, k1), anchor="mm")
    k2 = seg(t, 2.0, 2.8)
    rbox(d, (520, 744, 680, 800), fade(INKBLK, k2), r=6)
    text(d, (600, 772), "SSD1683", M(26, True), fill=fade("#ffffff", k2), anchor="mm")
    text(d, (600, 195), "Adafruit 4.2\" #6381 · ZJY400300-042CAAMFGN", F(28, "med"),
         fill=fade(MUTED, k1), anchor="ms")
    k3 = seg(t, 4.0, 4.8)
    if k3 > 0:
        cx, cy, r = 1400, 470, 170
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=fade(RULE, k3), width=22)
        p = seg(t, 4.0, min(T - .5, 10.0))
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * p, fill=fade(RED, k3), width=22)
        text(d, (cx, cy - 10), f"{6.0 * p:.1f} s", F(80, "heavy"), fill=fade(RED, k3), anchor="mm")
        text(d, (cx, cy + 60), "stock refresh", F(32, "demi"), fill=fade(INK2, k3), anchor="mm")
        text(d, (cx, cy + 240), "5966 ms measured · 0.17 fps", F(30, "med"), fill=fade(MUTED, k3),
             anchor="mm")


def capsule(d, cx, cy, up_black, k=1.0):
    r = 70
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fade(CARD, k), outline=fade(INK2, k), width=4)
    import random
    rng = random.Random(int(cx))
    for i in range(14):
        ox = rng.uniform(-40, 40)
        jy = rng.uniform(-12, 12)
        by = cy + (-38 + 76 * (1 - up_black)) + jy
        wy = cy + (38 - 76 * (1 - up_black)) + jy
        if i % 2:
            d.ellipse((cx + ox - 11, by - 11, cx + ox + 11, by + 11), fill=fade(INKBLK, k))
        else:
            d.ellipse((cx + ox - 11, wy - 11, cx + ox + 11, wy + 11), fill=fade("#ffffff", k),
                      outline=fade(MUTED, k), width=2)


def s_ink(d, t, T):
    eyebrow(d, "how e-paper moves")
    k = seg(t, 0, .6)
    text(d, (960, 230), "viewer", F(30, "demi"), fill=fade(MUTED, k), anchor="mm")
    d.line((330, 260, 1590, 260), fill=fade(RULE, k), width=4)
    for i in range(5):
        cx = 480 + i * 240
        dur = (i + 1) * 0.6
        p = seg(t, 2.6, 2.6 + dur)
        capsule(d, cx, 400, p, k)
        kv = seg(t, 2.6, 3.0)
        rbox(d, (cx - 80, 500, cx + 80, 540), fade(tint(BLUE, .35), kv), r=6)
        text(d, (cx, 580), f"{i + 1} frame" + ("s" if i else ""), F(28, "demi"), fill=fade(BLUE, kv),
             anchor="mm")
    k3 = seg(t, T * .62, T * .75)
    if k3 > 0:
        rbox(d, (510, 660, 1410, 770), fade(tint(AMBER, .14), k3), r=50)
        text(d, (960, 715), "ink travel grows with voltage × time", F(48, "bold"),
             fill=fade(AMBER, k3), anchor="mm")


def s_freq(d, t, T):
    eyebrow(d, "two different frequencies")
    k1 = seg(t, 2.0, 2.8)
    if k1 > 0:
        text(d, (520, 220), "frame rate", F(52, "heavy"), fill=fade(BLUE, k1), anchor="mm")
        box = (300, 290, 740, 620)
        panel(d, box, k1)
        y = 290 + (t * 125 * 330 / 10) % 330
        d.rectangle((300, y - 4, 740, y + 4), fill=fade(BLUE, k1))
        text(d, (520, 700), "controller scans every row", F(32, "demi"), fill=fade(INK2, k1), anchor="mm")
        text(d, (520, 750), "112.5 or 125 Hz", F(40, "bold"), fill=fade(BLUE, k1), anchor="mm")
    k2 = seg(t, T * .66, T * .76)
    if k2 > 0:
        text(d, (1400, 220), "update rate", F(52, "heavy"), fill=fade(GREEN, k2), anchor="mm")
        n = int(t * 3) % 4
        for i in range(3, -1, -1):
            o = i * 28
            box = (1200 + o, 300 + o, 1560 + o, 560 + o)
            d.rectangle(box, fill=fade(PAPER if i else "#ffffff", k2), outline=fade(INK2, k2), width=3)
        sq = 1210 + 70 * n
        d.rectangle((sq, 320, sq + 90, 410), fill=fade(INKBLK, k2))
        text(d, (1420, 700), "new pictures per second", F(32, "demi"), fill=fade(INK2, k2), anchor="mm")
        text(d, (1420, 750), "fps", F(40, "bold"), fill=fade(GREEN, k2), anchor="mm")


def s_wave(d, t, T):
    eyebrow(d, "a waveform is a list of frames")
    k = seg(t, 0, .7)
    text(d, (960, 240), "update time  =  frames ÷ frame rate", F(60, "bold"), fill=fade(INK, k), anchor="mm")
    k2 = seg(t, T * .4, T * .5)
    if k2 > 0:
        text(d, (230, 395), "stock full", F(34, "bold"), fill=fade(INK, k2), anchor="lm")
        x0, x1 = 480, 1690
        n = 24
        p = seg(t, T * .4, T * .95)
        for i in range(int(n * p)):
            xa = x0 + (x1 - x0) * i / n
            col = INKBLK if i % 2 == 0 else "#ffffff"
            d.rectangle((xa, 360, xa + (x1 - x0) / n - 2, 430), fill=fade(col, k2), outline=fade(INK2, k2))
        text(d, (x1, 470), "~6 s of flashing black and white (illustrative)", F(26, "med"),
             fill=fade(MUTED, k2), anchor="rm")
    k3 = seg(t, T * .6, T * .7)
    if k3 > 0:
        text(d, (230, 595), "ours", F(34, "bold"), fill=fade(INK, k3), anchor="lm")
        for i in range(4):
            xa = 480 + i * 14
            d.rectangle((xa, 560, xa + 11, 630), fill=fade(GREEN, k3))
        text(d, (560, 595), "4 frames ÷ 125 Hz = 32 ms", F(40, "bold"), fill=fade(GREEN, k3), anchor="lm")


def s_ladder(d, t, T):
    eyebrow(d, "what we measured")
    rows = [("stock 0xF7 full", .17, "5966 ms"), ("20-frame LUT", 3.0, "337 ms"),
            ("6 frames, full RAM", 11.1, "90 ms"), ("6 frames, row bands", 15.0, "66.8 ms"),
            ("4 frames, 112.5 Hz", 20.4, "49.0 ms"), ("4 frames, 125 Hz", 22.2, "45.0 ms")]
    x, y, w, bh, gap, vmax = 640, 210, 1000, 64, 32, 25
    ats = [0.6, 3.6, 6.0, 8.0, 10.8, 12.3]
    for i, ((lab, v, ms), at) in enumerate(zip(rows, ats)):
        k = seg(t, at, at + .8)
        if k <= 0:
            continue
        yy = y + i * (bh + gap)
        text(d, (x - 24, yy + bh / 2 - 12), lab, F(32, "demi"), fill=fade(INK, k), anchor="rm")
        text(d, (x - 24, yy + bh / 2 + 22), ms + " / frame", F(23, "med"), fill=fade(MUTED, k), anchor="rm")
        col = GREEN if i == 5 else (BLUE if i else RED)
        bw = max(6, w * v * k / vmax)
        rbox(d, (x, yy, x + bw, yy + bh), fade(col, k), r=10)
        s = f"{v * k:.2f} fps" if v < 1 else f"{v * k:.1f} fps"
        text(d, (x + bw + 18, yy + bh / 2), s, F(42, "heavy"), fill=fade(col, k), anchor="lm")


def pulses(d, x, y, n, col, k, w=34, h=60):
    for i in range(n):
        d.rectangle((x + i * (w + 8), y, x + i * (w + 8) + w, y + h), fill=fade(col, k))


def s_lut(d, t, T):
    eyebrow(d, "trick 1 · our own waveform (0x32)")
    cells = [("white → black", INKBLK, "#ffffff", 4, BLUE, "VSH1 × 4 frames", 1.5),
             ("black → white", "#ffffff", INKBLK, 4, PURPLE, "VSL × 4 frames", 3.2),
             ("white → white", "#ffffff", "#ffffff", 0, MUTED, "0 V", 5.5),
             ("black → black", INKBLK, INKBLK, 0, MUTED, "0 V", 5.5)]
    for i, (lab, to, frm, n, col, sub, at) in enumerate(cells):
        k = seg(t, at, at + .7)
        if k <= 0:
            continue
        cx = 300 + (i % 2) * 700
        cy = 230 + (i // 2) * 260
        rbox(d, (cx, cy, cx + 620, cy + 220), fade(CARD, k), r=18)
        text(d, (cx + 30, cy + 50), lab, M(34, True), fill=fade(INK, k), anchor="lm")
        d.rectangle((cx + 30, cy + 100, cx + 110, cy + 180), fill=fade(frm, k), outline=fade(INK2, k), width=3)
        text(d, (cx + 135, cy + 140), "→", M(40, True), fill=fade(INK2, k), anchor="mm")
        d.rectangle((cx + 160, cy + 100, cx + 240, cy + 180), fill=fade(to, k), outline=fade(INK2, k), width=3)
        if n:
            pulses(d, cx + 290, cy + 105, n, col, k)
        text(d, (cx + 290, cy + 200), sub, F(28, "bold"), fill=fade(col, k), anchor="ls")
    k = seg(t, T * .78, T * .88)
    if k > 0:
        text(d, (960, 820), "make_lut(4, to_black=VSH1, to_white=VSL, fr=0x05)", M(36, True),
             fill=fade(VIPER, k), anchor="mm")


def s_overhead(d, t, T):
    eyebrow(d, "trick 2 · stop paying overhead")
    items = [(1.0, "0x22 = 0xCC once", "power up the analog side", "then 0x0C: display only, each frame", BLUE),
             (5.6, "0x37 ping-pong off", "the controller stops swapping RAMs", "so partial writes stay correct", PURPLE),
             (7.6, "row-band writes", "send only rows that changed", "both RAMs: 0x24 new, 0x26 old", GREEN)]
    for i, (at, a, b, c, col) in enumerate(items):
        k = seg(t, at, at + .7)
        if k <= 0:
            continue
        y = 210 + i * 210
        rbox(d, (240, y, 1680, y + 170), fade(tint(col, .1), k), r=20, outline=fade(col, k), width=3)
        text(d, (290, y + 85), a, M(38, True), fill=fade(col, k), anchor="lm")
        text(d, (900, y + 62), b, F(36, "bold"), fill=fade(INK, k), anchor="lm")
        text(d, (900, y + 112), c, F(30, "med"), fill=fade(INK2, k), anchor="lm")


def s_fr(d, t, T):
    eyebrow(d, "trick 3 · frame rate (SSD1683 table 6-7)")
    rows = [("0001", "25"), ("0010", "50"), ("0011", "75"), ("0100", "100"), ("0101", "125"),
            ("1001", "37.5"), ("1010", "62.5"), ("1011", "87.5"), ("1100", "112.5")]
    k = seg(t, 0, .7)
    x, y = 260, 210
    text(d, (x, y), "FR[3:0]", M(30, True), fill=fade(MUTED, k), anchor="ls")
    text(d, (x + 260, y), "Hz", M(30, True), fill=fade(MUTED, k), anchor="ls")
    k_old = seg(t, 1.0, 1.6)
    k_new = seg(t, T * .35, T * .48)
    for i, (b, hz) in enumerate(rows):
        yy = y + 30 + i * 58
        col = INK2
        if b == "1100" and k_old > 0:
            rbox(d, (x - 20, yy, x + 420, yy + 50), fade(tint(AMBER, .2), k_old), r=8)
            col = AMBER
        if b == "0101" and k_new > 0:
            rbox(d, (x - 20, yy, x + 420, yy + 50), fade(tint(GREEN, .2), k_new), r=8)
            col = GREEN
        text(d, (x, yy + 25), b, M(34), fill=fade(col, k), anchor="lm")
        text(d, (x + 260, yy + 25), hz, M(34, True), fill=fade(col, k), anchor="lm")
    if k_old > 0:
        text(d, (x + 440, y + 30 + 8 * 58 + 25), "\"max\" in our notes", F(28, "demi"),
             fill=fade(AMBER, k_old), anchor="lm")
    if k_new > 0:
        text(d, (x + 440, y + 30 + 4 * 58 + 25), "real max", F(28, "demi"), fill=fade(GREEN, k_new), anchor="lm")
    kb = seg(t, T * .6, T * .7)
    if kb > 0:
        bx, by, bw = 1050, 330, 600
        text(d, (bx, by - 40), "4-frame demo, 3 runs each", F(30, "demi"), fill=fade(INK2, kb), anchor="ls")
        for i, (lab, v, col) in enumerate((("112.5 Hz", 49.0, AMBER), ("125 Hz", 45.0, GREEN))):
            kk = seg(t, T * .6 + i * .8, T * .7 + i * .8)
            yy = by + i * 130
            text(d, (bx, yy), lab, F(30, "demi"), fill=fade(INK, kk), anchor="lm")
            ww = bw * v / 55 * kk
            rbox(d, (bx, yy + 30, bx + ww, yy + 90), fade(col, kk), r=10)
            text(d, (bx + ww + 14, yy + 60), f"{v * kk:.1f} ms", F(40, "heavy"), fill=fade(col, kk), anchor="lm")
        k3 = seg(t, T * .85, T * .95)
        text(d, (bx + 300, by + 330), "20.4 to 22.2 fps", F(54, "heavy"), fill=fade(GREEN, k3), anchor="mm")


def s_budget(d, t, T):
    eyebrow(d, "where 45 ms goes")
    parts = [("panel busy", 32.0, "4 ÷ 125 Hz", BLUE, 1.6), ("SPI", 8.7, "20 MHz", PURPLE, 3.6),
             ("Python", 2.9, "", AMBER, 4.8)]
    x0, x1, y = 260, 1660, 380
    tot = 45.0
    x = x0
    for lab, v, sub, col, at in parts:
        k = seg(t, at, at + .7)
        w = (x1 - x0) * v / tot
        if k > 0:
            rbox(d, (x, y, x + w * k, y + 140), fade(col, k), r=8)
            text(d, (x + w / 2, y + 200), f"{lab}", F(34, "bold"), fill=fade(col, k), anchor="mm")
            text(d, (x + w / 2, y + 245), f"{v:g} ms", F(32, "demi"), fill=fade(INK2, k), anchor="mm")
            if sub:
                text(d, (x + w / 2, y + 70), sub, F(30, "bold"), fill=fade("#ffffff", k), anchor="mm")
        x += w
    k = seg(t, 5.5, 6.2)
    text(d, (960, 760), "busy is computed; SPI and Python were measured at 112.5 Hz",
         F(28, "med"), fill=fade(MUTED, k), anchor="mm")


def s_cost(d, t, T):
    eyebrow(d, "the cost")
    k = seg(t, 0, .8)
    if k > 0:
        im = Image.blend(Image.new("RGB", GHOST.size, BG), GHOST, k)
        d._image.paste(im, (200, 190))
        text(d, (590, 770), "camera still, 4-frame demo (brightened)", F(26, "med"), fill=fade(MUTED, k),
             anchor="mm")
    for i, (at, s, col) in enumerate(((T * .3, "black turns mid-gray", INK2), (T * .5, "ghost trail", RED),
                                      (T * .78, "full refresh 0xF7 clears it", GREEN))):
        kk = seg(t, at, at + .6)
        if kk > 0:
            pill(d, 1450, 330 + i * 150, s, col, kk, 36)


def s_paperboy(d, t, T):
    eyebrow(d, "what PaperBoy does differently")
    k1 = seg(t, 0, .8)
    text(d, (500, 215), "Adafruit SSD1683", F(40, "heavy"), fill=fade(INK, k1), anchor="mm")
    node(d, (330, 260, 670, 360), "RP2040", "SPI · new image", PY, k1, 36)
    arrow(d, (500, 365), (500, 410), fill=fade(INK2, k1))
    rbox(d, (300, 415, 700, 600), fade(tint(INKBLK, .08), k1), r=16, outline=fade(INKBLK, k1), width=4)
    text(d, (500, 455), "SSD1683 controller", F(34, "bold"), fill=fade(INK, k1), anchor="mm")
    for j, s in enumerate(("fixed LUT per transition", "frame rate ≤ 125 Hz", "you wait on BUSY")):
        text(d, (500, 500 + j * 34), s, F(26, "med"), fill=fade(INK2, k1), anchor="mm")
    arrow(d, (500, 605), (500, 650), fill=fade(INK2, k1))
    panel(d, (360, 680, 640, 770), k1)
    k2 = seg(t, 1.2, 2.2)
    if k2 > 0:
        text(d, (1420, 215), "PaperBoy · M5PaperS3", F(40, "heavy"), fill=fade(INK, k2), anchor="mm")
        node(d, (1250, 260, 1590, 360), "ESP32-S3", "parallel bus", VIPER, k2, 36)
        k3 = seg(t, 3.5, 4.5)
        arrow(d, (1420, 365), (1420, 410), fill=fade(INK2, k3))
        rbox(d, (1220, 415, 1620, 600), fade(tint(VIPER, .1), k3), r=16, outline=fade(VIPER, k3), width=4)
        text(d, (1420, 455), "no controller", F(34, "bold"), fill=fade(VIPER, k3), anchor="mm")
        for j, s in enumerate(("host drives rows + columns", "any voltage, any pixel", "every frame")):
            text(d, (1420, 500 + j * 34), s, F(26, "med"), fill=fade(INK2, k3), anchor="mm")
        arrow(d, (1420, 605), (1420, 650), fill=fade(INK2, k3))
        panel(d, (1280, 680, 1560, 770), k3)
        y = 680 + (t * 900) % 90
        d.line((1280, y, 1560, y), fill=fade(VIPER, k3), width=4)
    k4 = seg(t, T * .75, T * .85)
    if k4 > 0:
        pill(d, 960, 520, "up to 60 fps", VIPER, k4, 34)
        text(d, (960, 590), "160x144 area x3 · reported", F(24, "med"), fill=fade(MUTED, k4), anchor="mm")


def s_inkboy(d, t, T):
    eyebrow(d, "InkBoy · ~30 fps with a controller (reported)")
    k = seg(t, 0, .7)
    n = 8
    x0, y0, s = 330, 260, 90
    for i in range(n):
        p = seg(t, 2.5 + i * .35, 2.5 + i * .35 + T * .45)
        left = round(8 - 8 * p * (0.5 + 0.5 * (i % 4) / 3))
        g = int(30 + (225 * (8 - left) / 8))
        x = x0 + i * (s + 50)
        d.rectangle((x, y0, x + s, y0 + s), fill=fade((g, g, g), k), outline=fade(INK2, k), width=3)
        for j in range(8):
            col = AMBER if j < left else RULE
            d.rectangle((x + 8 + j * 10, y0 + s + 20, x + 14 + j * 10, y0 + s + 60), fill=fade(col, k))
        text(d, (x + s / 2, y0 + s + 95), f"{left} left", F(24, "demi"), fill=fade(INK2, k), anchor="mm")
    text(d, (960, 230), "each pixel: a budget of drive pulses", F(32, "demi"), fill=fade(INK2, k), anchor="ms")
    for i, (at, s2, col) in enumerate(((T * .25, "2-step waveform (was ~17)", BLUE),
                                       (T * .55, "6-8 pulses = full black to white", AMBER),
                                       (T * .55, "only changed pixels driven", GREEN))):
        kk = seg(t, at, at + .6)
        if kk > 0:
            pill(d, 960, 600 + i * 95, s2, col, kk, 30)


def s_route(d, t, T):
    eyebrow(d, "the route for Adafruit panels")
    rows = [("today, measured", 22.2, GREEN, "4 frames · 125 Hz", 0.3, False),
            ("+ write during BUSY", 26, AMBER, "overlap SPI with drive", 2.5, True),
            ("2-frame LUT + budgets", 35, AMBER, "InkBoy-style on SSD1683", 6.2, True),
            ("both", 50, AMBER, "if overlap works", 9.5, True),
            ("1 frame per update", 65, RED, "nobody has shown it", 11.5, True)]
    x, y, w, bh, gap, vmax = 640, 210, 1000, 66, 34, 75
    for i, (lab, v, col, sub, at, est) in enumerate(rows):
        k = seg(t, at, at + .8)
        if k <= 0:
            continue
        yy = y + i * (bh + gap)
        text(d, (x - 24, yy + bh / 2 - 12), lab, F(32, "demi"), fill=fade(INK, k), anchor="rm")
        text(d, (x - 24, yy + bh / 2 + 22), sub, F(23, "med"), fill=fade(MUTED, k), anchor="rm")
        bw = w * v * k / vmax
        if est:
            rbox(d, (x, yy, x + bw, yy + bh), fade(tint(col, .25), k), r=10, outline=fade(col, k), width=3)
        else:
            rbox(d, (x, yy, x + bw, yy + bh), fade(col, k), r=10)
        s = ("~" if est else "") + (f"{v:g}" if i < 4 else "60-70") + " fps" + (" est." if est else "")
        text(d, (x + bw + 18, yy + bh / 2), s, F(38, "heavy"), fill=fade(col, k), anchor="lm")


def s_risk(d, t, T):
    eyebrow(d, "is it safe?")
    k = seg(t, 0, .6)
    text(d, (960, 230), "not proven either way", F(64, "heavy"), fill=fade(RED, k), anchor="mm")
    cards = [("Good Display FAQ", "pushing the frame rate too high", "can damage the panel", 2.6),
             ("Krasnow blog, reader", "burn-in after ~10,000", "fast cycles", 6.5),
             ("InkBoy README", "custom waveforms may cause", "permanent image retention", 10.0)]
    for i, (src, a, b, at) in enumerate(cards):
        kk = seg(t, at, at + .7)
        if kk <= 0:
            continue
        x0 = 170 + i * 540
        rbox(d, (x0, 340, x0 + 500, 640), fade(tint(RED, .08), kk), r=18, outline=fade(RED, kk), width=3)
        text(d, (x0 + 250, 400), src, F(32, "heavy"), fill=fade(RED, kk), anchor="mm")
        text(d, (x0 + 250, 500), a, F(28, "demi"), fill=fade(INK, kk), anchor="mm")
        text(d, (x0 + 250, 545), b, F(28, "demi"), fill=fade(INK, kk), anchor="mm")
    k2 = seg(t, T * .85, T * .95)
    text(d, (960, 740), "risks: net DC charge · overdrive · skipping clean refreshes", F(32, "demi"),
         fill=fade(INK2, k2), anchor="mm")


def s_safe(d, t, T):
    eyebrow(d, "keeping the risk down")
    items = [("equal frames to black and white", "charge balances: 4 x VSH1, 4 x VSL", 0.8),
             ("0 V on unchanged pixels", "LUTWW and LUTBB stay at VSS", 3.6),
             ("stock voltages", "Adafruit_EPD values, no overdrive", 5.6),
             ("datasheet frame rates only", "125 Hz is the top of the table", 7.0),
             ("regular full refreshes", "vendors: every 5-10 fast updates", 8.6),
             ("power down when done", "0xCC leaves the high voltage on", 10.6),
             ("no animating for hours", "wear rate unmeasured", 12.4)]
    for i, (a, b, at) in enumerate(items):
        k = seg(t, at, at + .6)
        if k <= 0:
            continue
        col, row = i // 4, i % 4
        x = 200 + col * 820
        y = 200 + row * 150
        d.ellipse((x, y, x + 56, y + 56), fill=fade(GREEN, k))
        d.line((x + 14, y + 29, x + 25, y + 41, x + 43, y + 17), fill=fade("#ffffff", k), width=7)
        text(d, (x + 80, y + 18), a, F(34, "bold"), fill=fade(INK, k), anchor="lm")
        text(d, (x + 80, y + 60), b, F(26, "med"), fill=fade(MUTED, k), anchor="lm")


def s_intro(d, t, T):
    k = seg(t, 0, .7)
    text(d, (960, 430), "High-frequency e-paper", F(84, "heavy"), fill=fade(INK, k), anchor="mm")
    text(d, (960, 530), "Adafruit's SSD1683 panel from 0.17 to 22 fps", F(46, "med"), fill=fade(PINK, k),
         anchor="mm")


def s_outro(d, t, T):
    k = seg(t, 0, .7)
    text(d, (960, 420), "next: write during BUSY · per-pixel budgets", F(60, "heavy"), fill=fade(INK, k),
         anchor="mm")
    text(d, (960, 510), "then decide on an EPaperDisplay fast mode", F(40, "med"), fill=fade(INK2, k),
         anchor="mm")
    text(d, (960, 570), "Feather RP2040 ThinkInk · 4.2\" SSD1683 #6381 · CircuitPython 10.3.0-rc.0 · "
         "narration: Kokoro bm_george", F(28, "med"), fill=fade(MUTED, k), anchor="mm")


SCENES = [s_panel, s_ink, s_freq, s_wave, s_ladder, s_lut, s_overhead, s_fr, s_budget, s_cost,
          s_paperboy, s_inkboy, s_route, s_risk, s_safe]

TIMING = json.load(open(HERE / "vo" / "timing.json"))
assert len(TIMING) == len(SCENES), (len(TIMING), len(SCENES))
STARTS, LENS = [], []
cur = INTRO
for tm in TIMING:
    STARTS.append(cur)
    LENS.append(tm["dur"] + GAP)
    cur += tm["dur"] + GAP
TOTAL = cur + OUTRO


def subtitle(d, i, lt):
    words = TIMING[i]["words"]
    f = F(40, "demi")
    lines, line, wsum = [], [], 0
    for w in words:
        ww = d.textlength(w[0] + " ", font=f)
        if wsum + ww > 1640 and line:
            lines.append(line)
            line, wsum = [], 0
        line.append(w)
        wsum += ww
    lines.append(line)
    y = H - 50 - 56 * len(lines)
    d.rectangle((0, y - 26, W, H), fill="#f7f8fa")
    d.line((0, y - 26, W, y - 26), fill=RULE, width=2)
    for ln in lines:
        tw = sum(d.textlength(w[0] + " ", font=f) for w in ln)
        x = (W - tw) / 2
        for w, a, b in ln:
            c = INK if lt >= a else "#b4bcc6"
            d.text((x, y), w, font=f, fill=c)
            x += d.textlength(w + " ", font=f)
        y += 56


def frame(n):
    t = n / FPS
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    if t < INTRO:
        s_intro(d, t, INTRO)
    elif t >= TOTAL - OUTRO:
        s_outro(d, t - (TOTAL - OUTRO), OUTRO)
    else:
        i = max(j for j in range(len(STARTS)) if STARTS[j] <= t)
        lt = t - STARTS[i]
        SCENES[i](d, lt, LENS[i])
        text(d, (70, 70), f"{i + 1} / {len(SCENES)}", M(26), fill=MUTED)
        subtitle(d, i, lt)
        if lt < 0.25:
            im = Image.blend(Image.new("RGB", (W, H), BG), im, lt / 0.25)
    return im.tobytes()


def read_wav(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768


def audio(path):
    n = int(TOTAL * SR)
    out = np.zeros(n, np.float32)
    for i, st in enumerate(STARTS):
        a = read_wav(HERE / "vo" / f"line_{i:02d}.wav")
        s = int(st * SR)
        out[s:s + len(a)] += a[: n - s]
    tt = np.arange(n) / SR
    chords = [(220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63),
              (196.0, 246.94, 329.63)]
    pad = np.zeros(n, np.float32)
    clen = 6.0
    for ci in range(int(TOTAL / clen) + 1):
        a0, a1 = int(ci * clen * SR), min(n, int((ci + 1) * clen * SR + SR))
        st = tt[a0:a1] - ci * clen
        env = np.minimum(1, st / 1.5) * np.minimum(1, np.maximum(0, (clen + 1 - st) / 1.5))
        for f in chords[ci % 4]:
            pad[a0:a1] += (np.sin(2 * np.pi * f * st) + 0.3 * np.sin(4 * np.pi * f * st)) * env
    pad *= 0.05 / max(1e-6, np.abs(pad).max())
    fin = np.minimum(1, tt / 1.0) * np.minimum(1, (TOTAL - tt) / 1.5)
    out = out + pad * fin
    out = np.clip(out * (0.89 / max(1e-6, np.abs(out).max())), -1, 1)  # peak about -1 dB
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype("<i2").tobytes())


def main():
    arg = sys.argv[1]
    if arg == "stills":
        out = HERE / "stills"
        out.mkdir(exist_ok=True)
        for i, st in enumerate(STARTS):
            for frac in (0.5, 0.92):
                Image.frombytes("RGB", (W, H), frame(int((st + LENS[i] * frac) * FPS))).save(
                    out / f"s{i:02d}_{int(frac * 100)}.png")
        Image.frombytes("RGB", (W, H), frame(int(1.2 * FPS))).save(out / "intro.png")
        Image.frombytes("RGB", (W, H), frame(int((TOTAL - 1) * FPS))).save(out / "outro.png")
        print("stills in", out, "total", round(TOTAL, 1), "s")
        return
    mixp = HERE / "mix.wav"
    audio(mixp)
    nframes = int(TOTAL * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(mixp), "-c:v", "h264_videotoolbox", "-b:v", "8M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", arg]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with mp.Pool() as pool:
        for buf in pool.imap(frame, range(nframes), chunksize=8):
            p.stdin.write(buf)
    p.stdin.close()
    p.wait()
    print(f"{arg}: {TOTAL:.1f}s, {nframes} frames")


if __name__ == "__main__":
    main()
