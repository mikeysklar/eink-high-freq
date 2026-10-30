# t19: cropped RAM writes + Python work overlapped with BUSY, configurable LUT frames / FR.
# Needs setup.py, lut.py, t11.py, t12.py, t15.py, t18.py loaded first.
import gc

fbm = memoryview(fb)
cropA = bytearray(8000)
cropB = bytearray(8000)
cmA = memoryview(cropA)
cmB = memoryview(cropB)


def gather(cm, xb0, xb1, y0, y1):
    w = xb1 - xb0 + 1
    i = 0
    for y in range(y0, y1 + 1):
        cm[i:i + w] = rows[y][xb0:xb1 + 1]
        i += w
    return i


def send(c, cm, n, xb0, xb1, y0, y1):
    cmd(0x44, bytes([xb0, xb1]))
    cmd(0x45, bytes([y0 & 0xFF, y0 >> 8, y1 & 0xFF, y1 >> 8]))
    cmd(0x4E, bytes([xb0]))
    cmd(0x4F, bytes([y0 & 0xFF, y0 >> 8]))
    cmd(c, cm[:n])


def start(nf, fr):
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    load_lut(make_lut(nf, VSH1, VSL, fr)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    cmd(0x37, NO_PINGPONG)
    refresh(0xCC)


def finish():
    # clean full refresh with the OTP waveform, then deep sleep (HV off)
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    cmd(0x10, b"\x01")


def anim9(nf=4, fr=0x05, n=120, size=80, quiet=False):
    start(nf, fr)
    x, y, dx, dy = 0, 0, 24, 16
    square(x, y, size, 0)
    # first frame: whole square into 0x24, nothing pending for 0x26
    pend = None  # (cm, n, xb0, xb1, y0, y1) for 0x26
    nb = gather(cmB, 0, (size // 8) - 1, 0, size - 1)
    send(0x24, cmB, nb, 0, size // 8 - 1, 0, size - 1)
    show_nowait()
    prev = (0, (size // 8) - 1, 0, size - 1)
    t_busy = t_spi = 0
    t0 = time.monotonic_ns()
    for i in range(n):
        # --- during BUSY: 0x26 data = current frame over the band that just changed
        na = gather(cmA, *prev)
        ox, oy = x, y
        square(x, y, size, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - size: dx = -dx; x += 2 * dx
        if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        square(x, y, size, 0)
        band = (min(ox, x) // 8, (max(ox, x) + size) // 8 - 1, min(oy, y), max(oy, y) + size - 1)
        nb = gather(cmB, *band)
        a = time.monotonic_ns()
        wait_busy(2000)
        b = time.monotonic_ns()
        send(0x26, cmA, na, *prev)
        send(0x24, cmB, nb, *band)
        show_nowait()
        t_busy += b - a
        t_spi += time.monotonic_ns() - b
        prev = band
    wait_busy(2000)
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    if not quiet:
        print("nf %d fr 0x%02X: %.1f ms/frame = %.1f fps (wait %.1f, spi %.1f, py %.1f)" % (
            nf, fr, dt, 1000 / dt, t_busy / 1e6 / n, t_spi / 1e6 / n,
            dt - (t_busy + t_spi) / 1e6 / n))
    return dt


def show_nowait(mode=0x0C):
    cmd(0x44, FULL_X); cmd(0x45, FULL_Y)
    cmd(0x22, bytes([mode])); cmd(0x20)


gc.collect()
