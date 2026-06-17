"""Convert Basic Pitch output into monophonic buzzer sequences."""

from __future__ import annotations

from dataclasses import dataclass

from melomidi.notes import midi_to_buzzer_hz, snap_midi_to_buzzer


@dataclass(frozen=True)
class BuzzerNote:
    midi: int
    hz: int
    duration_ms: int


@dataclass(frozen=True)
class RawNote:
    start_s: float
    end_s: float
    pitch_midi: int
    amplitude: float = 1.0


def _quantize_ms(value_ms: float, grid_ms: int) -> int:
    if grid_ms <= 0:
        return max(1, int(round(value_ms)))
    return max(grid_ms, int(round(value_ms / grid_ms)) * grid_ms)


def notes_to_monophonic(raw_notes: list[RawNote], frame_ms: int = 50) -> list[RawNote]:
    """Collapse polyphonic output to a single melody line (highest pitch wins)."""
    if not raw_notes:
        return []

    end_s = max(n.end_s for n in raw_notes)
    frame_s = frame_ms / 1000.0
    mono: list[RawNote] = []
    t = 0.0

    while t < end_s:
        active = [n for n in raw_notes if n.start_s <= t < n.end_s]
        if active:
            winner = max(active, key=lambda n: (n.pitch_midi, n.amplitude))
            if mono and mono[-1].pitch_midi == winner.pitch_midi:
                mono[-1] = RawNote(
                    start_s=mono[-1].start_s,
                    end_s=t + frame_s,
                    pitch_midi=winner.pitch_midi,
                    amplitude=winner.amplitude,
                )
            else:
                mono.append(
                    RawNote(
                        start_s=t,
                        end_s=t + frame_s,
                        pitch_midi=winner.pitch_midi,
                        amplitude=winner.amplitude,
                    )
                )
        t += frame_s

    return mono


def merge_adjacent(notes: list[RawNote]) -> list[RawNote]:
    if not notes:
        return []
    merged: list[RawNote] = [notes[0]]
    for note in notes[1:]:
        prev = merged[-1]
        if note.pitch_midi == prev.pitch_midi:
            merged[-1] = RawNote(
                start_s=prev.start_s,
                end_s=note.end_s,
                pitch_midi=prev.pitch_midi,
                amplitude=max(prev.amplitude, note.amplitude),
            )
        else:
            merged.append(note)
    return merged


def to_buzzer_sequence(
    raw_notes: list[RawNote],
    *,
    grid_ms: int = 125,
    min_note_ms: int = 125,
    frame_ms: int = 50,
) -> list[BuzzerNote]:
    mono = merge_adjacent(notes_to_monophonic(raw_notes, frame_ms=frame_ms))
    result: list[BuzzerNote] = []

    for note in mono:
        duration_ms = _quantize_ms((note.end_s - note.start_s) * 1000.0, grid_ms)
        if duration_ms < min_note_ms:
            continue
        midi = snap_midi_to_buzzer(note.pitch_midi)
        hz = midi_to_buzzer_hz(midi)
        if result and result[-1].midi == midi:
            result[-1] = BuzzerNote(
                midi=midi,
                hz=hz,
                duration_ms=result[-1].duration_ms + duration_ms,
            )
        else:
            result.append(BuzzerNote(midi=midi, hz=hz, duration_ms=duration_ms))

    return result
