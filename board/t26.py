# t26: anim15 with one write per plane. The square always moves by (+-24, +-16), so the
# box covering the old and new squares (104 x 96) has one of 4 fixed images. Precompute
# them and send one window write per plane instead of two rect fills. Sprite-specific.
# Load after t25.
BW8, BH = 13, 96
PAT = {}
for _sx in (-1, 1):
    for _sy in (-1, 1):
        _b = bytearray(b"\xff" * (BW8 * BH))
        _c0 = 3 if _sx > 0 else 0
        _r0 = 16 if _sy > 0 else 0
        for _r in range(_r0, _r0 + 80):
            _b[_r * BW8 + _c0:_r * BW8 + _c0 + 10] = bytes(10)
        PAT[(_sx, _sy)] = bytes(_b)


def box1(c, a, b):
    # plane c goes from square at a to square at b (one step of +-24, +-16)
    xb0 = min(a[0], b[0]) // 8
    y0 = min(a[1], b[1])
    y1 = y0 + BH - 1
    P44[0] = xb0; P44[1] = xb0 + BW8 - 1
    P45[0] = y0 & 0xFF; P45[1] = y0 >> 8; P45[2] = y1 & 0xFF; P45[3] = y1 >> 8
    P4F[0] = y0 & 0xFF; P4F[1] = y0 >> 8
    c1(0x44, P44)
    c1(0x45, P45)
    c1(0x4E, CB[xb0])
    c1(0x4F, P4F)
    c1(c, PAT[(1 if b[0] > a[0] else -1, 1 if b[1] > a[1] else -1)])


def step(c, a, b):
    if a is None:
        rect1(c, b, Z800)
    elif a == b:
        pass
    else:
        box1(c, a, b)


def anim16(nf=1, lag=4, fr=0x05, n=400, size=80, quiet=False):
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
        if h[1] is not None:
            step(0x26, h[0], h[1])
        step(0x24, h[-2], h[-1])
        c1(0x44, FULL_X); c1(0x45, FULL_Y); c1(0x22, b"\x0c")
        dc.value = False
        spi.write(CB[0x20])
        cs.value = True
        if i == n - 1:
            dt = (time.monotonic_ns() - t0) / 1e6 / n
    wb()
    if not quiet:
        print("anim16 nf %d lag %d: %.1f ms/frame = %.1f fps" % (nf, lag, dt, 1000 / dt))
    return dt
