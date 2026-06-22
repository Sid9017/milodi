"""H300 蜂鸣器旋律线格式：(音符号, 时长编码) 字节对。

与 bk-hw-temp/projects/h300 的 ``beep_note.h`` / ``beep_tune.c`` 一致：
- 音符号 0–47：C3–B6（MIDI 48–95）；0xFF 休止
- 时长编码 d：实播 ms = min(5000, 50 + d×50)
"""

from __future__ import annotations

from milodi.extract import MelodyNote

BEEP_NOTE_REST = 0xFF
BEEP_NOTE_MIDI_LO = 48  # C3
BEEP_NOTE_MIDI_HI = 95  # B6


def midi_to_h300_note(midi: int) -> int | None:
    if BEEP_NOTE_MIDI_LO <= midi <= BEEP_NOTE_MIDI_HI:
        return midi - BEEP_NOTE_MIDI_LO
    return None


def ms_to_wire_dur(ms: int) -> int:
    if ms <= 50:
        return 0
    if ms >= 5000:
        return 99
    return int((ms - 50 + 25) // 50)


def wire_dur_to_ms(dcode: int) -> int:
    t = 50 + dcode * 50
    return min(5000, t)


def clip_notes_to_segment(
    notes: list[MelodyNote],
    start_ms: int,
    end_ms: int,
) -> list[MelodyNote]:
    """截取与 [start_ms, end_ms) 相交的音符并裁切边界。"""
    if start_ms >= end_ms:
        return []

    clipped: list[MelodyNote] = []
    for n in notes:
        ns = n.start_ms
        ne = n.start_ms + n.duration_ms
        if ne <= start_ms or ns >= end_ms:
            continue
        clip_start = max(ns, start_ms)
        clip_end = min(ne, end_ms)
        dur = clip_end - clip_start
        if dur <= 0:
            continue
        clipped.append(
            MelodyNote(
                start_ms=clip_start,
                duration_ms=dur,
                midi=n.midi,
                hz=n.hz,
                name=n.name,
                velocity=n.velocity,
            )
        )
    return sorted(clipped, key=lambda n: (n.start_ms, n.midi))


def notes_to_h300_pairs(notes: list[MelodyNote]) -> list[tuple[int, int]]:
    """将音符列表串行化为 H300 (note, duration_code) 对（多声部按时间展开）。"""
    if not notes:
        return []

    ordered = sorted(notes, key=lambda n: (n.start_ms, n.midi))
    pairs: list[tuple[int, int]] = []
    cursor = ordered[0].start_ms

    for n in ordered:
        if n.start_ms > cursor:
            gap = n.start_ms - cursor
            pairs.append((BEEP_NOTE_REST, ms_to_wire_dur(gap)))
            cursor = n.start_ms

        note_byte = midi_to_h300_note(n.midi)
        if note_byte is not None:
            pairs.append((note_byte, ms_to_wire_dur(n.duration_ms)))
        else:
            pairs.append((BEEP_NOTE_REST, ms_to_wire_dur(n.duration_ms)))

        end_ms = n.start_ms + n.duration_ms
        if end_ms > cursor:
            cursor = end_ms

    return pairs


def pairs_to_hex(pairs: list[tuple[int, int]], *, topic: int | None = None) -> str:
    """空格分隔十六进制，可选前缀 topic（如 0x41）。"""
    parts: list[str] = []
    if topic is not None:
        parts.append(f"{topic:02x}")
    for note, dur in pairs:
        parts.append(f"{note:02x}")
        parts.append(f"{dur:02x}")
    return " ".join(parts)


def pairs_to_lines(pairs: list[tuple[int, int]]) -> str:
    """人类可读：每行一对 note duration。"""
    lines = ["# H300 melody pairs: note duration (note 0=C3 .. 47=B6, ff=rest)"]
    for note, dur in pairs:
        ms = wire_dur_to_ms(dur)
        if note == BEEP_NOTE_REST:
            pitch = "REST"
        else:
            pitch = f"MIDI_{note + BEEP_NOTE_MIDI_LO}"
        lines.append(f"{note:02x} {dur:02x}  # {pitch}, ~{ms}ms")
    return "\n".join(lines) + "\n"
