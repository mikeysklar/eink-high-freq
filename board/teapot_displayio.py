# teapot_displayio: the baseline. Same teapot frames, shown the stock way: displayio
# EPaperDisplay with the Adafruit_CircuitPython_SSD1683 start sequence and full refresh
# (0x22 = F7). Only change from stock: seconds_per_frame=0 so it refreshes as fast as
# the panel allows instead of every 180 s. ram_width is given in bytes (50); the board's
# lib/adafruit_ssd1683.py has 400 on purpose for a pitfall photo and is left alone.
# Can run after teapot_demo.py (releases its SPI and pins).
import board, busio, displayio, epaperdisplay, fourwire, bitmaptools, gc, time, terminalio
from adafruit_display_text import label

displayio.release_displays()
for _n in ("spi", "cs", "dc", "rst", "busy", "dspi"):
    try:
        globals()[_n].deinit()
    except (KeyError, AttributeError, NameError):
        pass

START = (
    b"\x12\x80\x00\x32"            # soft reset and wait 50ms
    b"\x21\x00\x02\x40\x00"        # display update control 1 & 2
    b"\x3c\x00\x01\x05"            # border waveform
    b"\x11\x00\x01\x03"            # ram data entry mode
    b"\x18\x00\x01\x80"            # internal temperature sensor
    b"\x01\x00\x03\x2b\x01\x00"    # driver output control: 300 gates
    b"\x22\x00\x01\xf7"            # display update mode: full refresh
)
STOP = b"\x10\x80\x01\x01\x64"     # deep sleep

dspi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
bus = fourwire.FourWire(dspi, command=board.EPD_DC, chip_select=board.EPD_CS,
                        reset=board.EPD_RESET, baudrate=20_000_000)
display = epaperdisplay.EPaperDisplay(
    bus, START, STOP, width=400, height=300, ram_width=50, ram_height=300,
    busy_pin=board.EPD_BUSY, busy_state=True, seconds_per_frame=0,
    write_black_ram_command=0x24, write_color_ram_command=0x26,
    set_column_window_command=0x44, set_row_window_command=0x45,
    set_current_column_command=0x4E, set_current_row_command=0x4F,
    refresh_display_command=0x20, always_toggle_chip_select=False,
    address_little_endian=True, two_byte_sequence_length=True, colstart=0)

bmp = displayio.Bitmap(400, 300, 2)
pal = displayio.Palette(2)
pal[0] = 0x000000
pal[1] = 0xFFFFFF
grp = displayio.Group()
grp.append(displayio.TileGrid(bmp, pixel_shader=pal))
txt = label.Label(terminalio.FONT, text="", color=0x000000, background_color=0xFFFFFF,
                  scale=2, x=6, y=282)
grp.append(txt)
display.root_group = grp


def teapot_displayio(secs=40, path="/teapot.bin"):
    f = open(path, "rb")
    nfr = 120
    i = n = 0
    t0 = time.monotonic()
    times = []
    while time.monotonic() - t0 < secs:
        f.seek(i * 15000)
        bitmaptools.readinto(bmp, f, bits_per_pixel=1, element_size=1,
                              reverse_pixels_in_element=True)
        if times:
            txt.text = "%.2f fps" % (1 / (sum(times) / len(times)))
        ta = time.monotonic()
        display.refresh()
        while display.busy:
            pass
        times.append(time.monotonic() - ta)
        i = (i + 1) % nfr
        n += 1
    f.close()
    avg = sum(times) / len(times)
    print("displayio: %d refreshes, %.2f s each = %.3f fps" % (n, avg, 1 / avg))
    return avg


print("teapot_displayio loaded, free %d" % gc.mem_free())
