# t28: bouncing ball with a periodic balanced wipe. Equal black/white drive per change
# still leaves passed-over pixels gray (lag 4, 6, 8 all smear). Every `every` seconds the
# whole screen is driven black for k frames then white for k frames with the same 1-frame
# LUT (balanced), then the ball is redrawn from a clean history. Load after t27.
ZFILL = bytes(STRIDE * 30)


def wipe(k):
    # 0x24 black, 0x26 white -> BW drive (to black) on every pixel, k updates
    wfill(0x24, ZFILL); wfill(0x26)
    for _ in range(k):
        wb(); fgo()
    wb()
    # 0x24 white, 0x26 black -> WB drive (to white) on every pixel, k updates
    wfill(0x24); wfill(0x26, ZFILL)
    for _ in range(k):
        wb(); fgo()
    wb()
    wfill(0x26)              # both planes white: no drive until the ball is drawn


def ball2(nf=1, lag=4, fr=0x05, secs=20, every=4, k=12, clean=0, fin=True, quiet=False):
    # clean > 0: also an OTP clean (t29) every `clean` seconds, replacing that wipe
    start(nf, fr)
    if k > 0:
        wipe(k)              # match the background to the white our erase reaches
    gc.collect()
    ymax = (H - BS) * 16
    xbmax = (W - BS) // 8
    xb, dxb = 0, 1
    y, vy, g = 0, 0, 4
    vkick = 0
    h = [None] * (lag + 2)
    n = 0
    wipes = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    twipe = t0 + every * 1000000000
    tclean = t0 + clean * 1000000000
    cleans = 0
    dt = 0
    tail = -1
    drain = 0                # frames left with the ball hidden before a wipe
    while tail != 0:
        if drain:
            drain -= 1       # ball hidden: let both planes erase it with normal drive
            if drain == 0:
                wb(); wipe(k); wipes += 1
                twipe = time.monotonic_ns() + every * 1000000000
        elif tail < 0:
            xb += dxb
            if xb < 0 or xb > xbmax: dxb = -dxb; xb += 2 * dxb
            vy += g; y += vy
            if y > ymax:
                y = 2 * ymax - y
                vy = -vy * 15 // 16
                if vkick == 0: vkick = vy
                if vy > vkick // 2: vy = vkick
            n += 1
            if n & 63 == 0:
                tn = time.monotonic_ns()
                if tn > tend:
                    dt = (tn - t0) / 1e6 / n
                    tail = lag
                elif clean and tn > tclean:
                    # the OTP white is deeper than our erase reaches, so trails stand out
                    # until the background is brought to "our" white by one short wipe
                    wb(); otpclean(nf, fr); wipe(k); cleans += 1
                    twipe = time.monotonic_ns() + every * 1000000000
                    tclean = time.monotonic_ns() + clean * 1000000000
                    for j in range(lag + 2): h[j] = None
                elif k > 0 and tn > twipe:
                    drain = lag + 2      # hide the ball first so the wipe starts all white
        else:
            tail -= 1
        h.pop(0); h.append(None if drain else (xb, y >> 4))
        wb()
        cs.value = False
        if h[0] is not None: win1(0x26, h[0][0], h[0][1], F512)
        if h[1] is not None: win1(0x26, h[1][0], h[1][1], BALL)
        if h[-2] is not None: win1(0x24, h[-2][0], h[-2][1], F512)
        if h[-1] is not None: win1(0x24, h[-1][0], h[-1][1], BALL)
        c1(0x44, FULL_X); c1(0x45, FULL_Y); c1(0x22, b"\x0c")
        dc.value = False
        spi.write(CB[0x20])
        cs.value = True
    wb()
    if fin:
        time.sleep(1)
        finish()
    if not quiet:
        print("ball2 nf %d lag %d k %d every %d s clean %d s: %d frames, %d wipes, %d cleans, "
              "%.1f ms/frame = %.1f fps" % (nf, lag, k, every, clean, n, wipes, cleans, dt,
                                            1000 / dt))
    return dt
