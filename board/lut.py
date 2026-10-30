# SSD1683 B/W-mode waveform (datasheet Fig 6-7): 5 LUTs x 6 groups x 7 bytes
# order LUTC, LUTWW, LUTBW, LUTWB, LUTBB; byte = VS[7:6] | TP[5:0]
VSS, VSH1, VSL = 0x00, 0x40, 0x80


def make_lut(frames, to_black, to_white, fr=0x0C):
    def one(vs):
        g = bytearray(42)
        g[0:7] = bytes([1, vs | frames, 0, 0, 0, 1, 0])  # RP, A..D, SRab, SRcd
        return g

    lut = bytearray(227)
    lut[0:42] = one(VSS)          # LUTC: VCOM at DCVCOM
    lut[42:84] = one(VSS)         # LUTWW: white stays white
    lut[84:126] = one(to_black)   # LUTBW
    lut[126:168] = one(to_white)  # LUTWB
    lut[168:210] = one(VSS)       # LUTBB: black stays black
    lut[224] = fr
    return lut


def load_lut(lut):
    cmd(0x32, lut)
    cmd(0x3F, b"\x22")
    cmd(0x03, b"\x17")
    cmd(0x04, b"\x41\xa8\x32")
    cmd(0x2C, b"\x30")
    cmd(0x21, b"\x00\x00")  # use both RAMs normally: 0x26 = previous frame


import gc
gc.collect()
try:
    fb
except NameError:
    fb = bytearray(white)


def square(x0, y0=110, n=80, ink=0):
    for y in range(y0, y0 + n):
        r = y * STRIDE
        for xb in range(x0 // 8, (x0 + n) // 8):
            fb[r + xb] = ink


def run(lut, mode=0xCF, step=40):
    fb[:] = white
    ram(0x24, fb); ram(0x26, fb)
    init()
    refresh(0xF7)  # clean slate with the stock waveform
    load_lut(lut)
    cmd(0x3C, b"\x80")
    ts = []
    prev = None
    for x in range(0, 320 + 1, step):
        if prev is not None:
            square(prev, ink=0xFF)
        square(x)
        prev = x
        ram(0x24, fb)
        ts.append(refresh(mode))
        ram(0x26, fb)
    return ts
