# SmoothEPD review: verified claims, how it works, and what we can use

## Verification

All `c:` lines refer to `V3F/User/epd_fast.c`, `net:` to `epd_fast_net.c.bak`, `h:` to `epd_fast.h`, `td:` to our `teapot_demo.py`.

| Claim | Status |
|---|---|
| Fast LUT 1 frame: LUT1 `0x80,0x80` = white (VSL), LUT2 `0x40,0x40` = black (VSH1), 00/11 hold; byte 67 = `0x01` (c:378-393) | VERIFIED |
| FR `0x22`×6; EOPT/VGH/VSH1/VSH2/VSL/VCOM = `02 17 41 b0 32 28` (c:391-392) | VERIFIED |
| `0x26` = black mask, `0x24` = white mask (c:858-859) | VERIFIED |
| Ping-pong off with `0x37` + ten `0x00` (c:676-679); `0x3C=0x80` (c:681) | VERIFIED |
| Booster on once with `0x22=C0` (c:466-470), each scan `0x22=0C` (c:865-867) | VERIFIED. We already do this (td:129, td:134). |
| 50 Hz per frame | UNVERIFIED for the SSD1681. Strongly implied: `lut_full` is 9+4×12+9 = 66 frames (c:359-361), which is 1.32 s at 50 Hz, and the code says "measured 1314 ms" (h:42). Also h:49 gives 26 ms for 1 frame and 166 ms for 8, i.e. 20 ms per frame. |
| 47 Hz | Only stated (README:22). `EPD_FRAME_FIXED_US 21260` (c:77) gives 47.0 Hz. No measurement is logged, and the fps counter also counts calls that send nothing to the panel (main.c:176-186). |
| Budget 7/7, reloaded on every target change (c:310-311, c:761-762) | VERIFIED |
| Clean interval | Code says 2000 (c:317); header says 4000 (h:81). The code wins. |
| Soft settle every 1000 scans, 1 unit per call, only toward the shown colour (c:315-316, c:892-895, c:939-943) | VERIFIED. One reader's line numbers (765-794, 821-886, 905) came from the net file. The real ones are c:794-824, c:875-947, c:988-1013. |
| `s_debt` is int8 with no clamp (c:407) | VERIFIED. It can wrap: a pixel held black 7 scans, white 1 scan, repeated, gains +6 every 8 scans and passes 127 in about 170 scans, well before the 1000-scan settle. This is from arithmetic; nobody has observed it. |
| Net variant: no change detection, drives while the net count stays in [-7, +7] (net:765-775); `FastBegin` zeroes all counts (net:874) | VERIFIED |
| "Our lag scheme gives a reverted pixel no drive at all" | WRONG. W→B at step t and back at t+2 gives 2 black frames, then nothing from t+2 to t+lag-1. Then N-lag = B while N = W, so it gets 2 white frames at t+lag. The erase is equal in length but late, which is the net-variant rule. |
| HOLD ending: one all-zero scan (c:1054-1076) | VERIFIED. Our loop already sends all-hold scans whenever N == N-lag. |
| SPI /2 of a 100 MHz bus, about 50 MHz (c:58-61) | Prescaler VERIFIED. The 100 MHz bus clock is UNVERIFIED. |
| `0x3C=0x80` is something new to test | WRONG. We already set it (td:127). |

Web sources:
- InkBoy (https://github.com/kuslota/InkBoy) uses the same mask scheme and warns of possible "permanent image retention or panel damage".
- Fastwave (https://github.com/bootdsc/Fastwave-Eink-Driver, docs/BURN-IN.md) found that VCOM `0x08` stopped whole-panel darkening and that differential updates "will not lift a stain".
- Nobody has independently checked SmoothEPD's results.

## How SmoothEPD works

1. **Panel RAM holds commands, not pictures.** Each scan writes a 1-bit "drive black" plane to `0x26` and a "drive white" plane to `0x24`. The LUT has one frame at about 50 Hz. A pixel in neither plane gets VSS, so it holds. The booster stays up between scans.
2. **Each pixel has a remaining-drive counter (default driver).** It is reloaded to 7 whenever the pixel's target changes, including a flip back halfway through a transition. While it is above zero, the pixel is driven toward its current target. That is 7 × 20 ms = 140 ms, above the README's 120 ms minimum (README:34).
3. **Timing.**
   - The next frame is planned while the panel is BUSY. RAM is written only after BUSY falls (c:1016-1026).
   - The full 2 × 5000 B is sent every scan; partial windows are off (c:307).
   - The panel is the bottleneck: about 20 ms BUSY plus about 1.6 ms SPI per scan.
4. **DC handling.**
   - The default rule is not DC balanced on reversals, because the new colour always gets the full 7.
   - It keeps a signed per-pixel debt. Every 1000 scans it pays back 1 unit, but only where the pay-back direction matches the colour the pixel is showing, so nothing visible changes.
   - The real reset is a custom-LUT full refresh every 2000 scans (about 43 s). It takes 1.3 s and is itself DC balanced per pixel: 9 frames toward the opposite colour, 4 × (5 one way + 5 the other) shaking, then 9 frames to the final colour (c:354-361).
   - The net variant bounds DC exactly. The author says it "拖影很重" ("trails heavily", README:38).
5. **Results (claims only).**
   - 47 Hz on a 200×200 panel.
   - About 40 KB of RAM (README:27).
   - The demos are written so pixels get their full drive: 1 px of motion per frame, digits change every 7 frames, 2-4 px strokes, slow physics (stopWatch.c:43-44, SandSim.h:16).

## Mapping onto our setup

**Main point: our lag scheme already behaves like their net variant, the one they found leaves heavy trails.** That matches our notes: "balanced drive never returns fully to white" (resume:124, 130), and lag 6 and lag 8 did not change it.

Our per-change drive is also short: lag 6 × 8 ms = 48 ms, against their 140 ms.

**Ranked list of things to incorporate**

1. **Budget masks for the teapot, computed on the Mac.**
   - **What:** pixel p is driven toward N[p] if any of frames N-B..N differ from each other at p. This is exactly their counter rule, because remaining > 0 ⇔ the pixel changed within the last B scans.
   - **Writes:** `0x26` = drive & ~N, `0x24` = drive & N. These work with our current LUT unchanged: (`0x26`=1, `0x24`=0) is our to-black combination and (0, 1) is to-white (td:112-113).
   - **Why:** it fixes the late, short erase and gives each pixel full drive. This should mean fewer trails and less gray.
   - **Cost:** nothing on the RP2040. It is still two 15 KB planes per step, the same SPI and the same fps. `make_frames.py` simulates two loops so the state wraps.
   - **Caveat:** it is not DC balanced on reversals. Our notes say breaking balance needs Mikey's OK (resume:66). The Mac can compute each pixel's net debt per loop and report the maximum.
   - **First experiment:** B = 15 (about 120 ms at 8 ms), on video next to the current lag 6. Then try B = 8.
2. **Raise lag in the current scheme (a cheap control test).**
   - Try lag 15. It costs no fps, only a longer hide period before each wipe (lag+2 steps).
   - This separates "too little drive" from "late erase". If trails remain, item 1 is the fix.
3. **Their balanced full-refresh LUT, ported to the SSD1683 layout.**
   - Use FR `0x02` (50 Hz), 66 frames, about 1.3 s, instead of our 3.3 s OTP clean.
   - Cost: one LUT write.
   - Unknown whether it reaches OTP-level white (resume:136).
   - First experiment: replace `otpclean` in the 15 s slot and photograph the background.
4. **Mac-side debt ledger plus a same-colour soft-settle mask.**
   - Insert one settle step per loop that pays debt back only toward each pixel's displayed colour.
   - This could replace the visible 4 s wipe (the wipe and its afterimage are at resume:125-126).
   - Cost: nothing on the device.
5. **Change the content (theirs: thick strokes, slow motion).**
   - Render the teapot dither in 2×2 blocks or with fewer levels. The 4×4 Bayer pattern plus rotation creates many single-pixel reversals.
   - Cost: none.
6. **SPI at 31.25 MHz (125/4).**
   - They run far above the 20 MHz limit. 30 KB would take about 7.7 ms instead of about 15 ms, giving roughly 55 fps full screen (my estimate).
   - It is out of spec and untested on the SSD1683. Check for corrupt rows.

**On-device version for live content (the ball):** use a bit-sliced 4-plane counter (0..15). That is 4 × 15 KB = 60 KB, or about 4 KB per plane for a sprite window. It needs about 20 whole-plane bitwise ops per step. ulab is in our build (resume:35), but its speed for this is unknown. Try the sprite window first.

## Not useful for us

- **Booster trick, ping-pong off, `0x3C=0x80`, HOLD ending:** we already have all of these.
- **Dual-core A/B frame sharing:** CircuitPython does not expose the second core.
- **Per-pixel int8 arrays as written:** 240 KB at 400×300, and a per-pixel Python loop is too slow.
- **The net variant as written:** it is close to what we already do, and it trails.
- **Partial row windows:** disabled in their code, and we already window sprites. If a skipped row was driven last step, its old mask stays in RAM and keeps driving it, so a window has to cover last step's rows too.
- **Their 0x22 decode and EOPT `0x02`:** SSD1681-specific and undocumented.
- **Lifetime:** no project reports measurements, so it is unknown.

Source clone: `/private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src`. Our files: `/Volumes/clear/Downloads/ada/eink-high-freq/board/teapot_demo.py`, `/Volumes/clear/Downloads/ada/eink-high-freq/resume-20261027.md`.