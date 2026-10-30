for temp in (0x32, 0x50, 0x64, 0x6E, 0x7F):
    cmd(0x1A, bytes([temp, 0x00]))
    refresh(0x91)  # load LUT for the written temperature
    for name, img in (("white", white), ("black", black)):
        ram(0x24, img); ram(0x26, img)
        print("temp %d C" % temp, name, "C7", refresh(0xC7), "ms")
