"""Export buzzer sequences to human-readable / Arduino formats."""

from __future__ import annotations

from melomidi.converter import BuzzerNote
from melomidi.notes import midi_to_note_name


def format_text(notes: list[BuzzerNote]) -> str:
    lines = [
        f"{'#':>3}  {'MIDI':>4}  {'Hz':>5}  {'ms':>5}  Name",
        "-" * 36,
    ]
    for i, note in enumerate(notes, 1):
        lines.append(
            f"{i:>3}  {note.midi:>4}  {note.hz:>5}  {note.duration_ms:>5}  {midi_to_note_name(note.midi)}"
        )
    total_ms = sum(n.duration_ms for n in notes)
    lines.append("-" * 36)
    lines.append(f"notes: {len(notes)}, total: {total_ms} ms ({total_ms / 1000:.1f}s)")
    return "\n".join(lines)


def format_arduino(notes: list[BuzzerNote], use_note_names: bool = True) -> str:
    melody_items: list[str] = []
    for note in notes:
        if use_note_names and note.midi in range(48, 96):
            melody_items.append(midi_to_note_name(note.midi))
        else:
            melody_items.append(str(note.hz))

    duration_items = [str(n.duration_ms) for n in notes]
    melody = ", ".join(melody_items)
    durations = ", ".join(duration_items)

    return (
        f"int melody[] = {{ {melody} }};\n"
        f"int noteDurations[] = {{ {durations} }};\n"
        f"int noteCount = {len(notes)};\n"
    )
