"""Simulate passive buzzer playback with a square wave."""

from __future__ import annotations

import sys

import numpy as np
import sounddevice as sd

from melomidi.converter import BuzzerNote

SAMPLE_RATE = 22050
VOLUME = 0.28


def _render_note(hz: int, duration_ms: int, *, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    if hz <= 0 or duration_ms <= 0:
        return np.zeros(int(sample_rate * max(duration_ms, 0) / 1000), dtype=np.float32)

    count = max(1, int(sample_rate * duration_ms / 1000))
    t = np.arange(count, dtype=np.float32) / sample_rate
    wave = np.sign(np.sin(2 * np.pi * hz * t)) * VOLUME

    attack = min(count // 4, int(sample_rate * 0.004))
    release = min(count // 4, int(sample_rate * 0.008))
    envelope = np.ones(count, dtype=np.float32)
    if attack > 0:
        envelope[:attack] = np.linspace(0.0, 1.0, attack, dtype=np.float32)
    if release > 0:
        envelope[-release:] = np.linspace(1.0, 0.0, release, dtype=np.float32)

    return (wave * envelope).astype(np.float32)


def render_buzzer_sequence(
    notes: list[BuzzerNote],
    *,
    gap_ms: int = 20,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    if not notes:
        return np.array([], dtype=np.float32)

    gap = np.zeros(max(0, int(sample_rate * gap_ms / 1000)), dtype=np.float32)
    chunks: list[np.ndarray] = []
    for note in notes:
        chunks.append(_render_note(note.hz, note.duration_ms, sample_rate=sample_rate))
        if gap_ms > 0:
            chunks.append(gap)

    return np.concatenate(chunks)


def play_buzzer_sequence(
    notes: list[BuzzerNote],
    *,
    gap_ms: int = 20,
    loop: int = 1,
    sample_rate: int = SAMPLE_RATE,
) -> None:
    if not notes:
        print("warning: no notes to play", file=sys.stderr)
        return

    audio = render_buzzer_sequence(notes, gap_ms=gap_ms, sample_rate=sample_rate)
    for i in range(loop):
        if loop > 1:
            print(f"Playing ({i + 1}/{loop})...", file=sys.stderr)
        sd.play(audio, sample_rate)
        sd.wait()
