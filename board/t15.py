FULL_X = bytes([0, STRIDE - 1])
FULL_Y = bytes([0, 0, (H - 1) & 0xFF, (H - 1) >> 8])


def show(mode=0x0C):
    cmd(0x44, FULL_X); cmd(0x45, FULL_Y)  # update scans through the RAM window
    cmd(0x22, bytes([mode])); cmd(0x20)
    return wait_busy(2000)


def anim6(frames_lut, n=60):
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    load_lut(make_lut(frames_lut, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    refresh(0xCC)
    x, y, dx, dy = 0, 0, 24, 16
    t0 = time.monotonic_ns()
    for i in range(n):
        oy = y
        square(x, y, 80, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - 80: dx = -dx; x += 2 * dx
        if y < 0 or y > H - 80: dy = -dy; y += 2 * dy
        square(x, y, 80, 0)
        y0, y1 = min(oy, y), max(oy, y) + 79
        write_band(0x24, y0, y1)
        show()
        write_band(0x26, y0, y1)
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    print("lut %d: %.1f ms/frame = %.1f fps" % (frames_lut, dt, 1000 / dt))
anim6(6)
