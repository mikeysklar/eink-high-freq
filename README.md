# eink-high-freq

Fast refresh on an Adafruit 4.2" SSD1683 e-paper panel (400x300, #6381), driven from a
Feather RP2040 ThinkInk running stock CircuitPython over raw `busio.SPI`.

| Teapot, full screen 400x300, balanced drive | steady | avg with wipes + cleans |
|---|---|---|
| displayio, stock full refresh | 0.147 fps (6.78 s) | n/a |
| raw SSD1683, full frames (`teapot_demo.teapot`) | 36.4 fps | 28.7 fps |
| raw SSD1683, dirty windows (`teapot_win.teapot_win`) | **57.5 fps** (17.4 ms) | **46.0 fps** |

The bouncing ball sprite reaches 89 fps (70 fps averaged with cleanups).

## The tricks

1. **Custom 1-frame LUT.** Write a 227-byte waveform with `0x32`. BW and WB groups get
   equal frame counts (DC balanced); WW and BB stay at VSS, so unchanged pixels are not
   driven. RP and SR bytes are counts, and 0 skips the group. See `board/lut.py`.
2. **125 Hz frame rate.** The LUT's frame-rate byte set to `0x05` (datasheet Table 6-7, FR `0101`). BUSY
   is exactly frames x period: 8.1 ms for one frame.
3. **Fast update command.** `0x22 0x0C` then `0x20` runs only the display step with the
   loaded LUT. It needs one `0xCC` warm-up update after an OTP refresh.
4. **Both RAM planes as a drive mask.** `0x24` holds the new frame and `0x26` holds the
   old one, so only pixels that differ are driven. Turn ping-pong off with `0x37` and
   manage `0x26` yourself.
5. **Lag drive.** Keep `0x26` = frame N-lag instead of N-1 (lag 6 for the teapot). Every
   pixel that changed in the last `lag` steps is driven, so each change gets `lag x nf`
   frames, in equal amounts toward black and white. Darker motion, still balanced.
6. **Dirty windows.** Set the RAM window (`0x44`, `0x45`, `0x4E`, `0x4F`) to the
   byte-aligned box around the pixels that changed between N and N-lag, unioned with the
   previous step's box so the two planes stay equal outside it. The teapot averages 37%
   of the screen (max 47%). `teapot/make_window.py` precomputes them.
7. **Cleanup that keeps DC balance.** A balanced wipe (k frames black, k frames white)
   every 4 s, with the moving object hidden for lag+2 frames first, plus a full OTP
   clean every 15 s followed by one wipe. This removes the gray drift and afterimages.
8. **No allocation in the frame loop.** GC costs 9-12 ms on this heap. Poll BUSY with
   `while busy.value: pass` (calling `time.monotonic_ns()` per poll allocates and
   triggers GC). Preallocate buffers and memoryviews; control GC explicitly.
9. **Fewer SPI transactions.** Hold CS across D/C changes (`fcmd`), one CS assertion per
   frame, and let the controller fill rectangles (RAM window + constant byte stream)
   instead of copying slices in Python (memoryview slice assignment memmoves the tail).
10. **Frames from flash, not RAM.** 120 precomputed 1-bit frames (`teapot.bin`, 1.8 MB)
    and windows (`teapot_w6.bin`, 1.34 MB) live on CIRCUITPY. The ~6.8 ms flash read
    overlaps BUSY.
11. **Do all SPI between updates.** RAM writes during BUSY are dropped.
12. **Last RAM byte.** The SSD1683 commits the last RAM byte only when the next command
    arrives, so send a command (a NOP) before any reset.

Not used, on purpose: unbalanced or white-biased drive (budget masks), SPI above the
SSD1683's 20 MHz write limit, overclocking or PIO SPI. Never send `0x36` (programs OTP).

## Layout

| Path | What |
|---|---|
| `board/` | CircuitPython scripts copied to the board: `setup.py`, `lut.py`, `teapot_demo.py`, `teapot_win.py`, `fps_glyphs.py`, the `t*.py` experiments (ball, lag, LUT and SPI timing), `teapot_displayio.py` baseline, `pr_*.py` hardware tests for proposed CircuitPython changes |
| `board/cprun.py`, `board/flash.sh` | host helpers: run a script over the serial REPL; flash a UF2 by USB path |
| `teapot/` | `make_frames.py` renders the Utah teapot (`vendor/TeapotGeometry.js` from three.js, MIT) to 1-bit frames; `make_window.py` builds the dirty windows; `make_masks.py` is the unused budget-mask experiment |
| `gif-assets/` | GIF versions of the teapot and test GIFs for the CircuitPython `videogif` work |
| `research/`, `smoothepd.md` | research notes |
| `video/`, `video-smoothepd/` | scripts that build the explainer videos |

## Build the frames

```
python3 teapot/make_frames.py teapot/vendor/TeapotGeometry.js teapot 120
python3 teapot/make_window.py teapot/teapot.bin teapot/teapot_w6.bin 6
```

Copy `teapot.bin`, `teapot_w6.bin`, `board/fps_glyphs.py` and the board scripts to
CIRCUITPY, then run `teapot_demo.py` (setup, LUT, wipe, clean) followed by
`teapot_win(secs=30, fps=True)`.

## License

MIT-0 (see `LICENSE`), except `teapot/vendor/TeapotGeometry.js`, which is from three.js
under the MIT license.
