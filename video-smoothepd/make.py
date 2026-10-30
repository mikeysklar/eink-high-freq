"""SmoothEPD vs our fast e-ink explainer: George narration (vo/, from narrate.py + timing.py) over
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
SMOOTH, OURS, WDRV = PURPLE, PINK, "#2a7fb8"


def panel(d, box, k=1.0, fill=PAPER):
    x0, y0, x1, y1 = box
    rbox(d, (x0 - 24, y0 - 24, x1 + 24, y1 + 24), fade(PINK, k), r=18)
    d.rectangle(box, fill=fade(fill, k))


def pill(d, cx, cy, s, col, k=1.0, size=34):
    f = F(size, "bold")
    w = d.textlength(s, font=f)
    rbox(d, (cx - w / 2 - 30, cy - 34, cx + w / 2 + 30, cy + 34), fade(tint(col, .14), k), r=34)
    text(d, (cx, cy), s, f, fill=fade(col, k), anchor="mm")


def est_tag(d, xy, k=1.0, s="estimate", anchor="lm"):
    f = F(22, "bold")
    w = d.textlength(s, font=f)
    x, y = xy
    if anchor == "rm":
        x -= w + 24
    rbox(d, (x, y - 17, x + w + 24, y + 17), fade(tint(AMBER, .2), k), r=17)
    text(d, (x + 12 + w / 2, y), s, f, fill=fade(AMBER, k), anchor="mm")


def gray(level):
    """level 0 = white, 1 = black, drawn as an e-paper gray."""
    level = max(0.0, min(1.0, level))
    g = int(240 - 212 * level)
    return (g, g, g - 4 if g > 4 else g)


def drive_cell(d, box, kind, k=1.0):
    """kind: 'B' drive black, 'W' drive white, '-' hold."""
    if kind == "B":
        rbox(d, box, fade(INKBLK, k), r=6)
    elif kind == "W":
        rbox(d, box, fade("#ffffff", k), r=6, outline=fade(WDRV, k), width=4)
    else:
        rbox(d, box, fade(CARD, k), r=6, outline=fade(RULE, k), width=2)


def s_lineage(d, t, T):
    eyebrow(d, "the lineage")
    items = [("PaperBoy S3", ["raw parallel panel", "960x540 · 60 Hz", "no controller chip"], VIPER, .12),
             ("InkBoy", ["1.54\" SSD1681 · 200x200", "about 30 fps (reported)", "masks + pulse budget"],
              AMBER, .38),
             ("SmoothEPD", ["same SSD1681 panel", "47 Hz (stated)", "repo from 2026-10-25"], SMOOTH, .66)]
    for i, (name, sub, col, at) in enumerate(items):
        k = seg(t, T * at, T * at + .7)
        cx = 360 + i * 600
        node(d, (cx - 230, 250, cx + 230, 380), name, None, col, k, 48)
        for j, s in enumerate(sub):
            text(d, (cx, 440 + j * 50), s, F(32 if j != 1 else 36, "bold" if j == 1 else "med"),
                 fill=fade(col if j == 1 else INK2, k), anchor="mm")
        if i:
            part_arrow(d, (cx - 600 + 240, 315), (cx - 240, 315), k, fill=fade(INK2, k))
    k = seg(t, T * .8, T * .9)
    if k > 0:
        text(d, (960, 680), "ours: Adafruit 4.2\" SSD1683 · 400x300 · Feather RP2040", F(34, "demi"),
             fill=fade(OURS, k), anchor="mm")


def s_serial(d, t, T):
    eyebrow(d, "a serial panel, normally")
    k1 = seg(t, 0, .7)
    node(d, (90, 330, 370, 480), "your MCU", "sends a picture", INK2, k1, 38)
    part_arrow(d, (380, 405), (520, 405), k1)
    text(d, (450, 385), "SPI", M(26, True), fill=fade(INK2, k1), anchor="ms")
    k2 = seg(t, 1.0, 1.8)
    rbox(d, (530, 200, 1300, 640), fade(tint(INKBLK, .06), k2), r=18, outline=fade(INKBLK, k2), width=4)
    text(d, (915, 240), "SSD168x controller", F(36, "bold"), fill=fade(INK, k2), anchor="mm")
    for j, (lab, sub) in enumerate((("RAM 0x24", "new image"), ("RAM 0x26", "old image"))):
        y = 290 + j * 90
        rbox(d, (570, y, 900, y + 70), fade(CARD, k2), r=10, outline=fade(RULE, k2), width=3)
        text(d, (590, y + 35), lab, M(28, True), fill=fade(INK, k2), anchor="lm")
        text(d, (880, y + 35), sub, F(26, "med"), fill=fade(INK2, k2), anchor="rm")
    k3 = seg(t, T * .4, T * .55)
    if k3 > 0:
        text(d, (1100, 300), "fixed waveform", F(28, "bold"), fill=fade(INK, k3), anchor="mm")
        for j, s in enumerate(("W → W", "W → B", "B → W", "B → B")):
            rbox(d, (980, 330 + j * 62, 1220, 380 + j * 62), fade(tint(BLUE, .14), k3), r=8)
            text(d, (1100, 355 + j * 62), s, M(30, True), fill=fade(BLUE, k3), anchor="mm")
        text(d, (735, 520), "every pixel with the", F(26, "med"), fill=fade(MUTED, k3), anchor="mm")
        text(d, (735, 556), "same change gets the", F(26, "med"), fill=fade(MUTED, k3), anchor="mm")
        text(d, (735, 592), "same waveform", F(26, "med"), fill=fade(MUTED, k3), anchor="mm")
    part_arrow(d, (1310, 405), (1450, 405), k2)
    panel(d, (1490, 310, 1810, 500), k2)
    text(d, (1650, 405), "panel", F(36, "bold"), fill=fade(INK2, k2), anchor="mm")
    k4 = seg(t, T * .75, T * .85)
    if k4 > 0:
        pill(d, 960, 730, "no per-pixel control", RED, k4, 40)


# a small scene: a 3x3 black square moves one cell right
GW, GH = 10, 7


def _sq(x0):
    return {(x, y) for x in range(x0, x0 + 4) for y in range(2, 5)}


def s_masks(d, t, T):
    eyebrow(d, "the trick · RAM planes become drive masks")
    old, new = _sq(2), _sq(4)
    blk = new - old
    wht = old - new
    cs = 36
    grids = [("0x26 = drive black", "black mask", lambda p: "B" if p in blk else None, .05),
             ("0x24 = drive white", "white mask", lambda p: "W" if p in wht else None, .3),
             ("what each pixel gets", "", lambda p: "B" if p in blk else ("W" if p in wht else "-"), .62)]
    for i, (title, _, fn, at) in enumerate(grids):
        k = seg(t, T * at, T * at + .7)
        if k <= 0:
            continue
        x0 = 150 + i * 580
        y0 = 260
        text(d, (x0 + GW * cs / 2, y0 - 30), title, M(28, True) if i < 2 else F(32, "bold"),
             fill=fade(INK if i < 2 else SMOOTH, k), anchor="ms")
        for x in range(GW):
            for y in range(GH):
                b = (x0 + x * cs, y0 + y * cs, x0 + x * cs + cs - 4, y0 + y * cs + cs - 4)
                v = fn((x, y))
                if v is None:
                    rbox(d, b, fade("#f8f9fb", k), r=4, outline=fade(RULE, k), width=1)
                elif v == "-" and (x, y) in old:
                    rbox(d, b, fade(gray(.92), k), r=4)
                else:
                    drive_cell(d, b, v, k)
        if i == 1:
            text(d, (x0 - 82, y0 + GH * cs / 2), "+", F(70, "bold"), fill=fade(INK2, k), anchor="mm")
        if i == 2:
            text(d, (x0 - 82, y0 + GH * cs / 2), "=", F(70, "bold"), fill=fade(INK2, k), anchor="mm")
    k = seg(t, T * .62, T * .75)
    if k > 0:
        y = 600
        items = [("B", "drive black (VSH1)"), ("W", "drive white (VSL)"), ("-", "in neither: hold")]
        for j, (kind, lab) in enumerate(items):
            x = 330 + j * 450
            drive_cell(d, (x, y, x + 44, y + 44), kind, k)
            text(d, (x + 62, y + 22), lab, F(30, "demi"), fill=fade(INK2, k), anchor="lm")
    k = seg(t, T * .42, T * .55)
    if k > 0:
        text(d, (960, 730), "1-frame LUT · one scan ≈ 20 ms (50 Hz, inferred from their code)",
             F(32, "bold"), fill=fade(INK, k), anchor="mm")


def budget_sim(n_steps, flip_at, step_ms, budget=7):
    """Budget rule: target B for steps < flip_at, then W. Returns per-step drive kinds and levels."""
    kinds, levels, rem, lvl, prev = [], [], 0, 0.0, "W"
    for s in range(n_steps):
        tgt = "B" if s < flip_at else "W"
        if tgt != prev:
            rem = budget
            prev = tgt
        if rem > 0:
            kinds.append(tgt)
            rem -= 1
            lvl += (step_ms / 140) * (1 if tgt == "B" else -1)
            lvl = max(0.0, min(1.0, lvl))
        else:
            kinds.append("-")
        levels.append(lvl)
    return kinds, levels


def s_budget(d, t, T):
    eyebrow(d, "a drive budget per pixel")
    P, t0, n = 0.5, 1.0, 16
    step = int(max(0, t - t0) // P) if t >= t0 else -1
    step = min(step, n - 1)
    flip = 4
    kinds, levels = budget_sim(n, flip, 20)
    # remaining budget per step
    rem_list, rem, prev = [], 0, "W"
    for s in range(n):
        tgt = "B" if s < flip else "W"
        if tgt != prev:
            rem, prev = 7, tgt
        rem = max(0, rem - (1 if rem > 0 else 0))
        rem_list.append(rem)
    lvl = levels[step] if step >= 0 else 0.0
    rbox(d, (180, 270, 480, 570), gray(lvl), r=8, outline=INK2, width=4)
    text(d, (330, 610), "one pixel (illustration)", F(26, "med"), fill=MUTED, anchor="mm")
    tgt = "black" if step < flip else "white"
    text(d, (330, 235), f"target: {tgt}" if step >= 0 else "target: white", F(34, "bold"),
         fill=INK, anchor="ms")
    x0, y0 = 640, 300
    text(d, (x0, y0 - 24), "drive scans left", F(30, "demi"), fill=INK2, anchor="ls")
    r = rem_list[step] if step >= 0 else 0
    left = r + (1 if step >= 0 and kinds[step] != "-" else 0)
    for j in range(7):
        b = (x0 + j * 110, y0, x0 + j * 110 + 90, y0 + 90)
        if j < left:
            drive_cell(d, b, "B" if step < flip else "W")
        else:
            rbox(d, b, CARD, r=6, outline=RULE, width=2)
    text(d, (x0 + 790, y0 + 45), f"{left} / 7", F(48, "heavy"), fill=SMOOTH, anchor="lm")
    # step strip
    y1 = 470
    text(d, (x0, y1 - 20), "scans (slowed down)", F(26, "demi"), fill=MUTED, anchor="ls")
    for s in range(n):
        b = (x0 + s * 64, y1, x0 + s * 64 + 54, y1 + 54)
        if s <= step:
            drive_cell(d, b, kinds[s])
        else:
            rbox(d, b, "#fbfbfc", r=6, outline=RULE, width=1)
    if step >= flip and step < flip + 3:
        bx = x0 + flip * 64
        text(d, (bx + 27, y1 + 100), "target flips: reload to 7", F(30, "bold"), fill=RED, anchor="mm")
    k = seg(t, T * .2, T * .35)
    if k > 0:
        text(d, (960, 730), "7 scans × ~20 ms ≈ 140 ms of drive per change", F(38, "bold"),
             fill=fade(INK, k), anchor="mm")


def lag_sim(n, flip_at, lag):
    """Our scheme: 0x24 = frame N, 0x26 = frame N-lag; drive toward N where they differ."""
    frames = ["W"] * lag + ["B" if s < flip_at else "W" for s in range(n)]
    kinds = []
    for s in range(n):
        cur, old = frames[s + lag], frames[s]
        kinds.append(cur if cur != old else "-")
    return kinds


def s_slowmo(d, t, T):
    eyebrow(d, "slow motion · a pixel goes black for 2 frames, then back")
    n, flip = 12, 2
    P, t0 = 0.72, 1.0
    cur = (t - t0) / P if t >= t0 else -1
    step = min(n - 1, int(cur)) if cur >= 0 else -1
    cx0, cw = 470, 108
    rows = [("target", None, 210), ("SmoothEPD", "1 step ≈ 20 ms", 370), ("ours, lag 6", "1 step = 8 ms", 580)]
    smooth, slevels = budget_sim(n, flip, 20)
    ours = lag_sim(n, flip, 6)
    olevels, lv = [], 0.0
    for kd in ours:
        if kd != "-":
            lv = max(0.0, min(1.0, lv + (8 / 140) * (1 if kd == "B" else -1)))
        olevels.append(lv)
    for s in range(n):
        text(d, (cx0 + s * cw + (cw - 12) / 2, 170), str(s), M(24), fill=MUTED, anchor="ms")
    for ri, (name, sub, y) in enumerate(rows):
        col = INK if ri == 0 else (SMOOTH if ri == 1 else OURS)
        text(d, (80, y + 30 - (14 if sub else 0)), name, F(34, "bold"), fill=col, anchor="lm")
        if sub:
            text(d, (80, y + 50), sub, F(24, "med"), fill=MUTED, anchor="lm")
        for s in range(n):
            b = (cx0 + s * cw, y, cx0 + s * cw + cw - 12, y + 70)
            if ri == 0:
                tg = "B" if s < flip else "W"
                rbox(d, b, gray(1 if tg == "B" else 0.02), r=6, outline=RULE, width=2)
            elif s <= step:
                drive_cell(d, b, (smooth if ri == 1 else ours)[s])
            else:
                rbox(d, b, "#fbfbfc", r=6, outline=RULE, width=1)
        if ri > 0:
            lvl = (slevels if ri == 1 else olevels)[step] if step >= 0 else 0.0
            rbox(d, (330, y - 2, 404, y + 72), gray(lvl), r=6, outline=INK2, width=3)
    if step >= 0:
        x = cx0 + (min(cur, n - 0.01)) * cw
        d.line((x, 185, x, 660), fill=RED, width=4)
    text(d, (367, 680), "pixel", F(22, "med"), fill=MUTED, anchor="mm")
    text(d, (367, 705), "(illustration)", F(22, "med"), fill=MUTED, anchor="mm")
    if step >= 4:
        k = seg(cur, 4, 4.8)
        tb = d.textbbox((cx0 + 2 * cw, 478), "flip back: budget reloads, 7 white frames right away",
                        font=F(28, "bold"), anchor="lm")
        d.rectangle((tb[0] - 6, tb[1] - 4, tb[2] + 6, tb[3] + 4), fill=BG)
        text(d, (cx0 + 2 * cw, 478), "flip back: budget reloads, 7 white frames right away",
             F(28, "bold"), fill=fade(SMOOTH, k), anchor="lm")
    if step >= 2:
        k = seg(cur, 2.5, 3.3)
        text(d, (cx0 + 2 * cw, 688), "nothing yet", F(28, "bold"), fill=fade(OURS, k), anchor="lm")
    if step >= 7:
        k = seg(cur, 7, 7.8)
        text(d, (cx0 + 6 * cw, 700), "2 white frames, late",
             F(28, "bold"), fill=fade(OURS, k), anchor="lm")
    if step < 7:
        pass


def s_short(d, t, T):
    eyebrow(d, "drive time per change")
    rows = [("SmoothEPD budget", 140, SMOOTH, "7 × ~20 ms", .1),
            ("ours, lag 6", 48, OURS, "6 × 8 ms", .3)]
    x, y, w, bh, gap, vmax = 560, 280, 1080, 90, 80, 170
    xs = x + w * 120 / vmax
    k0 = seg(t, T * .62, T * .75)
    if k0 > 0:
        dashed_v(d, xs, y - 50, y + 2 * (bh + gap) - 40, fade(INK2, k0))
        text(d, (xs, y - 62), "120 ms: their README's minimum", F(28, "demi"), fill=fade(INK2, k0),
             anchor="ms")
    for i, (lab, v, col, sub, at) in enumerate(rows):
        k = seg(t, T * at, T * at + .9)
        if k <= 0:
            continue
        yy = y + i * (bh + gap)
        text(d, (x - 24, yy + bh / 2 - 14), lab, F(34, "demi"), fill=fade(INK, k), anchor="rm")
        text(d, (x - 24, yy + bh / 2 + 24), sub, F(26, "med"), fill=fade(MUTED, k), anchor="rm")
        bw = w * v * k / vmax
        rbox(d, (x, yy, x + bw, yy + bh), fade(col, k), r=10)
        text(d, (x + bw + 18, yy + bh / 2), f"{v * k:.0f} ms", F(48, "heavy"), fill=fade(col, k),
             anchor="lm")
    k = seg(t, T * .2, T * .3)
    if k > 0:
        est_tag(d, (x + w * 140 / vmax - 10, y + bh + 30), k, "~20 ms per scan: inferred, not measured", anchor="rm")
    k = seg(t, T * .8, T * .9)
    if k > 0:
        text(d, (960, 690), "our 8 ms is measured: BUSY = 8.1 ms per frame at 125 Hz", F(30, "med"),
             fill=fade(MUTED, k), anchor="mm")


def ball_pos(tt):
    return 0.5 + 0.38 * math.sin(tt * 1.3), 0.5 + 0.3 * math.sin(tt * 2.1 + 0.6)


def s_trails(d, t, T):
    eyebrow(d, "why it matters")
    boxes = [((150, 230, 870, 640), "short or late erase", "their net variant · our lag scheme", OURS, True),
             ((1050, 230, 1770, 640), "full erase every change", "their default budget rule", SMOOTH, False)]
    for i, (b, title, sub, col, smear) in enumerate(boxes):
        k = seg(t, 0.3 + i * T * .35, 1.0 + i * T * .35)
        if k <= 0:
            continue
        panel(d, b, k, fill="#f2f1ec")
        x0, y0, x1, y1 = b
        text(d, ((x0 + x1) / 2, y0 - 70), title, F(36, "bold"), fill=fade(col, k), anchor="ms")
        text(d, ((x0 + x1) / 2, y1 + 70), sub, F(28, "med"), fill=fade(INK2, k), anchor="mm")
        R = 42
        hist = 80 if smear else 4
        for j in range(hist, 0, -1):
            tt = t - j * 0.05
            if tt < 0:
                continue
            px, py = ball_pos(tt)
            cx, cy = x0 + R + (x1 - x0 - 2 * R) * px, y0 + R + (y1 - y0 - 2 * R) * py
            lev = (0.22 if smear else 0.35 * (1 - j / hist))
            c = fade(gray(lev), k)
            d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=c)
        px, py = ball_pos(t)
        cx, cy = x0 + R + (x1 - x0 - 2 * R) * px, y0 + R + (y1 - y0 - 2 * R) * py
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=fade(INKBLK, k))
    k = seg(t, T * .4, T * .5)
    if k > 0:
        text(d, (510, 760), "README: \"trails heavily\"", F(32, "bold"), fill=fade(OURS, k), anchor="mm")
    k = seg(t, T * .6, T * .7)
    if k > 0:
        text(d, (510, 805), "our ball: same smear at lag 4, 6 and 8 (filmed)", F(26, "med"),
             fill=fade(MUTED, k), anchor="mm")
        text(d, (1410, 760), "cleaner, by their account", F(32, "bold"), fill=fade(SMOOTH, k), anchor="mm")
        text(d, (1410, 805), "(drawings, not camera footage)", F(26, "med"), fill=fade(MUTED, k), anchor="mm")


DEBT_HIST = ["B"] * 7 + ["W"] * 2 + ["B"] * 7 + ["W"] * 7


def s_debt(d, t, T):
    eyebrow(d, "the price · DC stress")
    x0, y0, cw = 150, 250, 64
    n = len(DEBT_HIST)
    shown = int(min(n, max(0, (t - 0.6) / (T * 0.42) * n)))
    labels = [(0, "B 7"), (7, "W 2"), (9, "B 7"), (16, "W 7")]
    for s in range(n):
        b = (x0 + s * cw, y0, x0 + s * cw + cw - 10, y0 + 60)
        if s < shown:
            drive_cell(d, b, DEBT_HIST[s])
        else:
            rbox(d, b, "#fbfbfc", r=6, outline=RULE, width=1)
    for s, lab in labels:
        if s < shown:
            text(d, (x0 + s * cw, y0 - 18), lab, F(26, "demi"), fill=INK2, anchor="ls")
    if shown > 8:
        text(d, (x0 + 7 * cw + 60, y0 + 84), "flipped back after 2", F(22, "med"), fill=MUTED, anchor="mm")
    debt = sum(1 if c == "B" else -1 for c in DEBT_HIST[:shown])
    text(d, (x0, y0 + 140), "debt (black scans minus white scans):", F(32, "demi"), fill=INK2, anchor="lm")
    text(d, (x0 + 620, y0 + 140), f"{debt:+d}", F(56, "heavy"), fill=RED if debt else GREEN, anchor="lm")
    if shown >= n:
        text(d, (x0 + 760, y0 + 140), "pixel shows white, net black", F(30, "med"), fill=MUTED, anchor="lm")
    k = seg(t, T * .55, T * .65)
    if k > 0:
        y = 480
        text(d, (x0, y), "every 1000 scans: pay back 1 unit, only toward the color shown",
             F(36, "bold"), fill=fade(INK, k), anchor="lm")
        cases = [("shows white, debt +5", "1 white scan: nothing visible changes", GREEN, "W", 0.02),
                 ("shows black, debt +5", "skipped: a white scan would show", RED, "-", 1.0)]
        for j, (a, b2, col, kind, lv) in enumerate(cases):
            kk = seg(t, T * (.65 + j * .12), T * (.72 + j * .12))
            if kk <= 0:
                continue
            yy = 560 + j * 95
            rbox(d, (x0, yy, x0 + 70, yy + 70), fade(gray(lv), kk), r=6, outline=fade(INK2, kk), width=3)
            drive_cell(d, (x0 + 100, yy + 8, x0 + 154, yy + 62), kind, kk)
            text(d, (x0 + 190, yy + 35), a, F(30, "bold"), fill=fade(INK, kk), anchor="lm")
            text(d, (x0 + 560, yy + 35), b2, F(30, "med"), fill=fade(col, kk), anchor="lm")
    k = seg(t, T * .85, T * .95)
    if k > 0:
        text(d, (1770, 790), "ledger is int8, no clamp: it can wrap (arithmetic, not observed)",
             F(24, "med"), fill=fade(MUTED, k), anchor="rm")


def s_refresh(d, t, T):
    eyebrow(d, "the real reset")
    k = seg(t, 0, .7)
    x0, y0, cw = 150, 240, 24
    parts = ["O"] * 9 + (["B"] * 5 + ["W"] * 5) * 4 + ["F"] * 9
    text(d, (x0, y0 - 22), "their balanced full refresh: 66 frames", F(30, "bold"), fill=fade(SMOOTH, k),
         anchor="ls")
    shown = int(66 * seg(t, 0.3, T * .3))
    for i, p in enumerate(parts[:shown]):
        b = (x0 + i * cw, y0, x0 + i * cw + cw - 4, y0 + 50)
        kind = {"O": "W", "F": "B"}.get(p, p)
        drive_cell(d, b, kind, k)
    if shown >= 66:
        for a, b_, lab in ((0, 9, "9 to the opposite color"), (9, 49, "4 × (5 one way + 5 the other)"),
                           (49, 58, "9 to the final color")):
            xm = x0 + (a + b_) / 2 * cw
            text(d, (xm, y0 + 88), lab, F(24, "med"), fill=INK2, anchor="mm")
        text(d, (x0 + 66 * cw + 30, y0 + 25), "1.3 s", F(48, "heavy"), fill=SMOOTH, anchor="lm")
    # timelines
    ax0, ax1, secs = 300, 1760, 90
    pps = (ax1 - ax0) / secs
    rows = [("SmoothEPD", 470, SMOOTH, T * .3), ("ours (teapot)", 620, OURS, T * .62)]
    for name, y, col, at in rows:
        kk = seg(t, at, at + .8)
        if kk <= 0:
            continue
        text(d, (ax0 - 24, y + 25), name, F(32, "bold"), fill=fade(col, kk), anchor="rm")
        d.line((ax0, y + 25, ax1, y + 25), fill=fade(RULE, kk), width=4)
        if col == SMOOTH:
            for s0 in (43, 86):
                rbox(d, (ax0 + s0 * pps, y, ax0 + (s0 + 1.3) * pps + 4, y + 50), fade(SMOOTH, kk), r=4)
            text(d, (ax0 + 43 * pps + 30, y - 14), "every 2000 scans ≈ 43 s", F(26, "demi"),
                 fill=fade(SMOOTH, kk), anchor="ls")
            est_tag(d, (ax0 + 43 * pps + 360, y - 26), kk, "estimate at 47 Hz")
        else:
            for s0 in range(4, secs, 4):
                if s0 % 15:
                    d.line((ax0 + s0 * pps, y + 8, ax0 + s0 * pps, y + 42), fill=fade(OURS, kk * .6), width=4)
            for s0 in (15, 30, 45, 60, 75):
                rbox(d, (ax0 + s0 * pps, y, ax0 + (s0 + 3.3) * pps, y + 50), fade(OURS, kk), r=4)
            text(d, (ax0 + 15 * pps, y + 90), "3.3 s OTP clean every 15 s  ·  short balanced wipe every 4 s",
                 F(26, "demi"), fill=fade(OURS, kk), anchor="lm")
    kk = seg(t, T * .3, T * .4)
    if kk > 0:
        for s0 in (0, 30, 60, 90):
            text(d, (ax0 + s0 * pps, 770), f"{s0} s", F(24, "med"), fill=fade(MUTED, kk), anchor="mm")


def tile(d, x0, y0, w, h, title, sub, k):
    rbox(d, (x0, y0, x0 + w, y0 + h), fade("#f2f1ec", k), r=12, outline=fade(RULE, k), width=3)
    text(d, (x0 + w / 2, y0 - 22), title, F(30, "bold"), fill=fade(INK, k), anchor="ms")
    text(d, (x0 + w / 2, y0 + h + 40), sub, F(24, "med"), fill=fade(MUTED, k), anchor="mm")


DIG = {0: ["111", "101", "101", "101", "111"], 1: ["010", "110", "010", "010", "111"],
       2: ["111", "001", "111", "100", "111"], 3: ["111", "001", "111", "001", "111"],
       4: ["101", "101", "111", "001", "001"], 5: ["111", "100", "111", "001", "111"],
       6: ["111", "100", "111", "101", "111"], 7: ["111", "001", "010", "010", "010"],
       8: ["111", "101", "111", "101", "111"], 9: ["111", "101", "111", "001", "111"]}


def s_content(d, t, T):
    eyebrow(d, "content drawn to suit the panel")
    w, h, y0 = 380, 300, 280
    xs = [110, 560, 1010, 1460]
    ink = INKBLK
    # 1 thick strokes
    k = seg(t, T * .2, T * .3)
    if k > 0:
        x0 = xs[0]
        tile(d, x0, y0, w, h, "thick strokes", "2-4 px lines; thin lines gray", k)
        cx, cy = x0 + w / 2, y0 + h / 2
        d.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), outline=fade(ink, k), width=22)
        d.line((x0 + 40, y0 + 260, x0 + 340, y0 + 260), fill=fade(gray(.35), k), width=3)
    # 2 one pixel per frame (snake on a grid)
    k = seg(t, T * .35, T * .45)
    if k > 0:
        x0 = xs[1]
        tile(d, x0, y0, w, h, "1 px per frame", "snake step 1: \"most stable\"", k)
        c = 20
        head = int(t * 6)
        for j in range(10):
            p = (head - j) % 64
            gx = p % 16
            gy = 6 + (p // 16) % 2
            gx = gx if (p // 16) % 2 == 0 else 15 - gx
            bx, by = x0 + 30 + gx * c, y0 + 20 + gy * c
            sz = c if j < 7 else c - 8
            d.rectangle((bx, by, bx + sz - 2, by + sz - 2), fill=fade(ink, k))
    # 3 digits every 7 frames
    k = seg(t, T * .5, T * .6)
    if k > 0:
        x0 = xs[2]
        tile(d, x0, y0, w, h, "digits every 7 frames", "matches the 7-scan budget", k)
        fr = int(t * 20)
        val = (fr // 7) % 100
        c = 22
        for di, dv in enumerate((val // 10, val % 10)):
            for r, row in enumerate(DIG[dv]):
                for cc, bit in enumerate(row):
                    if bit == "1":
                        bx = x0 + 100 + di * 110 + cc * c
                        by = y0 + 60 + r * c
                        d.rectangle((bx, by, bx + c - 2, by + c - 2), fill=fade(ink, k))
        text(d, (x0 + w / 2, y0 + 250), f"frame {fr % 1000}", M(24), fill=fade(INK2, k), anchor="mm")
    # 4 slow physics
    k = seg(t, T * .72, T * .82)
    if k > 0:
        x0 = xs[3]
        tile(d, x0, y0, w, h, "slow physics", "dt 0.010: \"time to drive\"", k)
        import random
        rng = random.Random(3)
        for j in range(70):
            bx = rng.uniform(20, w - 40)
            phase = rng.uniform(0, 1)
            yy = ((phase + t * 0.06) % 1) ** 0.5
            by = 30 + yy * (h - 70) * (0.6 + 0.4 * rng.random())
            px, py = x0 + int(bx / 12) * 12, y0 + int(by / 12) * 12
            d.rectangle((px, py, px + 14, py + 14), fill=fade(ink, k))
    k = seg(t, T * .05, T * .18)
    if k > 0:
        text(d, (960, 740), "each pixel gets its full drive before it changes again", F(36, "bold"),
             fill=fade(SMOOTH, k), anchor="mm")


PLAN = [("Budget masks for the teapot, computed on the Mac",
         "B = 15 (~120 ms at 8 ms), then B = 8 · same SPI, same fps", False, .08),
        ("Lag 15, as a control", "tells too little drive apart from a late erase", False, .38),
        ("Port their balanced refresh LUT to the SSD1683", "1.3 s instead of our 3.3 s OTP clean · whiteness unknown",
         False, .5),
        ("Same-color settle from a Mac debt ledger", "could replace the visible 4 s wipe", False, .64),
        ("Coarser dither", "2x2 blocks or fewer levels: fewer 1 px reversals", False, .76),
        ("SPI at 31.25 MHz", "~55 fps full screen · out of spec, untested on SSD1683", True, .86)]


def s_plan(d, t, T):
    eyebrow(d, "what we will try, in order")
    y0, rh = 190, 102
    for i, (a, b, est, at) in enumerate(PLAN):
        k = seg(t, T * at, T * at + .6)
        if k <= 0:
            continue
        y = y0 + i * rh
        col = SMOOTH if i == 0 else INK2
        d.ellipse((150, y, 214, y + 64), fill=fade(col, k))
        text(d, (182, y + 32), str(i + 1), F(36, "heavy"), fill=BG, anchor="mm")
        text(d, (250, y + 16), a, F(36, "bold"), fill=fade(INK, k), anchor="lm")
        text(d, (250, y + 56), b, F(26, "med"), fill=fade(MUTED, k), anchor="lm")
        if est:
            est_tag(d, (250 + d.textlength(b, font=F(26, "med")) + 24, y + 56), k, "estimate")


def s_caveats(d, t, T):
    eyebrow(d, "caveats")
    cards = [("47 Hz", "the author's README claim", "nobody else has measured it", AMBER, .1),
             ("DC balance", "the budget rule breaks it", "needs Mikey's OK first", RED, .45),
             ("Lifetime", "no project reports it", "unknown, for them and for us", INK2, .72)]
    for i, (a, b, c, col, at) in enumerate(cards):
        k = seg(t, T * at, T * at + .7)
        if k <= 0:
            continue
        x0 = 150 + i * 560
        rbox(d, (x0, 280, x0 + 500, 620), fade(tint(col, .1), k), r=20, outline=fade(col, k), width=4)
        text(d, (x0 + 250, 380), a, F(64, "heavy"), fill=fade(col, k), anchor="mm")
        text(d, (x0 + 250, 480), b, F(30, "demi"), fill=fade(INK, k), anchor="mm")
        text(d, (x0 + 250, 530), c, F(30, "med"), fill=fade(INK2, k), anchor="mm")


def s_intro(d, t, T):
    k = seg(t, 0, .7)
    text(d, (960, 430), "SmoothEPD vs our fast e-ink", F(84, "heavy"), fill=fade(INK, k), anchor="mm")
    text(d, (960, 530), "what a 47 Hz SSD1681 driver does differently", F(46, "med"),
         fill=fade(SMOOTH, k), anchor="mm")


def s_outro(d, t, T):
    k = seg(t, 0, .7)
    text(d, (960, 410), "github.com/PinkiePie1/SmoothEPD", M(60, True), fill=fade(INK, k), anchor="mm")
    text(d, (960, 500), "ours: Adafruit 4.2\" SSD1683 · Feather RP2040 ThinkInk · CircuitPython",
         F(38, "med"), fill=fade(INK2, k), anchor="mm")
    text(d, (960, 560), "SmoothEPD numbers are the author's; ours are measured · narration: Kokoro bm_george",
         F(28, "med"), fill=fade(MUTED, k), anchor="mm")


SCENES = [s_lineage, s_serial, s_masks, s_budget, s_slowmo, s_short, s_trails, s_debt, s_refresh,
          s_content, s_plan, s_caveats]

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
           "-r", str(FPS), "-i", "-", "-i", str(mixp), "-vf", "scale=1280:720:flags=lanczos",
           "-c:v", "hevc_videotoolbox", "-tag:v", "hvc1", "-b:v", "2M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", arg]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with mp.Pool() as pool:
        for buf in pool.imap(frame, range(nframes), chunksize=8):
            p.stdin.write(buf)
    p.stdin.close()
    p.wait()
    print(f"{arg}: {TOTAL:.1f}s, {nframes} frames")


if __name__ == "__main__":
    main()
