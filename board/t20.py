# t20: manual RAM ping-pong. Each frame writes the new image into the RAM that holds
# the frame before last, and reloads the LUT with BW/WB swapped so the controller treats
# the other RAM as "old". One cropped band per frame instead of two, Python overlapped
# with BUSY. Needs setup, lut, t11, t12, t15, t18, t19 loaded first.
from ulab import numpy as np

A2 = np.frombuffer(fb, dtype=np.uint8).reshape((H, STRIDE))
cbuf = bytearray(STRIDE * H)
cmv = memoryview(cbuf)
CB = [bytes((i,)) for i in range(256)]


def fcmd(c, data=None):
    # CS stays low across the D/C change: one CS cycle per command
    cs.value = False
    dc.value = False
    spi.write(CB[c])
    if data:
        dc.value = True
        spi.write(data)
    cs.value = True


def crop(xb0, xb1, y0, y1):
    h, w = y1 - y0 + 1, xb1 - xb0 + 1
    np.frombuffer(cbuf, dtype=np.uint8, count=h * w).reshape((h, w))[:, :] = \
        A2[y0:y1 + 1, xb0:xb1 + 1]
    return h * w


def fsend(c, n, xb0, xb1, y0, y1):
    fcmd(0x44, bytes((xb0, xb1)))
    fcmd(0x45, bytes((y0 & 0xFF, y0 >> 8, y1 & 0xFF, y1 >> 8)))
    fcmd(0x4E, CB[xb0])
    fcmd(0x4F, bytes((y0 & 0xFF, y0 >> 8)))
    fcmd(c, cmv[:n])


def fgo():
    fcmd(0x44, FULL_X); fcmd(0x45, FULL_Y)
    fcmd(0x22, b"\x0c"); fcmd(0x20)


def union(a, b):
    return (min(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]))


def anim10(nf=4, fr=0x05, n=120, size=80, quiet=False):
    lut_n = make_lut(nf, VSH1, VSL, fr)   # old in 0x26, new in 0x24
    lut_s = make_lut(nf, VSL, VSH1, fr)   # old in 0x24, new in 0x26
    start(nf, fr)
    x, y, dx, dy = 0, 0, 24, 16
    square(x, y, size, 0)
    cur = (0, size // 8 - 1, 0, size - 1)
    k = crop(*cur)
    fsend(0x24, k, *cur)
    fgo()
    last = cur          # band changed by the update in flight
    tgt = 0x26          # RAM that receives the next frame
    t_busy = t_spi = 0
    t0 = time.monotonic_ns()
    for i in range(n):
        ox, oy = x, y
        square(x, y, size, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - size: dx = -dx; x += 2 * dx
        if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        square(x, y, size, 0)
        band = (min(ox, x) // 8, (max(ox, x) + size) // 8 - 1, min(oy, y), max(oy, y) + size - 1)
        u = union(last, band)   # target RAM is two frames stale over both bands
        k = crop(*u)
        a = time.monotonic_ns()
        wait_busy(2000)
        b = time.monotonic_ns()
        fsend(tgt, k, *u)
        fcmd(0x32, lut_s if tgt == 0x26 else lut_n)
        fgo()
        t_busy += b - a
        t_spi += time.monotonic_ns() - b
        last = band
        tgt = 0x24 if tgt == 0x26 else 0x26
    wait_busy(2000)
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    if not quiet:
        print("swap nf %d fr 0x%02X: %.1f ms/frame = %.1f fps (wait %.1f, spi %.1f, py %.1f)" % (
            nf, fr, dt, 1000 / dt, t_busy / 1e6 / n, t_spi / 1e6 / n,
            dt - (t_busy + t_spi) / 1e6 / n))
    return dt
