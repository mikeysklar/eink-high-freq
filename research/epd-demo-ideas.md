# Fast-refresh e-ink demo shortlist: SSD1683, 400x300, Feather RP2040

All fps figures below are **estimates**. They are capped by our measured numbers: 89 fps for a small sprite, 62 fps for a 320x208 window, and 36 fps full screen. A raw full frame is 15 KB, so the 3-4 MB of free flash holds about 200-260 uncompressed frames. Longer pre-rendered loops need RLE or delta compression.

## Top 12, ranked by wow times feasibility

### 1. Bad Apple, delta-encoded video
- **Viewer sees:** The full Bad Apple silhouette video playing at video rate on a 4.2" e-ink panel.
- **Why it shows off the panel:** It's the best-known "this can't be e-ink" clip. Its high-contrast silhouettes suit 1-bit output.
- **FPS (est.):** 24-30 full screen, as long as the decode is cheap. Window mode isn't needed.
- **Approach:** Pre-render on the Mac, then stream from flash. Bad Apple compresses very well with RLE or XOR deltas against the previous frame, so a minute or more could fit in 3 MB. The player can be CircuitPython. C is only needed if the decode can't keep up.
- **E-ink tuning:** The source is already 1-bit, so skip dithering and threshold it. Clean up ghosting with a full refresh at scene cuts.
- **Sources:** https://www.tonyweston.uk/web/badapple/index.html, https://hackaday.com/2026/07/21/20-fps-on-e-paper-display-without-help/

### 2. Raycaster corridor (Wolfenstein/Doom-style)
- **Viewer sees:** A first-person walk through solid-walled corridors, with distance shown as dithered shading.
- **Why it shows off the panel:** "Doom on e-ink" exists, but the precedents run at 1.6 fps or report no fps at all. Running it at 20+ fps would be new.
- **FPS (est.):** 15-30 in a 320x208 window, compute-bound. Render at 160x104 and double the pixels.
- **Approach:** Live in C. The Pico EL Doom port shows that the RP2040 can handle the work. A pre-rendered fly-through is the fallback.
- **E-ink tuning:** Flat walls with 4x4 Bayer shading per wall face, and slow turning speed. Avoid thin texture detail.
- **Sources:** https://www.hackster.io/news/michael-p-gets-an-industrial-electroluminescent-display-and-doom-running-on-a-raspberry-pi-pico-6813b4750dba, https://github.com/psychoplath9450/sumi-doom

### 3. Metaballs
- **Viewer sees:** Large black blobs that drift, merge and pinch apart.
- **Why it shows off the panel:** Organic, continuous motion is the opposite of what people expect from e-ink. The blobs are solid shapes, so ghosting stays low.
- **FPS (est.):** 40-62 in a window and about 30 full screen, if the field is computed on a coarse grid and interpolated.
- **Approach:** Live in C. CircuitPython only works on a coarse 50x38 grid with blocky cells.
- **E-ink tuning:** Solid fill with a 2-3 px edge band. Keep the speed to a few px per frame.
- **Source:** https://www.lexaloffle.com/bbs/?tid=29314

### 4. Demoscene tunnel
- **Viewer sees:** Checkerboard rings rushing toward the viewer, with a slow twist.
- **Why it shows off the panel:** This is the classic demoscene effect, and it is unmistakably "fast."
- **FPS (est.):** 36 full screen pre-rendered. Live in C at 200x150, doubled, fits the 62 fps window.
- **Approach:** Pre-render a seamless loop of about 60 frames (roughly 900 KB raw). A live version needs angle and distance tables at quarter resolution so they fit in 264 KB.
- **E-ink tuning:** Make the checks at least 8 px and keep ring speed moderate. Thin rings smear.
- **Source:** https://carette.xyz/posts/the_tunnel_effect_demoscene/

### 5. Reaction-diffusion (Gray-Scott), with Lenia as an alternative
- **Viewer sees:** Turing spots and worms growing, splitting and crawling across the whole screen.
- **Why it shows off the panel:** Whole-screen organic change, and nobody has found one on e-ink before.
- **FPS (est.):** 30-36 full screen.
- **Approach:** Pre-render only. The simulation is too heavy for the RP2040. Compress it with deltas.
- **E-ink tuning:** Threshold to 1-bit and pick parameters that give thick worms. Slow changes ghost the least.
- **Sources:** https://github.com/moshejs/reaction-diffusion, https://arxiv.org/pdf/1812.05433

### 6. Dithered 3D turntable (Crank the World style)
- **Viewer sees:** A shaded, raytraced object (spheres, a Menger sponge, a torus) slowly orbiting, with smooth tonal gradients made from dither.
- **Why it shows off the panel:** It shows "grayscale" 3D graphics on a 1-bit panel.
- **FPS (est.):** 36 full screen, or 62 for a windowed object.
- **Approach:** Pre-render with surface-stable or blue-noise dither.
- **E-ink tuning:** Use surface-stable dither so the dots don't flicker frame to frame. Rotate slowly.
- **Sources:** https://aras-p.info/blog/2024/05/20/Crank-the-World-Playdate-demo/, https://aras-p.info/blog/2025/02/09/Surface-Stable-Fractal-Dither-on-Playdate/

### 7. Tilt marble maze
- **Viewer sees:** Tilting the board rolls a heavy ball through a thick-walled maze.
- **Why it shows off the panel:** It's interactive, with instant response on e-ink. No e-paper version was found.
- **FPS (est.):** 60-89 with sprite-region updates.
- **Approach:** Live in CircuitPython with an accelerometer. C isn't needed.
- **E-ink tuning:** A ball of 16 px or more and walls of 6 px or more. Cap the speed so the ball doesn't trail.
- **Sources:** https://learn.adafruit.com/tilt-controlled-marble-maze/overview, https://www.blinky.games/learn/tilt-maze.html

### 8. Breakout or Pong
- **Viewer sees:** A playable arcade game with a fast ball and bricks breaking.
- **Why it shows off the panel:** A live game proves the speed better than any video. No e-paper Pong or Breakout was found.
- **FPS (est.):** 60-89, since only the ball and paddle regions change.
- **Approach:** Live CircuitPython with encoder or button input.
- **E-ink tuning:** A square ball of 8 px or more, thick paddles and solid bricks.
- **Source:** https://hackaday.io/project/27442-real-life-chrome-offline-t-rex-game/log/68187-e-ink-display (T-Rex precedent)

### 9. Falling sand
- **Viewer sees:** Grains pouring, piling and sliding, optionally tipped by tilt.
- **Why it shows off the panel:** Thousands of independent particles moving at once.
- **FPS (est.):** 20-40 in a window, compute-bound.
- **Approach:** Live in C on a 133x100 grid of 3 px grains. Python only works on a coarser grid.
- **E-ink tuning:** Grains of 3 px or more. Motion is local, so updates stay partial.
- **Sources:** https://www.instructables.com/Falling-Sand-Simulation/, https://gist.github.com/witnessmenow/29192dd0e5dda61f50900e3422cedeab

### 10. Oscilloscope-music and Lissajous figures
- **Viewer sees:** Morphing closed curves, harmonographs and the "mushroom" animation.
- **Why it shows off the panel:** Smooth vector motion, like a CRT, on paper.
- **FPS (est.):** 36 full screen pre-rendered. Live Lissajous in C reaches 40-62.
- **Approach:** Pre-render from the audio XY data. Simple Lissajous is cheap enough to run live.
- **E-ink tuning:** Strokes of 3 px or more and slow phase drift. This is the item most at risk of smear.
- **Sources:** https://oscilloscopemusic.com/info/about/, https://github.com/mbelouso/maths_fun

### 11. Truchet tile mosaic
- **Viewer sees:** Quarter-circle tiles flipping in waves, so the pattern keeps re-forming.
- **Why it shows off the panel:** Many crisp regional changes per second, with clear graphic design.
- **FPS (est.):** 60+, since each flip is a small region.
- **Approach:** Live CircuitPython with 40-60 px tiles.
- **E-ink tuning:** Arcs of 6 px or more. Flip tiles in a sweeping wave, not at random, for coherence.
- **Source:** https://github.com/paezha/truchet/blob/HEAD/vignettes/articles/a06-animated-mosaics.Rmd

### 12. Voxel-space terrain fly-over
- **Viewer sees:** A Comanche-style flight over dithered hills.
- **Why it shows off the panel:** Smooth 3D landscape motion. No microcontroller version was found.
- **FPS (est.):** 36 full screen pre-rendered.
- **Approach:** Pre-render a loop of about 200 frames.
- **E-ink tuning:** Coarse dither on the hills and a slow forward speed.
- **Sources:** https://simulationcorner.net/index.php?page=comanche, https://github.com/wenright/VoxelSpace-GPU

## Cross-cutting notes
- **Panel wear and ghosting:** Good Display recommends a full refresh after about five fast or partial refreshes. Ben Krasnow's commenters report ghosting after about 10k cycles, which is unverified. Insert a clean full refresh at loop boundaries and budget demo run time.
- **Dither:** Ordered dither shimmers when its phase moves. Keep the dither anchored to the screen or to surfaces, and move it along one axis at most (https://devforum.play.date/t/animated-dither-patterns-using-phase-offsets/10641).
- **Speed:** Our measured rates are already above every hobby e-paper number found, so content choice matters more than raw refresh.

## Best three to build next
1. **Bad Apple delta player.** It has the highest recognition, it's a pure pre-render, the player runs in CircuitPython, and its 1-bit source needs no dither. It proves full-screen video-rate playback in one clip.
2. **Tilt marble maze, or Breakout.** It's live, interactive, and at 60-89 fps it uses the measured sprite rate. No new driver work, and no e-paper precedent was found.
3. **Metaballs in C.** This is the "graphics ability" piece. It's live-computed, organic and full-window, with solid shapes that stay clean on e-ink. It also sets up the C path that the raycaster (item 2) would reuse.

## Rejected or poor fits
- **Game Boy emulators (InkBoy, PaperBoy):** They rely on per-pixel custom waveforms or raw row/column drive that SSD1683 doesn't expose, and emulation is too heavy for the RP2040.
- **32-grey and stacked-partial greyscale drivers:** These are driver research, not demos. They're slow and they add wear.
- **Krasnow LUT hack:** A technique, not a demo. Our stock speeds already beat its reported gains. Revisit only for a before/after video.
- **Physarum, DLA, Langton's ant, 10 PRINT:** Thin lines or one-cell-at-a-time growth. They smear or look slow, and don't show off speed.
- **Game of Life:** Already done on e-ink, so it's a baseline, not a wow.
- **Hourglass, SlowMovie, Eidolon, Very Slow Movie Player:** Deliberately slow, which is the opposite of the goal.
- **Spectrum analyzer:** A familiar look, it needs an FFT in C, and bar flicker ghosts.
- **Rotozoomer:** Thin rotating edges smear, and no 1-bit precedent was found. The tunnel covers the same ground.
- **Etch-a-Sketch and shake-to-erase:** Fun, but drawing speed doesn't show off the refresh rate.
- **Wave transitions (Seekink, Mynavi), DAZZLE, BMW iX Flow, 31" video panel, Modos:** These need different hardware or controller support. They're useful only as style references.
- **C64 and Spectrum dithered plasma:** A fine look, but the tunnel and reaction-diffusion items cover it with more motion.