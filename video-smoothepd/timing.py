"""Word timings for the narration with mlx_whisper, mapped onto the display text.

Reads vo/lines.json and vo/line_NN.wav, writes vo/timing.json
([{"display", "dur", "words": [[word, start, end], ...], "heard"}]).
Usage: ~/venvs/whisper/bin/python timing.py
"""
import json
import pathlib
import re
import wave

import mlx_whisper
import numpy as np

out = pathlib.Path(__file__).parent / "vo"
lines = json.load(open(out / "lines.json"))
timing = []
for i, ln in enumerate(lines):
    path = out / f"line_{i:02d}.wav"
    with wave.open(str(path)) as w:
        dur = w.getnframes() / w.getframerate()
    res = mlx_whisper.transcribe(str(path), path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                                 word_timestamps=True, language="en")
    heard = [(w["word"].strip(), w["start"], w["end"]) for s in res["segments"] for w in s["words"]]
    # Spread the display words over the heard span, weighted by length (digits are spoken long),
    # and snap each end to the nearest real word end.
    shown = ln["display"].split()
    t0, t1 = heard[0][1], heard[-1][2]
    ends = np.array([h[2] for h in heard])
    wt = np.array([len(w) + 1 + 4 * len(re.sub(r"\D", "", w)) for w in shown], float)
    cum = np.concatenate([[0], np.cumsum(wt)]) / wt.sum()
    words = []
    for k, w in enumerate(shown):
        a = t0 + (t1 - t0) * cum[k]
        b = t0 + (t1 - t0) * cum[k + 1]
        b = float(ends[np.argmin(abs(ends - b))])
        words.append([w, round(a, 3), round(max(a + 0.05, b), 3)])
    for k in range(1, len(words)):
        words[k][1] = max(words[k][1], words[k - 1][2])
    timing.append({"display": ln["display"], "dur": dur, "words": words,
                   "heard": " ".join(h[0] for h in heard)})
    print(f"{i}: {dur:.1f}s  {timing[-1]['heard']}")
json.dump(timing, open(out / "timing.json", "w"), indent=1)
print("total narration", round(sum(t["dur"] for t in timing), 1), "s")
