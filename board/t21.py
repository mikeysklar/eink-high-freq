# t21: anim10 without host stalls. Allocation-free BUSY wait (the old wait_busy allocated
# long ints from monotonic_ns every poll and kept triggering 11.7 ms GC passes), automatic
# GC off with a manual collect during BUSY when the heap runs low, and dead buffers freed.
# Needs setup, lut, t11, t12, t15, t18, t19, t20 loaded first.
import gc

for _n in ("black", "cropA", "cropB", "cmA", "cmB"):
    globals().pop(_n, None)
cbuf = bytearray(4096)
cmv = memoryview(cbuf)
gc.collect()

P44 = bytearray(2)
P45 = bytearray(4)
P4F = bytearray(2)


def wb(limit=400000):
    i = 0
    while busy.value:
        i += 1
        if i > limit:
            return False
    return True


def fsend2(c, n, xb0, xb1, y0, y1):
    P44[0] = xb0; P44[1] = xb1
    P45[0] = y0 & 0xFF; P45[1] = y0 >> 8; P45[2] = y1 & 0xFF; P45[3] = y1 >> 8
    P4F[0] = y0 & 0xFF; P4F[1] = y0 >> 8
    fcmd(0x44, P44)
    fcmd(0x45, P45)
    fcmd(0x4E, CB[xb0])
    fcmd(0x4F, P4F)
    fcmd(c, cmv[:n])


def anim11(nf=4, fr=0x05, n=200, size=80, low=12000, quiet=False):
    lut_n = make_lut(nf, VSH1, VSL, fr)
    lut_s = make_lut(nf, VSL, VSH1, fr)
    start(nf, fr)
    gc.collect()
    gc.disable()
    x, y, dx, dy = 0, 0, 24, 16
    square(x, y, size, 0)
    last = (0, size // 8 - 1, 0, size - 1)
    k = crop(*last)
    fsend2(0x24, k, *last)
    fgo()
    tgt = 0x26
    gcs = 0
    t0 = time.monotonic_ns()
    for i in range(n):
        ox, oy = x, y
        square(x, y, size, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - size: dx = -dx; x += 2 * dx
        if y < 0 or y > H - size: dy = -dy; y += 2 * dy
        square(x, y, size, 0)
        b0 = min(ox, x) // 8; b1 = (max(ox, x) + size) // 8 - 1
        r0 = min(oy, y); r1 = max(oy, y) + size - 1
        u0 = min(last[0], b0); u1 = max(last[1], b1)
        v0 = min(last[2], r0); v1 = max(last[3], r1)
        k = crop(u0, u1, v0, v1)
        if gc.mem_free() < low:
            gc.collect(); gcs += 1
        wb()
        fsend2(tgt, k, u0, u1, v0, v1)
        fcmd(0x32, lut_s if tgt == 0x26 else lut_n)
        fgo()
        last = (b0, b1, r0, r1)
        tgt = 0x24 if tgt == 0x26 else 0x26
    wb()
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    gc.enable()
    if not quiet:
        print("anim11 nf %d fr 0x%02X: %.1f ms/frame = %.1f fps, %d GCs, free %d" % (
            nf, fr, dt, 1000 / dt, gcs, gc.mem_free()))
    return dt
