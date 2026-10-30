_orig_load = load_lut
def load_lut(lut):
    _orig_load(lut)
    cmd(0x3F, bytes([EOPT]))

for EOPT, mode in ((0x22, 0xCC), (0x07, 0xCC), (0x07, 0x0C), (0x07, 0x04)):
    ts = run(make_lut(6, VSH1, VSL), mode)
    t = time.monotonic_ns()
    ram(0x24, fb); refresh(mode); ram(0x26, fb)
    loop = (time.monotonic_ns() - t) // 1_000_000
    print("EOPT %02X mode %02X" % (EOPT, mode), "busy", ts[1:4], "full loop", loop, "ms")
load_lut = _orig_load
