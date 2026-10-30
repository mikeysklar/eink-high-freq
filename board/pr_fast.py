# pr_fast: EPaperDisplay tests for the keep_awake, refresh_sequence and
# write_previous_ram_command PRs on the Feather RP2040 ThinkInk + 4.2" SSD1683 (#6381).
# Needs pr_raw.py loaded first (Raw, make_lut). A 40x40 black square moves 8 px per
# refresh across a white screen; a second 40x40 square stays still at the top left.
import board, busio, displayio, epaperdisplay, fourwire, time

NF, FR = 4, 0x05  # 4 frames per transition, same count toward black and white


def seq(c, data=b"", delay=None):
    # two_byte_sequence_length format: cmd, len hi (| 0x80 for delay), len lo, data, [delay ms]
    n = len(data)
    hi = (n >> 8) | (0x80 if delay is not None else 0)
    return bytes([c, hi, n & 0xFF]) + data + (bytes([delay]) if delay is not None else b"")


# stock: Adafruit_CircuitPython_SSD1683 start sequence, OTP full refresh (as teapot_displayio)
STOCK_START = (
    seq(0x12, delay=0x32)
    + seq(0x21, b"\x40\x00")
    + seq(0x3C, b"\x05")
    + seq(0x11, b"\x03")
    + seq(0x18, b"\x80")
    + seq(0x01, b"\x2b\x01\x00")
    + seq(0x22, b"\xf7")
)
STOCK_STOP = seq(0x10, b"\x01", delay=0x64)
STOCK_REFRESH = seq(0x20)

# fast: same reset, then the balanced fast LUT and voltages from teapot_demo.fast_mode,
# old RAM compare on (0x21 00 00), and 0x22 C0 to turn clock + analog on without driving.
FAST_START = (
    seq(0x12, delay=0x32)
    + seq(0x18, b"\x80")
    + seq(0x11, b"\x03")
    + seq(0x01, b"\x2b\x01\x00")
    + seq(0x32, make_lut(NF, VSH1, VSL, FR))
    + seq(0x3F, b"\x07")
    + seq(0x03, b"\x17")
    + seq(0x04, b"\x41\xa8\x32")
    + seq(0x2C, b"\x30")
    + seq(0x21, b"\x00\x00")
    + seq(0x3C, b"\x80")
    + seq(0x37, NO_PINGPONG)
    + seq(0x22, b"\xc0")
    + seq(0x20)
)
FAST_REFRESH = seq(0x22, b"\x0c") + seq(0x20)
FAST_REFRESH_DELAY = seq(0x22, b"\x0c") + seq(0x20, delay=5)  # 5 ms before BUSY is checked

RECT_Y, STATIC = 130, (0, 0)
_spi = None


def release():
    global _spi
    displayio.release_displays()
    if _spi is not None:
        _spi.deinit()
        _spi = None


def make_display(fast, refresh_sequence=FAST_REFRESH):
    global _spi
    release()
    _spi = spi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
    bus = fourwire.FourWire(spi, command=board.EPD_DC, chip_select=board.EPD_CS,
                            reset=board.EPD_RESET, baudrate=20_000_000)
    kw = dict(width=400, height=300, ram_width=50, ram_height=300,
              busy_pin=board.EPD_BUSY, busy_state=True, seconds_per_frame=0,
              write_black_ram_command=0x24,
              set_column_window_command=0x44, set_row_window_command=0x45,
              set_current_column_command=0x4E, set_current_row_command=0x4F,
              always_toggle_chip_select=False, address_little_endian=True,
              two_byte_sequence_length=True, colstart=0)
    if fast:
        d = epaperdisplay.EPaperDisplay(bus, FAST_START, b"", refresh_display_command=refresh_sequence,
                                        keep_awake=True, write_previous_ram_command=0x26, **kw)
    else:
        d = epaperdisplay.EPaperDisplay(bus, STOCK_START, STOCK_STOP, refresh_display_command=STOCK_REFRESH,
                                        write_color_ram_command=0x26, **kw)
    pal = displayio.Palette(2)
    pal[0] = 0x000000
    pal[1] = 0xFFFFFF
    bg = displayio.Bitmap(400, 300, 2)
    bg.fill(1)
    blk = displayio.Bitmap(40, 40, 2)
    g = displayio.Group()
    g.append(displayio.TileGrid(bg, pixel_shader=pal))
    g.append(displayio.TileGrid(blk, pixel_shader=pal, x=STATIC[0], y=STATIC[1]))
    rect = displayio.TileGrid(blk, pixel_shader=pal, x=48, y=RECT_Y)
    g.append(rect)
    d.root_group = g
    return d, rect


def timed_refresh(d):
    t0 = time.monotonic_ns()
    d.refresh()
    while d.busy:
        pass
    return (time.monotonic_ns() - t0) / 1e6


def stats(name, ms):
    ms = sorted(ms)
    avg = sum(ms) / len(ms)
    print("%s: n=%d avg %.1f ms min %.1f max %.1f median %.1f = %.1f fps" % (
        name, len(ms), avg, ms[0], ms[-1], ms[len(ms) // 2], 1000 / avg))


def move(d, rect, steps, dx=8):
    ms = []
    for _ in range(steps):
        x = rect.x + dx
        if x > 352 or x < 48:
            dx = -dx
            x = rect.x + dx
        rect.x = x
        ms.append(timed_refresh(d))
    return ms, dx


def check_ram(rect_x, rows=None, reads=1):
    # read both RAM planes back and compare with the expected image
    release()
    r = Raw(bitbang=True)
    if rows is None:
        rows = list(range(0, 300, 10)) + [39, 40, RECT_Y - 1, RECT_Y + 1, RECT_Y + 20, RECT_Y + 39, RECT_Y + 40]
    bad = {0: 0, 1: 0}
    for y in rows:
        exp = bytearray(b"\xff" * 50)
        if y < 40:
            exp[0:5] = bytes(5)
        if RECT_Y <= y < RECT_Y + 40:
            exp[rect_x // 8:rect_x // 8 + 5] = bytes(5)
        for ram in (0, 1):
            got = r.read_row(ram, y)
            for _ in range(reads - 1):
                again = r.read_row(ram, y)
                if again != got:
                    print("  row %d ram %d read differs: %s" % (y, ram, again.hex()))
            if got != exp:
                bad[ram] += 1
                if bad[ram] <= 3:
                    print("  row %d ram %s got %s" % (y, ("0x24", "0x26")[ram], got.hex()))
    print("RAM check, %d rows, rect at x=%d: 0x24 bad rows %d, 0x26 bad rows %d" % (
        len(rows), rect_x, bad[0], bad[1]))
    r.deinit()
    return bad


def clear_panel():
    release()
    r = Raw()
    r.clear()
    r.deinit()


def finish_panel():
    release()
    r = Raw()
    r.finish()
    r.deinit()
    print("finished: OTP refresh to white, deep sleep")


def baseline(n=5):
    clear_panel()
    d, rect = make_display(False)
    print("first (full) refresh %.1f ms" % timed_refresh(d))
    ms, _ = move(d, rect, n)
    print("per refresh ms:", ["%.0f" % m for m in ms])
    stats("baseline stock 0xF7", ms)
    finish_panel()


def fast(steps=76, refresh_sequence=FAST_REFRESH, name="fast"):
    clear_panel()
    d, rect = make_display(True, refresh_sequence)
    print("first refresh incl reset + start_sequence %.1f ms" % timed_refresh(d))
    ms, _ = move(d, rect, steps)
    stats(name, ms)
    x = rect.x
    try:
        check_ram(x)
    finally:
        finish_panel()


def switching(steps=20, rows=None, reads=1):
    # risk (b) and runtime switching: fast, re-enter fast via update_refresh_mode (RST +
    # start_sequence), switch to the stock OTP full refresh and back to fast.
    clear_panel()
    d, rect = make_display(True)
    print("first refresh %.1f ms" % timed_refresh(d))
    ms, dx = move(d, rect, steps)
    stats("fast before re-entry", ms)
    d.update_refresh_mode(FAST_START, 0, refresh_sequence=FAST_REFRESH)
    ms, dx = move(d, rect, 1, dx)
    print("first refresh after update_refresh_mode(FAST_START) %.1f ms" % ms[0])
    ms, dx = move(d, rect, steps, dx)
    stats("fast after re-entry", ms)
    d.update_refresh_mode(STOCK_START, 0, refresh_sequence=STOCK_REFRESH)
    ms, dx = move(d, rect, 2, dx)
    print("stock full refreshes after switch: %s ms" % ["%.0f" % m for m in ms])
    d.update_refresh_mode(FAST_START, 0, refresh_sequence=FAST_REFRESH)
    ms, dx = move(d, rect, 1, dx)
    print("first refresh back in fast mode %.1f ms" % ms[0])
    ms, dx = move(d, rect, steps, dx)
    stats("fast after switching back", ms)
    x = rect.x
    try:
        check_ram(x, rows, reads)
    finally:
        finish_panel()


print("pr_fast loaded")
