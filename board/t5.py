def b2w(label, lut, mode):
    init(); ram(0x24, black); ram(0x26, black); refresh(0xF7)
    load_lut(lut); cmd(0x3C, b"\x80")
    ram(0x26, black); ram(0x24, white)
    t = refresh(mode)
    print(label, t, "ms", "t=%.1f" % (time.monotonic() - T0))
    time.sleep(3)

T0 = time.monotonic()
b2w("1 LUTWB=VSH1 CF", make_lut(20, VSL, VSH1), 0xCF)
b2w("2 LUTWB=VSL  CF", make_lut(20, VSH1, VSL), 0xCF)
b2w("3 LUTWB=VSH1 C7", make_lut(20, VSL, VSH1), 0xC7)
