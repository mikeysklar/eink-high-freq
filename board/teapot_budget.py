# teapot_budget: the teapot with SmoothEPD/InkBoy budget masks instead of the lag trick.
# Load after teapot_demo.py (uses its init, fill, fast_mode, wipe, go, frame, finish, wb).
# Masks come from teapot/make_masks.py: each step is two 15000 B planes (0x26 = drive
# black, 0x24 = drive white, both 0 = hold) for the same 1-frame LUT. Layout: enter (B),
# loop (n), exit (B), enter+exit payback planes (nee), loop payback planes (nlp).
# No mid-run wipes. The rule is not DC balanced, so after the exit (screen blank) every
# frame of net drive is paid back exactly: payback plane j is held for 2**(nb-1-j)
# frames, loop planes once per loop played. Then a clean OTP refresh and deep sleep.


def teapot_budget(B=15, n=120, nee=5, nlp=7, fr=0x05, secs=20, k=8, fin=True,
                  path="/teapot_b15.bin"):
    S = 2 * FRB
    f = open(path, "rb")
    gc.collect()
    buf = bytearray(S)
    mv = memoryview(buf)
    b26, b24 = mv[:FRB], mv[FRB:]

    def step(i):
        f.seek(i * S)
        f.readinto(buf)
        wb()
        frame(0x26, b26)
        frame(0x24, b24)
        go()

    def hold(i, frames):
        f.seek(i * S)
        f.readinto(buf)
        wb()
        frame(0x26, b26)
        frame(0x24, b24)
        for _ in range(frames):
            wb(); go()

    init(); fill(0x24); fill(0x26); refresh(0xF7)
    fast_mode(1, fr)
    wipe(k)
    gc.collect()
    for i in range(B):
        step(i)
    loops = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    while True:
        for i in range(n):
            step(B + i)
        loops += 1
        if time.monotonic_ns() > tend:
            break
    dt = (time.monotonic_ns() - t0) / 1e6 / (loops * n)
    for i in range(B):
        step(B + n + i)
    tp = time.monotonic_ns()
    base = 2 * B + n
    for j in range(nee):
        hold(base + j, 1 << (nee - 1 - j))
    for j in range(nlp):
        hold(base + nee + j, loops << (nlp - 1 - j))
    wb()
    tp = (time.monotonic_ns() - tp) / 1e9
    f.close()
    if fin:
        time.sleep(1)
        finish()
    print("budget B %d: %d loops, %.1f ms/frame = %.1f fps, payback %.1f s" % (
        B, loops, dt, 1000 / dt, tp))
    return dt


print("teapot_budget loaded, free %d" % gc.mem_free())
