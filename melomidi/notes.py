"""MIDI / frequency helpers for buzzer output."""

from __future__ import annotations

# Arduino-style note frequencies (Hz), MIDI note number -> Hz
NOTE_FREQS: dict[int, int] = {
    24: 33, 25: 35, 26: 37, 27: 39, 28: 41, 29: 44, 30: 46, 31: 49,
    32: 52, 33: 55, 34: 58, 35: 62, 36: 65, 37: 69, 38: 73, 39: 78,
    40: 82, 41: 87, 42: 93, 43: 98, 44: 104, 45: 110, 46: 117, 47: 123,
    48: 131, 49: 139, 50: 147, 51: 156, 52: 165, 53: 175, 54: 185, 55: 196,
    56: 208, 57: 220, 58: 233, 59: 247, 60: 262, 61: 277, 62: 294, 63: 311,
    64: 330, 65: 349, 66: 370, 67: 392, 68: 415, 69: 440, 70: 466, 71: 494,
    72: 523, 73: 554, 74: 587, 75: 622, 76: 659, 77: 698, 78: 740, 79: 784,
    80: 831, 81: 880, 82: 932, 83: 988, 84: 1047, 85: 1109, 86: 1175, 87: 1245,
    88: 1319, 89: 1397, 90: 1480, 91: 1568, 92: 1661, 93: 1760, 94: 1865, 95: 1976,
}

NOTE_NAMES: dict[int, str] = {
    60: "NOTE_C4", 61: "NOTE_CS4", 62: "NOTE_D4", 63: "NOTE_DS4", 64: "NOTE_E4",
    65: "NOTE_F4", 66: "NOTE_FS4", 67: "NOTE_G4", 68: "NOTE_GS4", 69: "NOTE_A4",
    70: "NOTE_AS4", 71: "NOTE_B4", 72: "NOTE_C5", 73: "NOTE_CS5", 74: "NOTE_D5",
    75: "NOTE_DS5", 76: "NOTE_E5", 77: "NOTE_F5", 78: "NOTE_FS5", 79: "NOTE_G5",
    80: "NOTE_GS5", 81: "NOTE_A5", 82: "NOTE_AS5", 83: "NOTE_B5", 84: "NOTE_C6",
}


def snap_midi_to_buzzer(midi: int, min_midi: int = 48, max_midi: int = 84) -> int:
    """Clamp and snap to nearest supported buzzer note."""
    midi = max(min_midi, min(max_midi, int(round(midi))))
    if midi in NOTE_FREQS:
        return midi
    return min(NOTE_FREQS.keys(), key=lambda n: abs(n - midi))


def midi_to_buzzer_hz(midi: int) -> int:
    snapped = snap_midi_to_buzzer(midi)
    return NOTE_FREQS[snapped]


def midi_to_note_name(midi: int) -> str:
    snapped = snap_midi_to_buzzer(midi)
    return NOTE_NAMES.get(snapped, f"{NOTE_FREQS[snapped]}")
