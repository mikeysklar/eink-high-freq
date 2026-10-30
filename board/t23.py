# t23: shrink the live heap so a GC pass fits inside BUSY. anim12 never touches the
# full-screen buffers, so drop them and fill RAM from a small constant chunk instead.
# Load after t22.
FILL = bytes(b"\xff" * (STRIDE * 30))


def wfill(c, chunk=FILL, reps=H // 30):
    cmd(0x44, FULL_X); cmd(0x45, FULL_Y)
    cmd(0x4E, b"\x00"); cmd(0x4F, b"\x00\x00")
    cs.value = False
    dc.value = False
    spi.write(CB[c])
    dc.value = True
    for _ in range(reps):
        spi.write(chunk)
    cs.value = True


def start(nf, fr):
    init(); wfill(0x24); wfill(0x26); refresh(0xF7)
    load_lut(make_lut(nf, VSH1, VSL, fr)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    cmd(0x37, NO_PINGPONG)
    refresh(0xCC)


def finish():
    # clean full refresh with the OTP waveform, then deep sleep (HV off)
    init(); wfill(0x24); wfill(0x26); refresh(0xF7)
    cmd(0x10, b"\x01")


for _n in ("fb", "white", "black", "rows", "fbm", "fbmv", "A2", "cbuf", "cmv", "cropA",
           "cropB", "cmA", "cmB", "INK"):
    globals().pop(_n, None)
gc.collect()
_t = time.monotonic_ns(); gc.collect()
print("gc %.2f ms, free %d, alloc %d" % ((time.monotonic_ns() - _t) / 1e6, gc.mem_free(),
                                          gc.mem_alloc()))
