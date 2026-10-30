import gc
frames = None
gc.collect()
fb = bytearray(white)

def square(x0, y0=110, n=80, ink=0):
    for y in range(y0, y0 + n):
        r = y * STRIDE
        for xb in range(x0 // 8, (x0 + n) // 8):
            fb[r + xb] = ink

for mode in (0xFF, 0xFC, 0xCF):
    fb[:] = white
    ram(0x24, fb); ram(0x26, fb)
    refresh(0xF7)
    cmd(0x3C, b"\x80")
    ts = []
    prev = None
    for x in range(0, 320, 40):
        if prev is not None:
            square(prev, ink=0xFF)
        square(x)
        prev = x
        ram(0x24, fb)
        ts.append(refresh(mode))
        ram(0x26, fb)
    print("mode %02X" % mode, "ms per frame", ts)
