"""High-frequency e-paper explainer: narration with Kokoro bm_george on the GPU (mlx-audio).

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
    ("Adafruit's 4.2-inch e-paper: 400x300 pixels and an SSD1683 controller. A stock refresh "
     "takes 6 seconds. How fast can it really go?",
     "Ada fruit's four point two inch e-paper: four hundred by three hundred pixels, and an "
     "S S D sixteen eighty-three controller. A stock refresh takes six seconds. How fast can it "
     "really go?"),
    ("Each pixel holds charged black and white pigment. Voltage pulls one color to the surface. "
     "How far the ink moves depends on voltage and time.",
     "Each pixel holds charged black and white pigment. Voltage pulls one color to the surface. "
     "How far the ink moves depends on voltage, and time."),
    ("Two numbers both get called frequency. The frame rate is how often the controller scans "
     "every row and applies a voltage: 112.5 or 125 Hz. The update rate is new pictures per second.",
     "Two numbers both get called frequency. The frame rate is how often the controller scans "
     "every row and applies a voltage: a hundred twelve and a half, or a hundred twenty-five "
     "hertz. The update rate is new pictures per second."),
    ("A waveform is a list of frames. Update time is frames divided by frame rate. The stock "
     "waveform spends most of its 6 seconds flashing black and white to clean the image.",
     "A waveform is a list of frames. Update time is frames, divided by frame rate. The stock "
     "waveform spends most of its six seconds flashing black and white, to clean the image."),
    ("So far: stock, 0.17 fps. A custom 20-frame LUT: 3. Six frames: 11, then 15 with "
     "row-band writes. Four frames: 20. And 22 at 125 Hz.",
     "So far: stock, zero point one seven frames per second. A custom twenty frame lut: "
     "three. Six frames: eleven, then fifteen with row band writes. Four frames: twenty. And "
     "twenty-two, at a hundred twenty-five hertz."),
    ("Trick one: our own waveform. Only pixels that change get pushed: 4 frames toward black, "
     "or 4 toward white. Unchanged pixels get zero volts.",
     "Trick one: our own waveform. Only pixels that change get pushed: four frames toward "
     "black, or four toward white. Unchanged pixels get zero volts."),
    ("Trick two: stop paying overhead. Power up the analog side once, then send display-only "
     "updates. Turn off RAM ping-pong, and send only the rows that changed.",
     "Trick two: stop paying overhead. Power up the analog side once, then send display only "
     "updates. Turn off ram ping pong, and send only the rows that changed."),
    ("Trick three: the frame rate. Our notes said 112.5 Hz was the maximum. The datasheet table "
     "goes to 125. Same four frames: 49 ms became 45.",
     "Trick three: the frame rate. Our notes said a hundred twelve and a half hertz was the "
     "maximum. The datasheet table goes to a hundred twenty-five. Same four frames: forty-nine "
     "milliseconds became forty-five."),
    ("Where the 45 ms goes: 32 waiting on the panel, about 9 on SPI, about 3 in Python.",
     "Where the forty-five milliseconds goes: thirty-two waiting on the panel, about nine on "
     "S P I, about three in Python."),
    ("The cost: four frames don't move the ink all the way. Black looks gray, and a ghost trail "
     "follows the square. A full refresh wipes it.",
     "The cost: four frames don't move the ink all the way. Black looks gray, and a ghost trail "
     "follows the square. A full refresh wipes it."),
    ("PaperBoy is different. The M5PaperS3 panel has no controller. The ESP32-S3 drives the row "
     "and column lines itself, choosing the voltage for every pixel, every frame. It reports up "
     "to 60 fps in a small game area.",
     "PaperBoy is different. The M five Paper S three panel has no controller. The E S P "
     "thirty-two S three drives the row and column lines itself, choosing the voltage for every "
     "pixel, every frame. It reports up to sixty frames per second, in a small game area."),
    ("InkBoy reached about 30 fps on a panel with a controller: a 2-step waveform, and the host "
     "gives each pixel a budget of 6 to 8 pulses for a full black-to-white change.",
     "InkBoy reached about thirty frames per second on a panel with a controller: a two step "
     "waveform, and the host gives each pixel a budget of six to eight pulses, for a full black "
     "to white change."),
    ("The route for Adafruit panels, all estimates: write the next frame while the panel is "
     "busy, about 26 fps. A 2-frame LUT with per-pixel budgets, about 35. Both, maybe 50. "
     "60 to 70 would need one frame per update, and nobody has shown that with a controller.",
     "The route for Ada fruit panels, all estimates: write the next frame while the panel is "
     "busy, about twenty-six. A two frame lut with per pixel budgets, about thirty-five. Both, "
     "maybe fifty. Sixty to seventy would need one frame per update, and nobody has shown that "
     "with a controller."),
    ("Is it safe? Not proven either way. Good Display warns that pushing the frame rate too high "
     "can damage the panel. One builder saw burn-in after about 10,000 fast cycles. InkBoy warns "
     "of permanent image retention.",
     "Is it safe? Not proven either way. Good Display warns that pushing the frame rate too high "
     "can damage the panel. One builder saw burn in after about ten thousand fast cycles. InkBoy "
     "warns of permanent image retention."),
    ("Keep the risk down: equal frames toward black and white, so charge balances. Zero volts on "
     "unchanged pixels. Stock voltages, datasheet frame rates. Regular full refreshes, power down "
     "when done, and no animating for hours.",
     "Keep the risk down: equal frames toward black and white, so charge balances. Zero volts on "
     "unchanged pixels. Stock voltages, and datasheet frame rates. Regular full refreshes, power "
     "down when done, and no animating for hours."),
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
