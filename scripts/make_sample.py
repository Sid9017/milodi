#!/usr/bin/env python3
"""Generate a simple monophonic WAV for testing milodi."""

import math
import wave
from pathlib import Path

SAMPLE_RATE = 22050
OUT_PATH = Path("/tmp/milodi_sample.wav")

# Twinkle twinkle little star (C major), (midi, beats)
SCORE = [
    (60, 1), (60, 1), (67, 1), (67, 1), (69, 1), (69, 1), (67, 2),
    (65, 1), (65, 1), (64, 1), (64, 1), (62, 1), (62, 1), (60, 2),
]
BEAT_MS = 400


def midi_to_freq(midi: int) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def main() -> None:
    samples: list[int] = []
    for midi, beats in SCORE:
        freq = midi_to_freq(midi)
        n = int(SAMPLE_RATE * BEAT_MS * beats / 1000)
        for i in range(n):
            t = i / SAMPLE_RATE
            val = math.sin(2 * math.pi * freq * t) * 0.35
            samples.append(int(val * 32767))

    with wave.open(str(OUT_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(s.to_bytes(2, "little", signed=True) for s in samples))

    print(f"Wrote {OUT_PATH} ({len(samples) / SAMPLE_RATE:.1f}s)")


if __name__ == "__main__":
    main()
