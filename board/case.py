def case(frm, to, lut, mode=0xCF):
    init(); ram(0x24, frm); ram(0x26, frm); refresh(0xF7)
    load_lut(lut); cmd(0x3C, b"\x80")
    ram(0x26, frm)
    # new image: left half 'to', right half unchanged 'frm' as a control
    fb[:] = frm
    for y in range(H):
        r = y * STRIDE
        fb[r:r + STRIDE // 2] = to[r:r + STRIDE // 2]
    ram(0x24, fb)
    return refresh(mode)
