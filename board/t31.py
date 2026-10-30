# t31: spinning Utah teapot streamed from flash. Frames are pre-rendered on the Mac
# (teapot/make_frames.py, Newell patches) as 320x208 1-bit windows, 8320 B each, in
# /teapot.bin. Each step reads frame N into a pool buffer; 0x24 gets frame N and 0x26 the
# frame from `lag` steps back, both as one window write, so nothing needs erasing. Same
# cleanup as t28: hidden-object balanced wipe every `every` s, OTP clean every `clean` s.
# Load after t30 (uses wipe, otpclean, c1).
TW, TH = 320, 208
TB = TW // 8
TFR = TB * TH
TX0 = (STRIDE - TB) // 2      # RAM byte column
TY0 = (H - TH) // 2
TWHITE = b"\xff" * TFR
TP44 = bytes([TX0, TX0 + TB - 1])
TP45 = bytes([TY0 & 0xFF, TY0 >> 8, (TY0 + TH - 1) & 0xFF, (TY0 + TH - 1) >> 8])
TP4F = bytes([TY0 & 0xFF, TY0 >> 8])
for _n in ("AMIGA",):
    globals().pop(_n, None)
gc.collect()


def twin(c, data):
    c1(0x44, TP44)
    c1(0x45, TP45)
    c1(0x4E, CB[TX0])
    c1(0x4F, TP4F)
    c1(c, data)


def teapot(nf=1, lag=6, fr=0x05, secs=30, step=1, every=4, k=8, clean=15, fin=True,
           quiet=False, path="/teapot.bin"):
    f = open(path, "rb")
    f.seek(0, 2)
    nfr = f.tell() // TFR
    pool = [bytearray(TFR) for _ in range(lag + 2)]
    hist = [TWHITE] * (lag + 1)    # what each plane should show, oldest first
    start(nf, fr)
    if k > 0:
        wipe(k)
    gc.collect()
    fi = 0
    n = 0
    wipes = 0
    cleans = 0
    tread = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    twipe = t0 + every * 1000000000
    tclean = t0 + clean * 1000000000
    dt = 0
    tail = -1
    drain = 0
    while tail != 0:
        cur = TWHITE
        if drain:
            drain -= 1
            if drain == 0:
                wb(); wipe(k); wipes += 1
                twipe = time.monotonic_ns() + every * 1000000000
        elif tail < 0:
            buf = pool[n % (lag + 2)]
            tr = time.monotonic_ns()
            f.seek(fi * TFR)
            f.readinto(buf)
            tread += time.monotonic_ns() - tr
            cur = buf
            fi = (fi + step) % nfr
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
                    for j in range(lag + 1): hist[j] = TWHITE
                elif k > 0 and tn > twipe:
                    drain = lag + 2
        else:
            tail -= 1
        hist.pop(0); hist.append(cur)
        wb()
        cs.value = False
        twin(0x26, hist[0])
        twin(0x24, hist[-1])
        c1(0x44, FULL_X); c1(0x45, FULL_Y); c1(0x22, b"\x0c")
        dc.value = False
        spi.write(CB[0x20])
        cs.value = True
    wb()
    f.close()
    if fin:
        time.sleep(1)
        finish()
    if not quiet:
        print("teapot nf %d lag %d: %d frames, %d wipes, %d cleans, %.1f ms/frame = %.1f fps,"
              " read %.2f ms/frame" % (nf, lag, n, wipes, cleans, dt, 1000 / dt,
                                       tread / 1e6 / n))
    return dt
