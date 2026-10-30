# High-rate e-paper refresh: what others have done, and what applies to our SSD1683

**Spot-checked (5):**
- SSD1683 datasheet Rev 1.0, from a local pdftotext copy of the Crystalfontz PDF. I checked Table 6-7 (FR), the 0x22 option table, command 0x0C, and the SPI timing table.
- InkBoy write-up on circuitdigest.com.
- Hackaday "20 FPS on e-paper".
- CNX Software PaperBoy 60 fps article.
- ESPHome SSD1683 source, for the 0xD7 comment.

All five matched what the researchers reported.

## 1. Fastest real results found (fastest first)

| Who | Controller / panel | Visible fps | Drive / FR | Technique | Conf. | URL |
|---|---|---|---|---|---|---|
| Wenting Zhang, PaperBoy S3 | **No controller, direct drive**. M5PaperS3, 4.7" 960x540, ESP32-S3 | up to 60 (30-60 in most games). Game area only, 160x144 scaled 3x | n/a | Raw row/column drive that skips the waveform process. Only the game area is refreshed | **verified** (claim as stated in article) | https://www.cnx-software.com/2026/07/02/paperboy-game-boy-emulator-works-at-60-fps-on-esp32-s3-e-ink-devkit/ |
| Modos Paper Monitor / Caster | FPGA EPDC, direct drive. 13.3" 1600x1200 | "60 Hz" (binary mode) / "75 Hz max frame rate" | same figures | Per-pixel update timers, early cancel when a pixel gets new data, parallel regions, binary first and gray refine later. Their own page puts a typical region update at about 100 ms | secondhand (vendor) | https://www.modos.tech/blog/modos-paper-monitor , https://www.crowdsupply.com/modos-tech/modos-paper-monitor |
| InkBoy (kuslota) | **Controller-based**. Waveshare ESP32-S3-ePaper-1.54 V2, 200x200. The controller is not named, probably SSD1681-class | ~30 (an update starts every ~33 ms). Stock driver: ~2 | unknown | Waveform cut from ~17 steps to 2 (~50 ms full update). Per-pixel drive budget, with 6-8 drives covering a full B to W change. Only changed pixels are driven. Grays come from stopping the drive partway | **verified** | https://circuitdigest.com/news/esp32-s3-e-paper-game-boy-emulator-30-fps-custom-driver |
| **Us** | SSD1683 4.2" 400x300 | **20** (49.5 ms) | 112.5 Hz | 4-frame custom LUT, display-only 0x22, ping-pong off, row bands | measured | n/a |
| Tony Weston, Bad Apple | **No smart controller**. 960x540, parallel bus, ESP32-S3 | 20 | unknown | MPEG-like inter-frame delta. Host-generated "fast waveform" that leaves blacks gray | **verified** | https://hackaday.com/2026/07/21/20-fps-on-e-paper-display-without-help/ |
| E Ink / Ricoh patent US8203547 | generic EPD, ±15 V | 12.5 (worked example) | 20 ms voltage frame (50 Hz) | M = 1000/(R·VT) voltage frames per video frame, plus a per-pixel error model | verified-source (patent) | https://patents.google.com/patent/US8203547 |
| Soldered Inkplate 6MOTION | not SSD1683 | ~11 (91 ms partial) | unknown | Vendor-tuned partial waveform | secondhand (vendor) | https://liliputing.com/?p=169205 |
| IT8951 A2 mode | IT8951 + 10.3" panels | ~8 if back-to-back (A2 = 120 ms) / 5 fps in a review | 85 Hz (snippet) | A2 is a 1-bit waveform | verified-source / secondhand | https://unpkg.com/it8951@0.1.1/docs/enums/_it8951_.waveform.md |
| Ben Krasnow 2017 | 4.2" 400x300. Controller reported as IL0373/EK79652, not SSD1683 | ~3 | unknown | Shortened 42-byte LUT | secondhand | https://hackaday.com/2017/10/31/ben-krasnow-hacks-e-paper-for-fastest-refresh-rate/ |
| Vendor stock SSD1683 4.2" (OpenELAB, Good Display, Waveshare V2, Linux DRM patch) | SSD1683 400x300 | ~2.5-3.3 partial (0.3-0.4 s). ~0.7 fast (1.5 s) | unknown | Stock OTP waveforms | secondhand | https://openelab.io/a/s/products/4-2-inch-e-ink-high-rate-refresh-e-paper-400x300-spi , https://patchew.org/linux/20260430183311.2978142-1-devarsht@ti.com/ |

At 20 fps we are already ahead of every published SSD1683 result, roughly 6-8x the vendor partial mode. InkBoy is the only controller-based panel above us.

## 2. Techniques we haven't tried, ranked by expected gain

1. **Overlap SPI and Python with BUSY (pipelining).** Possible gain: up to ~11.6 ms/frame. Right now 8.7 + 2.9 ms run serially after the 37 ms busy. Nobody we found shows RAM writes during BUSY on SSD1683. ESPHome does chunked writes, but always before 0x20. Untested and unverified. Two things to test on hardware: (a) does a 0x24 write during BUSY get accepted without corrupting the current scan? (b) Since ping-pong is off, does it corrupt the frame being displayed? If it works, ~37-40 ms/frame, about 25-27 fps.
2. **Cut LUT frames from 4 to 2, then add an InkBoy-style per-pixel budget on the host.** This is the biggest lever, but it costs image quality. At 125 Hz, 2 frames = 16 ms of busy time. Mapping InkBoy onto SSD1683 is my own idea; no source does this. With ping-pong off, the host owns both RAMs (0x24 new, 0x26 old). The LUT is indexed per pixel by the (0x26, 0x24) bit pair, so the 4 LUT groups can mean "pulse black / pulse white / hold / hold". The host then decides which pixels get a pulse each frame and keeps a per-pixel budget of 6-8 pulses (InkBoy's number) for a full transition. The panel only ever runs a 1-2 frame LUT. Ceiling estimate: 16 ms busy + 8.7 SPI + 2.9 Py ≈ 28 ms ≈ 36 fps serial, or ≈ 19 ms ≈ 50 fps if #1 also works. InkBoy shows that 2 steps alone gives ghosting and graying, and that the budget fixes it.
3. **FR = 125 Hz (FR[3:0] = 0101) instead of 112.5 Hz (1100).** Gain is about 11% of busy time, so 4 frames go from 35.6 ms to 32 ms, saving roughly 3.5-4 ms. **Verified in the datasheet:** Table 6-7 lists 0101 = 125 Hz, and section 1 says "adjustable frame rate from 25Hz to 125Hz". So 112.5 Hz is **not** the max. It is a one-nibble change at WS byte 224 of the 0x32 stream.
4. **Delta-only RAM writes, sending changed bands only** (Weston, InkBoy, Modos). This cuts the 8.7 ms SPI time in proportion to how much of the image changes. It does nothing for busy time, because the LUT still scans all gates.
5. **Periodic clean refresh every 5-10 fast frames, plus ghost pre-compensation.** This is for quality, not speed. TRMNL, the idfxx readme, Soldered and the Waveshare FAQ all say every ~10 frames, and Inkplate's Game of Life does it every 40. Ghostbuster (EMSOFT 2024) does host-side source-image compensation, but I didn't verify it. TRMNL's charge-balance rule (N pushes to black, then N to white) matters for a 2-frame LUT.
6. **Things that won't help:**
   - 0x22 = 0xD7 ("fast"). ESPHome says it is "in busy state for the same amount of time" (verified). By the bit map it is clk + analog + load temp + display + off, with no LUT load. It isn't a shorter waveform.
   - 0x1A temperature forcing. This only picks a shorter OTP waveform, and we already override with 0x32.
   - SPI above 20 MHz. The datasheet fSCL write max is 20 MHz (verified), so we're already at the limit, and 40 MHz would save only ~4 ms off-spec.
   - Raising VSH/VGH. No source has numbers for it, and FOSDEM warns about panel damage.
   - Reducing MUX/gate count (0x01). No source ties it to scan time on SSD16xx.

## 3. Has 60-70 Hz visible been reached on a controller-based panel?

**No.** Every 60-80 "Hz/fps" figure is one of these:
- Direct drive with no controller: PaperBoy (raw row/column), Modos Caster (FPGA).
- A drive or scan rate, not new images per second: Modos says 60/75 Hz while its own typical region update is ~100 ms. E Ink patent US11721263 gives 120-240 Hz drive with a 95-115 ms page change. The academic paper runs at 66.67 Hz drive.
- Unverified marketing: Geniatech 60 Hz, Bigme 80 fps, Dasung 33-60 Hz. Dasung's figures conflict across retailers.

The best controller-based result is InkBoy at ~30 fps, on a 200x200 panel.

Realistic ceiling for our SSD1683 at 400x300:
- 1 frame of busy at 125 Hz is 8 ms, so the hard floor is ~8 ms busy plus whatever SPI and Python don't overlap.
- 2-frame LUT + per-pixel budget, serial: ~35 fps.
- Same, with SPI overlapped (if it works): ~50 fps.
- 60-70 fps would need a 1-frame LUT and full overlap. Each update would then move ink only a few percent, so expect very low contrast and heavy ghosting. Nobody has shown this.

Plan on 30-40 fps as the practical target.

## 4. Contradictions and dubious claims

- **0x0C / 0xCC confusion.** Several researchers flagged "0x0C is Booster Soft Start, not frame rate". That mixes up the *command* 0x0C (it is soft start, verified) with our *values*: FR nibble 1100 = 0x0C, and 0x22 parameters 0x0C / 0xCC. The 0x22 table lists only composite examples (80, C0, 91, 99, B1, B9, C7, CF, F7, FF). Our values follow the same bit pattern: 0x80 clk on, 0x40 analog on, 0x08 BW display mode, 0x04 display, 0x02 analog off, 0x01 clk off. 0xCC = power up and display BW, leaving power on. 0x0C = display BW only. Neither is listed in the table, but both follow from the bit pattern and both work on hardware.
- **"112.5 Hz is the datasheet max".** Wrong: 125 Hz exists (verified).
- **0x1A means two different things.** In the Zephyr and Linux threads, "0x1A/0x08" are dummy-line and gate-width *values* from Good Display sample code. On SSD168x, 0x1A is the temperature-write *register*. NuttX also says the 0x3A/0x3B meanings are undocumented, and they are absent from the SSD1683 Rev 1.0 command table.
- **ESPHome 0xD7 "fast mode".** It is only a comment and the code never sends it. The comment itself says busy time is unchanged.
- **InkBoy fps.** Kottke says 24 in the title and 30 in the body. The Register gives the stock rate as 3.33 fps while circuitdigest says ~2. Circuitdigest's 30 is the best-supported figure.
- **Modos numbers.** 60 vs 75 Hz is never reconciled, and the Zynq vs Spartan-6 FPGA reports conflict. Hackaday's "60 Hz monitor" article has no technical detail.
- **Krasnow "60 Hz".** That figure comes from a reader comment. Krasnow himself reports ~3 Hz, and his LUT is the IL0373 42-byte format (and it did not even carry over to a newer Good Display 4.2" panel).
- **TRMNL LUT bytes and 0x30 / 0x21 registers** are UC81xx-specific. The structure is a useful reference, but the bytes don't apply to SSD1683.
- **Unverified items:**
  - EMSOFT "fast mode = 1/5 of full time": the fetch failed.
  - Hackster "60 FPS E Ink Game Boy": returned 403. It is probably the same direct-drive PaperBoy project.
  - Unisystem GL16/GC16: lists 480 ms in its table and 980 ms in its text.
  - VB3300 "DU 260 ms @ 85 Hz": the fetch returned the wrong file.
- **Lifetime.** The "~10M refreshes, under a week at 20 fps" figure is a commenter's estimate. Waveshare rates ~1M refreshes and recommends a ≥180 s interval for normal use. At 20+ fps, panel wear is a real but unquantified risk. The InkBoy README warns of permanent image retention.

Datasheet text used for verification: /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/ssd1683.txt