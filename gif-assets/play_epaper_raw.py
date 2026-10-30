# play_epaper_raw: teapot_1bit.gif through videogif.GifDecoder into a 1-bit bytearray,
# pushed to the 4.2" SSD1683 on the Feather RP2040 ThinkInk with raw SPI. UNTESTED.
# Copy teapot_1bit.gif (or the 320x240 teapot_1bit_320.gif, set PATH) to CIRCUITPY.
#
# Per step: take a snapshot of the buffer, find the rows that differ from what the panel
# RAM holds, write that full-width row window to 0x24, update with 0x22 0x0C, wait for
# BUSY, write the same window to 0x26. Balanced fast LUT (board/pr_fast.py,
# pr-drafts/hw-results.md): 4 frames toward black, 4 toward white, WW/BB at VSS, frame rate
# byte 0x05. Every pixel is only driven when RAM goes old -> new, toward the new color, so
# drive toward black and toward white alternate per pixel. The panel starts white and the
# script ends with an all-white step before the OTP clean, so each pixel gets the same
# number of transitions toward black and toward white.
import board, busio, digitalio, gc, time

import videocore, videogif

PATH = "/teapot_1bit.gif"
SECS = 20
NF, FR = 4, 0x05

W, H = 400, 300
STRIDE = W // 8
FRB = STRIDE * H

spi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
while not spi.try_lock():
    pass
spi.configure(baudrate=20_000_000)


def out(pin, v):
    p = digitalio.DigitalInOut(pin)
    p.switch_to_output(v)
    return p


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


# from board/teapot_demo.py
def cmd(c, data=None):
    cs.value = False
    dc.value = False
    spi.write(CB[c])
    if data:
        dc.value = True
        spi.write(data)
    cs.value = True


def wb(limit=400000):
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
    cmd(0x12)
    wb(10000000)
    cmd(0x3C, b"\x05")
    cmd(0x18, b"\x80")
    cmd(0x11, b"\x03")
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
    def one(vs):
        g = bytearray(42)
        g[0:7] = bytes([1, vs | frames, 0, 0, 0, 1, 0])
        return g
    lut = bytearray(227)
    lut[0:42] = one(VSS)
    lut[42:84] = one(VSS)       # WW at VSS
    lut[84:126] = one(to_black)
    lut[126:168] = one(to_white)
    lut[168:210] = one(VSS)     # BB at VSS
    lut[224] = fr
    return lut


def fast_mode(nf, fr):
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


def finish():
    init(); fill(0x24); fill(0x26); refresh(0xF7)
    cmd(0x10, b"\x01")  # deep sleep, HV off


# from board/teapot_win.py
def win(x0, x1, y0, y1):
    cmd(0x44, bytes((x0, x1)))
    cmd(0x45, bytes((y0 & 0xFF, y0 >> 8, y1 & 0xFF, y1 >> 8)))
    cmd(0x4E, CB[x0])
    cmd(0x4F, bytes((y0 & 0xFF, y0 >> 8)))


gif = videogif.GifDecoder(PATH, bits_per_pixel=1)
gw = gif.width
gh = gif.height
gs = (gw + 7) // 8                # row stride, bytes (MSB first, 1 = white like the panel)
ox = (STRIDE - gs) // 2           # centered on the panel, in RAM bytes
oy = (H - gh) // 2
gc.collect()
buf = bytearray(gs * gh)          # VideoBuffer target, source writes here
cur = bytearray(gs * gh)          # snapshot pushed this step
ram = bytearray(b"\xff" * (gs * gh))  # what both RAM planes hold inside the GIF area
mv = memoryview(cur)


def changed_rows():
    # first and last row where cur differs from ram, or None
    y0 = 0
    while y0 < gh and cur[y0 * gs:(y0 + 1) * gs] == ram[y0 * gs:(y0 + 1) * gs]:
        y0 += 1
    if y0 == gh:
        return None
    y1 = gh - 1
    while cur[y1 * gs:(y1 + 1) * gs] == ram[y1 * gs:(y1 + 1) * gs]:
        y1 -= 1
    return y0, y1


def step():
    # push cur: the balanced pair of writes around one fast update
    r = changed_rows()
    if r is None:
        return False
    y0, y1 = r
    data = mv[y0 * gs:(y1 + 1) * gs]
    wb()
    win(ox, ox + gs - 1, oy + y0, oy + y1)
    cmd(0x24, data)
    go()
    wb()
    win(ox, ox + gs - 1, oy + y0, oy + y1)
    cmd(0x26, data)
    ram[y0 * gs:(y1 + 1) * gs] = data
    return True


init(); fill(0x24); fill(0x26); refresh(0xF7)   # OTP full refresh to white
fast_mode(NF, FR)

video = videocore.VideoBuffer(buf)
video.play(gif)
ms = []
n = 0
t0 = time.monotonic_ns()
tend = t0 + SECS * 1000000000
while True:
    t = time.monotonic_ns()
    if t > tend:
        break
    cur[:] = buf      # snapshot; a torn frame only looks wrong, both planes still match
    if step():
        t1 = time.monotonic_ns()
        ms.append((t1 - t) / 1e6)
        n += 1
        if n % 50 == 0:
            print("%d steps, last 50 avg %.1f ms" % (n, sum(ms[-50:]) / 50))
            gc.collect()
video.stop()
gif.deinit()

# all-white step: every black pixel gets its matching drive toward white
cur[:] = b"\xff" * len(cur)
step()
wb()
dt = (time.monotonic_ns() - t0) / 1e6
if ms:
    s = sorted(ms)
    print("%d steps in %.0f ms: avg %.1f ms min %.1f max %.1f median %.1f = %.1f fps" % (
        n, dt, sum(s) / len(s), s[0], s[-1], s[len(s) // 2], 1000 * len(s) / sum(s)))
time.sleep(1)
finish()
print("finished: OTP refresh to white, deep sleep")
