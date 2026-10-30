## lut-registers

Report on the LUT and registers in SmoothEPD's `V3F/User/epd_fast.c`. Paths below are relative to `/private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src`.

**Answer: yes, it uses a 1-frame LUT like ours, but at 50 Hz instead of 125 Hz.** One update is 1 panel frame of about 20 ms. They measure about 21.3 ms per scan in total, which is where the README's 47 Hz comes from.

**Init (`EPD_Init`, epd_fast.c:542-573)**
- Hardware reset: RST high 50 ms, low 20 ms, high 50 ms (lines 313-314 and 478-489).
- `0x12` software reset, then:
  - `0x01` = C7 00 01
  - `0x11` = 01 (X increments, Y decrements)
  - window via `0x44`/`0x45`/`0x4E`/`0x4F` (lines 515-533)
  - `0x3C` = 01
  - `0x18` = 80 (internal temperature sensor)

**Full refresh (`EPD_SendDisplay`, lines 575-635)**
- Same init, then `0x22`=B1 / `0x20` to load the temperature (lines 605-607).
- Loads the custom `lut_full`, writes the image to both `0x24` and `0x26`, then `0x22`=C7 / `0x20` (lines 626-628). Measured 1314 ms (epd_fast.h:42).
- `lut_full` timing, all at 50 Hz:
  - group 0: TPA=9 (line 359)
  - group 1: TPA 5, TPB 1, TPC 5, TPD 1, RP=3 (line 360)
  - group 2: TPA=9 (line 361)
- That totals 9 + 4×12 + 9 = 66 frames, about 1.32 s, which matches the measurement. So RP=n means n+1 runs, and FR nibble 0x2 means 50 Hz.

**Fast mode setup (`EPD_FastPrepareFrames`, lines 638-685)**
- Hardware reset only, with no `0x12` (line 660 comment). Then `0x01` C7 00 01, `0x11` 01, `0x18` 80.
- LUT load (lines 491-510): `0x32` takes bytes 0..152, then `0x3F`=byte 153, `0x03`=154, `0x04`=155..157, `0x2C`=158.
- `0x37`: ten bytes of 00, so ping-pong is off (lines 676-679).
- `0x3C` = 80: border driven to VCOM, per the SSD1683 table at ssd1683.txt:1838-1846.
- Booster turned on once with `0x22`=C0 / `0x20` (lines 465-474) and left on. epd_fast.h:51 says the LUT cannot be reloaded while the booster is up.
- Each scan writes `0x26` = black mask, then `0x24` = white mask, then `0x22`=0C / `0x20` (lines 727-735 and 862-867). The comment says 0x0C keeps the booster up.
- Power-off is `0x22`=03 (line 457). Deep sleep is `0x10` 01 (line 1096).
- The 0x22 bit meanings (0x0C = display mode 2, no clock or analog enable/disable) come from SSD1681 convention. The SSD1683 text uses a different code table (ssd1683.txt:1532-1585), so this decode is unverified.

**`lut_fast_base` decode (lines 378-393)**, using the SSD1681 153-byte layout: 5 rows of 12 VS bytes, then 12 groups × 7 TP/RP bytes, then FR ×6, XON ×3.
- LUT0 (RAM 00) and LUT3 (RAM 11): all zero, meaning VSS, no drive (lines 379 and 382).
- LUT1 (RAM 01, drive white): bytes 12 and 13 = 0x80, so phase A = 10 = VSL (line 380).
- LUT2 (RAM 10, drive black): bytes 24 and 25 = 0x40, so phase A = 01 = VSH1 (line 381).
- These level codes follow ssd1683.txt:718. Bit order is consistent with `0x26` being the MSB (lines 1-2 of the comment at 375-377, and lines 858-859).
- TP: byte 67 (group 1 TPA) = 0x01. Everything else in that range is 0, and RP = 0 (line 384).
- `EPD_FAST_FRAMES` = 1 (line 312), so `scratch[60]` = 0 and `scratch[68]` = 0 (lines 646-648). The result is exactly 1 drive frame.
  - frames = 2: adds group 1 TPB = 1, whose VS is 00, so it is a VSS rest frame.
  - frames ≥ 3: group 0 TPA = frames-2, giving frames-1 drive frames plus 1 VSS frame (lines 646-655).
- FR bytes 144-149 = 0x22 ×6, which is 50 Hz per ssd1683.txt:728. XON = 0 (line 391).
- Byte 153 EOPT = 0x02.
- Byte 154 VGH = 0x17 = 20 V (ssd1683.txt:1169).
- Byte 155 VSH1 = 0x41 = 15 V.
- Byte 156 VSH2 = 0xB0 = 5.8 V; unused, since no level is 11.
- Byte 157 VSL = 0x32 = −15 V.
- Byte 158 VCOM = 0x28 = −1.0 V (ssd1683.txt:1673). All at lines 391-392.

**Timing**
- `EPD_BUSY_POLLS_SCAN` comment: "panel 20 ms" (line 432).
- `EPD_FRAME_FIXED_US` = 21260 (line 77), which is 47 Hz.
- epd_fast.h:48-49: "26 ms" at 1 frame, "166 ms" at 8 frames.
- Per-pixel budget is 7 scans (lines 310-311), about 140 ms of drive, above the README's 120 ms floor.

**Compared with ours**
- Our encoding is old/new frame (`0x24`=N, `0x26`=N-lag). Theirs is command masks: `0x26` = push black, `0x24` = push white, neither = hold. Because direction is a free per-pixel choice, it does not have to be a frame difference. That is what makes their per-pixel budget and debt accounting possible.
- The voltages are the standard full-swing ±15 V, VCOM −1.0 V. Nothing unusual there.
- Their frames are 2.5× longer than ours (20 ms vs 8 ms), so 7 scans gives 140 ms of drive. Our lag × 8 ms gives much less per step.
- Two small things we could test:
  1. `0x3C`=0x80 (border to VCOM) during fast mode.
  2. The "HOLD ending": one extra scan with both masks all zero after drive stops (lines 1054-1076, `EPD_HOLD_ENDING` at line 318).
- Partial-row windows exist but are off by default (`EPD_PARTIAL_WINDOW` 0, line 307).
- Unknown: how the SSD1681 decodes 0x22=0x0C bit by bit, and the EOPT 0x02 meaning. Neither is in the SSD1683 text.

## pixel-state-machine

SmoothEPD pixel state machine report (angle: pixel-state-machine). All citations refer to the clone at `/private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src`.

**1. Per-pixel state (default driver, V3F/User/epd_fast.c)**
- `s_target[5000]` is a 1bpp copy of the last frame received (c:403). It is overwritten with `next` on every `EPD_FastFrame` call (c:1079-1081).
- `uint8_t s_remaining[40000]` counts the scans each pixel still needs toward its current target (c:404-405).
- `int8_t s_debt[40000]` is black pulses minus white pulses. It is used only by the maintenance passes (c:406-407).
- Two 1bpp masks, `s_mask_black` and `s_mask_white` (c:408-409).
- Budgets are `EPD_BUDGET_BLACK 7` and `EPD_BUDGET_WHITE 7` (c:310-311). The README says the whole driver uses about 40 KB, mostly for these per-pixel arrays (README:27).

**2. Choosing each pixel's drive (`epd_plan_frame`, c:740-791)**
- If a pixel differs from `s_target`, its `s_remaining` is reloaded to the full budget for the new colour (c:761-763). This also happens when it flips back mid-transition.
- While `s_remaining > 0`, the pixel goes into the white mask if its new colour is white, otherwise into the black mask (c:764-770).
- Counters are decremented only after activation (`epd_consume_budget`, c:794-824), which also does `++/--s_debt`.
- After the last driven scan, one extra scan with both masks all zero is sent (`EPD_HOLD_ENDING`, c:318 and c:1054-1076).

**3. RAM encoding**
- RAM 0x26 gets the black mask and RAM 0x24 gets the white mask (c:856-860, also c:727-731). No image data is stored in panel RAM.
- `lut_fast_base` (c:378-393):
  - LUT0 (00) is all zero: hold.
  - LUT1 (01) is `0x80,0x80`: white.
  - LUT2 (10) is `0x40,0x40`: black.
  - LUT3 (11) is zero: hold.
- With `frames=1`, `scratch[60]=0` and `scratch[68]=0` (c:646-648). Only group 1 TP[A]=`0x01` remains (byte 67, c:384), so it is one frame per scan.
- FR bytes are `0x22` x6 (c:391). Trailing bytes: EOPT `0x02`, VGH `0x17`, VSH1 `0x41`, VSH2 `0xb0`, VSL `0x32`, VCOM `0x28` (c:391-392).
- Other settings: 0x37 is ten `0x00` bytes, i.e. no ping-pong (c:676-679). 0x3C=`0x80` (c:681). Activation is 0x22=`0x0C` with the booster kept up (c:865-866).
- Both full planes are sent every scan because `EPD_PARTIAL_WINDOW 0` (c:307).

**4. Updates per transition**
- One transition is 7 scans of 1 controller frame each.
- The scan time is variously given as "26 ms" (h:49), `EPD_FRAME_FIXED_US 21260` (c:77) and 47 Hz (README:22). That makes 7 scans about 150-180 ms, above the README's 120 ms minimum (README:34). An exact ms figure is unknown.
- Counters only drain when frames keep arriving: V5 must keep re-sending the same frame (V3F/User/main.c, comment just above :105).

**5. DC handling**
- Default:
  - Every `EPD_SETTLE_INTERVAL 1000` scans there is one maintenance scan. It gives one pulse to pixels whose debt can be repaid in their displayed colour (`EPD_SOFT_SETTLE_ALL 0`, c:315-316 and c:875-947).
  - A full refresh runs every `EPD_CLEAN_INTERVAL 2000` scans (c:317, c:988-997). The header says 4000 (h:81), which contradicts the code.
- Net variant (epd_fast_net.c.bak):
  - There is no counter and no target state. The only state is `int8_t s_net` (net:402).
  - A pixel is driven toward its current colour whenever `s_net+d` stays within [-7,+7] (net:746-747, 765-769).
  - So a pixel lit for 1 frame then reverted gets 1 frame back, not 7 (README:37). A long-held white pixel turned black can get up to 14 frames.
  - After `FastBegin`, all pixels start at net 0 (net:874), so the first 7 scans drive the whole screen.
  - README:38 says this runs for a very long time but leaves heavy trails.

**6. Compared with our lag trick (0x24=N, 0x26=N-lag)**
- **Steady change:** for a pixel that changes once and then holds, both methods are the same: lag frames of drive vs 7 budget frames.
- **Reverted pixel:** this is the key difference. Take a pixel that goes W to B at step t and back to W at t+2 (lag 7). Ours gives it 2 black frames, then N equals N-lag, so it gets no drive at all. It is left gray with +2 net stress, which matches our trail and residue symptom. SmoothEPD reloads 7 white frames (c:761-763), so the pixel is fully driven back to white. Their default trades exactness of DC for clean visuals; the net variant gives exact DC, so that pixel gets only 2 white frames back.
- **SPI cost:** the same. Both send two full planes per step.
- **Plane meaning:** their planes are explicit black and white masks, not images. That frees the LUT from needing "old vs new" semantics: 00 and 11 are both hold.

**Candidates to incorporate (speculative, not done)**
- **Per-pixel remaining counter:** this replaces N-lag and should remove the reverted-pixel residue. At 120,000 px a byte array is 120 KB, so it would have to be packed. Possible approach: a 3-bit bit-sliced counter, 3 planes of 15 KB each, updated with whole-buffer bitwise ops. Whether that is fast enough in CircuitPython is unknown.
- **Net-clamp variant:** `s_net` within [-7,+7] as a principled DC bound. It could replace or stretch our 4 s balanced wipe.
- **Trailing all-hold scan:** one all-zero scan after driving ends (c:1054-1076). Its benefit is unverified on SSD1683.

## dc-compensation

SmoothEPD's default DC compensation (V3F/User/epd_fast.c, commit 242c5ba)

Repo root: /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src

Bottom line: the default code keeps an exact signed pulse count for every pixel. Every 1000 scans it pays back only 1 unit, and only toward the colour each pixel currently shows. A full refresh every 2000 scans clears the whole count. For us, the useful idea is the per-pixel ledger plus one tiny pay-back scan, run in place of a full refresh.

**1. What it counts per pixel**
- `static int8_t s_debt[EPD_PIXELS]` (c:407), with 40000 pixels (c:320). The comment says it is the black pulses minus the white pulses, used only for maintenance.
- Unit: one fast scan, which is 1 controller frame. `EPD_FAST_FRAMES 1` (c:312); the timing byte is `0x01` at row 5 of `lut_fast_base` (c:383), and `FastPrepareFrames` zeroes bytes 60 and 68 when frames <= 1 (c:647-649). One scan is about 20 ms (c:432) or 26 ms (h:49).
- Counting happens after the scan is sent (`epd_consume_budget`, c:765-794): a pixel in the black mask does `--s_remaining; ++s_debt`, and one in the white mask does `--s_remaining; --s_debt`.
- No limits: there is no clamp or saturation anywhere, so an int8 drift past ±127 would wrap. Whether that can happen in practice is unknown.
- The normal drive budget is separate. On each target change a pixel gets `EPD_BUDGET_BLACK 7` or `EPD_BUDGET_WHITE 7` scans (c:310-311, set at c:739). That is about 140 to 180 ms at 20 to 26 ms per scan, matching the README's ">=120 ms".
- The debt is not used for normal drive decisions (c:406).

**2. How often compensation runs**
- `EPD_SETTLE_INTERVAL 1000` scans (c:315). The check is at c:916-929.
- `s_settle_count` goes up on normal scans (c:961), on HOLD-ending scans (c:987) and on maintenance scans (c:869). It is reset to 0 after every settle attempt, including one that finds nothing to fix (c:920).
- At roughly 47 Hz, 1000 scans is about 21 s. That figure is my estimate; the code gives no time interval.

**3. How it is applied (`epd_maintenance_scan`, c:821-886)**
- It is a single fast scan. A pixel with debt > 0 (net black) is put in the white mask, and one with debt < 0 is put in the black mask (c:837-841).
- With `EPD_SOFT_SETTLE_ALL 0` (c:316), the default, a pixel is only included when the pay-back direction matches its current target colour (`px` bit set = white). Pay-back never pushes against the colour the pixel is showing, so the scan causes no visible change.
- A pixel showing black that has black debt is never repaid by soft settlement. Only the full refresh clears it.
- Each scan repays exactly 1 unit (c:874-884), not the whole debt.
- `s_remaining` and `s_target` are left alone (c:927 comment), so normal drive picks up again on the next frame.
- It uses the same `0x22=0x0C` activate as normal scans (c:813) and counts toward `s_scan_count` (c:868).
- The header comment says `=1` repays every nonzero debt in both directions (h:77-78). That claim holds only per call; the code still repays just 1 unit per call.

**4. Periodic full refresh**
- `EPD_CLEAN_INTERVAL 2000` scans (c:317), checked at c:905. The header comment says "full every 4000 scans" (h:81), which does not match the constant 2000.
- `s_scan_count` also counts HOLD-ending scans (c:986) and maintenance scans, so the full refresh comes slightly sooner than 2000 real frames.
- The refresh is `EPD_SendDisplay(next)` (c:907):
  - reset, load temperature (`0x22=0xB1`)
  - load `lut_full`
  - write the image to both 0x24 and 0x26 (c:618-623)
  - activate with `0x22=0xC7` (c:625-627)
- Time: "measured 1314 ms" (h:42), about 1.3 s (c:628).
- On success it zeroes all of `s_debt` (c:632-634). After that, `EPD_FastBegin` resets the counters and debt (c:888-902), and `EPD_FastPrepare` does a hardware reset, reloads the fast LUT, sets ping-pong off (`0x37`, ten bytes of `0x00`, c:671-674) and turns the booster on.
- `lut_full` (c:352-372) has 4 phase groups with rows 0x80/0x48/0x40 and 0x40/0x48/0x80, and timing rows `0x9`, then `0x5,0x1,0x0,0x5,0x1,0x0,0x3`, then `0x9`. Its tail bytes are `0x22,0x17,0x41,0x0,0x32,0x20`, labelled EOPT VGH VSH1 VSH2 VSL VCOM. The fast LUT tail is `0x02,0x17,0x41,0xb0,0x32,0x28` (c:397-398).
- main.c also does a full refresh after `EPD_IDLE_MS 4000` with no new frame (main.c:20, 105-112). It then waits `EPD_BLANK_DELAY_MS 10000` and does a full refresh to white before sleeping (main.c:21, 128-129).

**5. HOLD ending**
- `EPD_HOLD_ENDING 1` (c:318, 975-990): after driving stops, one all-zero-mask scan is sent over the last row range.

**Compared with our setup**
- Their compensation is weaker per event than our balanced wipe: 1 unit every 1000 scans.
- Their full refresh is much more frequent in scans (2000 scans, about 42 s at 47 Hz, my estimate) and shorter (1.3 s against our 3.3 s OTP refresh), because it uses a custom `lut_full`.
- The idea worth taking: keep an exact signed debt per pixel, and repay it only in the direction of each pixel's displayed colour, which is invisible. That could replace our visible 4 s wipe.
- For us, that ledger costs 120 KB as int8 for 400x300, which is a lot for CircuitPython on the RP2040. Packing it as 4-bit would halve it. Since the RAM 0x26 lag scheme already keeps black and white drive equal, our net debt per pixel may already be close to zero. Whether our gray residue comes from DC imbalance at all is unknown.

## net-limit-variant

Net-limit variant report (V3F/User/epd_fast_net.c.bak compared with V3F/User/epd_fast.c, read with diff only; nothing was built or run)

**Scope of the diff.** The net file is 996 lines and the default is 1100. The waveform/LUT tables, SPI, the 0x22/0x0C activation (net:737-738), the HOLD ending and the full-refresh clean every 2000 scans (`EPD_CLEAN_INTERVAL 2000`, net:315, :905) are the same in both. Only the per-pixel drive rule changes.

**What is replaced.**
- The defines change from `EPD_BUDGET_BLACK/WHITE 7` (fast:310-311) to `EPD_DC_BLACK/WHITE 7` (net:310-311). The comment says per-pixel net drive frames are capped at +7 toward black and -7 toward white.
- Per-pixel state changes from `s_target[]`, `s_remaining[]` and `s_debt[]` (fast:403-407) to a single `int8_t s_net[EPD_PIXELS]` (net:402), clamped to [-7,+7].
- Deleted from the net file: `EPD_SETTLE_INTERVAL 1000` and `EPD_SOFT_SETTLE_ALL 0` (fast:315-316), the whole `epd_maintenance_scan()` (fast:875-946) and its call in `EPD_FastFrame` (fast:1000-1014). That is the default build's "soft settlement": every 1000 scans it drives pixels whose `s_debt` is nonzero back toward zero, but only in the current target colour (`force=0`).
- `EPD_SetPulseBudget` keeps its signature but now sets the net limits, clamped to 1..127 (net:687-700).
- `EPD_FastBegin` no longer copies the target. It only zeroes `s_net` (net:870-882).

**Default rule (fast:752-772).** When a pixel's target changes, it loads a fixed budget: `s_remaining[p] = white ? s_budget_white : s_budget_black`. It then drives that many frames, whatever happened before. A pixel that was black for 2 frames still gets 7 white frames, so `s_debt` drifts. Only the 1000-scan soft settlement and the 2000-scan full refresh correct that drift.

**Net rule (net:744-791).** There is no change detection. On every scan, every pixel is tested against the clamp:
```
const int hi = (int)s_dc_black;  const int lo = -(int)s_dc_white;
const int d = ((px & m) != 0u) ? -(int)s_fast_frames : (int)s_fast_frames;
const int v = (int)s_net[p] + d;
if ((v >= lo) && (v <= hi)) { if (d > 0) mb |= m; else mw |= m; }
```
After the scan is sent, `epd_apply_charge()` (net:798-822) adds `s_fast_frames` per black frame and subtracts it per white frame (net:816, :818). The effects are:
- **Matching erase.** A pixel parked at -7 (white) that turns black for 2 frames ends at -5. When it goes back to white it gets exactly 2 white frames before hitting -7. The erase length equals the earlier on-time, as the README says (README lines 35-36: "if a pixel was only lit for 20 ms before going dark, the dark pulse also lasts only 20 ms instead of the original 120 ms").
- **Long transitions.** A full swing from a saturated colour (-7 to +7) gets 14 frames of drive, not 7.
- **Bounded charge.** Net DC on any pixel can never exceed ±7 frames. No periodic compensation pass is needed, so that code was removed.
- **Start-up drive.** After `FastBegin` zeroes `s_net`, every pixel gets up to 7 frames of drive toward its current colour. These are full-screen scans, because `EPD_PARTIAL_WINDOW 0` (net:308).

**Tradeoff from the README.**
- README line 37: in testing, the net-limited approach "supports very long periods of fast refresh, but because ink particles have inertia, the smearing/trailing is very heavy". The short erase does not fully move the particles back, so moving objects leave trails.
- README line 39 calls the default approach "limited compensation effect, but minimal impact on display quality".
- README line 42 rejects one more option: a periodic all-pixel DC compensation wipes the content and needs a normal refresh after it, so the author sees little point in it.
- Neither file contains any measurement (residue levels, panel life). Unknown.

**What this means for our SSD1683 driver.**
1. Our lag scheme (RAM 0x24 = frame N, RAM 0x26 = frame N-lag) gives equal drive toward black and white whatever the history. That is close to their default fixed-budget rule, minus the target-colour soft settlement. Their net variant is the history-aware alternative. On their 200x200 panel it produced the gray residue and trails we already see, so it is not a fix for our trails.
2. A per-pixel `int8` net counter would cost 120 KB at 400x300. On the RP2040 under CircuitPython that RAM is a big problem, and the masks would have to be built per pixel in Python, not by RAM-plane tricks. That fits poorly with our SPI-bound 36 fps.
3. Their default soft settlement (fast:875-946, every 1000 scans) adds DC-correcting frames only for pixels whose correction goes the same way as the colour they show. It never erases content. That could replace our hidden-object balanced wipe every 4 s without the visual break. It needs a per-pixel debt counter, though; whether a 2-bit or row-coarse approximation would be enough is unknown.
4. Both of their builds keep a full refresh every 2000 fast scans (about 43 s at 47 Hz), compared with our OTP refresh every 15 s.

## throughput-pipeline

SmoothEPD reaches 47 Hz mainly because its panel BUSY time is about 20 ms per step and its SPI share is small. It does not overlap SPI with BUSY, and it sends the full 2 x 5000 B frame every step.

**SPI and DMA**
- The SPI1 prescaler is "Mode0" = /2 on the 100 MHz HB2 bus, so about 50 MHz (epd_fast.c:58-61). The comment admits this is above SSD1681's 20 MHz limit ("试过就算是/2也能用", "tried, works even at /2"). I could not confirm the HB2 clock is 100 MHz. system_ch32h417.c:20 only shows V3F core at 100 MHz.
- Writes of 256 B or more go through DMA1 Ch3 via DMAMUX request 63 (epd_fast.c:67-73, 262-282). The CPU blocks while the DMA runs (epd_fast.c:144-184). Commands are sent one byte at a time, with CS toggled per byte (epd_fast.c:127-142).

**Bytes per update**
- `EPD_PARTIAL_WINDOW 0` (epd_fast.c:307), so every scan writes the full 0x26 black mask plus the full 0x24 white mask: 2 x 5000 B (epd_fast.c:1042-1043, 856-860).
- A row-window path exists (epd_fast.c:828-837) but is turned off. Column windowing was never made to work (epd_fast.c:1018-1020).
- At 50 MHz, 10,000 B is about 1.6 ms of wire time.

**Waveform and BUSY time**
- The fast LUT is 1 frame (lut_fast_base, epd_fast.c:378-393). FR bytes 144-149 are 0x22, VGH is 0x17, VSH1/VSH2/VSL are 0x41/0xB0/0x32 and VCOM is 0x28 (epd_fast.c:391-392).
- I could not find the SSD1681 FR table. If it matches SSD1683 Table 6-7 (ssd1683.txt:726-731), FR=2 means 50 Hz, so 20 ms per frame. That fits the "20 ms" comments (epd_fast.c:432, epd_fast.h:84). epd_fast.h:49 says 26 ms, which conflicts.
- The booster is powered once with 0x22/0xC0 (epd_fast.c:466-475, 684) and each scan triggers with 0x22/0x0C (epd_fast.c:863-869). Ping-pong is off via 0x37 x10 zeros (epd_fast.c:676-679).
- Their panel steps at about 50 Hz. Ours steps at 125 Hz with 8.1 ms BUSY.

**BUSY wait**
- `EPD_WFI 0` (epd_fast.c:428), so it busy-polls. The EXTI falling-edge wakeup is set up (epd_fast.c:222-234, 287-293) but not used.
- Timeouts are 20M polls per scan and 200M for long operations (epd_fast.c:431-432).

**What overlaps with BUSY**
- `epd_activate()` returns right away and sets `s_pending` (epd_fast.c:863-869).
- On the next call, `epd_plan_frame()` (a 40,000-pixel budget/mask pass) runs before `EPD_FastSync()` (epd_fast.c:1016 vs 1026). The comment at 1025 says RAM cannot be written while BUSY is high.
- `epd_consume_budget()` runs after activate, also during BUSY (epd_fast.c:1053).
- So computation of N+1 overlaps BUSY of N. SPI transfer does not.

**Dual-core split**
- The V5F core (400 MHz) runs the simulation and drawing. Its `EPD_FastFrame` just memcpys 5000 B into a shared A/B slot at 0x20170000 (epd_producer.c:98-114, epd_share.h:22, 30-39).
- `write_seq`/`read_seq` act as a counting semaphore with a depth of 2. If both slots are full, the producer drops the frame and counts it rather than overwriting (epd_share.c:31-50). Fences are `fence rw,rw` (epd_share.c:9-12). An IPC CH0 bit1 flag is set but the consumer polls (epd_share.c:5-7, main.c:99).
- The V3F core (100 MHz) runs peek, `EPD_FastFrame`, release (main.c:99, 176, 185). The producer paces itself with `Delay_Ms(7)` (fluidDemo.c:285).
- The README says the stopwatch demo also works single-core on CH32V303 (README.md:26-27).

**Time budget estimate (from code)**
- BUSY about 20 ms, plus SPI about 1.6 ms, plus command bytes, minus plan/consume (hidden in BUSY).
- The code's own constant is `EPD_FRAME_FIXED_US 21260u` (epd_fast.c:77). 1e6 / 21260 = 47.04 Hz, which is very likely where "47 Hz" comes from.
- Cross-check: the comment says hold = 11000 µs gives about 30 fps, implying about 22.3 ms fixed (epd_fast.c:1033-1034).

**Where 47 Hz appears**
- Stated in README.md:22.
- Measured at runtime by V3F: `cons_fps` (main.c:189-199). It is drawn on-panel as '3' (fluidDemo.c:282).
- main_epd_demo.c.bak:233 says "45 fps".
- No logged measurement is in the repo.
- Caveat: V3F's counter increments even when a frame drives nothing (main.c:176-186).

**Possibly useful for us**
1. Their 47 Hz is BUSY-bound at about 50 Hz FR with 10 KB per step. Ours is SPI-bound (30 KB at 15.6 MHz). Their unfinished row-band windowing (epd_fast.c:516-534, 828-837) is the obvious fix for the small-sprite case. Note their comment that cursor X must be 0 (epd_fast.c:529).
2. Do the per-pixel planning before waiting on BUSY, and the bookkeeping right after the trigger (epd_fast.c:1016-1053). In CircuitPython that means computing frame N+1 before polling BUSY.
3. If our RP2040 SPI exceeds the 20 MHz spec (ssd1683.txt:2430), as they do at about 50 MHz, our 30 KB step could get much shorter. Untested on SSD1683, so this is unknown.
4. An A/B double buffer that drops frames rather than blocking the producer (epd_share.c:31-42) would fit RP2040's second core. CircuitPython does not expose it.

Files: /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src/V3F/User/epd_fast.c, .../V3F/User/main.c, .../Common/Common/epd_share.c, .../V5F/User/epd_producer.c

## grayscale-and-content

SmoothEPD does not do grayscale; it is strictly 1-bit black and white. The useful part of its demos is how they shape content so each pixel gets its full drive before it changes again.

**Grayscale: none**
- `V5F/User/epd_fast.h:6` says "black and white only". The frame is 1 bpp (bit 1 = white, bit 0 = black) at `epd_fast.h:8-9`.
- The repo has no hits for gray, grey, dither, bayer or shade. The only "level" hits are the comments on the LUT level rows (`V3F/User/epd_fast.c:327,376`).
- The README says inkboy did 4-gray (`README.md:15-16`). SmoothEPD does not carry that over.
- The fast LUT has one drive row toward white (`0x80,0x80`, `epd_fast.c:380`) and one toward black (`0x40,0x40`, `epd_fast.c:381`). Both hold rows are zero (`:379,:382`). It is 1 controller frame (`epd_fast.c:384`, `EPD_FAST_FRAMES 1` at `:312`). There are no intermediate drive levels.
- Each pixel gets a fixed pulse budget of 7 toward black and 7 toward white when its target changes (`EPD_BUDGET_BLACK/WHITE 7`, `epd_fast.c:310-311`; reload at `:761-762`). If content flips a pixel before its budget runs out, the pixel is left part-way: an accidental gray, not a feature.
- The authors treat gray as a defect. `stopWatch.c:44` says, in effect: "update digits every 7 frames; faster turns gray (each pixel needs about 7 frames of drive)".
- One scan is about 21 ms (`EPD_FRAME_FIXED_US 21260u`, `epd_fast.c:77`), so 7 pulses is about 149 ms. That fits the README's figure of at least 120 ms per transition (`README.md:34`).

**What the demos show and how they draw them**
- `V5F/User/main.c:6` runs `fluidDemo()`; `stopWatchDemo()` is commented out on line 7.
- **stopWatch.c**
  - Content: a 3x5 block-font stopwatch with each font dot drawn as an 8x8 block (`CELL 8`, `:24,:73-95`), plus an fps counter at half size.
  - Around it a "snake" runs on a rectangular ring. Four hollow circles and squares drift, and a dashed border crawls.
- **fluidDemo.c / SandSim.c**: a 64x64-cell PIC/FLIP fluid with 2500 particles (`SandSim.h:10-14`; the README says 2300). It also draws an acceleration arrow and fps text in Fixedsys 8x10.
- **main_epd_demo.c.bak** is the older single-core stopwatch with the same drawing code.

**Content tricks against ghosting and gray**
1. **Content change rate matches the drive budget.** Digits update only every `DIGIT_DIV 7` frames (`stopWatch.c:44,380-382`), the same as the 7-pulse budget.
2. **Motion of at most 1 px per frame.** `SNAKE_STEP 1` is commented "1 is most stable (each pixel gets enough pulses)" (`stopWatch.c:43`). The dashed border moves 1 px every 3 frames (`stopWatch.c:325`).
3. **Thick strokes.**
   - The snake body is 2x2 for the first 2/3 of its length and 1 px only at the tail (`stopWatch.c:150-154`). The head is 4x4 (`:160`).
   - The arrow is drawn with a 2x2 brush along a Bresenham line (`fluidDemo.c:92-124`).
   - Circle rings are about 3 px wide and squares 2 px (`stopWatch.c:198,221`, with `SHAPE_STROKE 1`). The comment at `:165` says thin lines gray most easily.
4. **Positions snap to a coarse grid.** Particles are rounded to their 2 px cell (`fluidDemo.c:187-188,206-207`) and drawn as 4x4 blocks, so neighbours overlap and the fluid reads as a solid mass (`:19-21,209-215`). A pixel changes only when a particle crosses a cell.
5. **Slow physics on purpose.** `dt 0.010f` is commented "particles a bit slower, give enough time to drive white/black" (`SandSim.h:16`).
6. **The producer is throttled.** There is a 20 ms delay per frame in `stopWatch.c:387` and 7 ms in `fluidDemo.c:285`. `epd_producer.c:93-95` says, in effect: "don't send frames too fast, keep content continuous, otherwise charge imbalance, especially fast-moving thin lines; slow the motion or shorten the full-refresh interval". `README.md:45` says the same: use slow-moving blocks and avoid fast changes and thin lines moving fast sideways.
7. **Clean shutdown** (`main_epd_demo.c.bak:455-485`):
   - 2 s more of new frames, then 1 s of identical frames so the remaining budgets and HOLD scans drain.
   - Then a full refresh and sleep.
   - `V3F/User/main.c:20-21,104-140` does the same on the dual-core build: after 4000 ms with no new frame it runs a full refresh, waits 10 s, refreshes to white, then sleeps.
8. **Minor bug:** `SHAPE_SLOW` is defined (3 in `stopWatch.c:236`, 2 in `.bak:234`) but never used, so the comment's slowdown is not applied.

**What we could use**
- **Gray:** nothing to borrow. Their gray is the same unfinished-drive problem we see as trails.
- **Match content updates to drive length.** Our equivalent of their 7-frame budget is our `lag`. Change any pixel at most once every `lag` frames. Move the sprite at most 1 px per step, or snap it to a grid that moves only every `lag` frames.
- **120 ms at our 8.1 ms/frame is about 15 frames.** If our `lag` is lower than that, the README suggests it is too short for full transitions. I did not check our `lag` value.
- **Stroke width and blocks.** Use strokes of at least 2 px and solid blocks, with no 1 px edges moving sideways.
- **Shutdown.** Push identical frames until everything has drained, then do the full refresh.
- **Not covered by these demos:** what each mask bit sends to the panel, and how the `s_debt` compensation and `epd_fast_net.c.bak` work.

## api-and-lifecycle

SmoothEPD api-and-lifecycle report (clone at .../scratchpad/smoothepd-src, read only, nothing executed)

**Public API** (V3F/User/epd_fast.h)
- Setup: `EPD_Hal_Init`, `EPD_Init` (h:37-38).
- Full refresh: `EPD_SendDisplay(image)`, commented as "measured 1314 ms" (h:43).
- Fast mode: `EPD_FastPrepare` / `EPD_FastPrepareFrames(n)` (h:53-54), `EPD_FastBegin(shown)` (h:82), `EPD_FastFrame(next)` (h:86) and `EPD_FastSync` (h:89).
  - `EPD_FastFrame` is non-blocking. It triggers the update and returns; the next call waits on BUSY before writing RAM (epd_fast.c:1026-1029).
  - It returns 1 when it drove, 0 for hold-only, -1 on timeout (h:70-71).
- Tuning: `EPD_SetPulseBudget(black, white)`, pulses per transition, default 7/7 (h:57, c:310-311). `EPD_SetTargetFps` gives hold = 1e6/fps - 21260 us (c:77, c:708-714).
- Other: `EPD_TakeTimeoutFlag` (read-clear, h:95) and `EPD_Sleep` (h:99).
- V5F/User/epd_fast.h is the same API proxied over shared memory. On V5F, Init, SendDisplay, Begin, Prepare and Sleep do nothing (epd_producer.c:7-8). V5F/User/main.c:6 just calls `fluidDemo()`.

**Startup** (V3F/User/main.c)
- `EPD_Hal_Init`, then a 20 ms delay (main.c:83-84).
- On the first frame, `epd_restart_fast` (main.c:43-52, 158-168) runs `EPD_SendDisplay` (a full refresh) then `EPD_FastBegin` and `EPD_FastPrepare`. So yes, there is always an initial full refresh.
- `EPD_SendDisplay` (c:574-636) does:
  - reset, SW reset 0x12, 0x01=C7 00 01, 0x11=01, 0x3C=0x01, 0x18=0x80 (internal sensor)
  - 0x22=0xB1 + 0x20 to load temperature (c:605-607)
  - then loads custom `lut_full` over 0x32 (c:349-373; EOPT 0x22, VGH 0x17, VSH1 0x41, VSH2 0x00, VSL 0x32, VCOM 0x20)
  - writes the image to both 0x24 and 0x26, then 0x22=0xC7 (c:626-628)
  - zeroes the per-pixel debt counter (c:632-634)
- `EPD_FastPrepareFrames` (c:638-685) does:
  - hardware reset only, no 0x12 (c:657)
  - 0x18=0x80
  - loads `lut_fast_base` (c:378-393)
  - 0x37 followed by ten 0x00 bytes (c:676-679)
  - 0x3C=0x80
  - `epd_analog_on`: 0x22=0xC0 (c:466-475), so the booster comes up once
- Each fast step is 0x22=0x0C, 0x20 (c:863-868): display with the booster kept on. This is the same trick as our ping-pong-off plus held analog.

**Refreshes during a run** (all inside `EPD_FastFrame`)
- **Full clean:** every `EPD_CLEAN_INTERVAL` = 2000 fast scans it calls `EPD_SendDisplay(next)`, then FastBegin and FastPrepare (c:317, 988-996). The header comments say 4000 (h:81); the code says 2000. At 47 Hz that is about 43 s.
- **Soft settlement:** every `EPD_SETTLE_INTERVAL` = 1000 scans, one scan drives each pixel with nonzero `s_debt` one pulse in the repaying direction (c:315, 875-940, 1000-1012).
  - `s_debt` is an int8 per pixel counting black pulses minus white pulses (c:402-403, 935-942).
  - With `EPD_SOFT_SETTLE_ALL` = 0 (c:316), it only repays pixels whose repay direction matches the color currently shown, so the image is not disturbed.
- **HOLD ending:** after the last driven scan, one extra scan with both planes all zero (c:1053-1076, `EPD_HOLD_ENDING` = 1 at c:318).
- **Timeout recovery:** if `EPD_TakeTimeoutFlag` is set, main calls `epd_restart_fast` again, which is a full refresh plus re-prepare (main.c:178-184).

**Shutdown and panel safety** (main.c:105-150)
- After 4000 ms with no new frame (`EPD_IDLE_MS`, main.c:20), it does a full refresh of the last frame.
- It waits 10 s (main.c:21), does a full refresh to white (0xFF), then calls `EPD_Sleep`.
- `EPD_Sleep` (c:1085-1098) waits for BUSY, then `epd_analog_off` (0x22=0x03 then 0x20, c:452-464), then 0x10=0x01 (deep sleep mode 1), then 100 ms.
- `epd_reset` always turns analog off before toggling RST: 50 ms high, 20 ms low, 50 ms high (c:477-488, 313-314).
- The BUSY waits have poll-count timeouts: 200,000,000 polls for long operations and 20,000,000 per scan (c:431-447).

**Temperature**
- It is read only during a full refresh (0x22=0xB1). The custom LUT then overwrites the OTP waveform anyway.
- There is no temperature compensation in the fast path and no 0x1A or 0x1B use (no grep hits). Whether this is deliberate is unknown.

**What we could use**
1. Per-pixel signed pulse-debt accounting with periodic same-direction repayment. This is the closest analog to our gray-residue problem and costs no visible flash.
2. Clean refresh by scan count, not wall time.
3. Fixed-shape hold or "discharge" scan after motion stops.
4. Panel-safe shutdown before any deep sleep: blank to white, analog off (0x22=0x03), then 0x10=0x01. Reset always analog-off first.
5. A BUSY timeout that falls back to full reinit.

Their fast LUT uses VSH1 0x41, VSL 0x32, VCOM 0x28 (c:391-392). That differs from ours; I did not compare further.

## inkboy-upstream

InkBoy research: kuslota/InkBoy, upstream of SmoothEPD (web sources plus the repo's main branch, read 2026-10-28)

The repo source was read to stdout only. No files were written and nothing was built. The commit SHA is unknown; the root tree SHA is 823265ea5a9307749e5f61ea07eb7a40df793cc8.

**Sources**
- Repo: https://github.com/kuslota/InkBoy (MIT). A controller repo is at https://github.com/kuslota/inkboy-controller.
- Author: "Bo Made It" on YouTube; demo at https://www.youtube.com/watch?v=XiZmM6hwwAU.
- Press coverage: theregister.com/a/5303394, timeextension.com (2026-10-19), securitylab.ru/news/578859.php.
- None of these mention a bilibili post. Whether one exists is unknown.

**Supported hardware**
- Only the Waveshare ESP32-S3-ePaper-1.54 V2: 200x200 SSD1681, with an AO3401 panel power switch.
  - README; `components/ssd1681_fast/ssd1681_fast.c:26-28`; `include/ssd1681_fast.h:7-9`.
- No other panels are listed.
- The waveform tables are copied from Waveshare `EPD_1in54_V2.c` (`ssd1681_vendor_tables.h:1`).

**How 30 fps works**
Source: `docs/how-it-works.md`; register details from the files cited below.
- The stock partial update is 17 frames, about 360 ms. InkBoy uses one active frame instead: about 20 ms in dithered mode and about 14 ms in grayscale.
- Analog power stays on between scans, which saves about 90 ms per update:
  - Power on with 0x22 = 0xC0 (`ssd1681_fast.c:428`).
  - Each scan uses 0x22 = 0x0C with no power on/off bits (`:580`).
  - Power off is 0x03 (`:327`).
- RAM is used as explicit per-pixel masks, not as current and previous images:
  - Black mask goes to 0x26, white mask to 0x24 (`:578-579`).
  - Row codes are 00 HOLD, 01 white, 10 black, 11 special (`include/ssd1681_gray_waveform.h:17-18`).
  - The driver checks that the masks are disjoint (`:646`, `:653`).
- 0x37 is sent as ten 0x00 bytes, so ping-pong is off (`:421-425`). Border 0x3C = 0x80 (`:426`).
- The LUT is the Waveshare partial LUT (`ssd1681_vendor_tables.h:21-35`), patched in `vendor_load` (`ssd1681_fast.c:364-374`):
  - Bytes [1] and [37] are zeroed and [60] (group 0 TP) is set to 0.
  - [68] is set to 0, which drops group 1's VSS phase B.
  - Low bits of [144] are set to FR code 2 (dithered) or 7 (gray) (`fast_display.c:227`).
  - That leaves one frame in group 1 phase A: LUT1 = 0x80 (VSL, white) and LUT2 = 0x40 (VSH1, black).
- Source voltages are stock 0x04 = {0x41, 0xB0, 0x32} and VCOM 0x2C = 0x28 (`vendor_tables.h:34-35`).
- SPI runs at 20 MHz during play and 10 MHz otherwise (`ssd1681_fast.c:94`, `ssd1681_fast.h:10`). Each 5,000-byte plane is sent at that rate.
- Pacing is a fixed 33.334 ms slot that always takes the latest emulator frame (59.7 fps). Missed slots are skipped. Dithered mode does one scan per slot; gray mode does two.

**Per-pixel budget (dithered mode)**
- When a pixel's target changes, it gets a pulse counter: Black and White pulses, each 1-8, default 8 (`docs/tuning.md`).
- Each delivered scan decrements the counter. Failed transfers don't consume budget.
- After drive ends, one final all-HOLD scan runs (`fast_display.c:338`, `:401`).

**4-gray method**
- Each of the 12 K/D/L/W transitions has its own dose count. Defaults (how-it-works.md):
  - K→D 2, K→L 4, K→W 7
  - D→K 4, D→L 1, D→W 6
  - L→K 4, L→D 1, L→W 5
  - W→K 7, W→D 3, W→L 2
- Each transition also has a HOLD flag.
- A per-pixel model tracks the estimated level and doses left. A mid-drive retarget scales from the level actually reached.
- History corrections: by default the L→K→L round trip gets -1 dose, and a reversal gets 150%.
- "Lighten" can weaken the white drive by setting VSL to 0x32, 0x2A, 0x22 or 0x1A (-15/-13/-11/-9 V) (`ssd1681_fast.c:383-390`).
- The special row 11 can use VSH2 at 0x2D (11 V) or 0xCE (8.8 V) (`ssd1681_gray_waveform.h:20-25`). It fixes "dark stains behind moving white objects" (`tuning.md`).

**Results and caveats (as stated)**
- About 30 fps, versus 3.33 fps with the stock driver (Register). Busy scenes can drop below 30.
- Grayscale "can leave faint trails" (README).
- Warning: "Custom waveforms and high refresh rates may cause permanent image retention or panel damage". Panel life "has not been validated".
- No DC-balance accounting appears in the driver.
- A full refresh only happens at start and finish (`fast_display.c:223`, `:256`).
- In gameplay, `continuous_play` turns off both the 2,402-update cap and the 2,400-update clean interval (`ssd1681_fast.c:164`, `:171`; `ssd1681_fast.h:12-13`). So there is no periodic clean during play.
- The driver allows only certain commands and never sends 0x30, the OTP waveform-programming command (`ssd1681_fast.c:15-16`, `:105-114`).

**What we could use**
1. **Unequal drive instead of equal black/white.** Their fix for residue is to tune white and black separately: per-transition doses, lower VSL, and a weaker VSH2 row. Our gray build-up may come from white and black pulses not being equally effective. Lowering VSL on our panel via 0x04 is worth testing; the SSD1683 allows VSL from -5 to -17 V in 500 mV steps (`research/ssd1683.txt:156`). Equal pulse counts are DC balanced but may not be balanced optically.
2. **Explicit masks instead of frame N vs N-lag.** Per-pixel counters make each pixel's drive length independent of the global lag, and add a final HOLD scan.
3. **Keep analog power on with 0x22 = 0x0C.** Check whether our update control byte already does this (unknown from here).
4. **Fixed-slot pacing that always takes the latest frame.**
5. **Doses scaled by history.** It is their answer to round-trip ghosting.

They do not solve long-term drift with any periodic wipe, so our 4 s and 15 s cleans have no counterpart there.

## smoothepd-public

I found no outside discussion of SmoothEPD itself: no Bilibili video, forum thread, Hackaday post or criticism. Its README results are the author's own claims, unchecked by anyone else. The most useful outside find is a separate 2026 SSD1683 project with a burn-in write-up that matches the gray residue we see.

**SmoothEPD and its author** (from the GitHub API and https://github.com/PinkiePie1/SmoothEPD):
- **Activity:** the repo was created 2026-10-25 09:05Z and has 4 commits (b9597a9, 2fc5fe7, 2c2c8f4, 242c5ba). The net-charge variant came in 2c2c8f4: "update readme and add net charge constrained update method".
- **Reception:** 48 stars, 9 forks and 0 issues ever filed. The forks show no visible changes.
- **Author:** the account name is "WizardCat", created 2014, with 16 public repos. Most are WCH CH32 toolchain work (CH32V203Dev has 25 stars, ch572dev has 12). There is also a FLIP fluid simulation repo, FLIP_MCU, which is where the particle demo comes from. No Bilibili account or blog is linked.
- **Claims (README only):**
  - 47 Hz on a 1.54" SSD1681 panel.
  - A 0.01 s stopwatch and a 2300-particle fluid demo.
  - About 40 KB of RAM for a 5 KB panel.
  - The driver was "vibe coded" and then reviewed by hand.
  - Pixels need at least 120 ms of drive, and periodic normal refreshes are needed against ghosting.
  - Avoid fast thin horizontal lines.
  - Other panel sizes "should theoretically" work, but none were tested.
- **Not reported anywhere:** lifetime or ghosting measurements, and video evidence. Searches in English and Chinese for "SmoothEPD", "PinkiePie1" and "47帧" turned up only the GitHub page.

**InkBoy, the project it builds on**
- **Repo:** https://github.com/kuslota/InkBoy, created 2026-10-12, 140 stars. It runs on an ESP32-S3 with a Waveshare 1.54" 200x200 V2 panel at "about 30 fps", with 4 grays made by stopping transitions partway ("deliberate ghosting").
- **Waveform:** the fixed waveform tables come from Waveshare's e-Paper library. The tuning knobs it names (pulse counts, HOLD, history corrections) have no values given.
- **Its own warnings:** "may cause permanent image retention or panel damage" and "Long-term panel life has not been validated."
- **Coverage:**
  - Hackaday: https://hackaday.com/2026/10/14/tiny-e-paper-display-delivers-30-fps-of-game-boy-fun/
  - Time Extension: https://www.timeextension.com/news/2026/10/homebrew-inkboy-project-looking-to-bring-game-boy-games-to-e-paper-displays
  - Video: https://www.youtube.com/watch?v=XiZmM6hwwAU
- **Criticism (Hackaday comments):**
  - Bart Zuidgeest: "e-ink has a max cycle count... At this frame rate, you have 10 to 20 hours of play time guaranteed by datasheet."
  - Another commenter: "There are good reasons these things mostly run slow."
  - helge raised temperature compensation, which none of these projects mention.
- **Original idea:** Wenting Zhang's PaperBoy S3 (https://www.tomshardware.com/video-games/retro-gaming/designer-turns-niche-e-ink-dev-board-into-a-60hz-game-boy-handheld-960x540-display-powered-by-ultra-low-cost-esp32-s3-microcontroller). It drives a raw parallel 960x540 panel at 60 Hz and only touches changed pixels. That panel has no SSD controller, so it doesn't carry over to our SPI panel directly.

**Fastwave-Eink-Driver, the 2026 SSD168x project most relevant to us**
https://github.com/bootdsc/Fastwave-Eink-Driver, created 2026-08-22, last pushed 2026-10-12.
- **Measured times:**

  | Panel | Controller | Vendor partial | This driver |
  |---|---|---|---|
  | 5.79" 792x272 (cascaded) | SSD1683 | 336 ms | 48–89 ms |
  | 4.26" 800x480 | SSD1677 | 540 ms | "30 ms up" (as printed) |
  | 1.54" | SSD1681 | 363 ms | 72 ms |

  The 1.54" streams at 34 fps with drive 2. It does not test a 4.2" 400x300 panel.
- **Timing:** "BUSY = frames x frame period, and content does not affect it." It also says raising the rails once and then sending bare DISPLAY bytes removes the vendor sequence's +91 to 124 ms overhead.
- **Register 0x22:** bit 4 reloads the OTP waveform, which overrides a custom LUT.
- **Burn-in notes** (docs/BURN-IN.md), which bear directly on our trails:
  - Unchanged pixels get a "skipped LUT phase: source parked at VSS against a negative common," which is a small DC field on every update. VCOM 0x08 (-0.2 V) "stopped whole-panel darkening."
  - About 1 hour of streaming with static white letterbox bars left visible burn-in in the bars only.
  - "A pixel that went black-to-white and then sat still can also park grey", and a later differential frame will not finish it.
  - "Driving white onto already-white darkens", so a white top-up was rejected.
  - Clearing takes vendor full refreshes. A differential update "will not lift a stain".
  - Never go above ±17 V (VSH1=0x4B, VSL=0x3A).
  - Lifetime: "One minute of video here is on the order of that entire five-year budget" for a signage panel.

**What could be useful for us** (suggestions only, nothing tested):
1. Fastwave's VCOM 0x08 offset and its note about the unchanged-pixel phase are a likely cause of our gray build-up. We should check what VCOM our LUT uses and what our unchanged-pixel (BB/WW) groups drive.
2. Its "parked gray" finding supports our periodic balanced wipe plus an OTP full refresh. It suggests a differential fix alone won't be enough.
3. No public source backs SmoothEPD's 47 Hz, its lifetime, or its ghosting behaviour, so its net-stress method still needs the code read and testing on our panel.
4. None of these projects reports measured panel lifetime or temperature compensation. "Unknown" is the honest answer on lifetime.

## ssd1681-vs-ssd1683

SSD1681 vs SSD1683 portability report (angle: ssd1681-vs-ssd1683)

**Summary.** Their RAM and LUT polarity is the same as ours, so it ports with no LUT change. The LUT byte layout, RP/SR meaning, FR placement and the per-pixel state cost do not port directly. The biggest finding is that each of their transitions gets about 7 × 20 ms of drive, which is roughly 3x what our lag=6 gives at 125 Hz.

**Same polarity, so it ports directly**
- **RAM-to-LUT selection is identical.** SSD1681 L1 is R=0/BW=1 and L2 is R=1/BW=0 (ssd1681 Table 6-5). Their fast LUT sets L1 bytes 12-13 to 0x80 (phase A = VSL, "drive white") and L2 bytes 24-25 to 0x40 (VSH1, "drive black") (epd_fast.c:380-381). They write the black mask to 0x26 and the white mask to 0x24 (epd_fast.c:858-859). Our make_lut puts VSH1 in LUTBW (84) and VSL in LUTWB (126) (teapot_demo.py:112-113, 121).
- **Their mask scheme would run on our existing LUT unchanged.** Write mask_white to 0x24 and mask_black to 0x26. 00 and 11 select our VSS LUTs, which hold.
- **Booster kept up.** Same pattern as ours: 0x22=0xC0 once (epd_fast.c:466-470), then 0x22=0x0C per scan (epd_fast.c:865-867). We use 0xCC then 0x0C (teapot_demo.py:129, 134).
- **Voltages are nearly the same.** Theirs: VGH 0x17, VSH1 0x41, VSL 0x32 (epd_fast.c:391-392). Ours: 0x17, 0x41, 0x32. Only VSH2 (0xB0 vs our 0xA8, unused) and VCOM (0x28 vs our 0x30) differ.
- **0x37.** They send ten 0x00 bytes (epd_fast.c:676-679), which turns ping-pong off (F[6]=0) on both chips. We also set Display Mode 2 for the WS bytes (NO_PINGPONG). Effect of that difference: unknown.

**Needs translation**
- **LUT layout.**
  - SSD1681 has 153 bytes in 0x32 plus 6 more through 0x3F/0x03/0x04/0x2C (159 total). VS fields are packed 4 phases per byte (bytes 0-59). TP is a separate 8-bit byte, 0-255 frames (bytes 60-143).
  - SSD1683 has 227 bytes. Each byte is VS[7:6] plus TP[5:0], so a phase is at most 63 frames (ssd1683.txt:669-683, Fig 6-7).
- **Repeat counts differ.** SSD1681 RP/SR = 0 means repeat once. SSD1683 RP/SR = 0 skips the group (ssd1683.txt:690). Their RP[0]=0 (epd_fast.c:384) must become 1 on our chip, which our make_lut already does.
- **Frame rate placement.** SSD1681 has a separate FR per group, packed two 4-bit values per byte at bytes 144-149 (range 0-7, rated 25-200 Hz). Theirs are all 0x22. SSD1683 has one global FR at byte 224, with 0x05 = 125 Hz as the maximum (Table 6-7).
- **SSD1681 FR-to-Hz table is unknown.** Rev 0.13 does not include one. Their timing implies about 50 Hz: 1 frame takes 26 ms and 8 frames take 166 ms (epd_fast.h:49), so (166-26)/7 ≈ 20 ms per frame.
- **EOPT.** Theirs is 0x02, the SSD1681 POR value, which has no documented meaning (epd_fast.c:391; ssd1681 0x3F table). Ours is 0x07. SSD1683 only documents 0x22 and 0x07.
- **Frame count.** EPD_FastPrepareFrames patches TP[0A] at byte 60 and TP[1B] at byte 68 (epd_fast.c:647-657). The default is EPD_FAST_FRAMES=1 (epd_fast.c:312). The SSD1683 equivalents are byte offsets inside each 42-byte LUT block.
- **SSD1683 adds** 3-color/BW mode selection by 0x22 and a VCOM "floating" level for VS=11. **It lacks** per-group FR and FR above 125 Hz.

**Drive energy (most actionable)**
- Their budget is 7 black and 7 white scans per target change (epd_fast.c:310-311), at about 20 ms per scan (epd_fast.c:77, EPD_FRAME_FIXED_US 21260). That is about 140 ms per transition, matching the README's "≥120 ms" (README.md:34).
- Ours is lag × one 8 ms frame at 125 Hz, so about 48 ms at lag=6.
- **Hypothesis, untested:** our gray residue may be under-drive, not imbalance. To test, try nf=2-3 frames per step or lag ≈ 15 at 125 Hz.
- **Behaviour difference.** When a pixel's target changes, they reload the full budget toward the new colour (epd_fast.c:761-763). With our lag method, a pixel that flips and flips back within `lag` steps has N == N-lag, so it gets no drive at all.

**Throughput: 200x200 vs 400x300**
- They send 2 × 5000 B per scan, always the full screen (EPD_PARTIAL_WINDOW 0, epd_fast.c:307). This goes by DMA at SPI /2 of 100 MHz, about 50 MHz (epd_fast.c:57-61), which is above the 20 MHz in the datasheet. That is about 1.6 ms on the wire against about 20 ms of panel time, so they are panel-bound at 47 Hz.
- We send 2 × 15000 B. At our real 15.625 MHz that is about 15.4 ms on the wire plus 8.1 ms BUSY, about 23.5 ms per step (about 42 fps ceiling, 36 fps measured), so we are SPI-bound.
- **Per-pixel state does not fit in CircuitPython.** They keep s_remaining (uint8) and s_debt (int8) per pixel (epd_fast.c:398-401): 80 KB at 200x200, 240 KB at 400x300. That exceeds our CircuitPython heap. A per-pixel loop over 120k pixels in Python per step is also not viable. A port would need 3-4 bit packed bit-planes with whole-byte bitwise ops, or a native C module. Feasibility of either: unknown.

**Also worth porting**
- A one-scan all-zero "HOLD ending" after a change finishes (EPD_HOLD_ENDING, epd_fast.c:318).
- Debt-directed maintenance scans that drive only pixels whose net debt is nonzero (epd_fast.c:874-946), instead of our blind full-screen wipe.

**Source:** the SSD1681 datasheet (Rev 0.13), from https://cdn.shopify.com/s/files/1/0264/7629/files/SSD1681.pdf. Its extracted text is at /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/ssd1681/ssd1681.txt.

## compare-to-ours

Per-pixel drive tracking is worth trying. For the teapot it costs nothing on the RP2040, because the masks can be precomputed on the Mac. It also points to a hole in our lag trick that would explain the trails better than DC imbalance does. A 31.25 MHz SPI clock could raise full-screen fps, but it is out of spec and untested.

1. **Drive method.**
   - SmoothEPD sends a black-mask plane to 0x26 and a white-mask plane to 0x24 (epd_fast.c:858-859). Its LUT has 01 = drive white, 10 = drive black, 00 and 11 = hold (epd_fast.c:378-382). Our `make_lut` already has that shape: BW toward black, WB toward white, WW and BB at VSS (teapot_demo.py:110-114). So we only need to change what we write into the two RAMs, not the LUT.
   - Each pixel keeps a counter. When its target changes, the counter is reloaded to 7 for black or 7 for white (epd_fast.c:310-311, 761-762). The pixel is driven until the counter reaches 0 (764-771, 811-819).
   - Our trick has a hole. A pixel that goes W to B to W inside the lag window has N == N-lag, so it gets no drive at all and is left part-black (teapot_demo.py:223-231). Dithered teapot pixels and sprite edges do this all the time. That fits our note that lag 6 or 8 did not change the smear (resume-20261027.md:124, 131): more lag cannot fix a reversal that is never driven.

2. **Drive length.** Their README sets a minimum of 120 ms per transition. Their scan BUSY is about 20 ms (epd_fast.c:432) and one scan is "26 ms" (epd_fast.h:49), so 7 scans is roughly 140 ms or more. Our lag 6 at 8.1 ms gives about 49 ms, and the wipe (k=8) about 65 ms. On their rule we under-drive by about 2.5x, which would mean lag around 15. The ms of real drive per scan on their panel is unknown.

3. **Compensation.**
   - **Default file:** a signed `s_debt` per pixel (epd_fast.c:407). Every 1000 scans it sends one pulse against the debt, only on pixels whose debt points toward their current color (315-316, 892-895). A custom-LUT full refresh (1.3 s, lut_full at 352-373, sequence at 581-629) runs every 2000 scans (317). The header says 4000 (epd_fast.h:81).
   - **`epd_fast_net.c.bak`:** keeps driving toward the target while the per-pixel net stays inside [-7, +7]. Every pixel ends up pinned at the end of its color with bounded DC. This bound is the alternative to our wipe.
   - **HOLD ending:** one extra scan with all-zero masks after drive stops (epd_fast.c:1054-1076).
   - Their full refresh is 1.3 s from a custom LUT against our 3.3 s OTP clean. We would have to port it to the SSD1683's 227-byte layout. Whether it looks good enough is unknown.

4. **SPI.**
   - They run DMA at /2 of 100 MHz, about 50 MHz, and the comment says the chip tolerates /2 although the spec says 20 MHz (epd_fast.c:58-61).
   - Like us they write only after BUSY drops (1025-1026). They compute the next frame during BUSY (1045).
   - They always send the full frame (`EPD_PARTIAL_WINDOW 0`, 307), 10 KB per scan.
   - On the RP2040, asking for 31.25 MHz (125/4) would cut our 30 KB from about 15 ms to about 7.7 ms. That is roughly 36 to about 55 fps full screen (my estimate), but 1.5x over the SSD1683 limit and untested on it.

5. **Panel voltages** (lut_fast_base bytes 153-158 at epd_fast.c:391-392):

| Setting | Theirs | Ours |
|---|---|---|
| EOPT | 0x02 | 0x07 |
| VGH | 0x17 | 0x17 |
| VSH1 | 0x41 | 0x41 |
| VSH2 | 0xB0 | 0xA8 |
| VSL | 0x32 | 0x32 |
| VCOM | 0x28 | 0x30 |

   No big differences. The SSD1681 FR byte 0x22 (391) to Hz is unknown.

**Cost on the RP2040 in CircuitPython:**
- Their layout, one byte each for remaining and debt per pixel, needs 2 x 120000 = 240 KB. That will not fit.
- Bit-sliced in Python, a 0..7 counter takes 3 planes (45 KB) plus a 15 KB target plane, with the mask planes reusing b24/b26. The net variant's [-7, +7] range needs 4 planes (60 KB). Updating 15000 bytes x 3-4 planes per step in pure Python would take well over 100 ms, against an 8.1 ms BUSY window. I haven't measured that.
- ulab bitwise ops might do it, but I haven't checked whether our build has them.
- Live content (ball, square) would need C: a native module or a core change.
- **The teapot is free.** Its frames are already rendered on the Mac. `make_frames.py` can simulate the budget or net counters over the 120-frame loop, run two passes so the state wraps, and write the black and white masks as the two 15 KB planes per step. That is the same 30 KB SPI and the same fps, with no RP2040 CPU or RAM cost. The panel must start from a known state, so reset the simulated state at each OTP clean, as they do (epd_fast.c:632-634).

**What to try, in order:**
1. Precomputed per-pixel budget masks for the teapot, with a budget of about 15 frames at 125 Hz (about 120 ms). This tests whether the trails come from the lag-reversal hole and under-drive, without any white bias.
2. The net-bounded variant: it may let the 4 s wipe go.
3. A custom SSD1683 full-refresh LUT to shorten the 3.3 s clean flash.
4. SPI at 31.25 MHz, over spec.

Files compared:
- /Volumes/clear/Downloads/ada/eink-high-freq/board/teapot_demo.py
- /Volumes/clear/Downloads/ada/eink-high-freq/resume-20261027.md
- /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src/V3F/User/epd_fast.c
- /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src/V3F/User/epd_fast.h
- /private/tmp/claude-501/-Volumes-clear-Downloads-ada-eink-high-freq/c23f0ba0-0e50-41d2-b287-d5860fdf136c/scratchpad/smoothepd-src/V3F/User/epd_fast_net.c.bak

