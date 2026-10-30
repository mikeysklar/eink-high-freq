# teapot_win: teapot_demo.teapot() with dirty windows. Same balanced lag trick and cleanup;
# steady steps write only the precomputed window covering this and the previous step's
# changed pixels (teapot/make_window.py), so the RAM planes stay equal outside it. Steps
# whose pair or previous pair has a blank frame (around wipes and cleans) write full
# frames from teapot.bin. Load after teapot_demo.py.
import struct


from fps_glyphs import GCH, GLY

# fps counter in the bottom-left corner, which no teapot frame or window touches
CX0, CW, CY0, CH = 1, 14, 270, 24     # RAM bytes 1..14 (7 glyphs of 16 px), rows 270..293
CWIN = (CX0, CX0 + CW - 1, CY0, CY0 + CH - 1)


def render(text, dst):
    for ci, ch in enumerate(text):
        g = GCH.find(ch) * 48
        o = 2 * ci
        for r in range(CH):
            dst[o] = GLY[g]
            dst[o + 1] = GLY[g + 1]
            g += 2
            o += CW


def teapot_win(nf=1, lag=6, fr=0x05, secs=30, every=4, k=8, clean=15, fin=True,
               path="/teapot.bin", wpath="/teapot_w6.bin", fps=False):
    f = open(path, "rb")
    f.seek(0, 2)
    nfr = f.tell() // FRB
    g = open(wpath, "rb")
    ent = []
    for i in range(nfr):
        ent.append(struct.unpack("<IBBHH", g.read(10)))
    gc.collect()
    buf = bytearray(2 * FRB)
    mv = memoryview(buf)
    b26, b24 = mv[:FRB], mv[FRB:]
    white = b"\xff" * FRB
    hist = [-1] * (lag + 1)
    # counter uses the lag trick too: on a change, lag steps of 0x26 = old, 0x24 = new,
    # then one step of new/new to stop the drive
    cblank = b"\xff" * (CW * CH)
    c_new = bytearray(cblank)
    c_old = bytearray(cblank)
    c_age = lag + 1
    s = 0
    s_last = 0
    init(); fill(0x24); fill(0x26); refresh(0xF7)
    fast_mode(nf, fr)
    if k > 0:
        wipe(k)
    gc.collect()
    fi = n = wipes = cleans = nwin = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    twipe = t0 + every * 1000000000
    tclean = t0 + clean * 1000000000
    dt = 0
    tail = -1
    drain = 0
    prev_real = False
    t_last = t0
    while tail != 0:
        cur = -1
        s += 1
        if fps and s & 31 == 0:
            tn = time.monotonic_ns()
            if tn - t_last >= 1000000000:
                c_old[:] = c_new
                render("%4.1ffps" % ((s - s_last) * 1e9 / (tn - t_last)), c_new)
                c_age = 0
                t_last, s_last = tn, s
        if drain:
            drain -= 1
            if drain == 0:
                wb(); wipe(k); wipes += 1
                twipe = time.monotonic_ns() + every * 1000000000
                prev_real = False
                c_old[:] = cblank       # the wipe erased the counter: draw it again
                c_age = 0
        elif tail < 0:
            cur = fi
            fi = (fi + 1) % nfr
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
                    for j in range(lag + 1): hist[j] = -1
                    prev_real = False
                    c_old[:] = cblank
                    c_age = 0
                elif k > 0 and tn > twipe:
                    drain = lag + 2
        else:
            tail -= 1
        hist.pop(0); hist.append(cur)
        a, b = hist[0], hist[-1]
        real = a >= 0 and b >= 0
        full = not (real and prev_real)
        if not full:
            off, x0, x1, y0, y1 = ent[b]
            sz = (x1 - x0 + 1) * (y1 - y0 + 1)
            g.seek(off)
            g.readinto(mv[:2 * sz])
            wb()
            win(x0, x1, y0, y1)
            cmd(0x26, mv[:sz])
            win(x0, x1, y0, y1)
            cmd(0x24, mv[sz:2 * sz])
            nwin += 1
        else:
            if a >= 0:
                f.seek(a * FRB); f.readinto(b26)
            if b >= 0:
                f.seek(b * FRB); f.readinto(b24)
            wb()
            frame(0x26, b26 if a >= 0 else white)
            frame(0x24, b24 if b >= 0 else white)
        prev_real = real
        if fps and (c_age <= lag or full):
            win(*CWIN)
            cmd(0x26, c_old if c_age < lag else c_new)
            win(*CWIN)
            cmd(0x24, c_new)
            if c_age <= lag:
                c_age += 1
        go()
    wb()
    f.close()
    g.close()
    if fin:
        time.sleep(1)
        finish()
    print("teapot_win lag %d: %d frames (%d windowed), %d wipes, %d cleans, %.1f ms/frame"
          " = %.1f fps" % (lag, n, nwin, wipes, cleans, dt, 1000 / dt))
    return dt


def win(x0, x1, y0, y1):
    cmd(0x44, bytes((x0, x1)))
    cmd(0x45, bytes((y0 & 0xFF, y0 >> 8, y1 & 0xFF, y1 >> 8)))
    cmd(0x4E, CB[x0])
    cmd(0x4F, bytes((y0 & 0xFF, y0 >> 8)))


print("teapot_win loaded, free %d" % gc.mem_free())
