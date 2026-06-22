"""从音频提取主旋律并转换为蜂鸣器音符数组。"""

from milodi.extract import PIANO_CONFIG, INSTRUMENTAL_CONFIG, ExtractConfig, extract_melody

__all__ = ["ExtractConfig", "INSTRUMENTAL_CONFIG", "PIANO_CONFIG", "extract_melody"]
