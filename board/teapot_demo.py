# teapot_demo: spinning Utah teapot on the Adafruit 4.2" SSD1683 panel, standalone.
# Frames are pre-rendered on the Mac by teapot/make_frames.py (Newell's patches) as
# full-screen 1-bit images, 15000 B each, in /teapot.bin. Same method as t25-t31:
# 1-frame custom LUT at 125 Hz; RAM 0x24 holds frame N and 0x26 frame N-lag, so every
# pixel that changed in the last `lag` steps gets lag frames of drive, equal toward black
# and white. Both frames are read from flash each step (two 15 KB buffers, no pool).
# Cleanup: every `every` s the teapot is hidden for lag+2 steps, then a balanced
# full-screen wipe (k frames black, k white); every `clean` s an OTP clean after a SW
# reset, then one wipe. teapot() ends with a clean OTP refresh and deep sleep.
import board, busio, digitalio, gc, time

W, H = 400, 300
STRIDE = W // 8
FRB = STRIDE * H
try:
    spi.deinit()
except NameError:
    pass
spi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
while not spi.try_lock():
    pass
spi.configure(baudrate=20_000_000)


def out(pin, v):
    p = digitalio.DigitalInOut(pin)
    p.switch_to_output(v)
    return p


try:
    for p in (cs, dc, rst, busy):
        p.deinit()
except NameError:
    pass
cs = out(board.EPD_CS, True)
dc = out(board.EPD_DC, True)
rst = out(board.EPD_RESET, True)
busy = digitalio.DigitalInOut(board.EPD_BUSY)
CB = [bytes((i,)) for i in range(256)]
FULL_X = bytes([0, STRIDE - 1])
FULL_Y = bytes([0, 0, (H - 1) & 0xFF, (H - 1) >> 8])
NO_PINGPONG = bytes([0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
VSS, VSH1, VSL = 0x00, 0x40, 0x80
FILLW = b"\xff" * (STRIDE * 30)
FILLB = bytes(STRIDE * 30)


def cmd(c, data=None):
    cs.value = False
    dc.value = False
    spi.write(CB[c])
    if data:
        dc.value = True
        spi.write(data)
    cs.value = True


def wb(limit=400000):
    # allocation-free BUSY wait (time.monotonic_ns() here would trigger GC passes)
    i = 0
    while busy.value:
        i += 1
        if i > limit:
            return False
    return True


def refresh(mode):
    cmd(0x22, CB[mode])
    cmd(0x20)
    wb(10000000)


def init():
    rst.value = False
    time.sleep(0.01)
    rst.value = True
    time.sleep(0.01)
    wb(10000000)
    cmd(0x12)  # SW reset
    wb(10000000)
    cmd(0x3C, b"\x05")
    cmd(0x18, b"\x80")  # internal temp sensor
    cmd(0x11, b"\x03")  # X inc, Y inc
    cmd(0x44, FULL_X)
    cmd(0x45, FULL_Y)
    cmd(0x01, bytes([(H - 1) & 0xFF, (H - 1) >> 8, 0]))


def fill(c, chunk=FILLW):
    cmd(0x44, FULL_X); cmd(0x45, FULL_Y)
    cmd(0x4E, b"\x00"); cmd(0x4F, b"\x00\x00")
    cs.value = False
    dc.value = False
    spi.write(CB[c])
    dc.value = True
    for _ in range(H // 30):
        spi.write(chunk)
    cs.value = True


def make_lut(frames, to_black, to_white, fr):
    # datasheet Fig 6-7: LUTC, LUTWW, LUTBW, LUTWB, LUTBB x 6 groups x 7 bytes
    def one(vs):
        g = bytearray(42)
        g[0:7] = bytes([1, vs | frames, 0, 0, 0, 1, 0])
        return g
    lut = bytearray(227)
    lut[0:42] = one(VSS)
    lut[42:84] = one(VSS)
    lut[84:126] = one(to_black)
    lut[126:168] = one(to_white)
    lut[168:210] = one(VSS)
    lut[224] = fr
    return lut


def fast_mode(nf, fr):
    # voltages from Adafruit_EPD ThinkInk_420_Grayscale4_MFGN
    cmd(0x32, make_lut(nf, VSH1, VSL, fr))
    cmd(0x3F, b"\x07")
    cmd(0x03, b"\x17")
    cmd(0x04, b"\x41\xa8\x32")
    cmd(0x2C, b"\x30")
    cmd(0x21, b"\x00\x00")
    cmd(0x3C, b"\x80")
    cmd(0x37, NO_PINGPONG)
    refresh(0xCC)


def go():
    cmd(0x44, FULL_X); cmd(0x45, FULL_Y)
    cmd(0x22, b"\x0c"); cmd(0x20)


def wipe(k):
    # balanced: every pixel k frames toward black, then k toward white
    fill(0x24, FILLB); fill(0x26)
    for _ in range(k):
        wb(); go()
    wb()
    fill(0x24); fill(0x26, FILLB)
    for _ in range(k):
        wb(); go()
    wb()
    fill(0x26)


def otpclean(nf, fr):
    # OTP waveform only runs after a SW reset (after fast_mode, 0xF7 ends in ~156 ms);
    # 0x1A temp + 0x91 + 0xC7 takes 3.3 s, 0xF7 6.0 s
    init(); fill(0x24); fill(0x26)
    cmd(0x1A, b"\x5a\x00")
    refresh(0x91)
    refresh(0xC7)
    fast_mode(nf, fr)


def finish():
    init(); fill(0x24); fill(0x26); refresh(0xF7)
    cmd(0x10, b"\x01")  # deep sleep, HV off


def frame(c, buf):
    cmd(0x4E, b"\x00"); cmd(0x4F, b"\x00\x00")
    cmd(c, buf)


def teapot(nf=1, lag=6, fr=0x05, secs=30, every=4, k=8, clean=15, fin=True, quiet=False,
           path="/teapot.bin"):
    f = open(path, "rb")
    f.seek(0, 2)
    nfr = f.tell() // FRB
    gc.collect()
    b24 = bytearray(FRB)
    b26 = bytearray(FRB)
    white = b"\xff" * FRB
    hist = [-1] * (lag + 1)    # frame index each step showed, -1 = blank; oldest first
    init(); fill(0x24); fill(0x26); refresh(0xF7)
    fast_mode(nf, fr)
    if k > 0:
        wipe(k)
    gc.collect()
    fi = 0
    n = 0
    wipes = cleans = 0
    tread = 0
    t0 = time.monotonic_ns()
    tend = t0 + secs * 1000000000
    twipe = t0 + every * 1000000000
    tclean = t0 + clean * 1000000000
    dt = 0
    tail = -1
    drain = 0
    while tail != 0:
        cur = -1
        if drain:
            drain -= 1
            if drain == 0:
                wb(); wipe(k); wipes += 1
                twipe = time.monotonic_ns() + every * 1000000000
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
                elif k > 0 and tn > twipe:
                    drain = lag + 2
        else:
            tail -= 1
        hist.pop(0); hist.append(cur)
        tr = time.monotonic_ns()
        a, b = hist[0], hist[-1]
        if a >= 0:
            f.seek(a * FRB); f.readinto(b26)
        if b >= 0:
            f.seek(b * FRB); f.readinto(b24)
        tread += time.monotonic_ns() - tr
        wb()
        frame(0x26, b26 if a >= 0 else white)
        frame(0x24, b24 if b >= 0 else white)
        go()
    wb()
    f.close()
    if fin:
        time.sleep(1)
        finish()
    if not quiet:
        print("teapot nf %d lag %d: %d frames, %d wipes, %d cleans, %.1f ms/frame = %.1f fps,"
              " read %.2f ms/step" % (nf, lag, n, wipes, cleans, dt, 1000 / dt,
                                      tread / 1e6 / max(n, 1)))
    return dt


init()
print("teapot_demo loaded, free %d" % gc.mem_free())
