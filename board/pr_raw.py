# pr_raw: raw SSD1683 access on the Feather RP2040 ThinkInk for the EPaperDisplay PR tests.
# Writes go over busio.SPI; RAM reads (0x27) bit-bang SCK/SDA because the panel's SDA is
# bidirectional and there is no MISO. Used to clear the panel before a test, to read back
# both RAM planes after one, and to finish with a stock OTP refresh and deep sleep.
import board, busio, digitalio, time

W, H = 400, 300
STRIDE = W // 8
FULL_X = bytes([0, STRIDE - 1])
FULL_Y = bytes([0, 0, (H - 1) & 0xFF, (H - 1) >> 8])
VSS, VSH1, VSL = 0x00, 0x40, 0x80
NO_PINGPONG = bytes([0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def make_lut(frames, to_black, to_white, fr):
    # same as teapot_demo.make_lut: BW and WB groups get the same frame count, WW/BB at VSS
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


def _out(pin, v):
    p = digitalio.DigitalInOut(pin)
    p.switch_to_output(v)
    return p


class Raw:
    def __init__(self, bitbang=False):
        self.cs = _out(board.EPD_CS, True)
        self.dc = _out(board.EPD_DC, True)
        self.rst = _out(board.EPD_RESET, True)
        self.busy = digitalio.DigitalInOut(board.EPD_BUSY)
        self.bb = bitbang
        if bitbang:
            self.sck = _out(board.EPD_SCK, False)
            self.sda = _out(board.EPD_MOSI, False)
        else:
            self.spi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
            while not self.spi.try_lock():
                pass
            self.spi.configure(baudrate=20_000_000)

    def deinit(self):
        for p in (self.cs, self.dc, self.rst, self.busy):
            p.deinit()
        if self.bb:
            self.sck.deinit()
            self.sda.deinit()
        else:
            self.spi.unlock()
            self.spi.deinit()

    def _w(self, buf):
        if not self.bb:
            self.spi.write(buf)
            return
        sck, sda = self.sck, self.sda
        for b in buf:
            for i in range(7, -1, -1):
                sda.value = (b >> i) & 1
                sck.value = True
                sck.value = False

    def cmd(self, c, data=None):
        self.cs.value = False
        self.dc.value = False
        self._w(bytes((c,)))
        if data:
            self.dc.value = True
            self._w(data)
        self.cs.value = True

    def wb(self, limit=10000000):
        i = 0
        while self.busy.value:
            i += 1
            if i > limit:
                return False
        return True

    def reset(self):
        self.rst.value = False
        time.sleep(0.01)
        self.rst.value = True
        time.sleep(0.01)
        self.wb()
        self.cmd(0x12)  # SW reset
        self.wb()

    def init(self):
        self.reset()
        self.cmd(0x3C, b"\x05")
        self.cmd(0x18, b"\x80")
        self.cmd(0x11, b"\x03")
        self.cmd(0x44, FULL_X)
        self.cmd(0x45, FULL_Y)
        self.cmd(0x01, bytes([(H - 1) & 0xFF, (H - 1) >> 8, 0]))

    def fill(self, c, v):
        self.cmd(0x44, FULL_X)
        self.cmd(0x45, FULL_Y)
        self.cmd(0x4E, b"\x00")
        self.cmd(0x4F, b"\x00\x00")
        row = bytes([v]) * (STRIDE * 30)
        self.cs.value = False
        self.dc.value = False
        self._w(bytes((c,)))
        self.dc.value = True
        for _ in range(H // 30):
            self._w(row)
        self.cs.value = True

    def write_box(self, c, xb, y, nb, rows, v):
        self.cmd(0x44, bytes([xb, xb + nb - 1]))
        self.cmd(0x45, bytes([y & 0xFF, y >> 8, (y + rows - 1) & 0xFF, (y + rows - 1) >> 8]))
        self.cmd(0x4E, bytes([xb]))
        self.cmd(0x4F, bytes([y & 0xFF, y >> 8]))
        self.cmd(c, bytes([v]) * (nb * rows))

    def refresh(self, mode):
        self.cmd(0x22, bytes((mode,)))
        self.cmd(0x20)
        self.wb()

    def clear(self):
        # stock OTP full refresh to white after a reset (balanced OTP waveform)
        self.init()
        self.fill(0x24, 0xFF)
        self.fill(0x26, 0xFF)
        self.refresh(0xF7)

    def finish(self):
        self.clear()
        self.cmd(0x10, b"\x01")  # deep sleep mode 1, HV off

    def read_row(self, ram, y, xb=0, n=STRIDE):
        # bit-banged 0x27 read, first byte is a dummy (datasheet 0x27)
        assert self.bb
        self.cmd(0x41, bytes((ram,)))  # 0 = BW RAM (0x24), 1 = RED RAM (0x26)
        self.cmd(0x44, FULL_X)
        self.cmd(0x45, FULL_Y)
        self.cmd(0x4E, bytes([xb]))
        self.cmd(0x4F, bytes([y & 0xFF, y >> 8]))
        self.cs.value = False
        self.dc.value = False
        self._w(b"\x27")
        self.dc.value = True
        sck, sda = self.sck, self.sda
        sda.switch_to_input()
        out = bytearray(n + 1)
        for k in range(n + 1):
            v = 0
            for _ in range(8):
                sck.value = True
                v = (v << 1) | sda.value
                sck.value = False
            out[k] = v
        self.cs.value = True
        sda.switch_to_output(False)
        return bytes(out[1:])


def ram_retention_test():
    # risk (b), raw: write known bytes to both RAMs (no refresh, nothing is driven), read them
    # back, then HW reset + SW reset 0x12 and read again.
    r = Raw()
    r.init()
    r.fill(0x24, 0xFF)
    r.fill(0x26, 0xFF)
    r.write_box(0x24, 10, 10, 5, 4, 0xA5)
    r.write_box(0x26, 10, 10, 5, 4, 0x3C)
    r.deinit()
    r = Raw(bitbang=True)
    exp24 = b"\xff" * 10 + b"\xa5" * 5 + b"\xff" * 35
    exp26 = b"\xff" * 10 + b"\x3c" * 5 + b"\xff" * 35
    res = {}
    for tag in ("before reset", "after HW+SW reset"):
        if tag != "before reset":
            r.reset()
        a = r.read_row(0, 11)
        b = r.read_row(1, 11)
        res[tag] = (a == exp24, b == exp26)
        print("%s: 0x24 row11 %s match=%s | 0x26 row11 %s match=%s" % (
            tag, a[8:17].hex(), a == exp24, b[8:17].hex(), b == exp26))
    r.deinit()
    return res


def busy_timing(trials=5, nf=4, fr=0x05):
    # risk (a), raw: after the fast LUT is loaded, start a mode 2 update (0x22 0x0C 0x20) on
    # equal RAM planes (WW/BB only, nothing driven) and count BUSY polls until it goes high.
    r = Raw()
    r.clear()
    r.cmd(0x32, make_lut(nf, VSH1, VSL, fr))
    r.cmd(0x3F, b"\x07")
    r.cmd(0x03, b"\x17")
    r.cmd(0x04, b"\x41\xa8\x32")
    r.cmd(0x2C, b"\x30")
    r.cmd(0x21, b"\x00\x00")
    r.cmd(0x3C, b"\x80")
    r.cmd(0x37, NO_PINGPONG)
    r.refresh(0xC0)
    busy = r.busy
    for t in range(trials):
        r.cmd(0x22, b"\x0c")
        t0 = time.monotonic_ns()
        r.cmd(0x20)
        polls = 0
        first = busy.value
        while not busy.value and polls < 100000:
            polls += 1
        t1 = time.monotonic_ns()
        while busy.value:
            pass
        t2 = time.monotonic_ns()
        print("trial %d: BUSY high at first poll=%s, low polls before high=%d, "
              "busy high for %.1f ms" % (t, first, polls, (t2 - t1) / 1e6))
    r.finish()
    r.deinit()


def last_byte_test(after=None):
    # does the last RAM byte written survive a HW reset that follows the write directly?
    # `after` is an optional command sent between the write and the reset (e.g. 0x7F NOP).
    r = Raw()
    r.init()
    r.fill(0x24, 0xFF)
    r.fill(0x26, 0xFF)
    r.write_box(0x26, 10, 10, 5, 4, 0x00)   # rows 10-13, bytes 10-14 black
    r.write_box(0x26, 10, 10, 5, 4, 0xFF)   # back to white; its last byte is row 13 byte 14
    if after is not None:
        r.cmd(after)
    r.rst.value = False
    time.sleep(0.01)
    r.rst.value = True
    time.sleep(0.01)
    r.wb()
    r.deinit()
    r = Raw(bitbang=True)
    rows = [r.read_row(1, y)[8:17].hex() for y in range(10, 14)]
    print("after=%s: 0x26 rows 10-13 bytes 8-16: %s" % (after, rows))
    r.deinit()
