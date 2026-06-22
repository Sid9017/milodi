# milodi

从音频（MP3 / WAV / M4A / FLAC / OGG）提取旋律，导出为 JSON、MIDI 或 H300 蜂鸣器线格式，并可用方波模拟无源蜂鸣器预览。

基于 [Spotify Basic Pitch](https://github.com/spotify/basic-pitch) 做音符检测，支持钢琴高保真多声部转录与器乐主旋律单声部提取两种工作流。

## 功能

- **钢琴模式**（默认）：保留 Basic Pitch 检测到的全部音符，适合钢琴曲转 MIDI
- **器乐模式**（`--instrumental`）：HPSS 预处理 + 单声部最高音，输出适合蜂鸣器播放的主旋律
- **导出格式**：文本表格、`json`、`midi`、`h300`（十六进制线格式）、`h300-detail`（可读明细）
- **H300 兼容**：输出格式与 `bk-hw-temp/projects/h300` 的 `beep_note.h` / `beep_tune.c` 一致
- **Web UI**：上传音频、可视化音谱、区间裁剪、导出旋律

## 环境要求

**Python 3.10 或 3.11**（macOS 上 Basic Pitch 的 TensorFlow 暂不支持 3.12+）。

## 安装

```bash
git clone git@github.com:Sid9017/milodi.git
cd milodi
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# 可选：安装 Web UI 依赖
pip install -e ".[web]"
```

首次运行会下载 Basic Pitch 模型（约几十 MB）。若 shell 里 `python` 指向系统 Python，请直接用 `.venv/bin/milodi`。

## 命令行用法

```bash
# 钢琴转录（默认）：文本预览音符列表
milodi song.mp3

# 器乐主旋律：单声部 + 蜂鸣器音高吸附
milodi song.mp3 --instrumental

# 方波蜂鸣器预览
milodi song.mp3 --play
milodi song.mp3 --instrumental --play

# 导出 MIDI
milodi song.mp3 -o output.mid

# 导出 JSON
milodi song.mp3 --format json -o melody.json

# 导出 H300 十六进制线格式（.hex 自动识别格式）
milodi song.mp3 --instrumental -o melody.hex

# 导出 H300 可读明细
milodi song.mp3 --format h300-detail

# 只导出音频片段（毫秒）
milodi song.mp3 --start-ms 5000 --end-ms 15000 -o clip.hex --format h300
```

### 常用参数

| 参数 | 说明 |
|------|------|
| `--piano` | 显式启用钢琴多声部模式（与默认行为相同） |
| `--instrumental` | 器乐主旋律模式 |
| `--onset-threshold` | Basic Pitch onset 阈值（0–1，默认 0.55） |
| `--frame-threshold` | Basic Pitch frame 阈值（0–1，默认 0.38） |
| `--min-note-ms` | 最短音符长度（ms） |
| `--min-freq` / `--max-freq` | 频率范围（Hz） |
| `--no-melodia` | 关闭 Basic Pitch 的 melodia_trick |

## Web UI

```bash
.venv/bin/python -m milodi.web.app
# 浏览器打开 http://127.0.0.1:8765
```

支持上传音频、切换钢琴 / 器乐模式、在音谱上选取导出区间，并下载 H300 格式文件。

## 快速测试

```bash
.venv/bin/python scripts/make_sample.py
.venv/bin/milodi /tmp/milodi_sample.wav --instrumental
.venv/bin/milodi /tmp/milodi_sample.wav --instrumental --play
```

测试曲为《小星星》前两句。器乐模式下输出应接近：

```
   #  start   MIDI  vel    ms  Name
   1       0     60  100   750  NOTE_C4
   2     750     67  100   750  NOTE_G4
   3    1500     69  100   875  NOTE_A4
   ...
```

## 处理流程

**钢琴模式**

1. Basic Pitch 检测音符
2. 按振幅过滤，保留全部声部
3. 输出原始 MIDI 音高与时值

**器乐模式**

1. HPSS 谐波提取 + 高通滤波（削弱打击乐与低音）
2. Basic Pitch 检测音符
3. 按时间帧取最高音 → 单声部主旋律
4. 合并相邻相同音高、量化时长
5. 映射到标准蜂鸣器频率（`NOTE_C4` 等）

复杂编曲效果有限，建议把输出当作初稿再人工微调。

## 项目结构

```
milodi/
├── cli.py            # 命令行入口
├── extract.py        # 旋律提取
├── export.py         # JSON / MIDI / H300 导出
├── h300.py           # H300 蜂鸣器线格式
├── playback.py       # 方波预览播放
├── web/              # Flask Web UI
├── scripts/
│   └── make_sample.py
└── pyproject.toml
```

## License

见仓库根目录。
