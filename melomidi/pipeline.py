"""Shared audio -> buzzer conversion pipeline."""

from __future__ import annotations

from pathlib import Path

from melomidi.converter import BuzzerNote, to_buzzer_sequence
from melomidi.extract import extract_notes


def audio_to_buzzer(
    audio_path: str | Path,
    *,
    grid_ms: int = 125,
    min_note_ms: int = 125,
    frame_ms: int = 50,
) -> list[BuzzerNote]:
    raw_notes = extract_notes(audio_path)
    return to_buzzer_sequence(
        raw_notes,
        grid_ms=grid_ms,
        min_note_ms=min_note_ms,
        frame_ms=frame_ms,
    )
