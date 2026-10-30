"""Render a spinning Utah teapot as 1-bit frames for the SSD1683 panel.

Martin Newell's 32 Bezier patches, read from three.js r160 TeapotGeometry.js (MIT), as
John Park's CG Turbo demos do (Adafruit_Learning_System_Guides
CircuitPython_Turbo/CG_Turbo_Demos/tools/make_meshes.py). Tessellated, z-buffered,
Lambert shaded, then 1-bit with a screen-space 4x4 Bayer dither (the pattern stays put
while the surface turns, so fewer pixels flip per frame) and a black silhouette edge.

Output: teapot.bin, FRAMES frames of WB x HT bytes (row-major, MSB = left pixel,
1 = white, 0 = black, the panel's RAM format), plus preview PNGs.

usage: make_frames.py <TeapotGeometry.js> <outdir> [frames]
"""
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

WT, HT = 400, 300          # window in px (full screen); WT multiple of 8
WB = WT // 8
SEG = 12                   # tessellation per patch side
ELEV = np.radians(22)      # camera looks down this much
ROLL = np.radians(45)      # spin axis tilted this much on screen
LIGHT = np.array([-0.5, -0.8, 0.6])
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 + 1 / 32


def js_numbers(text, name):
    body = re.search(name + r"\s*=\s*\[(.*?)\]", text, re.S).group(1)
    body = re.sub(r"/\*.*?\*/", " ", body).replace("- ", "-")   # three.js writes "- 0.784"
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", body)]


def bern(t):
    return np.array([(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3])


def dbern(t):
    return np.array([-3 * (1 - t) ** 2, 3 * (1 - t) ** 2 - 6 * t * (1 - t),
                     6 * t * (1 - t) - 3 * t * t, 3 * t * t])


def tessellate(ctrl):
    """ctrl: [patch][4][4][3] -> vertices [N,3], normals [N,3], triangles [M,3]."""
    ts = np.linspace(0, 1, SEG + 1)
    verts, norms, tris = [], [], []
    for p in ctrl:
        base = len(verts)
        for u in ts:
            for v in ts:
                bu, bv, du, dv = bern(u), bern(v), dbern(u), dbern(v)
                pt = np.einsum("i,j,ijk->k", bu, bv, p)
                tu = np.einsum("i,j,ijk->k", du, bv, p)
                tv = np.einsum("i,j,ijk->k", bu, dv, p)
                n = np.cross(tu, tv)
                ln = np.linalg.norm(n)
                verts.append(pt)
                norms.append(n / ln if ln > 1e-9 else np.zeros(3))
        for i in range(SEG):
            for j in range(SEG):
                a = base + i * (SEG + 1) + j
                b, c, d = a + 1, a + SEG + 1, a + SEG + 2
                tris += [(a, c, b), (b, c, d)]
    verts, norms = np.array(verts), np.array(norms)
    # degenerate patch corners (poles) get no normal: borrow the neighbour average
    bad = np.linalg.norm(norms, axis=1) < 0.5
    for k in np.nonzero(bad)[0]:
        near = np.linalg.norm(verts - verts[k], axis=1) < 1e-3
        m = norms[near & ~bad].sum(0)
        norms[k] = m / (np.linalg.norm(m) or 1)
    return verts, norms, np.array(tris)


def view(ang):
    ca, sa = np.cos(ang), np.sin(ang)
    rz = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]])
    ce, se = np.cos(ELEV), np.sin(ELEV)
    rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    cr, sr = np.cos(ROLL), np.sin(ROLL)
    ry = np.array([[cr, 0, -sr], [0, 1, 0], [sr, 0, cr]])   # about the view axis
    return ry @ rx @ rz


def render(verts, norms, tris, ang, scale, center):
    m = view(ang)
    v = (verts - center) @ m.T
    n = norms @ m.T
    # screen: x right, y down (from -z), depth = y (camera at -y looking +y)
    sx = v[:, 0] * scale + WT / 2
    sy = -v[:, 2] * scale + HT / 2
    dep = v[:, 1]
    light = LIGHT / np.linalg.norm(LIGHT)
    shade = np.clip(np.abs(n @ light), 0, 1)       # two-sided: inner surfaces show too
    zb = np.full((HT, WT), np.inf)
    img = np.ones((HT, WT))
    for a, b, c in tris:
        xs, ys = sx[[a, b, c]], sy[[a, b, c]]
        x0, x1 = int(max(np.floor(xs.min()), 0)), int(min(np.ceil(xs.max()), WT - 1))
        y0, y1 = int(max(np.floor(ys.min()), 0)), int(min(np.ceil(ys.max()), HT - 1))
        if x0 > x1 or y0 > y1:
            continue
        det = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(det) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / det
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / det
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * dep[a] + w1 * dep[b] + w2 * dep[c]
        s = w0 * shade[a] + w1 * shade[b] + w2 * shade[c]
        zs = zb[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (z < zs)
        zs[upd] = z[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = s[upd]
    cover = np.isfinite(zb)
    return img, cover, zb


def to_1bit(img, cover, zb):
    by = np.tile(BAYER, (HT // 4 + 1, WT // 4 + 1))[:HT, :WT]
    tone = 0.9 * img ** 1.6                         # darker: thin dithered black fades on e-ink
    white = np.where(cover, tone > by, True)
    # silhouette and depth-jump edges in black
    edge = np.zeros_like(cover)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        c2 = np.roll(np.roll(cover, dy, 0), dx, 1)
        z2 = np.roll(np.roll(zb, dy, 0), dx, 1)
        edge |= cover & (~c2 | (np.abs(np.where(c2, z2, zb) - zb) > 0.35))
    edge |= np.roll(edge, 1, 0) | np.roll(edge, 1, 1)   # 2 px outline
    white &= ~edge
    return white


def pack(white):
    bits = np.packbits(white.astype(np.uint8), axis=1)   # MSB first, 1 = white
    return bits.tobytes()


def main():
    js, out = Path(sys.argv[1]), Path(sys.argv[2])
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    out.mkdir(parents=True, exist_ok=True)
    text = js.read_text()
    idx = np.array(js_numbers(text, "teapotPatches"), dtype=int).reshape(-1, 4, 4)
    ctl = np.array(js_numbers(text, "teapotVertices")).reshape(-1, 3)
    verts, norms, tris = tessellate(ctl[idx])
    lo, hi = verts.min(0), verts.max(0)
    center = np.array([0, 0, (lo[2] + hi[2]) / 2])
    # fit the largest outline over all angles, symmetric about the window center
    ex = ez = 0
    for f in range(frames):
        v = (verts - center) @ view(2 * np.pi * f / frames).T
        ex = max(ex, np.abs(v[:, 0]).max())
        ez = max(ez, np.abs(v[:, 2]).max())
    scale = 0.97 * min(WT / (2 * ex), HT / (2 * ez))
    blob = bytearray()
    sheet = []
    for f in range(frames):
        img, cover, zb = render(verts, norms, tris, 2 * np.pi * f / frames, scale, center)
        w = to_1bit(img, cover, zb)
        blob += pack(w)
        if f % (frames // 8) == 0:
            sheet.append(Image.fromarray((w * 255).astype(np.uint8)))
    (out / "teapot.bin").write_bytes(blob)
    pre = Image.new("L", (4 * (WT + 8), 2 * (HT + 8)), 128)
    for k, im in enumerate(sheet[:8]):
        pre.paste(im, ((k % 4) * (WT + 8), (k // 4) * (HT + 8)))
    pre.save(out / "preview.png")
    print("%d frames x %d B = %d B, %d triangles, scale %.1f" % (
        frames, WB * HT, len(blob), len(tris), scale))


if __name__ == "__main__":
    main()
