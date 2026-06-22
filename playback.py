"""方波蜂鸣器预览播放。"""

from __future__ import annotations

import time

import numpy as np
import sounddevice as sd

from milodi.extract import MelodyNote

SAMPLE_RATE = 22050


def _square_wave(freq: float, duration_s: float, volume: float = 0.3) -> np.ndarray:
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * volume
    attack = min(int(SAMPLE_RATE * 0.005), n)
    release = min(int(SAMPLE_RATE * 0.01), n)
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return (wave * env).astype(np.float32)


def play_melody(notes: list[MelodyNote], gap_ms: int = 20) -> None:
    gap_s = gap_ms / 1000.0
    for note in notes:
        if note.hz <= 0:
            time.sleep(note.duration_ms / 1000.0)
            continue
        audio = _square_wave(note.hz, note.duration_ms / 1000.0)
        sd.play(audio, SAMPLE_RATE)
        sd.wait()
        time.sleep(gap_s)
