"""Precompute dirty windows for the lag-trick teapot (teapot_demo.teapot, balanced drive).

Each step writes RAM 0x24 = frame i and 0x26 = frame i-lag. Only pixels where they differ
(D_i) get drive; elsewhere the planes must be equal or stale RAM keeps driving. After a
full write the planes differ only at D_i, so if step i writes the window W_i covering
D_i and D_{i-1}, the planes outside W_i are equal again (by induction). Steps whose pair
or previous pair involves a blank frame (after wipes and cleans) use full writes.

Output: index of n entries (u32 offset, u8 x0, u8 x1, u16 y0, u16 y1; x in RAM bytes),
then per step the 0x26 crop followed by the 0x24 crop, row-major.

usage: make_window.py <teapot.bin> <out.bin> <lag>
"""
import struct
import sys

import numpy as np

W, H = 400, 300
WB = W // 8


def box(m):
    """Byte-aligned bbox of a [H, WB] bool mask: x0, x1 (bytes), y0, y1, inclusive."""
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return 0, 0, 0, 0
    return xs.min(), xs.max(), ys.min(), ys.max()


def main():
    src, out, lag = sys.argv[1], sys.argv[2], int(sys.argv[3])
    fr = np.fromfile(src, np.uint8).reshape(-1, H, WB)
    n = len(fr)
    diff = [(fr[i] != fr[(i - lag) % n]) for i in range(n)]   # per byte
    idx, data = [], bytearray()
    base = n * 10
    tot = 0
    for i in range(n):
        x0, x1, y0, y1 = box(diff[i] | diff[(i - 1) % n])
        crop = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        idx.append(struct.pack("<IBBHH", base + len(data), x0, x1, y0, y1))
        data += fr[(i - lag) % n][crop].tobytes() + fr[i][crop].tobytes()
        tot += (y1 - y0 + 1) * (x1 - x0 + 1)
    open(out, "wb").write(b"".join(idx) + data)
    avg = tot / n
    print("lag %d: avg window %.0f B per plane (%.0f%% of 15000), max %d; file %d B" % (
        lag, avg, 100 * avg / 15000,
        max((e[2] - e[1] + 1) * (e[4] - e[3] + 1) for e in
            (struct.unpack("<IBBHH", x) for x in idx)), base + len(data)))


if __name__ == "__main__":
    main()
