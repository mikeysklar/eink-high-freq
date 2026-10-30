# t29: periodic clean with the vendor OTP waveform, made short by the Good Display "fast
# refresh" trick: write a high temperature into 0x1A so the controller picks the OTP's
# high-temperature (short) waveform. Still the vendor's balanced waveform. Then reload
# the 1-frame LUT. ball2(k=-1) uses it. Load after t28.


def otpclean(nf, fr, temp=0x5A):
    # Needs a SW reset first: after our LUT setup, 0xF7/0xC7 finish in ~156 ms and don't
    # run the OTP waveform. After init, 0x91 + 0xC7 takes 3.3 s at any forced temperature
    # (25-110 C), vs 6.0 s for 0xF7.
    init(); wfill(0x24); wfill(0x26)
    cmd(0x1A, bytes([temp, 0x00]))   # temperature register
    refresh(0x91)                     # load OTP LUT for that temperature
    refresh(0xC7)                     # display with it, analog off
    load_lut(make_lut(nf, VSH1, VSL, fr)); cmd(0x3F, b"\x07"); cmd(0x3C, b"\x80")
    cmd(0x37, NO_PINGPONG)
    refresh(0xCC)


def time_otpclean(nf=1, fr=0x05, temp=0x5A):
    t = time.monotonic_ns()
    otpclean(nf, fr, temp)
    print("otpclean temp 0x%02x: %.0f ms" % (temp, (time.monotonic_ns() - t) / 1e6))
