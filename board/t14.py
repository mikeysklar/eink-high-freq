def anim5(band24, band26, n=60):
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    load_lut(make_lut(6, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    refresh(0xCC)
    x, y, dx, dy = 0, 0, 24, 16
    for i in range(n):
        oy = y
        square(x, y, 80, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - 80: dx = -dx; x += 2 * dx
        if y < 0 or y > H - 80: dy = -dy; y += 2 * dy
        square(x, y, 80, 0)
        b0, b1 = min(oy, y), max(oy, y) + 79
        write_band(0x24, *((b0, b1) if band24 else (0, H - 1)))
        cmd(0x22, b"\x0c"); cmd(0x20); wait_busy(2000)
        write_band(0x26, *((b0, b1) if band26 else (0, H - 1)))
