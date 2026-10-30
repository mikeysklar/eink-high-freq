# t30: checkered spinning ball (Amiga-style homage) on the t28 method: lagged 0x26,
# 1-frame LUT, hidden-ball balanced wipe every few seconds, OTP clean every `clean` s.
# 96 px sphere, 16 longitude x 8 latitude checks, axis tilted, black outline so white
# checks still read as a ball. 16 precomputed 1-bit frames (1152 B each) built on the
# board: per-pixel longitude/latitude is computed once, each frame only shifts longitude.
# Spin direction follows the horizontal direction. Load after t29.
import math

AS = 96                      # ball size in px
AB = AS // 8                 # width in RAM bytes
ASUB = 8                     # frames per check width of rotation
NLON = 16                    # longitude checks around the whole sphere
NFR = 2 * ASUB               # two checks = identical pattern, so 16 frames
FA = b"\xff" * (AB * AS)
P44a = bytearray(2)
P45a = bytearray(4)
P4Fa = bytearray(2)


def make_amiga(tilt=0.3, ring=2.5):
    R = AS / 2
    ct, st = math.cos(tilt), math.sin(tilt)
    lonq = bytearray(AS * AS)    # longitude in 1/ASUB check units, 0 .. NLON*ASUB-1
    latb = bytearray(AS * AS)    # 0 = outside, 1/2 = latitude band parity + 1, 3 = outline
    for yy in range(AS):
        py = yy + 0.5 - R
        for xx in range(AS):
            px = xx + 0.5 - R
            d2 = px * px + py * py
            if d2 > R * R:
                continue
            i = yy * AS + xx
            if d2 > (R - ring) ** 2:
                latb[i] = 3
                continue
            z = math.sqrt(R * R - d2)
            x1 = px * ct + py * st
            y1 = -px * st + py * ct
            lon = math.atan2(x1, z) + math.pi           # 0 .. 2 pi
            lat = math.asin(max(-1.0, min(1.0, y1 / R))) + math.pi / 2   # 0 .. pi
            lonq[i] = int(lon / (2 * math.pi) * NLON * ASUB) % (NLON * ASUB)
            latb[i] = 1 + (int(lat / math.pi * 8) & 1)
    frames = []
    for p in range(NFR):
        b = bytearray(FA)
        for i in range(AS * AS):
            v = latb[i]
            if v == 0:
                continue
            if v == 3 or ((lonq[i] + p) // ASUB + v) & 1:
                b[(i // AS) * AB + (i % AS) // 8] &= ~(0x80 >> (i % 8)) & 0xFF
        frames.append(bytes(b))
    return frames


_t = time.monotonic()
AMIGA = make_amiga()
gc.collect()
print("amiga frames: %d x %d B in %.1f s, free %d" % (len(AMIGA), len(AMIGA[0]),
                                                    time.monotonic() - _t, gc.mem_free()))


def wina(c, xb0, y0, data):
    y1 = y0 + AS - 1
    P44a[0] = xb0; P44a[1] = xb0 + AB - 1
    P45a[0] = y0 & 0xFF; P45a[1] = y0 >> 8; P45a[2] = y1 & 0xFF; P45a[3] = y1 >> 8
    P4Fa[0] = y0 & 0xFF; P4Fa[1] = y0 >> 8
    c1(0x44, P44a)
    c1(0x45, P45a)
    c1(0x4E, CB[xb0])
    c1(0x4F, P4Fa)
    c1(c, data)


def amiga(nf=1, lag=6, fr=0x05, secs=30, every=4, k=8, clean=15, fin=True, quiet=False):
    start(nf, fr)
    if k > 0:
        wipe(k)
    gc.collect()
    ymax = (H - AS) * 16     # y in 1/16 px
    xhmax = (W - AS) // 8 * 2   # x in half RAM bytes: 4 px per frame
    xh, dxh = 0, 1
    y, vy, g = 0, 0, 4
    vkick = 0
    ph = 0
    h = [None] * (lag + 2)   # (xb, y, phase)
    n = 0
    wipes = 0
    cleans = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    twipe = t0 + every * 1000000000
    tclean = t0 + clean * 1000000000
    dt = 0
    tail = -1
    drain = 0
    while tail != 0:
        if drain:
            drain -= 1
            if drain == 0:
                wb(); wipe(k); wipes += 1
                twipe = time.monotonic_ns() + every * 1000000000
        elif tail < 0:
            xh += dxh
            if xh < 0 or xh > xhmax: dxh = -dxh; xh += 2 * dxh
            ph = (ph + dxh) % NFR
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
                    wb(); otpclean(nf, fr); wipe(k); cleans += 1
                    twipe = time.monotonic_ns() + every * 1000000000
                    tclean = time.monotonic_ns() + clean * 1000000000
                    for j in range(lag + 2): h[j] = None
                elif k > 0 and tn > twipe:
                    drain = lag + 2
        else:
            tail -= 1
        h.pop(0); h.append(None if drain else (xh >> 1, y >> 4, ph))
        wb()
        cs.value = False
        a = h[0]; b = h[1]
        if a is not None and (b is None or a[0] != b[0] or a[1] != b[1]):
            wina(0x26, a[0], a[1], FA)
        if b is not None: wina(0x26, b[0], b[1], AMIGA[b[2]])
        a = h[-2]; b = h[-1]
        if a is not None and (b is None or a[0] != b[0] or a[1] != b[1]):
            wina(0x24, a[0], a[1], FA)
        if b is not None: wina(0x24, b[0], b[1], AMIGA[b[2]])
        c1(0x44, FULL_X); c1(0x45, FULL_Y); c1(0x22, b"\x0c")
        dc.value = False
        spi.write(CB[0x20])
        cs.value = True
    wb()
    if fin:
        time.sleep(1)
        finish()
    if not quiet:
        print("amiga nf %d lag %d: %d frames, %d wipes, %d cleans, %.1f ms/frame = %.1f fps"
              % (nf, lag, n, wipes, cleans, dt, 1000 / dt))
    return dt
