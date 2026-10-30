def anim(frames_lut, n=60, mode=0x0C):
    init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
    load_lut(make_lut(frames_lut, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    refresh(0xCC)
    x, y, dx, dy = 0, 0, 24, 16
    t0 = time.monotonic_ns()
    for i in range(n):
        square(x, y, 80, 0xFF)
        x += dx; y += dy
        if x < 0 or x > W - 80: dx = -dx; x += 2 * dx
        if y < 0 or y > H - 80: dy = -dy; y += 2 * dy
        square(x, y, 80, 0)
        ram(0x24, fb); cmd(0x22, bytes([mode])); cmd(0x20); wait_busy(2000); ram(0x26, fb)
    dt = (time.monotonic_ns() - t0) / 1e6 / n
    print("lut %d frames: %.1f ms/frame = %.1f fps" % (frames_lut, dt, 1000 / dt))

anim(6)
time.sleep(2)
anim(10)
