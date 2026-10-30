# make_gifs: test GIFs for the videocore GIF source, with per-frame rect JSON.
# Own GIF89a writer (LZW from scratch-built table, same encoder as the gif-build test that
# made C_t.gif); every file is decoded again with Pillow and ffmpeg and compared to the
# reference canvas this script composites itself.
# Run: <venv>/bin/python -I make_gifs.py <teapot.bin> <out dir>
import json, os, struct, subprocess, sys, zlib

import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]


def lzw(idx, mcs):
    clear = 1 << mcs
    eoi = clear + 1
    out = bytearray()
    acc = nb = 0

    def emit(c, sz):
        nonlocal acc, nb
        acc |= c << nb
        nb += sz
        while nb >= 8:
            out.append(acc & 255)
            acc >>= 8
            nb -= 8

    size = mcs + 1
    table = {}
    nxt = eoi + 1
    emit(clear, size)
    w = None
    for k in idx.tolist():
        if w is None:
            w = k
            continue
        key = (w, k)
        if key in table:
            w = table[key]
            continue
        emit(w, size)
        if nxt < 4096:
            table[key] = nxt
            nxt += 1
            if nxt - 1 == (1 << size) and size < 12:
                size += 1
        else:
            emit(clear, size)
            table = {}
            nxt = eoi + 1
            size = mcs + 1
        w = k
    emit(w, size)
    emit(eoi, size)
    if nb:
        out.append(acc & 255)
    sub = bytearray([mcs])
    for i in range(0, len(out), 255):
        c = out[i:i + 255]
        sub += bytes([len(c)]) + c
    return bytes(sub + b"\0")


def write_gif(path, W, H, pal, frames, loop=True, bg=0):
    # pal: list of (r, g, b), length a power of two >= 4 (LZW min code size = log2 len)
    # frames: dicts with x, y, w, h, idx (h x w uint8), delay, disposal, trans (index|None),
    # gce (False = no Graphic Control Extension)
    bits = len(pal).bit_length() - 1
    assert 1 << bits == len(pal) and bits >= 2
    b = bytearray(b"GIF89a" + struct.pack("<HHBBB", W, H, 0x80 | (bits - 1), bg, 0))
    b += bytes(c for rgb in pal for c in rgb)
    if loop:
        b += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\0\0\0"
    for f in frames:
        if f.get("gce", True):
            t = f["trans"]
            b += b"\x21\xf9\x04" + bytes([(f["disposal"] << 2) | (t is not None)])
            b += struct.pack("<H", f["delay"]) + bytes([t or 0, 0])
        b += b"\x2c" + struct.pack("<HHHHB", f["x"], f["y"], f["w"], f["h"], 0)
        b += lzw(f["idx"].ravel(), bits)
    b += b";"
    open(path, "wb").write(b)


def composite(W, H, frames, bg=0):
    # reference model: GIF89a disposal 0/1 keep, 2 restore rect to background index
    canvas = np.full((H, W), bg, np.uint8)
    out = []
    for f in frames:
        x, y, w, h = f["x"], f["y"], f["w"], f["h"]
        sub = f["idx"]
        reg = canvas[y:y + h, x:x + w]
        keep = sub == f["trans"] if f["trans"] is not None else np.zeros_like(sub, bool)
        reg[~keep] = sub[~keep]
        out.append(canvas.copy())
        if f["disposal"] == 2:
            canvas[y:y + h, x:x + w] = bg
    return out


def delta_frames(fr, trans, delay, align8):
    # frame 0 full; later frames the bbox of changed pixels (x byte-aligned for 1 bpp),
    # unchanged pixels inside it set to the transparent index
    H, W = fr[0].shape
    frames = []
    for i, cur in enumerate(fr):
        if i == 0:
            frames.append(dict(x=0, y=0, w=W, h=H, idx=cur.copy(), trans=None,
                               delay=delay, disposal=1))
            continue
        d = cur != fr[i - 1]
        if not d.any():
            x0, y0, x1, y1 = 0, 0, (8 if align8 else 1), 1
        else:
            ys = np.where(d.any(1))[0]
            xs = np.where(d.any(0))[0]
            x0, x1 = xs[0], xs[-1] + 1
            if align8:
                x0, x1 = x0 // 8 * 8, min(W, (x1 + 7) // 8 * 8)
            y0, y1 = ys[0], ys[-1] + 1
        sub = cur[y0:y1, x0:x1].copy()
        sub[~d[y0:y1, x0:x1]] = trans
        frames.append(dict(x=int(x0), y=int(y0), w=int(x1 - x0), h=int(y1 - y0), idx=sub,
                           trans=trans, delay=delay, disposal=1))
    return frames


def pillow_frames(path):
    im = Image.open(path)
    out = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        out.append(np.array(im.convert("RGB")))
    return out


def ffmpeg_frames(path, W, H):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ignore_loop", "1", "-i", path,
                        "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    a = np.frombuffer(r.stdout, np.uint8)
    return list(a.reshape(-1, H, W, 3))


def rgb565(rgb, order="<"):
    v = ((rgb[..., 0].astype(np.uint16) >> 3) << 11) | ((rgb[..., 1].astype(np.uint16) >> 2) << 5) \
        | (rgb[..., 2].astype(np.uint16) >> 3)
    return v.astype(order + "u2").tobytes()


def build(name, W, H, pal, frames, purpose, loop=True, bg=0, one_bit=False):
    path = os.path.join(OUT, name)
    write_gif(path, W, H, pal, frames, loop, bg)
    ref = composite(W, H, frames, bg)
    lut = np.array(pal, np.uint8)
    exp = [lut[c] for c in ref]
    got_p = pillow_frames(path)
    got_f = ffmpeg_frames(path, W, H)
    ok_p = sum(np.array_equal(a, b) for a, b in zip(exp, got_p)) if len(got_p) == len(exp) else -1
    ok_f = sum(np.array_equal(a, b) for a, b in zip(exp, got_f)) if len(got_f) == len(exp) else -1
    meta = dict(file=name, width=W, height=H, loop=loop, background_index=bg,
                palette=["%06x" % (r << 16 | g << 8 | b) for r, g, b in pal],
                lzw_min_code_size=len(pal).bit_length() - 1, frames=[])
    if one_bit:
        meta["crc32_packed"] = ("CRC-32 of the canvas as palette indices, 1 bit per pixel, "
                                "MSB first, rows of width/8 bytes (1 = white)")
    meta["crc32_index"] = "CRC-32 of the canvas as palette indices, 1 byte per pixel"
    meta["crc32_rgb565le"] = "CRC-32 of the canvas as RGB565, little-endian uint16 per pixel"
    meta["crc32_rgb565be"] = "same, big-endian (reverse_bytes_in_word=True)"
    for i, (f, c) in enumerate(zip(frames, ref)):
        e = dict(i=i, x=f["x"], y=f["y"], w=f["w"], h=f["h"], disposal=f["disposal"],
                 delay_cs=f["delay"], transparent=f["trans"],
                 crc32_index="%08x" % zlib.crc32(c.tobytes()),
                 crc32_rgb565le="%08x" % zlib.crc32(rgb565(lut[c])),
                 crc32_rgb565be="%08x" % zlib.crc32(rgb565(lut[c], ">")))
        if not f.get("gce", True):
            e["gce"] = False
        if one_bit:
            e["crc32_packed"] = "%08x" % zlib.crc32(np.packbits(c, axis=1).tobytes())
        meta["frames"].append(e)
    json.dump(meta, open(path[:-4] + ".json", "w"), indent=1)
    ar = [f["w"] * f["h"] * 100 / (W * H) for f in frames[1:]]
    row = dict(file=name, size=os.path.getsize(path), frames=len(frames), dims="%dx%d" % (W, H),
               pal=len(pal), mean="%.1f" % np.mean(ar) if ar else "-",
               max="%.1f" % max(ar) if ar else "-", purpose=purpose,
               pillow="%d/%d" % (ok_p, len(exp)), ffmpeg="%d/%d" % (ok_f, len(exp)))
    print(row)
    return row, ref


rows = []

# 1. teapot, 400x300, 1 = white. Index 0 black, 1 white, 2 transparent (GCT entry magenta,
# never shown), 3 unused. A GIF table with 3 entries is not allowed, so it has 4.
raw = open(SRC, "rb").read()
N, H, W = 120, 300, 400
fr = np.unpackbits(np.frombuffer(raw, np.uint8).reshape(N, H, W // 8), axis=2).reshape(N, H, W)
PAL1 = [(0, 0, 0), (255, 255, 255), (255, 0, 255), (0, 0, 0)]
frames = delta_frames(fr, 2, 2, True)
row, ref = build("teapot_1bit.gif", W, H, PAL1, frames,
                 "e-paper 1-bit, 400x300 needs MAX_WIDTH >= 400", one_bit=True)
packed = b"".join(np.packbits(c, axis=1).tobytes() for c in ref)
print("teapot_1bit vs teapot.bin bit-exact:", packed == raw)
row["bin"] = packed == raw
rows.append(row)

# 2. same, centered 320x240 crop (x 40..359, y 30..269; 40 is byte aligned)
fc = fr[:, 30:270, 40:360]
frames = delta_frames(fc, 2, 2, True)
row, ref = build("teapot_1bit_320.gif", 320, 240, PAL1, frames,
                 "1-bit within current MAX_WIDTH 320", one_bit=True)
row["bin"] = all(np.array_equal(a, b) for a, b in zip(ref, fc))
rows.append(row)

# 3. small_rgb: 64x64, 15 colors + transparent index 15, a ball circling over stripes
PAL16 = [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
         (0, 255, 255), (255, 128, 0), (128, 0, 255), (64, 64, 64), (128, 128, 128),
         (0, 96, 48), (96, 32, 0), (255, 160, 200), (32, 32, 96), (255, 0, 255)]
yy, xx = np.mgrid[0:64, 0:64]
bgimg = np.where(((xx + yy) // 8) % 2 == 0, 9, 14).astype(np.uint8)
fr = []
for i in range(20):
    a = 2 * np.pi * i / 20
    cx, cy = 32 + 18 * np.cos(a), 32 + 18 * np.sin(a)
    im = bgimg.copy()
    im[(xx - cx) ** 2 + (yy - cy) ** 2 <= 81] = 2 + i % 7
    im[(xx - cx) ** 2 + (yy - cy) ** 2 <= 9] = 1
    fr.append(im)
frames = delta_frames(fr, 15, 4, False)
row, _ = build("small_rgb.gif", 64, 64, PAL16, frames, "RGB565 path on a TFT, 25 fps")
rows.append(row)

# 4a. disposal_2: black background (index 0), 16x16 squares; frame 4 uses disposal 1 so its
# square stays, the others are restored to background after showing
PAL4 = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 255)]
frames = [dict(x=0, y=0, w=64, h=64, idx=np.zeros((64, 64), np.uint8), trans=None,
               delay=20, disposal=2)]
frames[0]["idx"][24:40, 24:40] = 3
for i in range(1, 9):
    frames.append(dict(x=(i - 1) * 6, y=(i - 1) * 6, w=16, h=16,
                       idx=np.full((16, 16), 1 + i % 2, np.uint8), trans=None, delay=20,
                       disposal=1 if i == 4 else 2))
row, _ = build("disposal_2.gif", 64, 64, PAL4, frames, "disposal 2 (restore to bg); frame 4 disposal 1")
rows.append(row)

# 4b. delay_0: delays 0 and 1 cs (browsers clamp these to 10 cs; a decoder must not divide
# by them or spin)
frames = []
for i, d in enumerate([0, 1, 0, 1, 0, 1]):
    im = np.full((32, 32), i % 4, np.uint8)
    im[:, i * 5:i * 5 + 4] = 3 - i % 4
    frames.append(dict(x=0, y=0, w=32, h=32, idx=im, trans=None, delay=d, disposal=1))
row, _ = build("delay_0.gif", 32, 32, PAL4, frames, "delays 0 and 1 cs")
rows.append(row)

# 4c. single_frame: no loop extension, no GCE
im = ((xx[:32, :32] // 8 + yy[:32, :32] // 8) % 4).astype(np.uint8)
frames = [dict(x=0, y=0, w=32, h=32, idx=im, trans=None, delay=0, disposal=0, gce=False)]
row, _ = build("single_frame.gif", 32, 32, PAL4, frames, "one frame, no GCE, no loop ext",
               loop=False)
rows.append(row)

json.dump(rows, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
