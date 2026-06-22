"""器乐预处理：削弱打击乐与低音和声，突出旋律声部。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

BASIC_PITCH_SR = 22050
_BASS_CUTOFF_HZ = 120.0


def prepare_instrumental(audio_path: str | Path) -> Path:
    """HPSS 谐波分量 + 高通滤波，写出临时 WAV 供 Basic Pitch 分析。"""
    y, _sr = librosa.load(str(audio_path), sr=BASIC_PITCH_SR, mono=True)

    harmonic, _percussive = librosa.effects.hpss(y, margin=3.0)

    sos = butter(
        4, _BASS_CUTOFF_HZ, btype="highpass", fs=BASIC_PITCH_SR, output="sos"
    )
    melodic = sosfilt(sos, harmonic).astype(np.float32)

    peak = float(np.max(np.abs(melodic))) or 1.0
    melodic = melodic / peak * 0.9

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, melodic, BASIC_PITCH_SR)
    return Path(tmp.name)
