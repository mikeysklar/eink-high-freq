"""SmoothEPD vs our fast e-ink explainer: narration with Kokoro bm_george on the GPU (mlx-audio).

Writes vo/line_NN.wav (24 kHz mono, 16-bit) and vo/lines.json. Run timing.py next for word
timings. Usage: ~/.venvs/mlx-audio/bin/python narrate.py [line numbers to redo]
"""
import json
import pathlib
import sys
import wave

import espeakng_loader

espeakng_loader.get_library_path = lambda: "/opt/homebrew/lib/libespeak-ng.dylib"
espeakng_loader.get_data_path = lambda: "/opt/homebrew/share/espeak-ng-data"

import numpy as np  # noqa: E402
from mlx_audio.tts.utils import load_model  # noqa: E402

VOICE, SPEED, SR = "bm_george", 1.12, 24000

# (what the viewer reads, what the voice says)
LINES = [
    ("SmoothEPD comes from a line of fast e-paper hacks. PaperBoy drove a raw parallel panel at "
     "60 Hz. InkBoy got about 30 fps from a 1.54-inch SSD1681. SmoothEPD states 47 Hz on the same "
     "200x200 panel.",
     "Smooth E P D comes from a line of fast e-paper hacks. PaperBoy drove a raw parallel panel, "
     "at sixty hertz. InkBoy got about thirty frames a second from a one point five four inch, "
     "S S D sixteen eighty-one. Smooth E P D states forty-seven hertz, on the same two hundred by "
     "two hundred panel."),
    ("Those panels, and our 4.2-inch SSD1683, sit behind a controller. You send a picture, and it "
     "applies a fixed waveform to each old-to-new change. No per-pixel control.",
     "Those panels, and our four point two inch S S D sixteen eighty-three, sit behind a "
     "controller. You send a picture, and it applies a fixed waveform to each old-to-new change. "
     "No per-pixel control."),
    ("The trick: the two RAM planes stop being pictures. One means drive black, the other drive "
     "white, with a one-frame LUT of about 20 ms. A pixel in neither plane holds.",
     "The trick: the two RAM planes stop being pictures. One means, drive black. The other, drive "
     "white. With a one-frame lut, of about twenty milliseconds. A pixel in neither plane, holds."),
    ("Each pixel gets a budget of 7 scans, about 140 ms. The budget reloads whenever the pixel's "
     "target changes, even if it flips back halfway.",
     "Each pixel gets a budget of seven scans, about a hundred and forty milliseconds. The budget "
     "reloads whenever the pixel's target changes, even if it flips back halfway."),
    ("Slowed down: a pixel goes black for 2 frames, then back to white. SmoothEPD drives it white "
     "right away, for the full 7. Our lag trick erases it late, with only 2 white frames.",
     "Slowed down: a pixel goes black for two frames, then back to white. Smooth E P D drives it "
     "white right away, for the full seven. Our lag trick erases it late, with only two white "
     "frames."),
    ("Even a clean change is short for us: lag 6 times 8 ms is 48 ms of drive. Their budget is "
     "140, above the 120 ms their README calls the minimum.",
     "Even a clean change is short for us: lag six, times eight milliseconds, is forty-eight "
     "milliseconds of drive. Their budget is a hundred and forty, above the hundred and twenty "
     "their readme calls the minimum."),
    ("Their author also tried a net-balanced variant, where the erase only matches the on-time. "
     "He wrote that it trails heavily. That is our gray smear, and lag 6 or 8 did not fix it.",
     "Their author also tried a net-balanced variant, where the erasing pulse only matches the "
     "on-time. He wrote that it trails heavily. That is our gray smear, and lag six or eight did not fix "
     "it."),
    ("The price: full drive both ways is not DC balanced. So every pixel keeps a debt count. Every "
     "1000 scans it pays back one unit, only toward the color it already shows.",
     "The price: full drive both ways is not D C balanced. So every pixel keeps a debt count. "
     "Every thousand scans, it pays back one unit, only toward the color it already shows."),
    ("The real reset is a balanced full refresh: 66 frames, 1.3 s, every 2000 scans, about every "
     "43 s. Ours is a 3.3 s OTP clean every 15 s.",
     "The real reset is a balanced full refresh: sixty-six frames, one point three seconds, every "
     "two thousand scans. About every forty-three seconds. Ours is a three point three second "
     "O T P clean, every fifteen seconds."),
    ("Their demos are drawn to suit the panel: thick strokes, motion of one pixel per frame, "
     "digits that change every 7 frames, and slow physics.",
     "Their demo programs are drawn to suit the panel: thick strokes, motion of one pixel per "
     "frame, digits that change every seven frames, and slow physics."),
    ("What we will try, in order: budget masks for the teapot, computed on the Mac. Lag 15 as a "
     "control. Their balanced refresh LUT. A same-color settle. A coarser dither. Faster SPI.",
     "What we will try, in order: budget masks for the teapot, computed on the Mac. Lag fifteen, "
     "as a control. Their balanced refresh lut. A same-color settle. A coarser dither. And faster "
     "S P I."),
    ("Caveats: 47 Hz is the author's own claim; nobody else has measured it. Breaking DC balance "
     "needs Mikey's OK. And panel lifetime under any of this is unknown.",
     "Caveats: forty-seven hertz is the author's own claim; nobody else has measured it. Breaking "
     "D C balance needs Mikey's OK. And panel lifetime, under any of this, is unknown."),
]

out = pathlib.Path(__file__).parent / "vo"
out.mkdir(exist_ok=True)
redo = {int(a) for a in sys.argv[1:]}
model = load_model("mlx-community/Kokoro-82M-bf16")
for i, (display, spoken) in enumerate(LINES):
    path = out / f"line_{i:02d}.wav"
    if redo and i not in redo and path.exists():
        continue
    chunks = [np.array(r.audio) for r in model.generate(text=spoken, voice=VOICE, speed=SPEED,
                                                        lang_code="b")]
    audio = np.concatenate(chunks).astype(np.float32)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{i}: {len(audio) / SR:.1f}s")
json.dump([{"display": d, "spoken": s} for d, s in LINES], open(out / "lines.json", "w"), indent=1)
