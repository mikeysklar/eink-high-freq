init(); fb[:] = white; ram(0x24, fb); ram(0x26, fb); refresh(0xF7)
load_lut(make_lut(20, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
refresh(0xCC)
for y in range(100, 180):
    rows[y][:] = bytes(STRIDE)
write_band(0x24, 100, 179); print("step1", show()); write_band(0x26, 100, 179)
