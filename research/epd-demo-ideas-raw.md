## hackaday-eink

Hackaday e-paper finds, checked against the pages where I could fetch them. Only the Game Boy, 2020 movie player, Krasnow, and badge pages were opened directly. The rest come from search snippets and are marked.

1. **Game Boy at 30 FPS on e-paper (Bo)**
   - What: Game Boy-style video on a Waveshare ESP32-S3 1.54" e-paper board, with 4-bit grey from deliberate under-driving.
   - Why it's striking: It's the closest thing to real-time e-ink animation, and the ghosting is part of the look.
   - Difficulty: Hard. It relies on the controller's per-pixel drive budget and per-transition calibration. On an SSD1683 you would need custom LUTs, and that is not the same hardware.
   - Source: https://hackaday.com/2026/10/14/tiny-e-paper-display-delivers-30-fps-of-game-boy-fun/ (fetched). No source code yet.

2. **20 FPS video via delta encoding (Tony)**
   - What: An MPEG-like scheme that sends only changed pixels, driving 960x540 panels at about 20 FPS.
   - Why it's striking: Shows that moving regions can refresh much faster than full screen.
   - Difficulty: Medium to hard. Pre-rendering the delta frames is feasible; the decoder must run on the RP2040.
   - Source: Not opened. The article URL was not returned by search. It is referenced in the Game Boy article above.

3. **Krasnow's fast-refresh LUT hack (2017)**
   - What: Rewrote the waveform LUTs on a 4.2" e-paper module to speed up refresh, and scoped the drive signals to confirm.
   - Why it's striking: Directly relevant to your 4.2" panel. The before/after demo is the kind of thing that sells the speed.
   - Difficulty: Medium. This is a LUT edit on your own controller.
   - Source: https://hackaday.com/2017/10/31/ben-krasnow-hacks-e-paper-for-fastest-refresh-rate/ (fetched). The page gives no numeric rate.

4. **Animated e-paper badge flipbook (Hackaday.io)**
   - What: Pre-rendered 1-bit frames played in sequence on a 1.54" panel.
   - Why it's striking: A plain flipbook of crisp bitmaps is easy to make look good on 1-bit e-ink.
   - Difficulty: Easy with pre-render. Your panel's frames are 400x300 at 1 bit, so 15 KB each. That is roughly 200 frames in 3 MB of free flash.
   - Source: https://hackaday.io/project/180145-animated-e-paper-badge/details (fetched).

5. **Chrome T-Rex on e-paper (Hackaday.io)**
   - What: An offline T-Rex-style game on a 2.9" Waveshare panel. The builder noted ghosting and retained images.
   - Why it's striking: A game on e-ink is unusual. Simple sprites suit 1-bit and the thick-stroke rule.
   - Difficulty: Easy to medium, live compute on RP2040 is feasible for a sprite game.
   - Source: https://hackaday.io/project/27442-real-life-chrome-offline-t-rex-game/log/68187-e-ink-display (search snippet only).

6. **Live 1-bit sprite game (Pong or Breakout style)**
   - What: Original idea, not a found project. Thick paddles and a ball, with partial updates on the moving regions.
   - Why it's striking: Live interaction at fast refresh is rarely shown on e-ink.
   - Difficulty: Medium. Live compute on RP2040 works if the sprites are small, so it fits the 89 fps small-sprite number.
   - Source: None. This is my suggestion, not a found project.

Caveats:
- E Ink reportedly says current production modules do not support video-rate updates, and constant updates reduce power efficiency and may shorten panel life. Reader comments on the Game Boy article claim a cycle-count limit. Both are unverified. Source: https://invidis.com/sixteen-nine/2025/03/18/heres-a-31-inch-color-e-paper-display-running-full-motion-video/ (search snippet).
- Tom Whitwell's slow Psycho player (https://medium.com/@tomwhitwell/how-to-build-a-very-slow-movie-player-in-2020-c5745052e4e4) is dithered video at one frame every two minutes. It is not fast, so I left it out of the list.

## demoscene-1bit

1. Metaballs (PICO-8 cart by samuelks)
Blobs that merge and separate, drawn as thick solid shapes that could be thresholded to black and white.
Why it works on e-ink: large solid blobs at slow-to-medium speed suit the 50-140 ms drive time, and the grid-interpolation approach keeps the per-frame work low.
Difficulty: live compute is plausible on RP2040 in C, since the code samples a coarse grid and interpolates rather than computing every pixel. Python would likely be too slow at full 400x300.
Source: https://www.lexaloffle.com/bbs/?tid=29314 (a related thread at https://www.lexaloffle.com/bbs/?tid=32180 also covers metaballs)

2. Tunnel effect
A texture-mapped tunnel where the angle becomes U and distance becomes V, so the pattern rushes toward the viewer. Thick ring or checker textures would read well in 1-bit.
Why it works on e-ink: the moving rings are high-contrast and large, though fast motion may ghost.
Difficulty: pre-render is the practical route. The Second Reality version precomputes per-pixel distance and angle tables, and a full-screen table at 400x300 is about 120k entries, which is heavy for 264 KB of RAM. Live compute would need a small tile or a lower resolution.
Source: https://carette.xyz/posts/the_tunnel_effect_demoscene/

3. Rotozoomer, twister, vector balls, fire, starfield (C/SDL demo effects collection)
A open-source C collection with folders for rotozoomer, twister, vectorballs, fire, stars and scroller. The sine scroller is a candidate for a thick-stroke scroll that is not text-reading.
Why it works on e-ink: the twister and vector balls are solid shapes, which suit e-ink. The rotozoomer is a strong candidate for a showpiece, but thin rotating edges may smear.
Difficulty: these are SDL 1.2 desktop code, so porting to RP2040 C means rewriting the drawing layer. Live compute is plausible in C for the simpler effects. The repo does not mention dithering or 1-bit output.
Source: https://github.com/flightcrank/demo-effects

4. Monochrome Atari ST demo thread (Pouet)
A forum list of mono-screen ST demos, including "Monoscreen" by Dead Braincells (2007), "mode_nr1" by Bodo Wenzel (2013), "Alf Demo" by Echo Cray (2013), "Time Slices" by Defence Force (2015) and "1bit Atari" by Attle (2019). The thread does not describe the effects used, so each demo would need to be checked by watching or downloading it.
Why it works on e-ink: these were built for true 1-bit hardware, so their look already fits the panel.
Difficulty: unknown until the demos are inspected. Atari ST mono is 640x400, close to the panel.
Source: https://www.pouet.net/topic.php?which=3812&page=2

5. Demozoo monochrome production catalog
A tagged list of 1-bit and monochrome productions on Demozoo, which is the best place to find more examples. I did not open it, so I cannot confirm the entries.
Why it works on e-ink: it is the source for real 1-bit effects, not guesses.
Difficulty: n/a (research pointer).
Source: https://demozoo.org/productions/tagged/monochrome/?order=title&dir=asc&page=1

6. Error 23 by Resource and The Dreams (C64)
A dithered, colourful plasma that commenters name as the demo's standout moment. It is not 1-bit, but it shows that coarse ordered dithering reads well as a plasma look.
Why it works on e-ink: coarse dithering is the look e-ink handles best, so the plasma could be re-dithered for black and white.
Difficulty: live compute is hard at full resolution, so pre-rendering is the likely route. The forum text does not explain the method in detail.
Source: https://www.pouet.net/prod.php?which=24466

7. 70908 by Scoopex (ZX Spectrum)
A plasma built from dithered blocks, praised by a commenter as huge. Like the C64 demo, it is a reference for coarse dither plasma, not a 1-bit demo.
Why it works on e-ink: blocky dithered plasma uses large areas that change slowly, which suits the panel.
Difficulty: pre-render is the practical route.
Source: https://www.pouet.net/prod.php?which=80915

Notes: I found no source for a 1-bit rotozoomer with dithering, so the rotozoomer idea is a suggestion, not a confirmed demo. The Sommarhack 2022 "Monofillah" 16 KB monochrome demo showed up in search results, but I could not open its source page, so I left it out. The difficulty ratings are my estimates from RAM and frame rate, not measurements on your board.

## playdate

Playdate angle, 6 items. All are from search snippets, not fetched pages, so treat the performance figures as approximate.

1. Crank the World (Aras Pranckevičius, 2024)
Raytraced spheres and a raymarched tunnel, sponge and field, drawn with a static blue-noise dither standing in for grayscale. Each frame updates only 1 in 4 or 1 in 6 pixels to hit playable speed.
Why it works on e-ink: 3D shading reads as texture at a 1-bit level, and partial per-frame updates suit slow e-ink drive.
Difficulty: live compute is hard on RP2040 (sponge/tunnel-style raymarching is too heavy for CircuitPython). Pre-rendering the frames is realistic; a C live version with 1-in-N pixel updates is feasible.
Source: https://aras-p.info/blog/2024/05/20/Crank-the-World-Playdate-demo/

2. Surface-stable fractal dither (Aras port of Rune Skovbo Johansen's technique)
Dither dots stay attached to 3D surfaces while their density changes with distance. A simple scene runs at about 22 fps on Playdate. Includes a crank-controlled orbit camera.
Why it works on e-ink: a slowly orbiting, smoothly dithered 3D object is the kind of slow, solid-ish motion that e-ink handles well.
Difficulty: live compute, moderate in C; pre-render is easy if you want the look without the cost.
Sources: https://aras-p.info/blog/2025/02/09/Surface-Stable-Fractal-Dither-on-Playdate/ and https://github.com/aras-p/playdate-dither3d

3. Tiny software 3D renderer (community post)
Quake BSP maps, a z-buffer and Bayer-matrix lighting, in a 1-bit cel-shaded style inspired by Return of the Obra Dinn.
Why it works on e-ink: coarse Bayer dithering and solid cel shapes match the "coarse ordered dither, solid shapes" look your constraints favor.
Difficulty: live compute in C is a large job; a BSP walkthrough would need a lot of RAM care on 264 KB. Pre-render the walkthrough as frames for streaming.
Source: https://daily.dev/posts/building-a-tiny-3d-renderer-for-a-tiny-handheld-ncrfzmr8j (I did not open the full post.)

4. Bayer-dithered diffuse lighting (Elliott Regan demo)
A Three.js scene with a 4x4 Bayer threshold on diffuse lighting, in a Monument Valley-like style. Flat, bold shapes lit with coarse dither.
Why it works on e-ink: large, stable regions with an ordered pattern are robust to e-ink drive and do not smear.
Difficulty: easy to pre-render from any 3D tool; live version on RP2040 is simple per-pixel math (a lookup of a 4x4 threshold).
Source: https://www.elliottregan.com/demos/dither-demo.html

5. Dithering-and-flashing exploration (whoisjim, Playdate forum)
Compares posterized, dithered and enlarged-pixel versions of an image. Finding: 5-level dithering flashes too much to ship, and per-frame dithering looks better but draws more slowly.
Why it matters for you: this is a direct warning about the same tradeoff on e-ink, so it is a good guide for picking the dither level in a demo.
Difficulty: pre-render (a test harness, not a showpiece on its own).
Sources: https://devforum.play.date/t/an-exploration-of-dithering-and-flashing/10272 and https://github.com/whoisjim/playdate-dithering-demo

6. Animated dither phase offsets (Playdate forum)
Animating the phase offset of a dither pattern to create fades and motion. The thread notes that moving the offset on both axes causes unwanted flashing.
Why it works on e-ink: a slow dither-phase shimmer or a dither-to-solid fade could be a striking transition, but the thread's flashing warning means one axis only.
Difficulty: easy pre-render; trivial live on RP2040 since it is only a pattern offset.
Source: https://devforum.play.date/t/animated-dither-patterns-using-phase-offsets/10641

Notes: no official Panic particle or dithering-shader demo turned up, so the community projects above are the closest Playdate sources. The Crank the World and surface-stable posts are from 2024 and 2025, so their performance numbers may have shifted with later SDK releases. Nothing here has been run on hardware.

## physics-sims

1. Bad Apple on EPD_Painter (ESP32-S3, 960x540, 4 grey levels, about 20 fps). Video playback on a parallel-bus e-paper panel, with a delta engine that redraws only changed pixels. It shows that a delta-redraw approach can reach video-like rates. Why it fits: it is a big, recognizable video on e-paper, the thing people least expect. Difficulty: live playback needs an ESP32-S3-class chip, but on the RP2040 you would pre-render delta frames and stream them from flash. Note that this panel is not SSD1683 and the hardware is not SPI. Source: https://www.tonyweston.uk/web/badapple/index.html

2. Solar-powered Conway's Game of Life on a 400x300 e-ink panel. The simulation advances one generation at a time, with the pace set by ambient light. Why it fits: the panel size matches yours, cells can be 3 to 4 px thick, and the slow evolution suits e-ink. Difficulty: live compute, easy on the RP2040. A 4 px cell grid is 100x75 cells, which fits in RAM, and one generation per second or so is practical even in CircuitPython. Source: https://goodereader.com/blog/e-paper/solar-powered-e-ink-conways-game-of-life-with-circadian-rhythm (Hackaday tag page with the project: https://hackaday.com/tag/game-of-life/)

3. Falling sand on a 400x300 panel with thick grains. Sand piles and slides under gravity. Why it fits: the piles are solid shapes with slow, readable motion, and the scene changes only where grains move, which suits e-ink. Difficulty: live compute in C on the RP2040 is comfortable. In Python it is slow but workable at a coarse grid of 3 px grains, about 133x100 cells. Pre-rendering is also simple. Sources: https://www.instructables.com/Falling-Sand-Simulation/ (ST7789 LCD build) and https://gist.github.com/witnessmenow/29192dd0e5dda61f50900e3422cedeab (64x64 RGB matrix with an accelerometer, about 40 grains)

4. Animated sand hourglass. Grains flow from the top bulb to the bottom. Why it fits: it is a single large, slow, high-contrast motion with a solid silhouette, which is ideal for e-ink. Difficulty: trivial. It can be pre-rendered or simulated live in Python at low cost. Source: https://community.dfrobot.com/makelog-315624.html (ESP8266 OLED version)

5. Game of Flow, a cellular-automaton fluid simulation. Realtime fluid with effects such as oil floating on water, built from simple local update rules. Why it fits: blobby, thick-walled fluid regions show up well in 1-bit, and the motion is slow and smooth. Difficulty: live compute on the RP2040 is feasible in C, since the rules are integer-based. The source is a paper, so this is an idea, not a finished demo. Source: http://www.vonmammen.org/publications/2017-VRST-GameOfFlow.pdf

6. Real-time boids, double pendulum, n-body, or cloth on e-ink. No source found. Searches turned up only general GxEPD2 setup material and academic double-pendulum papers. The closest refresh-rate datapoint is Espressif's Inkplate page, which lists a 91 ms partial refresh (about 11 fps) on the 6MOTION model. That came from a search snippet, not a fetched page. Source: https://developer.espressif.com/blog/2026/05/inkplate-esp32-epaper-development-boards/

Gaps: no e-paper physics demo was found in the forums or on Hackaday beyond the items above. The EPD_Painter result is the strongest evidence that high-rate e-paper animation is being done by hobbyists, though on different hardware. Items 5 and 6 come from search snippets I did not open in full.

## cellular-generative

Search-snippet findings only. I did not WebFetch the pages, so details are from search results. No e-ink Gray-Scott, Physarum, Lenia, or DLA demo turned up, which suggests the gap you're looking for is real.

1. **Gray-Scott reaction-diffusion (Turing spots and worms)**
   - Description: Two-chemical reaction-diffusion field, thresholded to 1-bit. Spots and worms grow, split and drift.
   - Why it works on e-ink: Blobs and worms are thick and slow-changing, which fits the refresh limits. Changes ripple across the whole panel, so the full-screen refresh is what you see.
   - Difficulty: Pre-render on a PC. Live on RP2040 would need a 400x300 float grid per step, which is too slow.
   - Source: https://github.com/moshejs/reaction-diffusion (WebGL sandbox, notes an 8-bit packed fallback for constrained hardware). Also https://github.com/amandaghassaei/ReactionDiffusionShader

2. **Lenia / SmoothLife (continuous Game of Life, "smooth gliders")**
   - Description: Continuous-state cellular automaton where soft blobs glide, split and collide. Lenia has 400+ catalogued "species."
   - Why it works on e-ink: Solid organic blobs with smooth, slow motion. Thresholded to 1-bit they read as bold shapes, not thin lines.
   - Difficulty: Pre-render. Live convolution is too heavy for RP2040.
   - Source: https://arxiv.org/pdf/1812.05433 (Chan, Lenia primary paper). Background: https://arxiv.org/pdf/2508.02935

3. **Conway's Game of Life on e-ink (Adafruit solar build)**
   - Description: Classic Life on an e-ink panel driven by an ESP32.
   - Why it works on e-ink: Easy to read, and blocky cells upscaled 4x or more give thick strokes. Doing it on a 400x300 panel at a higher-resolution grid is a step up.
   - Difficulty: Live on RP2040 is easy with a bit-packed grid (for example 100x75 cells at 4px). Partial refresh of changed regions keeps frame rate up.
   - Source: https://blog.adafruit.com/2023/08/01/conways-game-of-life-via-eink-display-and-solar-power-esp32-solar-gaming/ (already done on e-ink, so it is a baseline, not the wow factor)

4. **Truchet tile animation**
   - Description: Grid of quarter-circle or diagonal tiles that flip and rotate in steps, forming shifting mosaics.
   - Why it works on e-ink: Tiles of 40-60px give thick arcs and solid fills. Each flip changes a small region, so it shows off partial-refresh speed, which is the fast-refresh point you want.
   - Difficulty: Live on RP2040 is easy: random rotation per tile and bit blits. Good candidate for live compute.
   - Source: https://github.com/paezha/truchet/blob/HEAD/vignettes/articles/a06-animated-mosaics.Rmd (R tutorial with discrete-step animation, black-and-white fills)

5. **Langton's ant (scaled up)**
   - Description: Turing-complete ant on a grid that builds highway patterns and chaotic growth. Ant state machine on a bit grid.
   - Why it works on e-ink: Only the ant's one- or two-cell change per step needs redrawing, so it suits fast partial refresh. Thin 1px trails smear, so scale cells to 4px or more.
   - Difficulty: Live on RP2040 is trivial.
   - Source: https://hackaday.io/project/176615-exponentially-replicating-langtons-ants (VGA build, not e-paper, but the algorithm and display-agnostic framing carry over)

6. **10 PRINT (random diagonal maze)**
   - Description: Random forward or back slash in each cell, producing a maze-like texture that builds up over time.
   - Why it works on e-ink: Reads as bold maze texture at large cell sizes (20px+). Strokes are thin if cells are small, so use big cells.
   - Difficulty: Live on RP2040 is trivial. Full redraw every frame will flicker on e-ink, so update only changed cells or pre-render the sequence.
   - Source: https://www.chestervisualarts.org.uk/10print (browser project based on the C64 one-liner, plus the Coding Train tutorial it cites)

7. **Diffusion-limited aggregation (DLA) growth**
   - Description: Particles random-walk and stick to a growing cluster, creating branching crystal shapes.
   - Why it works on e-ink: Growth is monotonic (pixels only get added), so each frame refreshes only the new pixels, which is good for fast partial updates. Branches are thin, though, so use thick particles.
   - Difficulty: Live on RP2040 is feasible for a few thousand particles. There is a Cornell RP2040 cyclic-DLA project, which is a useful reference.
   - Source: https://magzter.com/stories/education/Circuit-Cellar/CATCHING-LIGHTNING-IN-AN-IMU (Circuit Cellar article, Nov 2024; a magazine page, so verify before relying on it)

8. **Physarum slime mold (weakest fit)**
   - Description: Agents follow and deposit a chemical trail that forms networks.
   - Why it works on e-ink: Networks are thin and fine, so they smear. It only works with thick trails on a coarse grid.
   - Difficulty: Pre-render. Live on RP2040 is hard, though a small grid with few agents might work.
   - Source: https://www.michaelfogleman.com/projects/physarum/ (CPU Go version, the most embedded-friendly reference I found)

Ranking for your goal (striking on e-ink, fast refresh shown off): Truchet and Gray-Scott are the strongest. Truchet is live-friendly and shows partial refresh. Gray-Scott and Lenia are best as pre-rendered, full-screen morphing pieces that show graphics ability. Langton's ant and DLA are good live options that stress refresh speed.

## 3d-realtime

1. Doom-style raycaster on e-ink (doom-xt4)
Wolfenstein-style raycaster with Doom sprites on an 800x480 SSD1677 e-ink panel (XTeink X4, ESP32-C3). Renders to a 200x120 grayscale buffer, uses 1-bit sprites, and does a full refresh on pause for clean frames. Why it works on e-ink: big solid walls and slow walk animation (about 200 ms per frame). Difficulty: live compute on an ESP32-C3, so RP2040 is harder but similar in class. No fps is reported. Source: https://github.com/davidpavlicek36/doom-xt4

2. Doom on a PocketBook e-reader
A Doom port on an e-ink reader. The author calls it "kind of crappy" but "pretty cool" because of slow refresh. No fps or hardware specs in the page. Why it works: it's the closest precedent for your goal, and the page shows the refresh limit is the main problem. Difficulty: unknown, likely live compute. Source: https://www.christopherburg.com/archive/doom-played-on-e-ink/

3. 1-Bit Doom streamed to an ESP32 OLED
DOS games are rendered on a PC, dithered to 1-bit in the browser, and streamed over WiFi to a 128x64 SSD1306. The author says the result is surprisingly playable. Why it works: the same pre-render-and-stream model you have, so it fits your 8 MB flash plan or a live PC feed. Difficulty: pre-render, easy on RP2040 if frames are stored in flash. Source: https://www.sanderdesnaijer.com/projects/1-bit-doom

4. Doom on a one-bit electroluminescent display (Pico)
A Doom port with dithering to a 320x256 one-bit amber EL display on a Raspberry Pi Pico (RP2040). Why it works: it is the same MCU class and a similar 1-bit, high-contrast look, and the port is GPL-2.0 on GitHub. Difficulty: live compute on RP2040, but the Pico is proven capable. Source: https://www.hackster.io/news/michael-p-gets-an-industrial-electroluminescent-display-and-doom-running-on-a-raspberry-pi-pico-6813b4750dba

5. NU40 DK Doom-style shooter on a tiny OLED
A raycaster on a 128x64 SSD1306, reported at 24 fps, with the real Doom 1 shareware streamed from a Mac as a bonus. Why it works: the fps number is a useful baseline for live raycasting at small resolution. Difficulty: live compute, small screen, so it would need a larger frame for e-ink. Source: https://www.hackster.io/nucode_korea/doom-style-3d-shooter-on-a-tiny-oled-with-nu40-dk-907b2a

6. doom-nano raycaster on an Arduino Nano
A Wolfenstein-style engine on an ATmega328 with a 128x64 I2C OLED, reported at up to 14 fps. Why it works: it shows the simplest live-compute path on tiny hardware. Difficulty: easy live compute, but the RP2040 has far more headroom. Source: https://github.com/daveruiz/doom-nano

7. Comanche-style voxel landscape
The classic voxel-space renderer. The reference page describes the 1024x1024 height and color maps, which are too large for RP2040 flash at full size. A GPU port (VoxelSpace-GPU) runs about 20 fps in a web demo and about 500 fps on GPU. Why it could look striking: large filled shapes and smooth flying motion suit e-ink if the view is dithered coarsely. Difficulty: hard live on RP2040 (about 264 KB RAM), easier as pre-rendered frames at low resolution. I found no microcontroller demo of this. Sources: https://simulationcorner.net/index.php?page=comanche and https://github.com/wenright/VoxelSpace-GPU

8. Rotating 3D cube with thick, dithered shading
Rotating cube demos exist for small OLED displays (Adafruit blog, ESP8266 MicroPython) and for CircuitPython on a PCD8544 LCD. Your display would need thick edges and filled faces because thin wireframe lines smear. Adding coarse ordered dithering to the faces would show grayscale shading on 1-bit output. Difficulty: easy, live compute on RP2040, or pre-render as a loop. Sources: https://blog.adafruit.com/2018/10/01/3d-wireframe-cube-with-micropython-on-an-oled-display/ and https://gist.github.com/johanvandegriff/363e63d6fb7f4114f72e472f0a00b024

9. Offline dithering for pre-rendered 3D frames
A dithering library for e-paper with 4- and 16-level grayscale palettes, built on a Rust/WASM core. Use it to generate dithered 3D frames on a computer before streaming them to the panel. Difficulty: easy, pre-render tooling only. Source: https://cdn.jsdelivr.net/npm/@opendisplay/epaper-dithering@6.0.0/README.md

Notes: The searches were limited (about six searches and three page fetches), so this list is not exhaustive. I found no real-time 3D raymarching or voxel demo on any e-ink or tiny monochrome display. The closest e-ink precedent, doom-xt4, reports no fps, so you would need to measure its frame rate yourself. The best candidates for your goal are items 3 and 4 (streamed or dithered Doom-style 3D) and item 7 (voxel terrain, pre-rendered).

## eink-video-games

1. Bad Apple at 20 fps on a 960x540 4-grey panel
Full-motion greyscale Bad Apple on a stock ESP32-S3 with the panel driven over its parallel bus, no FPGA or PC. The write-up says the waveforms live in registers and a delta engine only updates changed pixels.
Why it works: the motion is bold and high-contrast, and the frame rate is steady enough to read as video.
Difficulty: live compute on an MCU is hard. Pre-rendered frames from flash are the practical route, but the 20 fps figure is for a different controller and panel, so it does not transfer directly to SSD1683.
Source: https://www.tonyweston.uk/web/badapple/index.html

2. PaperBoy, Game Boy emulator on the M5Stack PaperS3 (4.7", 960x540)
CrankBoy emulator core running Game Boy games at 30 to 60 fps. Tetris is the most demanding and Super Mario Land runs fastest. The panel exposes a raw row/column driver interface, which bypasses the waveform method.
Why it works: a full-screen moving game on e-paper, with the audience already knowing what they are looking at.
Difficulty: high. It needs a raw row/column driver, and I did not verify whether SSD1683 exposes that. Live emulation on RP2040 would be far slower than on the ESP32-S3 used here.
Source: https://www.cnx-software.com/2026/07/02/paperboy-game-boy-emulator-works-at-60-fps-on-esp32-s3-e-ink-devkit/

3. InkBoy, Game Boy on a 1.54" 200x200 Waveshare panel
About 30 fps Game Boy on a small e-paper board. The modder built a driver that can pause a pixel's white-to-black transition, which gives four grey shades. Controls run on a separate ESP32-C3 gamepad. The author warns that heavy use may leave permanent ghost imprints.
Why it works: it shows that games are playable at all on small e-paper, and the 4-grey result shows the graphics range.
Difficulty: medium to hard, since the per-pixel grey driver is custom. Live emulation would be too slow on RP2040.
Source: https://github.com/kuslota/InkBoy (also covered at https://www.techeblog.com/inkboy-game-boy-e-paper-esp32/)

4. SUMI DOOM, original Doom on an Xteink X4 e-reader
Doom renders at 120x160, then is dithered with blue-noise ordered dithering to 480x640 on the e-ink panel. The author reports about 1.6 fps.
Why it works: Doom is instantly recognisable, and the dithered look suits 1-bit output.
Difficulty: live compute on an ESP32-C3 at this frame rate. The low frame rate is the weak point for your goal, so a pre-rendered or lower-res cut would show it better.
Source: https://github.com/psychoplath9450/sumi-doom

5. Doom II (PrBoom) on a PocketBook 360 Plus, 2011
An early e-reader port of Doom II. Hackaday noted that e-ink is notorious for slow redraw, but this demo achieves a fast page redraw.
Why it works: it is the classic "Doom on e-ink" demo that people remember.
Difficulty: live compute on a Linux e-reader, not comparable to RP2040. Useful mainly as a reference point for the idea.
Source: https://hackaday.com/2011/04/10/doom-ii-on-epaper-display/

6. Modos Paper Monitor running Return of the Obra Dinn and similar games
A 60 to 75 Hz e-ink monitor showing monochrome games. Obra Dinn is a 1-bit-style game, and a reviewer reported that smearing was less of a problem than on LCDs. The 75 Hz monitor also ran Blanc with up to 16 grey shades.
Why it works: it proves that games look good on e-ink when content is chosen for it. Obra Dinn's dithered art style is a close match for 1-bit output.
Difficulty: not a build, since this is commercial hardware. It is useful as a content and style reference.
Sources: https://gigazine.net/gsc_news/en/20250910-modos-75hz-paper-monitor/ and https://www.androidauthority.com/modos-flow-e-ink-paper-60hz-display-3677057/

7. Ben Krasnow's fast-refresh firmware hack on a 4.2" e-paper module
He modified the firmware of a 4.2-inch e-paper module to raise its refresh rate, with oscilloscope analysis of the drive signals and a demo video. Later projects build on the same technique.
Why it works: the panel size matches yours, and the demo shows what a faster refresh looks like on it.
Difficulty: medium to hard. It is a firmware and waveform change, so it may not carry over to SSD1683 without checking that controller's LUT behaviour.
Source: https://hackaday.com/2017/10/31/ben-krasnow-hacks-e-paper-for-fastest-refresh-rate

8. Flicker-free 32-grey e-ink driver
A driver that produces 32 grey levels and avoids update flicker, using computed look-up tables. The LUTs make it easier to try alternative refresh modes.
Why it works: it shows the graphics range (32 greys) that most e-ink demos never use. Gradient or shaded animation would show this well.
Difficulty: medium. The LUTs can be pre-computed, so the playback side is easy on RP2040 if the frames are pre-rendered.
Source: https://hackaday.com/2024/03/23/clever-e-ink-driver-does-32-levels-of-grey-avoids-update-flicker-and-more

9. Inkplate 6 MOTION partial-refresh animation (about 11 fps)
A hands-on review of a panel with a partial refresh rate near 11 fps, aimed at reducing visible latency in animations and video.
Why it works: it shows smooth partial-update animation as a category.
Difficulty: low to medium, since it is a commercial board with a usable API. Less relevant to your SSD1683 setup.
Source: https://hackaday.com/2024/06/06/hands-on-inkplate-6-motion

Notes:
- I found no source for an e-paper Pong, Tetris or Breakout build. The searches returned only general fast-refresh posts.
- The Hackaday posts "20 fps on e-paper display without help" (https://hackaday.com/2026/07/21/20-fps-on-e-paper-display-without-help/) and "Tiny E-Paper Display Delivers 30 FPS Of Game Boy Fun" (https://hackaday.com/2026/10/14/tiny-e-paper-display-delivers-30-fps-of-game-boy-fun/) appeared in search results only. I did not open them, so their details are unverified.
- Most of the frame-rate numbers above come from different controllers. Your measured 89 fps on a small sprite is already faster than the Bad Apple and PaperBoy figures, so the bottleneck for a demo is more likely content and grey handling than raw refresh.

## reddit-forums

No Reddit, Adafruit forum, or EEVblog threads turned up in search, so these items come from articles, project pages, and blog posts. Most are not SSD1683 demos, and the Adafruit-specific angle is thin.

1. InkBoy Game Boy at 30 fps (4 grey levels)
- What: Game Boy emulator on a cheap 1.54" Waveshare ESP32-S3 e-paper, with a custom per-pixel driver and a shortened waveform.
- Why it's striking: 30 fps on e-paper, with grey made by stopping the pigment partway through a transition. Big reaction on video and in the press.
- Difficulty: live compute with a custom waveform. Not SSD1683, so the waveform work does not port directly.
- Sources: https://www.theregister.com/offbeat/2026/10/15/youtuber-built-30-frame-per-second-grayscale-game-boy-then-open-sourced-it-for-all-e-paper-displays/5303394 ; code https://github.com/kuslota/InkBoy ; video https://www.youtube.com/watch?v=XiZmM6hwwAU

2. Bad Apple at 20 fps (July 2026)
- What: Bad Apple video on 960x540 e-paper panels (Lilygo, M5PaperS3) driven from an ESP32.
- Why it's striking: it sends only the pixel changes between frames (MPEG-like delta encoding) and uses optimized waveforms that move only the pigment needed. Strong 1-bit content with high-contrast motion.
- Difficulty: pre-render deltas on a PC, then stream them. That fits the 3-4 MB of free flash. The panels here have no smart driver chip, so the client does all the waveform work. The SSD1683 has its own LUT, so the method needs adapting.
- Sources: https://hackaday.com/2026/07/21/20-fps-on-e-paper-display-without-help/ ; project page with video https://www.tonyweston.uk/web/badapple/index.html

3. Fast partial refresh on a 4.2" 400x300 panel (Ben Krasnow)
- What: Replacing the LUT waveforms on a 4.2" 400x300 e-paper module to speed up partial updates. Covered in an Applied Science video.
- Why it's striking: the closest match to your panel size and resolution. Commenters report roughly double the refresh rate. The post itself gives no measured figure.
- Risks reported in comments: ghosting after about 10,000 cycles, and blurry partial updates.
- Difficulty: LUT editing on the controller, moderate. The post does not confirm an SSD1683, so check the controller first.
- Sources: https://benkrasnow.blogspot.com/2017/10/fast-partial-refresh-on-42-e-paper.html ; https://hackaday.com/2017/10/31/ben-krasnow-hacks-e-paper-for-fastest-refresh-rate

4. Wave transition on e-paper (E Ink Ripple, Seekink)
- What: A wave-shaped transition that hides the refresh flash between updates.
- Why it's striking: a graphic effect that makes the panel look smooth instead of flashing.
- Difficulty: needs controller support. Unverified for SSD1683. Could be simulated with a sequence of partial updates.
- Source: https://www.notebookcheck.com/E-Paper-Seekink-kaschiert-langsame-E-Ink-Aktualisierung-mit-Wellen-Animationen.1101096.0.html

5. Monochrome video on a commercial e-paper monitor (Modos Paper Monitor, 2022)
- What: Demo videos of full-motion monochrome video on a large e-paper monitor.
- Why it's striking: the public reference point for "e-paper can play video." Shows what the crowd expects to see.
- Difficulty: not reproducible on your hardware. Use as a benchmark for the demo's look.
- Source: https://www.theregister.com/2022/06/24/modos_e_paper_monitors/

6. 31" color e-paper playing motion video (trade show)
- What: A trade-show demo of smooth-looking video on a 31.2" E Ink panel.
- Why it's striking: strong public interest. E Ink's own position is that current production modules do not support video-rate updates, so treat it as a demo, not a product.
- Difficulty: not reproducible on your hardware.
- Source: https://www.sixteen-nine.net/?p=41462

7. SlowMovie (slow frame-by-frame video on a 7.5" panel)
- What: Plays video one frame at a time, deliberately slow, on a Waveshare 7.5" panel from a Raspberry Pi.
- Why it's striking: a good fit for e-ink's slow-update look, but it is the opposite of the fast-refresh goal you asked for.
- Difficulty: pre-render. Easy to port to your 400x300 panel.
- Source: https://github.com/gitzain/slowmovie

Hardware notes for SSD1683 planning (from a GDEQ042T81 datasheet listing): fast refresh takes about 1.5 s and flickers once per update, and the vendor recommends a full-screen refresh after every five fast operations. Source: https://www.good-display.com/product/443.html. The Rust driver page at https://github.com/Boudewijn26/ssd1683 and the Mischianti guide at https://mischianti.org/ssd1683-eink-display-with-gxepd-and-esp32-and-crowpanel-4-2-hmi-basics-and-configuration/ are also relevant to SSD1683 waveform choices, though I did not verify their timing numbers in full.

Gap: search did not index Reddit or the Adafruit and EEVblog threads. Targeted queries on those sites may turn up more.

## asia-eink

1. Bad Apple at 20 fps on a $71 e-paper panel
- What: Bad Apple played at 20.0 fps (the author reports 20 fps, not 24, on a 960x540, 4-grey panel). A "delta engine" repaints only pixels that changed between frames. The page is long, and I read only the first 100,000 characters.
- Why it works on 1-bit e-ink: Video-rate greyscale on a visible, high-contrast subject is the kind of thing nobody expects from e-paper. Delta updates are the key idea for your 400x300 panel too.
- Difficulty: Pre-render. Store the per-frame deltas in flash and stream them. Live compute on RP2040 is not realistic at this size.
- Caveat: Different panel (960x540, not SSD1683), so the frame rate does not transfer directly.
- Source: https://www.tonyweston.uk/web/badapple/index.html

2. Game Boy emulator on a tiny e-paper panel at about 30 fps
- What: A 200x200, 4-grey e-paper driven by an ESP32 runs Game Boy games at about 30 fps. The developer shortened the electrical pulse sequence that moves the particles in each pixel, and tracks each pixel separately. The driver is not public yet; the developer has promised to release it.
- Why it works: Small, thick-stroke sprite art with motion is exactly the content e-ink can handle well.
- Difficulty: Live compute, but the core loop is an emulator, so it is heavy for an RP2040 running Python. Better in C, and it needs a custom waveform.
- Source: https://www.makeuseof.com/developer-uses-an-esp32-tiny-e-paper-display-to-run-games-at-30fps/ (the same story is in the XDA piece below; a YouTube video titled "GameBoy on E-Paper ESP32 at 30FPS" is also listed in search results but I did not open it)

3. Game Boy emulator at 60 Hz on an M5Paper S3
- What: The developer ran a Game Boy emulator at 60 Hz by focusing all processing on the 160x144 game area. XDA describes the panel as a 4.7-inch M5Stack PaperS3 (ESP32-S3). The article gives no measured frame rate.
- Why it works: A small, fixed window updating at high rate is the best-case scenario for e-ink.
- Difficulty: Live compute, and too heavy for RP2040 in its current form.
- Source: https://www.xda-developers.com/someone-made-an-e-ink-esp32-game-boy-and-it-runs-at-a-very-playable-60hz-refresh-rate/ (note: XDA's claim conflicts with the 30 fps figure above; neither is independently measured)

4. Four-grey, fast-mode slideshow or shader demo on the exact panel family
- What: Good Display's product page for the GDEY042T81 4.2-inch panel (SSD1683, 400x300) lists full refresh at 2 s, fast mode at 1.5 s with one flash, partial refresh at 0.3 s with no flicker, and 4 grey levels. The page also recommends one full refresh after about five fast or partial refreshes to limit ghosting.
- Why it works: Four grey levels of a slow-moving, smooth gradient or plasma effect would show off greyscale in a way most e-ink demos do not.
- Difficulty: Pre-render the greyscale frames (or stream them from flash) and drive them with the vendor fast or partial modes.
- Source: https://www.good-display.cn/product/379.html (vendor specs, not independently verified)

5. Stacked partial refreshes to fake greyscale
- What: A Lichuang (oshwhub) open-hardware project on a modified 4.2-inch SSD1619 panel shows 4-grey, 16-grey and partial-refresh grey displays, with greyscale built by stacking multiple partial refreshes. The page is a search snippet only; I could not open the full page.
- Why it works: Visible dithered or banded grey on a slow-changing image is a striking, unusual effect.
- Difficulty: Pre-render or live. The partial-refresh loop is simple, but the number of passes costs time and wear.
- Source: https://oshwhub.com/shilihualang/han-jia-qian-gai-zhuang-ji-jian-kai-fa-ban

6. Transition effects that hide the e-paper blanking
- What: A Mynavi News demo (posted on X) uses animated transitions when redrawing e-paper. The point is that the screen goes blank during a full refresh, so the transition is designed to be watched rather than hidden. The post is a snippet; I did not open it.
- Why it works: Turns the slow refresh into a visible effect, which fits your "graphics" goal.
- Difficulty: Pre-render (a short set of transition frames) plus a partial-refresh driver.
- Source: https://x.com/mn_pc_digital/status/1847543860937052235

7. Chinese handheld firmware claiming 60 fps on e-ink (title only)
- What: A bilibili video titled "做了个60fps的墨水屏掌机固件" (I made a 60 fps e-ink handheld firmware). I could not open the page to verify the claim or the panel.
- Why it works: If real, this would be the high-refresh target you want.
- Difficulty: Live compute, and unknown.
- Source: https://www.bilibili.com/video/BV1PpLE6NEuR/

Notes
- Items 1 and 2 are the strongest matches for "fast refresh plus graphics." Both use delta or shortened-waveform drivers, which is the technique to copy for SSD1683.
- Waveshare's ESP32 e-paper tutorial warns that continuous high-rate refreshing accelerates panel aging and is unsuitable for animation or video. Plan for a wear budget.
- I did not find a published SSD1683 demo reaching 89 fps. Your measured numbers are already ahead of anything I could verify.
- Searches that returned nothing useful: Qiita, Zhihu, and the Adafruit blog (the Adafruit fetch returned a 403).

## sensor-interactive

Sensor-interactive e-paper demos (search angle: accelerometer, audio, rotary encoder). No e-paper tilt maze or e-ink audio visualizer turned up, so those two would be open ground for us.

1. **Etch-A-Sketch on e-ink (TekkaSketch)**
   - What: Etch-A-Sketch clone with an e-ink panel, ESP32, and two rotary encoders. Drawings persist with power off, and there is a snake mode.
   - Why striking: Partial refresh gives a fluid drawing feel. Slow thin lines will smear, so use thick strokes.
   - Difficulty: Live compute, easy on RP2040 (encoder input, small redraws).
   - Source: https://www.open-electronics.org/tekkasketch-reinventing-the-etch-a-sketch-with-e-ink-and-esp32-innovation/

2. **Shake-to-erase drawing pad (Inkplate 6 + MPU6050)**
   - What: Two encoders draw, and shaking the board erases the screen.
   - Why striking: A full-panel flash-clear triggered by a physical gesture shows off refresh speed. Detail was taken from search snippets only, since the page returned 403.
   - Difficulty: Live compute, easy (IMU shake threshold plus full refresh).
   - Source: https://www.allaboutcircuits.com/projects/shake-it-off-a-digital-drawing-pad-inspired-by-the-iconic-etch-a-sketch/

3. **Tilt marble maze (Adafruit, Dano Wall)**
   - What: Accelerometer tilt steers a ball through a maze. The original is servo-tilted cardboard, not a display.
   - Why striking: Ball physics with partial refresh of only the ball's region is a clear e-ink showcase. Thick walls and a large ball suit the panel.
   - Difficulty: Live compute, moderate on RP2040 (physics is cheap, the constraint is region-only redraws).
   - Source: https://learn.adafruit.com/tilt-controlled-marble-maze/overview

4. **Tilt Maze browser game (Blinky Games)**
   - What: Web tilt-maze game, a reference for gameplay and level design.
   - Why striking: Simple, readable 1-bit layout, so it survives coarse rendering.
   - Difficulty: Live compute, easy to moderate.
   - Source: https://www.blinky.games/learn/tilt-maze.html

5. **Rotating 3D cube on e-paper (Soldered Inkplate sketch)**
   - What: Live accelerometer data rotates a solid 3D cube on an e-paper panel.
   - Why striking: Solid rotating shapes are a good fit for e-ink. Smooth motion has to be slow enough for the panel.
   - Difficulty: Pre-render is the strong option, since a 30 to 60 frame turntable can stream from flash. Live 3D on RP2040 is hard in Python.
   - Source: https://docs.soldered.com/inkplate/4tempera/peripherals/accelerometer/

6. **Lissajous / X-Y oscilloscope (StephenJohnson79)**
   - What: Monochrome dual-channel scope with an X-Y Lissajous mode, using sine tones or microphone input. It is a browser app.
   - Why striking: Lissajous curves are slow, smooth, and graphic. Draw them with thick traces.
   - Difficulty: Live compute, moderate. Needs fast ADC sampling on RP2040, and the plotting itself is cheap.
   - Source: https://github.com/StephenJohnson79/Lissajous-Oscilloscope

7. **ESP32 audio spectrum analyzer (Elektor, CrowPanel)**
   - What: Stereo FFT bar analyzer on a 3.5" ESP32 display.
   - Why striking: Bars are familiar, but e-ink refresh is slow, so this is a weaker fit unless the bars are thick and decay slowly.
   - Difficulty: Live compute, hard on RP2040 in Python (FFT needs C).
   - Source: https://www.elektormagazine.com/labs/diy-esp32-audio-spectrum-analyzer-crowpanel-35-hmi-display

8. **Inkplate 6MOTION dynamic-content board**
   - What: Hardware built for animated e-paper content with partial updates.
   - Why striking: Confirms partial-update animation is a supported use case. The refresh figure (about 91 ms per partial update, about 11 fps) came from a search snippet and is not verified against the source.
   - Difficulty: Hardware reference, not a demo.
   - Source: https://www.cnx-software.com/2024/05/24/inkplate-6-motion-stm32-wireless-e-paper-display-higher-resolution-faster-refresh-rates/

9. **Gravity Tilt ball game (UCSB student proposal)**
   - What: Accelerometer tilts a plane so a ball rolls toward a hole while avoiding pits. It used an LCD, not e-paper.
   - Why striking: Confirms tilt-ball gameplay is a known fit for small displays.
   - Difficulty: Live compute, easy to moderate.
   - Source: https://www.ece.ucsb.edu/~yoga/courses/ECE153B/W2022/ProjectProposals/GravityTilt.pdf

Hardware notes: The Inkplate boards and Waveshare ESP32-S3 e-paper boards (https://www.waveshare.com/esp32-s3-epaper-13.3e6.htm) were the e-paper hardware found. None of the sources target SSD1683 directly, so the ideas transfer but the drivers would need porting. Best pick for our goals is the tilt marble maze (3) with region-only partial refresh, or a pre-rendered rotating solid (5) for a smooth showcase.

## oscilloscope-vector

Oscilloscope-vector and related 1-bit demo ideas, with sources. Only items I found sources for are listed. Flying toasters and Mystify on e-ink returned nothing usable, so they are omitted.

1. Oscilloscope music (Jerobeam Fenderson)
Audio left/right channels drive X/Y, so the sound draws thick glowing shapes such as the mushroom animation.
Why it fits: slow, large, closed-curve motion with solid shapes suits e-ink. Thin fast strokes would smear, so use 2px+ lines.
Difficulty: pre-render. Compute XY frames offline from the audio and stream them from flash.
Sources: https://oscilloscopemusic.com/info/about/ and https://spectrum.ieee.org/jerobeam-fendersons-trippy-oscilloscope-music

2. Lissajous and harmonograph animation
Animated Lissajous curves and damped pendulum traces with thick strokes.
Why it fits: smooth, slow motion over a few hundred pixels is what e-ink handles best.
Difficulty: pre-render (the math is cheap, so live compute is also plausible in C).
Sources: https://github.com/mbelouso/maths_fun and https://robertinventor.com/software/Lissajous_3D/spirographs.htm

3. Animated spirograph (epicycles and hypotrochoids)
A p5.js app with many curve types. Each frame adds one more arc to the figure, so the image builds up slowly.
Why it fits: the build-up is slow and thick-lined, and the final image is a high-contrast solid figure.
Difficulty: pre-render from the same math.
Source: https://github.com/wesscheid/Spiro

4. Asteroids-style vector game (CircuitPython port)
"staroids" targets RP2040 and ESP32-S2. Per the search snippet, the author notes that Asteroids needs a high framerate, so you trade off sprite count and size.
Why it fits: it shows the RP2040 doing real-time vector play, but e-ink will be slower than a CRT, so use fewer, larger sprites.
Difficulty: live compute on RP2040. Hard in CircuitPython; feasible in C.
Source: https://awesome.ecosyste.ms/projects/github.com%2Ftodbot%2Fcircuitpython_staroids (I could not open this page, which returned HTTP 403. The description comes from search snippets only.)

5. Vector Asteroids on a Pico-driven CRT or vector display
A Pico/ESP32 project that renders Asteroids-style vector graphics with particles.
Why it fits: a direct precedent for a 1-bit vector renderer on a microcontroller. Its frame rate would be the limit on e-ink.
Difficulty: live compute, C recommended.
Source: the search result at https://hackaday.com/2023/04/17/bust-out-that-old-analog-scope-for-some-velociraster-fun (a scope-based vector art project; I saw only the title and snippet, not the body). The Pico/ESP32 Asteroids project came up in search but I did not capture its URL, so use the staroids link above as the RP2040 reference.

6. Conway's Game of Life (Inkplate example)
A 1-bit cellular automaton on Soldered's Inkplate 6 Flick example.
Why it fits: it is a chunky 1-bit animation with solid blocks, closer to e-ink's strengths than thin vector lines. A blob-and-glider style grid would look good on a 400x300 panel.
Difficulty: live compute, moderate. Feasible in C on RP2040.
Source: https://components.espressif.com/components/solderedelectronics/inkplate/versions/1.2.0/examples/inkplate6flick/projects/game_of_life

Reality-check references (not demos, but they set your speed budget):

7. Inkplate 6 MOTION partial refresh
Soldered claims 11 fps from partial refresh. Hackaday reports this as the vendor's claim and says the author did not measure it.
Source: https://hackaday.com/2024/06/06/hands-on-inkplate-6-motion

8. Paperino e-paper animation mode
This project's fastest animation mode reached about 4 fps, against a standard 0.8 s update. The author says e-paper suits static content, not animation.
Source: https://hackaday.io/project/21551-paperino/log/59718-e-paper-basics-3-a-bonus-update-mode-for-animations

Notes for the team: items 1-3 fit pre-rendering from flash best, and item 6 is the best live-compute candidate. Items 7 and 8 suggest partial refresh gives a few fps at best, so favour slow, thick-stroke content and expect periodic full refreshes to clear ghosting. The Hackaday project search (oscilloscope and e-paper) and the flying-toaster and Mystify searches produced no e-ink sources, so they would need a different search angle.

## eink-art-installs

1. DAZZLE (San Diego airport, E Ink Prism). 2,100 solar-powered tiles with 15+ looping animations (ripples, traffic, snowflakes) across a building facade.
   - Why it works: a huge area moving slowly in daylight, which suits e-ink's strengths.
   - Difficulty: pre-render. The tiles are a different panel type, so only the content idea transfers.
   - Source: https://venturebeat.com/business/artists-create-the-worlds-biggest-e-ink-public-art-at-san-diego-airport and https://www.sixteen-nine.net/?p=15378

2. BMW iX Flow (CES 2022 concept). An entire car body in E Ink that flips between black and white.
   - Why it works: big, flat-colour inversions that read clearly at a distance. A 1-bit inversion wipe would be the direct analogue.
   - Difficulty: trivial pre-render, just full-screen frame flips.
   - Source: https://www.motor1.com/news/558913/bmw-color-changing-exterior-paint/ and https://coolhunting.com/technology/bmws-ix-flow-color-changing-exterior/

3. Geniatech 31.2-inch E Ink video demo (Embedded World, March 2025). Video playback on a large e-paper panel.
   - Why it works: shows that video-like content is being attempted on e-paper, and the reporter found it striking.
   - Difficulty: pre-render, with a fast waveform. The frame rate is not confirmed by the source.
   - Source: https://invidis.com/2025/03/18/heres-a-31-inch-color-e-paper-display-running-full-motion-video/ and https://www.sixteen-nine.net/?p=41462

4. Eidolon I + II by Jonas Sjøvaag. Framed e-ink screens that cycle through curated photo sequences.
   - Why it works: the slow, visible transitions are the concept itself, which matches the "slow-ish motion" look you want.
   - Difficulty: easy pre-render. Frames stream from flash, so it fits the RP2040 well.
   - Source: https://app-api.ddw.nl/en/programme/archive/2025/eidolon
   - Note: the page says the photos are from DDW 2024 and the piece is archived. A search summary had said it was on view now, and the page does not support that.

5. Pervasive Displays partial-update animation. Partial updates allow animation by refreshing only changed regions.
   - Why it works: this is the path to fast sprites and local motion without full-screen flashes.
   - Difficulty: live compute on RP2040 is feasible, since only changed regions are sent.
   - Source: https://www.eenewseurope.com/en/pervasive-introduces-partial-update-for-e-paper-displays/ (a news article, not a demo video; I did not fetch it).

6. Papercast 7.5 fps e-paper demo (2019). Reported as an experimental e-paper video-rate refresh.
   - Why it works: shows the upper bound of what has been demonstrated on e-paper.
   - Difficulty: unknown, since the technique was not described in detail.
   - Source: https://www.eenewseurope.com/news/e-paper-animation-boost-partial-updates (taken from search results; I did not fetch it, so treat the 7.5 fps figure as unverified).

7. "Meeting Time," Kaohsiung Museum of Fine Arts. E-paper displays mounted on robotic arms.
   - Why it works: physical motion combined with e-paper content.
   - Difficulty: hardware-heavy, not an RP2040 demo.
   - Source: found only in search results, not fetched.

Notes for the search:
- E Ink's own position, as reported in search results, is that current production modules do not support video-rate updates. This is not confirmed by a fetched page.
- Visionect did not turn up a usable demo source, so I did not list it.

