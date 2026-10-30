# t24: two-update drive budget with no per-pixel math. 0x24 = frame N, 0x26 = frame N-2,
# so every pixel that changed in the last two steps is driven: each change gets `2 x nf`
# frames, the screen updates every nf frames. RAM changes are rectangle fills done by the
# controller (window + constant byte stream). Load after t23.
Z800 = bytes(800)
F800 = b"\xff" * 800
P44 = bytearray(2)
P45 = bytearray(4)
P4F = bytearray(2)


def rect(c, sq, val, size=80):
    xb0 = sq[0] // 8
    y0 = sq[1]
    y1 = y0 + size - 1
    P44[0] = xb0; P44[1] = xb0 + size // 8 - 1
    P45[0] = y0 & 0xFF; P45[1] = y0 >> 8; P45[2] = y1 & 0xFF; P45[3] = y1 >> 8
    P4F[0] = y0 & 0xFF; P4F[1] = y0 >> 8
    fcmd(0x44, P44)
    fcmd(0x45, P45)
    fcmd(0x4E, CB[xb0])
    fcmd(0x4F, P4F)
    fcmd(c, val)


def anim13(nf=2, fr=0x05, n=300, size=80, quiet=False):
    start(nf, fr)
    gc.collect()
    x, y, dx, dy = 0, 0, 24, 16
    h = [None, None, None, None]   # positions N-3, N-2, N-1, N
    t0 = time.monotonic_ns()
    dt = 0
    for i in range(n + 2):
        if i < n:
            x += dx; y += dy
            if x < 0 or x > W - size: dx = -dx; x += 2 * dx
            if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        h[0] = h[1]; h[1] = h[2]; h[2] = h[3]; h[3] = (x, y)
        wb()
        if h[0] is not None: rect(0x26, h[0], F800)   # 0x26: frame N-3 -> N-2
        if h[1] is not None: rect(0x26, h[1], Z800)
        if h[2] is not None: rect(0x24, h[2], F800)   # 0x24: frame N-1 -> N
        rect(0x24, h[3], Z800)
        fgo()
        if i == n - 1:
            dt = (time.monotonic_ns() - t0) / 1e6 / n
    wb()
    if not quiet:
        print("anim13 nf %d: %.1f ms/frame = %.1f fps" % (nf, dt, 1000 / dt))
    return dt


def anim14(nf=1, lag=4, fr=0x05, n=400, size=80, quiet=False):
    # 0x24 = frame N, 0x26 = frame N-lag: each change is driven for lag updates of nf frames
    start(nf, fr)
    gc.collect()
    x, y, dx, dy = 0, 0, 24, 16
    h = [None] * (lag + 2)   # positions N-lag-1 .. N
    t0 = time.monotonic_ns()
    dt = 0
    for i in range(n + lag):
        if i < n:
            x += dx; y += dy
            if x < 0 or x > W - size: dx = -dx; x += 2 * dx
            if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        h.pop(0); h.append((x, y))
        wb()
        if h[0] is not None: rect(0x26, h[0], F800)   # 0x26: frame N-lag-1 -> N-lag
        if h[1] is not None: rect(0x26, h[1], Z800)
        if h[-2] is not None: rect(0x24, h[-2], F800)  # 0x24: frame N-1 -> N
        rect(0x24, h[-1], Z800)
        fgo()
        if i == n - 1:
            dt = (time.monotonic_ns() - t0) / 1e6 / n
    wb()
    if not quiet:
        print("anim14 nf %d lag %d: %.1f ms/frame = %.1f fps, %d frames drive/change" % (
            nf, lag, dt, 1000 / dt, nf * lag))
    return dt
