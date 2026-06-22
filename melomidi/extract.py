"""主旋律提取配置与算法。"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from basic_pitch.inference import predict

from melomidi.notes import BuzzerNote, midi_to_hz, midi_to_name, snap_midi

NoteEvent = tuple[float, float, int, float, list | None]


@dataclass
class MelodyNote:
    start_ms: int
    duration_ms: int
    midi: int
    hz: int
    name: str
    velocity: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MonophonizeMode = Literal["salience", "highest"]


@dataclass
class ExtractConfig:
    """Basic Pitch 与后处理参数。

    钢琴高保真请用 ``PIANO_CONFIG``：保留 Basic Pitch 检测到的全部音符，
    不做单声部化、量化或蜂鸣器音高吸附。
    """

    onset_threshold: float = 0.55
    frame_threshold: float = 0.38
    minimum_note_length: float = 180.0
    minimum_frequency: float | None = 150.0
    maximum_frequency: float | None = 1200.0
    melodia_trick: bool = True

    frame_ms: float = 10.0
    min_segment_ms: int = 150
    merge_gap_ms: int = 40
    quantize_grid_ms: int = 125
    min_amplitude: float = 0.15
    max_pitch_jump: int = 7

    preprocess: bool = False
    monophonize: MonophonizeMode = "salience"
    polyphonic: bool = False


DEFAULT_CONFIG = ExtractConfig()

INSTRUMENTAL_CONFIG = ExtractConfig(
    onset_threshold=0.45,
    frame_threshold=0.28,
    minimum_note_length=100.0,
    minimum_frequency=130.0,
    maximum_frequency=2000.0,
    melodia_trick=True,
    min_segment_ms=80,
    merge_gap_ms=60,
    quantize_grid_ms=100,
    min_amplitude=0.10,
    max_pitch_jump=12,
    preprocess=True,
    monophonize="highest",
)

# 钢琴：Basic Pitch 默认灵敏度，保留全部检测音符与原始时值/音高
PIANO_CONFIG = ExtractConfig(
    onset_threshold=0.5,
    frame_threshold=0.3,
    minimum_note_length=58.0,
    minimum_frequency=None,
    maximum_frequency=None,
    melodia_trick=True,
    min_amplitude=0.05,
    preprocess=False,
    polyphonic=True,
)


def _predict_notes(
    audio_path: Path,
    cfg: ExtractConfig,
) -> tuple[Any, Any, list[NoteEvent]]:
    analysis_path = audio_path
    tmp_path: Path | None = None

    if cfg.preprocess:
        from melomidi.preprocess import prepare_instrumental

        tmp_path = prepare_instrumental(analysis_path)
        analysis_path = tmp_path

    try:
        return predict(
            str(analysis_path),
            onset_threshold=cfg.onset_threshold,
            frame_threshold=cfg.frame_threshold,
            minimum_note_length=cfg.minimum_note_length,
            minimum_frequency=cfg.minimum_frequency,
            maximum_frequency=cfg.maximum_frequency,
            melodia_trick=cfg.melodia_trick,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def _map_polyphonic(
    note_events: list[NoteEvent],
    min_amplitude: float,
) -> list[MelodyNote]:
    """保留 Basic Pitch 全部音符，不做后处理压缩。"""
    notes: list[MelodyNote] = []
    for start, end, pitch, amp, _bends in note_events:
        if amp < min_amplitude:
            continue
        midi = int(pitch)
        start_ms = int(round(start * 1000))
        duration_ms = max(1, int(round((end - start) * 1000)))
        notes.append(
            MelodyNote(
                start_ms=start_ms,
                duration_ms=duration_ms,
                midi=midi,
                hz=midi_to_hz(midi),
                name=midi_to_name(midi),
                velocity=max(1, min(127, int(round(amp * 127)))),
            )
        )
    return sorted(notes, key=lambda n: (n.start_ms, n.midi))


def _monophonize(
    note_events: list[NoteEvent],
    frame_ms: float,
    min_amplitude: float,
    mode: MonophonizeMode,
) -> list[tuple[int, int, int]]:
    if mode == "highest":
        return _monophonize_by_highest_pitch(note_events, frame_ms, min_amplitude)
    return _monophonize_by_salience(note_events, frame_ms, min_amplitude)


def _monophonize_by_salience(
    note_events: list[NoteEvent],
    frame_ms: float,
    min_amplitude: float,
) -> list[tuple[int, int, int]]:
    if not note_events:
        return []

    filtered = [e for e in note_events if e[3] >= min_amplitude]
    if not filtered:
        filtered = note_events

    end_s = max(e[1] for e in filtered)
    n_frames = int(math.ceil(end_s * 1000 / frame_ms)) + 1
    pitches = np.zeros(n_frames, dtype=np.int16)
    amps = np.zeros(n_frames, dtype=np.float32)

    for start, end, pitch, amp, _bends in filtered:
        i0 = max(0, int(start * 1000 / frame_ms))
        i1 = min(int(end * 1000 / frame_ms) + 1, n_frames)
        for i in range(i0, i1):
            if amp >= amps[i]:
                amps[i] = amp
                pitches[i] = pitch

    return _segments_from_pitches(pitches, frame_ms)


def _monophonize_by_highest_pitch(
    note_events: list[NoteEvent],
    frame_ms: float,
    min_amplitude: float,
) -> list[tuple[int, int, int]]:
    if not note_events:
        return []

    end_s = max(e[1] for e in note_events)
    n_frames = int(math.ceil(end_s * 1000 / frame_ms)) + 1
    pitches = np.zeros(n_frames, dtype=np.int16)

    for start, end, pitch, amp, _bends in note_events:
        if amp < min_amplitude:
            continue
        i0 = max(0, int(start * 1000 / frame_ms))
        i1 = min(int(end * 1000 / frame_ms) + 1, n_frames)
        for i in range(i0, i1):
            if pitch > pitches[i]:
                pitches[i] = pitch

    if not np.any(pitches):
        for start, end, pitch, _amp, _bends in note_events:
            i0 = max(0, int(start * 1000 / frame_ms))
            i1 = min(int(end * 1000 / frame_ms) + 1, n_frames)
            for i in range(i0, i1):
                if pitch > pitches[i]:
                    pitches[i] = pitch

    return _segments_from_pitches(pitches, frame_ms)


def _segments_from_pitches(
    pitches: np.ndarray, frame_ms: float
) -> list[tuple[int, int, int]]:
    segments: list[tuple[int, int, int]] = []
    n_frames = len(pitches)
    i = 0
    while i < n_frames:
        if pitches[i] == 0:
            i += 1
            continue
        pitch = int(pitches[i])
        j = i + 1
        while j < n_frames and pitches[j] == pitch:
            j += 1
        segments.append((int(i * frame_ms), int((j - i) * frame_ms), pitch))
        i = j
    return segments


def _filter_short(
    segments: list[tuple[int, int, int]], min_ms: int
) -> list[tuple[int, int, int]]:
    return [s for s in segments if s[1] >= min_ms]


def _merge_adjacent(
    segments: list[tuple[int, int, int]],
    gap_ms: int,
    max_pitch_jump: int,
) -> list[tuple[int, int, int]]:
    if not segments:
        return []
    merged: list[tuple[int, int, int]] = [segments[0]]
    for start_ms, dur_ms, pitch in segments[1:]:
        ps, pd, pp = merged[-1]
        end_prev = ps + pd
        gap = start_ms - end_prev
        if pitch == pp and gap <= gap_ms:
            merged[-1] = (ps, start_ms + dur_ms - ps, pp)
        elif (
            abs(pitch - pp) <= min(2, max_pitch_jump)
            and 0 <= gap <= gap_ms
        ):
            merged[-1] = (ps, start_ms + dur_ms - ps, max(pitch, pp))
        else:
            merged.append((start_ms, dur_ms, pitch))
    return merged


def _quantize_duration(ms: int, grid_ms: int) -> int:
    return max(grid_ms, int(round(ms / grid_ms)) * grid_ms)


def _map_to_buzzer(
    segments: list[tuple[int, int, int]],
    grid_ms: int,
) -> list[MelodyNote]:
    notes: list[MelodyNote] = []
    for start_ms, dur_ms, midi in segments:
        snapped: BuzzerNote | None = snap_midi(midi)
        if snapped is None:
            continue
        notes.append(
            MelodyNote(
                start_ms=start_ms,
                duration_ms=_quantize_duration(dur_ms, grid_ms),
                midi=snapped.midi,
                hz=snapped.hz,
                name=snapped.name,
            )
        )
    return notes


def extract_melody(
    audio_path: str | Path,
    config: ExtractConfig | None = None,
) -> list[MelodyNote]:
    """从音频提取音符。``PIANO_CONFIG`` 保留多声部细节；其他配置做单声部主旋律。"""
    cfg = config or DEFAULT_CONFIG
    _model_output, _midi_data, note_events = _predict_notes(Path(audio_path), cfg)

    if cfg.polyphonic:
        return _map_polyphonic(note_events, cfg.min_amplitude)

    segments = _monophonize(
        note_events, cfg.frame_ms, cfg.min_amplitude, cfg.monophonize
    )
    segments = _filter_short(segments, cfg.min_segment_ms)
    segments = _merge_adjacent(segments, cfg.merge_gap_ms, cfg.max_pitch_jump)
    return _map_to_buzzer(segments, cfg.quantize_grid_ms)
