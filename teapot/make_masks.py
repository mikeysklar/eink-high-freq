"""Turn teapot.bin frames into per-step drive masks (SmoothEPD / InkBoy budget rule).

A pixel is driven toward its target in step i if its target changed in any of the last
B steps (i-B, i]; this is SmoothEPD's per-pixel counter reloaded to B on every change.
Unlike the lag trick this is not DC balanced, so each loop also pays its own debt back:
a pixel with excess black frames gets extra white frames in idle steps where it already
shows white (and the reverse), which does not change what is shown (SmoothEPD's
same-colour settle, done exactly here because the loop is known in advance).

Each step is two planes for our 1-frame LUT (teapot_demo.make_lut):
  0x26 = 1, 0x24 = 0 -> one frame toward black
  0x26 = 0, 0x24 = 1 -> one frame toward white
  both 0             -> hold (VSS)
Output layout, 2 x 15000 B per step (0x26 plane first):
  enter:  B steps, from an all-white screen into frames n-B..n-1 (the loop starts at 0)
  loop:   n steps, frames 0..n-1, history wrapping, debt paid back within the loop
  exit:   B steps, from frame n-1 to all white
  payback: bit planes of the enter+exit debt (nee), then of one loop's debt (nlp),
           largest first; plane j is held for 2**(nb-1-j) frames by repeating go(),
           loop planes k times for k loops played, while the screen is blank
mode "raw" (default): pure budget rule, loop debt paid back after the run.
mode "bal": also settle the loop to zero net drive (keeps each change's first frames,
           but most dithered pixels then get only 1-2 frames).

usage: make_masks.py <teapot.bin> <out.bin> <B> [raw|bal]
"""
import sys

import numpy as np

W, H = 400, 300


def load(path):
    raw = np.fromfile(path, np.uint8).reshape(-1, H, W // 8)
    return np.unpackbits(raw, axis=2).astype(bool)        # True = white


def budget(seq, steps, B):
    """seq: targets with B+1 history in front. Returns black, white drive [steps, H, W]."""
    chg = seq[1:] != seq[:-1]                              # chg[s-1]: change at step s
    blk, wht = [], []
    for i in steps:
        drive = chg[i - B:i].any(0)
        blk.append(drive & ~seq[i])
        wht.append(drive & seq[i])
    return np.array(blk), np.array(wht)


def debt(blk, wht):
    return blk.sum(0, dtype=np.int32) - wht.sum(0, dtype=np.int32)


def settle(blk, wht, tgt, age, B):
    """Balance each pixel's net drive over the loop without changing what is shown.
    1. add same-colour frames in idle steps (excess black -> white frames where the
       target is white, and the reverse)
    2. pixels that flip often are driven every step and have no idle steps: drop frames
       of the excess colour, oldest in their run first, so each change keeps its first
       frames of drive."""
    d = debt(blk, wht)
    idle = ~(blk | wht)
    for need, cand, plane in ((np.maximum(d, 0), idle & tgt, wht),
                              (np.maximum(-d, 0), idle & ~tgt, blk)):
        plane |= cand & (np.cumsum(cand, 0) <= need)
    for a in range(B, 0, -1):
        d = debt(blk, wht)
        if not d.any():
            break
        for need, plane in ((np.maximum(d, 0), blk), (np.maximum(-d, 0), wht)):
            cand = plane & (age >= a)
            plane &= ~(cand & (np.cumsum(cand, 0) <= need))
    return debt(blk, wht)


def ages(seq, n):
    """Steps since each pixel's target last changed, for the last n entries of seq."""
    age = np.zeros(seq.shape[1:], np.int32)
    out = []
    for s in range(1, len(seq)):
        age = np.where(seq[s] != seq[s - 1], 0, age + 1)
        out.append(age)
    return np.array(out[-n:])


def pack(blk, wht):
    out = bytearray()
    for b, w in zip(blk, wht):
        out += np.packbits(b, axis=1).tobytes()            # 0x26
        out += np.packbits(w, axis=1).tobytes()            # 0x24
    return out


def stats(name, blk, wht):
    d = debt(blk, wht)
    print("%-7s %3d steps, %5.1f%% px driven/step, net debt max |%d| frames, %d px nonzero" % (
        name, len(blk), 100 * (blk | wht).mean(), np.abs(d).max(), (d != 0).sum()))
    return d


def main():
    src, out, B = sys.argv[1], sys.argv[2], int(sys.argv[3])
    mode = sys.argv[4] if len(sys.argv) > 4 else "raw"
    fr = load(src)
    n = len(fr)
    white = np.ones((1, H, W), bool)
    hist = fr[n - B - 1:]                                  # frames n-B-1..n-1

    eb, ew = budget(np.concatenate([np.repeat(white, B + 1, 0), fr[n - B:]]),
                    range(B + 1, 2 * B + 1), B)
    lb, lw = budget(np.concatenate([hist, fr]), range(B + 1, B + 1 + n), B)
    xb, xw = budget(np.concatenate([hist, np.repeat(white, B, 0)]),
                    range(B + 1, 2 * B + 1), B)

    stats("enter", eb, ew)
    stats("loop", lb, lw)
    if mode == "bal":
        # two loops of history so ages near step 0 see the wrap
        age = ages(np.concatenate([fr, fr]), n)
        full = (lb | lw).sum()
        settle(lb, lw, fr, age, B)
        print("        settle changed drive frames %d -> %d" % (full, (lb | lw).sum()))
        stats("loop+pb", lb, lw)
    stats("exit", xb, xw)

    # debt paid while the screen is blank, as binary planes: enter + exit once per cycle,
    # loop debt once per loop played (planes repeated k times on the board)
    ee, nee = planes(debt(eb, ew) + debt(xb, xw))
    lp, nlp = planes(debt(lb, lw))
    print("payback: enter+exit %d planes, loop %d planes (%d frames per loop)" % (
        nee, nlp, (1 << nlp) - 1 if nlp else 0))

    blob = pack(eb, ew) + pack(lb, lw) + pack(xb, xw) + pack(*ee) + pack(*lp)
    open(out, "wb").write(blob)
    print("%s: %d B; teapot_budget(B=%d, n=%d, nee=%d, nlp=%d)" % (
        out, len(blob), B, n, nee, nlp))


def planes(d):
    """Binary planes paying debt d back: plane j is held for 2**(nb-1-j) frames."""
    nb = int(np.abs(d).max()).bit_length()
    pb, pw = [], []
    for j in range(nb):
        bit = 1 << (nb - 1 - j)
        pb.append((np.maximum(-d, 0) & bit) > 0)           # excess white -> black frames
        pw.append((np.maximum(d, 0) & bit) > 0)
    return (np.array(pb), np.array(pw)), nb


if __name__ == "__main__":
    main()
