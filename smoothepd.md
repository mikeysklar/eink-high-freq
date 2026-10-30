# SmoothEPD vs our fast refresh

## Summary

SmoothEPD uses a 1-frame LUT like ours, but panel RAM holds drive masks, not pictures. Each pixel gets a 7-scan budget that restarts on every change. Our lag scheme behaves like their "net" variant, which the author says trails heavily. Their default rule gives each change full drive, gives up DC balance on reversals, and relies on scheduled cleanups. The best thing to try is that rule as precomputed masks for the teapot.

## What it is

- **Panel:** 1.54" 200x200, SSD1681 (stated, README).
- **MCU:** WCH CH32H417. The V5F core (400 MHz) draws, and the V3F core (100 MHz) drives the panel. The stopwatch demo also runs on a single-core CH32V303 (stated).
- **Speed:** 47 Hz (stated). `EPD_FRAME_FIXED_US 21260` gives 47.0 Hz (verified in source).
- **Lineage:** PaperBoy S3 (Wenting Zhang, raw parallel panel, 60 Hz), then InkBoy (kuslota, ESP32-S3, same 1.54" panel, about 30 fps, 4 grays), then SmoothEPD.

## How it works (verified in source unless marked)

1. **RAM holds commands, not pictures.** `0x26` gets a "drive black" mask and `0x24` gets a "drive white" mask. A pixel in neither mask holds. The LUT is one frame, FR `0x02`, about 50 Hz (strongly implied, not verified for the SSD1681).
2. **Per-pixel budget.** Budget is 7 for black and 7 for white. It reloads to 7 whenever the pixel's target changes, including a flip back halfway through. 7 scans x 20 ms = 140 ms. The README says pixels need at least 120 ms (stated).
3. **Frames.** About 20 ms BUSY plus about 1.6 ms SPI per scan. The full 2 x 5000 B is sent every scan. SPI is /2 of the bus, about 50 MHz, which is above the 20 MHz limit (prescaler verified, bus clock not).
4. **DC debt and soft settle.** Each pixel has a signed int8 debt with no clamp. Every 1000 scans it pays back 1 unit, but only toward the color the pixel already shows, so nothing visible changes.
5. **Full refresh.** Every 2000 scans (about 43 s) a custom LUT runs. It takes 1.3 s and is DC balanced per pixel: 9 frames to the opposite color, then 4 x (5 + 5) shaking, then 9 frames to the final color. The source says 2000 scans, though the header says 4000.
6. **Net variant** (`epd_fast_net.c.bak`). It keeps exact DC balance by only driving while the net count stays within -7..+7. The author says it "trails heavily" (stated).

## Side by side

| | SmoothEPD | Ours (4.2" SSD1683) |
|---|---|---|
| Panel | 200x200, 5000 B/plane | 400x300, 15 KB/plane |
| LUT | 1 frame, ~50 Hz | 1 frame, 125 Hz (measured by us) |
| RAM content | drive masks | frame N and frame N-lag |
| Drive per change | 7 x 20 ms = 140 ms, restarts on change | lag 6 x 8 ms = 48 ms |
| Reversal | new color gets full 7 | equal but late erase (like their net variant) |
| DC balance | broken on reversals, debt tracked | balanced |
| Cleanup | soft settle /1000 scans, 1.3 s LUT /2000 scans | 4 s balanced wipe, 3.3 s OTP clean /15 s |
| SPI | ~50 MHz (out of spec) | 15.625 MHz (measured by us) |
| Speed | 47 Hz (stated) | 89.2 fps sprite, 36.4 fps full-screen teapot (measured by us) |

## What to try (ranked)

1. **Budget masks for the teapot, computed on the Mac.** Drive pixel p toward N[p] if frames N-B..N differ at p. Write `0x26` = drive & ~N and `0x24` = drive & N. These work with our current LUT. Same SPI, same fps, no cost on the RP2040. It breaks DC balance on reversals, so it needs Mikey's OK. Have the Mac report the worst per-pixel debt per loop. *First experiment:* B = 15 (about 120 ms), on video next to lag 6. Then try B = 8.
2. **Lag 15 in the current scheme.** This is a control test that costs no fps. If trails stay, the late erase is the cause, and item 1 is the fix.
3. **Their balanced full-refresh LUT on SSD1683.** FR `0x02`, 66 frames, about 1.3 s, in place of the 3.3 s OTP clean. *First experiment:* put it in the 15 s slot and photograph the background. We don't know yet if it reaches OTP white.
4. **Mac-side debt ledger plus a same-color settle step** once per loop. This might replace the visible 4 s wipe.
5. **Thicker content.** Use 2x2 dither blocks or fewer levels. The 4x4 Bayer pattern with rotation makes many 1-pixel reversals.
6. **SPI at 31.25 MHz.** This could give about 55 fps full screen (estimate). It is out of spec, so check for corrupt rows.

## Not useful for us

- Booster on once with `0x22=C0`, ping-pong off, `0x3C=0x80`, HOLD ending: we already have these.
- Dual-core frame sharing: CircuitPython does not expose the second core.
- Per-pixel int8 arrays: 240 KB at 400x300, and too slow in Python.
- Net variant as written: close to ours, and it trails.
- Partial row windows: disabled in their code. We already window sprites.
- Their `0x22` decode and EOPT `0x02`: specific to the SSD1681.

## Caveats

- Nobody else has measured SmoothEPD's 47 Hz, ghosting, or lifetime.
- The int8 debt can wrap. A pixel held black 7 scans and white 1 scan gains +6 every 8 scans and passes 127 in about 170 scans. That is arithmetic. Nobody has seen it happen.
- Breaking DC balance (items 1 and 4) needs Mikey's OK.
- Panel lifetime under this drive is unknown. InkBoy warns of "permanent image retention or panel damage".

## Sources

- SmoothEPD: https://github.com/PinkiePie1/SmoothEPD
- InkBoy: https://github.com/kuslota/InkBoy
- PaperBoy S3: https://www.tomshardware.com/video-games/retro-gaming/designer-turns-niche-e-ink-dev-board-into-a-60hz-game-boy-handheld-960x540-display-powered-by-ultra-low-cost-esp32-s3-microcontroller
- Fastwave burn-in notes: https://github.com/bootdsc/Fastwave-Eink-Driver (docs/BURN-IN.md)
- Ours: `research/smoothepd-synthesis.md`, `research/smoothepd-reader-reports.md`, `resume-20261027.md`
