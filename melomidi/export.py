"""导出旋律为 JSON / MIDI / H300 线格式。"""

from __future__ import annotations

import json
from pathlib import Path

import pretty_midi

from melomidi.extract import MelodyNote
from melomidi.h300 import clip_notes_to_segment, notes_to_h300_pairs, pairs_to_hex, pairs_to_lines


def to_json(notes: list[MelodyNote], indent: int = 2) -> str:
    payload = {
        "notes": [n.to_dict() for n in notes],
    }
    return json.dumps(payload, indent=indent, ensure_ascii=False)


def to_h300_hex(
    notes: list[MelodyNote],
    *,
    start_ms: int = 0,
    end_ms: int | None = None,
    topic: int | None = 0x41,
) -> str:
    if end_ms is not None:
        notes = clip_notes_to_segment(notes, start_ms, end_ms)
    elif start_ms > 0:
        notes = clip_notes_to_segment(
            notes, start_ms, max((n.start_ms + n.duration_ms for n in notes), default=start_ms)
        )
    pairs = notes_to_h300_pairs(notes)
    return pairs_to_hex(pairs, topic=topic)


def to_h300_detail(
    notes: list[MelodyNote],
    *,
    start_ms: int = 0,
    end_ms: int | None = None,
) -> str:
    if end_ms is not None:
        notes = clip_notes_to_segment(notes, start_ms, end_ms)
    elif start_ms > 0:
        notes = clip_notes_to_segment(
            notes, start_ms, max((n.start_ms + n.duration_ms for n in notes), default=start_ms)
        )
    return pairs_to_lines(notes_to_h300_pairs(notes))


def write_midi(
    notes: list[MelodyNote],
    path: str | Path,
    *,
    tempo: float = 120,
    program: int = 0,
) -> None:
    pm = _build_pretty_midi(notes, tempo=tempo, program=program)
    pm.write(str(path))


def to_midi_bytes(
    notes: list[MelodyNote],
    *,
    tempo: float = 120,
    program: int = 0,
) -> bytes:
    import io

    buf = io.BytesIO()
    _build_pretty_midi(notes, tempo=tempo, program=program).write(buf)
    return buf.getvalue()


def _build_pretty_midi(
    notes: list[MelodyNote],
    *,
    tempo: float,
    program: int,
) -> pretty_midi.PrettyMIDI:
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    inst = pretty_midi.Instrument(program=program)
    for note in notes:
        start = note.start_ms / 1000.0
        end = start + note.duration_ms / 1000.0
        inst.notes.append(
            pretty_midi.Note(
                velocity=note.velocity,
                pitch=note.midi,
                start=start,
                end=end,
            )
        )
    pm.instruments.append(inst)
    return pm


def write_export(
    notes: list[MelodyNote],
    path: str | Path,
    fmt: str = "json",
    *,
    start_ms: int = 0,
    end_ms: int | None = None,
) -> None:
    path = Path(path)
    if fmt in {"h300", "hex"}:
        path.write_text(
            to_h300_hex(notes, start_ms=start_ms, end_ms=end_ms),
            encoding="utf-8",
        )
    elif fmt == "h300-detail":
        path.write_text(
            to_h300_detail(notes, start_ms=start_ms, end_ms=end_ms),
            encoding="utf-8",
        )
    elif fmt in {"midi", "mid"}:
        segment = (
            clip_notes_to_segment(notes, start_ms, end_ms)
            if end_ms is not None
            else notes
        )
        write_midi(segment, path)
    else:
        path.write_text(to_json(notes), encoding="utf-8")
