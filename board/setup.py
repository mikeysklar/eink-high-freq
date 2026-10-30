import board, busio, digitalio, time

W, H = 400, 300
STRIDE = W // 8
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


def cmd(c, data=None):
    dc.value = False
    cs.value = False
    spi.write(bytes([c]))
    cs.value = True
    if data:
        dc.value = True
        cs.value = False
        spi.write(data)
        cs.value = True


def wait_busy(limit_ms=10000):
    t = time.monotonic_ns()
    while busy.value:
        if (time.monotonic_ns() - t) // 1_000_000 > limit_ms:
            return -1
    return (time.monotonic_ns() - t) // 1_000_000


def init():
    rst.value = False
    time.sleep(0.01)
    rst.value = True
    time.sleep(0.01)
    wait_busy()
    cmd(0x12)  # SW reset
    wait_busy()
    cmd(0x3C, b"\x05")  # border
    cmd(0x18, b"\x80")  # internal temp sensor
    cmd(0x11, b"\x03")  # X inc, Y inc
    cmd(0x44, bytes([0, STRIDE - 1]))
    cmd(0x45, bytes([0, 0, (H - 1) & 0xFF, (H - 1) >> 8]))
    cmd(0x01, bytes([(H - 1) & 0xFF, (H - 1) >> 8, 0]))


def ram(c, buf):
    cmd(0x4E, b"\x00")
    cmd(0x4F, b"\x00\x00")
    cmd(c, buf)


def refresh(mode):
    cmd(0x22, bytes([mode]))
    cmd(0x20)
    return wait_busy()


white = bytearray(b"\xff" * (STRIDE * H))
black = bytearray(STRIDE * H)
init()
print("init ok, busy =", busy.value)
