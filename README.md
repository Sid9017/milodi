# melomidi

从音频（MP3/WAV 等）提取主旋律，转成蜂鸣器可播放的 `melody[]` / `noteDurations[]` 数组，并可用方波模拟无源蜂鸣器预览。

基于 [Spotify Basic Pitch](https://github.com/spotify/basic-pitch) 做音符检测，再单声部化 + 量化，输出格式兼容 [ESP Audio Grid Sequencer](https://www.espboards.dev/tools/audio-grid-sequencer/)。

## 安装

**需要 Python 3.10 或 3.11**（macOS 上 Basic Pitch 的 TensorFlow 暂不支持 3.12+）。

```bash
cd melomidi
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

首次运行会下载 Basic Pitch 模型（约几十 MB）。若 `python` 被 shell alias 到系统 Python，请直接用 `.venv/bin/melomidi`。

## 用法

```bash
# 文本预览（音高、时长、音名）
melomidi song.mp3

# 转换后直接播放蜂鸣器预览
melomidi song.mp3 --play
melomidi play song.mp3

# 导出 Arduino 数组
melomidi song.mp3 --format arduino -o melody.h

# 循环播放、音符间静音间隔
melomidi play song.mp3 --loop 2 --gap-ms 30 -q
```

## 示例

```bash
.venv/bin/python scripts/make_sample.py
.venv/bin/melomidi /tmp/melomidi_sample.wav
.venv/bin/melomidi play /tmp/melomidi_sample.wav
```

测试曲为《小星星》前两句，输出应接近：

```
  #  MIDI     Hz     ms  Name
  1    60    262    750  NOTE_C4
  2    67    392    750  NOTE_G4
  3    69    440    875  NOTE_A4
  ...
```

换你自己的 MP3：

```bash
.venv/bin/melomidi play your_song.mp3
.venv/bin/melomidi your_song.mp3 --format arduino -o melody.h
```

## 流程

1. Basic Pitch 检测多声部音符
2. 按时间帧取最高音 → 单声部主旋律
3. 合并相邻相同音高
4. 时长量化到网格
5. 映射到标准蜂鸣器频率（`NOTE_C4` 等）
6. 方波 + 短包络模拟无源蜂鸣器播放

复杂编曲效果有限，建议把输出当作初稿再人工微调。
