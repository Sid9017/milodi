"""Basic Pitch inference wrapper."""

from __future__ import annotations

from pathlib import Path

from basic_pitch.inference import predict

from melomidi.converter import RawNote


def extract_notes(audio_path: str | Path) -> list[RawNote]:
    """Run Basic Pitch and return note events."""
    _, _, note_events = predict(str(audio_path))

    notes: list[RawNote] = []
    for start_s, end_s, pitch_midi, amplitude, _ in note_events:
        if pitch_midi <= 0:
            continue
        notes.append(
            RawNote(
                start_s=float(start_s),
                end_s=float(end_s),
                pitch_midi=int(round(pitch_midi)),
                amplitude=float(amplitude),
            )
        )

    notes.sort(key=lambda n: (n.start_s, -n.pitch_midi))
    return notes
