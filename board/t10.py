sub = bytearray(10 * 80)


def write_rect(c, x, y, w=80, h=80):
    xb0, nb = x // 8, w // 8
    y1 = y + h - 1
    cmd(0x44, bytes([xb0, xb0 + nb - 1]))
    cmd(0x45, bytes([y & 0xFF, y >> 8, y1 & 0xFF, y1 >> 8]))
    cmd(0x4E, bytes([xb0]))
    cmd(0x4F, bytes([y & 0xFF, y >> 8]))
    i = 0
    for r in range(y, y + h):
        o = r * STRIDE + xb0
        sub[i:i + nb] = fb[o:o + nb]
        i += nb
    cmd(c, sub)


def anim2(frames_lut, n=60):
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    load_lut(make_lut(frames_lut, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    refresh(0xCC)
    x, y, dx, dy = 0, 0, 24, 16
    spi_ns = busy_ns = 0
    t0 = time.monotonic_ns()
    for i in range(n):
        ox, oy = x, y
        square(x, y, 80, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - 80: dx = -dx; x += 2 * dx
        if y < 0 or y > H - 80: dy = -dy; y += 2 * dy
        square(x, y, 80, 0)
        a = time.monotonic_ns()
        write_rect(0x24, ox, oy); write_rect(0x24, x, y)
        b = time.monotonic_ns()
        cmd(0x22, b"\x0c"); cmd(0x20); wait_busy(2000)
        c = time.monotonic_ns()
        write_rect(0x26, ox, oy); write_rect(0x26, x, y)
        spi_ns += (b - a) + (time.monotonic_ns() - c); busy_ns += c - b
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    print("lut %d: %.1f ms/frame = %.1f fps (spi %.1f, busy %.1f, other %.1f)" % (
        frames_lut, dt, 1000 / dt, spi_ns / 1e6 / n, busy_ns / 1e6 / n,
        dt - (spi_ns + busy_ns) / 1e6 / n))

anim2(6)
time.sleep(2)
anim2(4)
