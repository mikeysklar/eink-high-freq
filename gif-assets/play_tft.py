# play_tft: play small_rgb.gif through videogif.GifDecoder into a 16-bit plain buffer
# that displayio shows in a Group, and print the frame rate over 10 s. UNTESTED.
# Any videocore board with a display (ESP32-P4-Function-EV, or a TFT on board.DISPLAY).
# Copy small_rgb.gif and small_rgb.json to CIRCUITPY.
# The file has 20 frames at 4 cs (25 fps), so 25 fps is the target.
import json, time

import board, displayio, videocore, videogif

try:
    from binascii import crc32
except ImportError:
    crc32 = None

PATH = "/small_rgb.gif"
SECS = 10
REVERSE = True  # same as the display's reverse_bytes_in_word (most built-in displays swap)

display = board.DISPLAY

gif = videogif.GifDecoder(PATH, reverse_bytes_in_word=REVERSE)
w, h = gif.width, gif.height
buf = bytearray(w * h * 2)
last = bytearray(buf)

video = videocore.VideoBuffer(buf)
video.x = (display.width - w) // 2
video.y = (display.height - h) // 2
root = displayio.Group()
root.append(video)
display.root_group = root

# expected CRC-32 of each frame as RGB565 (make_gifs.py), big-endian when REVERSE; a match
# tells which frame landed, no match on every frame likely means REVERSE is wrong
key = "crc32_rgb565be" if REVERSE else "crc32_rgb565le"
crcs = {}
try:
    with open(PATH[:-4] + ".json") as f:
        for e in json.load(f)["frames"]:
            crcs[int(e[key], 16)] = e["i"]
except OSError:
    pass

video.play(gif)
n = matched = 0
seen = set()
t0 = time.monotonic()
t_last = t0
n_last = 0
while True:
    # a new frame landed when the buffer changed (every frame moves the ball)
    if buf != last:
        last[:] = buf
        n += 1
        if crc32 and crcs:
            i = crcs.get(crc32(last) & 0xFFFFFFFF)
            if i is not None:
                matched += 1
                seen.add(i)
    t = time.monotonic()
    if t - t_last >= 1:
        print("%.1f fps" % ((n - n_last) / (t - t_last)))
        t_last, n_last = t, n
    if t - t0 >= SECS:
        break
video.stop()
gif.deinit()
dt = time.monotonic() - t0
print("%d frames in %.1f s = %.1f fps (target 25)" % (n, dt, n / dt))
if crc32 and crcs:
    print("CRC matched %d of %d frames, %d of 20 distinct frames seen" % (matched, n, len(seen)))
