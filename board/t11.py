fbmv = memoryview(fb)
INK = {0: bytes(10), 0xFF: b"\xff" * 10}


def square(x0, y0=110, n=80, ink=0):
    row = INK[ink]
    xb = x0 // 8
    for y in range(y0, y0 + n):
        o = y * STRIDE + xb
        fb[o:o + 10] = row


def write_band(c, y0, y1):
    cmd(0x44, bytes([0, STRIDE - 1]))
    cmd(0x45, bytes([y0 & 0xFF, y0 >> 8, y1 & 0xFF, y1 >> 8]))
    cmd(0x4E, b"\x00")
    cmd(0x4F, bytes([y0 & 0xFF, y0 >> 8]))
    cmd(c, fbmv[y0 * STRIDE:(y1 + 1) * STRIDE])


def anim3(frames_lut, n=60):
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    load_lut(make_lut(frames_lut, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    refresh(0xCC)
    x, y, dx, dy = 0, 0, 24, 16
    spi_ns = busy_ns = 0
    t0 = time.monotonic_ns()
    for i in range(n):
        oy = y
        square(x, y, 80, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - 80: dx = -dx; x += 2 * dx
        if y < 0 or y > H - 80: dy = -dy; y += 2 * dy
        square(x, y, 80, 0)
        y0, y1 = min(oy, y), max(oy, y) + 79
        a = time.monotonic_ns()
        write_band(0x24, y0, y1)
        b = time.monotonic_ns()
        cmd(0x22, b"\x0c"); cmd(0x20); wait_busy(2000)
        c = time.monotonic_ns()
        write_band(0x26, y0, y1)
        spi_ns += (b - a) + (time.monotonic_ns() - c); busy_ns += c - b
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    print("lut %d: %.1f ms/frame = %.1f fps (spi %.1f, busy %.1f, other %.1f)" % (
        frames_lut, dt, 1000 / dt, spi_ns / 1e6 / n, busy_ns / 1e6 / n,
        dt - (spi_ns + busy_ns) / 1e6 / n))

anim3(6)
time.sleep(2)
anim3(4)
