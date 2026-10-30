init(); print("busy after init", busy.value)
load_lut(make_lut(6, VSH1, VSL)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
for mode in (0x0C, 0x04):
    fb[:] = white; ram(0x24, fb); print("warm CC", refresh(0xCC)); ram(0x26, fb)
    ts = []
    for x in range(0, 321, 40):
        fb[:] = white; square(x)
        ram(0x24, fb); r = cmd(0x22, bytes([mode])); cmd(0x20); ts.append(wait_busy(2000)); ram(0x26, fb)
    print("mode %02X" % mode, ts)
