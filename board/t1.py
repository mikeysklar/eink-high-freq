for name, img in (("white", white), ("black", black), ("white", white)):
    t = time.monotonic_ns()
    ram(0x24, img); ram(0x26, img)
    spi_ms = (time.monotonic_ns() - t) / 1e6
    print(name, "spi %.1f ms" % spi_ms, "F7 busy", refresh(0xF7), "ms")
