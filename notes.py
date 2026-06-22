"""标准蜂鸣器音符频率与名称映射。"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BuzzerNote:
    midi: int
    hz: int
    name: str


# Arduino Tone 常用音符表（C4–B5）
BUZZER_NOTES: list[BuzzerNote] = [
    BuzzerNote(60, 262, "NOTE_C4"),
    BuzzerNote(61, 277, "NOTE_CS4"),
    BuzzerNote(62, 294, "NOTE_D4"),
    BuzzerNote(63, 311, "NOTE_DS4"),
    BuzzerNote(64, 330, "NOTE_E4"),
    BuzzerNote(65, 349, "NOTE_F4"),
    BuzzerNote(66, 370, "NOTE_FS4"),
    BuzzerNote(67, 392, "NOTE_G4"),
    BuzzerNote(68, 415, "NOTE_GS4"),
    BuzzerNote(69, 440, "NOTE_A4"),
    BuzzerNote(70, 466, "NOTE_AS4"),
    BuzzerNote(71, 494, "NOTE_B4"),
    BuzzerNote(72, 523, "NOTE_C5"),
    BuzzerNote(73, 554, "NOTE_CS5"),
    BuzzerNote(74, 587, "NOTE_D5"),
    BuzzerNote(75, 622, "NOTE_DS5"),
    BuzzerNote(76, 659, "NOTE_E5"),
    BuzzerNote(77, 698, "NOTE_F5"),
    BuzzerNote(78, 740, "NOTE_FS5"),
    BuzzerNote(79, 784, "NOTE_G5"),
    BuzzerNote(80, 831, "NOTE_GS5"),
    BuzzerNote(81, 880, "NOTE_A5"),
    BuzzerNote(82, 932, "NOTE_AS5"),
    BuzzerNote(83, 988, "NOTE_B5"),
]

MIDI_TO_NOTE = {n.midi: n for n in BUZZER_NOTES}

_PITCH_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_to_hz(midi: int) -> int:
    return int(round(440.0 * (2.0 ** ((midi - 69) / 12.0))))


def midi_to_pitch_name(midi: int) -> str:
    """完整 MIDI 音名，如 C4、F#5。"""
    return f"{_PITCH_NAMES[midi % 12]}{midi // 12 - 1}"


def snap_midi(midi: int) -> BuzzerNote | None:
    if midi in MIDI_TO_NOTE:
        return MIDI_TO_NOTE[midi]
    if midi < BUZZER_NOTES[0].midi or midi > BUZZER_NOTES[-1].midi:
        return None
    return min(BUZZER_NOTES, key=lambda n: abs(n.midi - midi))


def midi_to_name(midi: int) -> str:
    if midi in MIDI_TO_NOTE:
        return MIDI_TO_NOTE[midi].name
    return f"NOTE_{midi_to_pitch_name(midi).replace('#', 'S')}"
