import gc
fbmv = memoryview(fb)
rows = [fbmv[y * STRIDE:(y + 1) * STRIDE] for y in range(H)]
gc.collect()


def square(x0, y0=110, n=80, ink=0):
    row = INK[ink]
    xb = x0 // 8
    for y in range(y0, y0 + n):
        rows[y][xb:xb + 10] = row

t = time.monotonic_ns()
for _ in range(10): square(80, 80, 80, 0)
print("square rows-memoryview %.2f ms" % ((time.monotonic_ns() - t) / 1e6 / 10))
anim3(6)
time.sleep(2)
anim3(4)
