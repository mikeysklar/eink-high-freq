# t25: anim14 with one CS assertion per frame; only D/C toggles between commands.
# Load after t24.


def c1(c, data):
    dc.value = False
    spi.write(CB[c])
    dc.value = True
    spi.write(data)


def rect1(c, sq, val, size=80):
    xb0 = sq[0] // 8
    y0 = sq[1]
    y1 = y0 + size - 1
    P44[0] = xb0; P44[1] = xb0 + size // 8 - 1
    P45[0] = y0 & 0xFF; P45[1] = y0 >> 8; P45[2] = y1 & 0xFF; P45[3] = y1 >> 8
    P4F[0] = y0 & 0xFF; P4F[1] = y0 >> 8
    c1(0x44, P44)
    c1(0x45, P45)
    c1(0x4E, CB[xb0])
    c1(0x4F, P4F)
    c1(c, val)


def anim15(nf=1, lag=4, fr=0x05, n=400, size=80, quiet=False):
    start(nf, fr)
    gc.collect()
    x, y, dx, dy = 0, 0, 24, 16
    h = [None] * (lag + 2)
    t0 = time.monotonic_ns()
    dt = 0
    for i in range(n + lag):
        if i < n:
            x += dx; y += dy
            if x < 0 or x > W - size: dx = -dx; x += 2 * dx
            if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        h.pop(0); h.append((x, y))
        wb()
        cs.value = False
        if h[0] is not None: rect1(0x26, h[0], F800)
        if h[1] is not None: rect1(0x26, h[1], Z800)
        if h[-2] is not None: rect1(0x24, h[-2], F800)
        rect1(0x24, h[-1], Z800)
        c1(0x44, FULL_X); c1(0x45, FULL_Y); c1(0x22, b"\x0c")
        dc.value = False
        spi.write(CB[0x20])
        cs.value = True
        if i == n - 1:
            dt = (time.monotonic_ns() - t0) / 1e6 / n
    wb()
    if not quiet:
        print("anim15 nf %d lag %d: %.1f ms/frame = %.1f fps" % (nf, lag, dt, 1000 / dt))
    return dt
