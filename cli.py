"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from milodi.export import write_export
from milodi.extract import (
    DEFAULT_CONFIG,
    INSTRUMENTAL_CONFIG,
    PIANO_CONFIG,
    ExtractConfig,
    extract_melody,
)


def _print_table(notes) -> None:
    print(f"{'#':>4}  {'start':>6}  {'MIDI':>5}  {'vel':>3}  {'ms':>5}  Name")
    for i, n in enumerate(notes, 1):
        vel = getattr(n, "velocity", 100)
        print(
            f"{i:>4}  {n.start_ms:>6}  {n.midi:>5}  {vel:>3}  {n.duration_ms:>5}  {n.name}"
        )


def _resolve_config(args: argparse.Namespace) -> ExtractConfig:
    if args.piano:
        cfg = PIANO_CONFIG
    elif args.instrumental:
        cfg = INSTRUMENTAL_CONFIG
    else:
        cfg = ExtractConfig(
            onset_threshold=args.onset_threshold,
            frame_threshold=args.frame_threshold,
            minimum_note_length=args.min_note_ms,
            minimum_frequency=args.min_freq or None,
            maximum_frequency=args.max_freq or None,
            melodia_trick=not args.no_melodia,
        )
    if args.no_melodia:
        cfg = ExtractConfig(**{**asdict(cfg), "melodia_trick": False})
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从音频提取旋律 / 转录钢琴 MIDI")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--play", action="store_true", help="播放蜂鸣器预览")
    parser.add_argument(
        "--format",
        choices=["text", "json", "midi", "h300", "h300-detail"],
        default="text",
    )
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--start-ms", type=int, default=0, help="导出区间起点 (ms)")
    parser.add_argument("--end-ms", type=int, default=None, help="导出区间终点 (ms)")
    parser.add_argument("play_target", nargs="?", help="milodi play <file>")
    parser.add_argument(
        "--onset-threshold", type=float, default=0.55, help="Basic Pitch onset 阈值 (0–1)"
    )
    parser.add_argument(
        "--frame-threshold", type=float, default=0.38, help="Basic Pitch frame 阈值 (0–1)"
    )
    parser.add_argument(
        "--min-note-ms", type=float, default=180.0, help="最短音符长度 (ms)"
    )
    parser.add_argument(
        "--min-freq", type=float, default=150.0, help="最低频率 (Hz)，0 表示不限制"
    )
    parser.add_argument(
        "--max-freq", type=float, default=1200.0, help="最高频率 (Hz)，0 表示不限制"
    )
    parser.add_argument(
        "--no-melodia", action="store_true", help="关闭 Basic Pitch melodia_trick"
    )
    parser.add_argument(
        "--piano",
        action="store_true",
        help="钢琴模式：保留全部音符细节，多声部转 MIDI（推荐钢琴曲）",
    )
    parser.add_argument(
        "--instrumental",
        action="store_true",
        help="纯器乐主旋律：HPSS 预处理 + 单声部最高音",
    )
    args = parser.parse_args(argv)

    audio = args.audio
    if args.play_target and not audio:
        audio = args.play_target

    if not audio:
        parser.print_help()
        return 1

    if args.piano and args.instrumental:
        print("请只选择 --piano 或 --instrumental 之一", file=sys.stderr)
        return 1

    cfg = _resolve_config(args)
    if not args.piano and not args.instrumental:
        # 未指定模式时，默认钢琴高保真转录
        cfg = PIANO_CONFIG

    notes = extract_melody(audio, cfg)

    if args.format == "text" and not args.output:
        _print_table(notes)
    elif args.output:
        fmt = args.format if args.format != "text" else "json"
        out = Path(args.output)
        if out.suffix.lower() in {".mid", ".midi"}:
            fmt = "midi"
        elif out.suffix.lower() == ".hex":
            fmt = "h300"
        write_export(
            notes,
            out,
            fmt=fmt,
            start_ms=args.start_ms,
            end_ms=args.end_ms,
        )
        print(f"已写入 {out}", file=sys.stderr)
    elif args.format in {"h300", "h300-detail"}:
        from milodi.export import to_h300_detail, to_h300_hex

        if args.format == "h300-detail":
            print(to_h300_detail(notes, start_ms=args.start_ms, end_ms=args.end_ms))
        else:
            print(to_h300_hex(notes, start_ms=args.start_ms, end_ms=args.end_ms))

    if args.play or (args.play_target and audio):
        try:
            from milodi.playback import play_melody

            play_melody(notes)
        except ImportError:
            print("播放需要 sounddevice", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
