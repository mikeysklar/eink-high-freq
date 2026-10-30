for y in range(100, 116):
    rows[y][:] = b"\xff" * STRIDE
write_band(0x24, 100, 115); print("step2", show()); write_band(0x26, 100, 115)
