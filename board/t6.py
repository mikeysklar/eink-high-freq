for frames, mode in ((20, 0xCF), (20, 0xCC), (10, 0xCC), (6, 0xCC), (4, 0xCC)):
    ts = run(make_lut(frames, VSH1, VSL), mode)
    print(frames, "frames mode %02X" % mode, "ms", ts[1:], "t=%.1f" % time.monotonic())
