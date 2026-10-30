# pio_spi: CPU at 240 MHz and panel writes through PIO at exactly 20 MHz (the SSD1683
# write limit). busio.SPI can't do this: after cpu.frequency is set, the pico-sdk moves
# clk_peri to the 48 MHz USB PLL (PICO_CLOCK_ADJUST_PERI_CLOCK_WITH_SYS_CLOCK is 0), so
# hardware SPI would drop to 12 MHz. PIO runs from clk_sys instead.
# Load after teapot_demo.py: it replaces the global `spi` with an object that has the
# same write(), so cmd/fill/frame/teapot work unchanged.
#
# One bit = 12 PIO cycles at 240 MHz (4.17 ns each), mode 0, MSB first:
#   cycle 0  data changes, SCK low       (out pins,1 side 0 [2])
#   cycle 3  SCK rises                    (nop side 1 [5])
#   cycle 9  SCK falls                    (nop side 0 [2])
# SCK 25 ns high / 25 ns low (datasheet min 25/25); data setup 12.5 ns (min 10), hold
# 37.5 ns (datasheet 40; busio SPI at 15.625 MHz changed data at the falling edge, 32 ns).
import array
import microcontroller
import rp2pio

microcontroller.cpu.frequency = 240_000_000
spi.deinit()

PROG = array.array("H", [
    0x6201,   # out pins, 1   side 0 [2]
    0xB542,   # nop           side 1 [5]
    0xA242,   # nop           side 0 [2]
])


class PioSPI:
    def __init__(self):
        self.sm = rp2pio.StateMachine(
            PROG, frequency=240_000_000,
            first_out_pin=board.EPD_MOSI, out_pin_count=1,
            first_sideset_pin=board.EPD_SCK, sideset_pin_count=1,
            initial_out_pin_state=0, initial_sideset_pin_state=0,
            auto_pull=True, pull_threshold=8, out_shift_right=False)

    def write(self, buf):
        # wait until the last bit is out (SM stalls on the empty FIFO) before CS/DC move
        sm = self.sm
        sm.clear_txstall()
        sm.write(buf)
        while not sm.txstall:
            pass

    def deinit(self):
        self.sm.deinit()


spi = PioSPI()
print("pio_spi: cpu %d MHz, sm %d Hz, free %d" % (
    microcontroller.cpu.frequency // 1000000, spi.sm.frequency, gc.mem_free()))
