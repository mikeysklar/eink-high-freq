# t22: per-pixel drive budget on the SSD1683 (InkBoy idea, mapped onto the RAM planes).
# 0x24 holds the image. 0x26 holds the image with "still active" pixels inverted, so the
# normal LUT (BW -> VSH1, WB -> VSL, WW/BB -> VSS) keeps pushing exactly those pixels.
# A pixel stays active for `keep` updates after it changes: keep x nf frames of drive
# per transition, while the screen updates every nf frames. Equal drive both directions.
# Needs setup, lut, t11, t12, t15, t18, t19, t20, t21 loaded first.
from ulab import numpy as np


def sqimg(h, w, ux, uy, sq, size):
    a = np.full((h, w), 255, dtype=np.uint8)
    if sq is not None:
        c0 = sq[0] // 8 - ux; r0 = sq[1] - uy
        a[max(r0, 0):min(r0 + size, h), max(c0, 0):min(c0 + size // 8, w)] = 0
    return a


def fsend3(c, buf, xb0, xb1, y0, y1):
    P44[0] = xb0; P44[1] = xb1
    P45[0] = y0 & 0xFF; P45[1] = y0 >> 8; P45[2] = y1 & 0xFF; P45[3] = y1 >> 8
    P4F[0] = y0 & 0xFF; P4F[1] = y0 >> 8
    fcmd(0x44, P44)
    fcmd(0x45, P45)
    fcmd(0x4E, CB[xb0])
    fcmd(0x4F, P4F)
    fcmd(c, buf)


def frame12(hist, size, keep):
    pts = [s for s in hist if s is not None]
    ux = min(s[0] for s in pts) // 8
    uy = min(s[1] for s in pts)
    ux1 = (max(s[0] for s in pts) + size) // 8 - 1
    uy1 = max(s[1] for s in pts) + size - 1
    h, w = uy1 - uy + 1, ux1 - ux + 1
    imgs = [sqimg(h, w, ux, uy, s, size) for s in hist[-(keep + 1):]]
    mask = np.zeros((h, w), dtype=np.uint8)
    for j in range(keep):
        mask = np.bitwise_or(mask, np.bitwise_xor(imgs[j], imgs[j + 1]))
    new = imgs[-1]
    return new, np.bitwise_xor(new, mask), (ux, ux1, uy, uy1)


def anim12(nf=2, keep=2, fr=0x05, n=300, size=80, low=14000, quiet=False):
    start(nf, fr)
    gc.collect()
    gc.disable()
    x, y, dx, dy = 0, 0, 24, 16
    hist = [None] * (keep + 2) + [(x, y)]  # U spans keep+3 spots so stale actives get cleared
    gcs = 0
    t0 = time.monotonic_ns()
    for i in range(n + keep):
        if i < n:
            x += dx; y += dy
            if x < 0 or x > W - size: dx = -dx; x += 2 * dx
            if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        hist = hist[1:] + [(x, y)]   # after the run, repeat the last spot to drain the mask
        r24, r26, u = frame12(hist, size, keep)
        if gc.mem_free() < low:
            gc.collect(); gcs += 1
        wb()
        fsend3(0x24, r24, *u)
        fsend3(0x26, r26, *u)
        fgo()
        if i == n - 1:
            dt = (time.monotonic_ns() - t0) / 1e6 / n
    wb()
    gc.enable()
    if not quiet:
        print("anim12 nf %d keep %d: %.1f ms/frame = %.1f fps, %d GCs" % (
            nf, keep, dt, 1000 / dt, gcs))
    return dt
