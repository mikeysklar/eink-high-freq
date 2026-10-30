# t27: bouncing ball demo on the t25 method (0x26 lags `lag` frames, 1-frame LUT, one CS
# assertion per frame). A 64 px round ball is a precomputed bitmap written into a
# byte-aligned window; the old spot is erased with a white fill first. x moves in 8 px
# (one RAM byte) steps, y in whole pixels with gravity. Load after t25.
BS = 64                      # ball size in px
BB = BS // 8                 # ball width in RAM bytes
F512 = b"\xff" * (BB * BS)
P44b = bytearray(2)
P45b = bytearray(4)
P4Fb = bytearray(2)


def make_ball():
    b = bytearray(F512)
    r2 = (BS // 2) ** 2
    for yy in range(BS):
        for xx in range(BS):
            dx2 = 2 * xx - (BS - 1); dy2 = 2 * yy - (BS - 1)
            if dx2 * dx2 + dy2 * dy2 <= 4 * r2:
                b[yy * BB + xx // 8] &= ~(0x80 >> (xx % 8)) & 0xFF
    return bytes(b)


BALL = make_ball()


def win1(c, xb0, y0, data):
    y1 = y0 + BS - 1
    P44b[0] = xb0; P44b[1] = xb0 + BB - 1
    P45b[0] = y0 & 0xFF; P45b[1] = y0 >> 8; P45b[2] = y1 & 0xFF; P45b[3] = y1 >> 8
    P4Fb[0] = y0 & 0xFF; P4Fb[1] = y0 >> 8
    c1(0x44, P44b)
    c1(0x45, P45b)
    c1(0x4E, CB[xb0])
    c1(0x4F, P4Fb)
    c1(c, data)


def ball(nf=1, lag=4, fr=0x05, secs=20, fin=True, quiet=False):
    start(nf, fr)
    gc.collect()
    ymax = (H - BS) * 16     # y in 1/16 px fixed point, no floats per frame
    xbmax = (W - BS) // 8
    xb, dxb = 0, 1
    y, vy, g = 0, 0, 4       # g = 0.25 px/frame^2: ~0.5 s fall at ~85 fps
    vkick = 0
    h = [None] * (lag + 2)
    n = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    dt = 0
    tail = -1
    while tail != 0:
        if tail < 0:
            xb += dxb
            if xb < 0 or xb > xbmax: dxb = -dxb; xb += 2 * dxb
            vy += g; y += vy
            if y > ymax:
                y = 2 * ymax - y
                vy = -vy * 15 // 16
                if vkick == 0: vkick = vy
                if vy > vkick // 2: vy = vkick   # re-kick once it decays to half height
            n += 1
            if n & 63 == 0 and time.monotonic_ns() > tend:
                dt = (time.monotonic_ns() - t0) / 1e6 / n
                tail = lag
        else:
            tail -= 1        # hold the last spot so the lagged plane catches up
        h.pop(0); h.append((xb, y >> 4))
        wb()
        cs.value = False
        if h[0] is not None: win1(0x26, h[0][0], h[0][1], F512)
        if h[1] is not None: win1(0x26, h[1][0], h[1][1], BALL)
        if h[-2] is not None: win1(0x24, h[-2][0], h[-2][1], F512)
        win1(0x24, h[-1][0], h[-1][1], BALL)
        c1(0x44, FULL_X); c1(0x45, FULL_Y); c1(0x22, b"\x0c")
        dc.value = False
        spi.write(CB[0x20])
        cs.value = True
    wb()
    if fin:
        time.sleep(1)    # leave the last frame up briefly, then clean refresh + deep sleep
        finish()
    if not quiet:
        print("ball nf %d lag %d: %d frames, %.1f ms/frame = %.1f fps" % (
            nf, lag, n, dt, 1000 / dt))
    return dt
