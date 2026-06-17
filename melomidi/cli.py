#!/usr/bin/env python3
"""CLI: MP3/WAV -> buzzer melody via Basic Pitch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from melomidi.export import format_arduino, format_text
from melomidi.pipeline import audio_to_buzzer
from melomidi.play import play_buzzer_sequence


def _add_convert_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", type=Path, help="Input audio file (mp3, wav, etc.)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write Arduino arrays to this file (prints to stdout if omitted)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "arduino"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--grid-ms",
        type=int,
        default=125,
        help="Quantize note lengths to this grid in ms (default: 125)",
    )
    parser.add_argument(
        "--frame-ms",
        type=int,
        default=50,
        help="Time resolution for monophonic extraction (default: 50)",
    )
    parser.add_argument(
        "--min-note-ms",
        type=int,
        default=125,
        help="Drop notes shorter than this (default: 125)",
    )
    parser.add_argument(
        "--hz",
        action="store_true",
        help="Use raw Hz values in Arduino export instead of NOTE_* names",
    )


def _convert_kwargs(args: argparse.Namespace) -> dict:
    return {
        "grid_ms": args.grid_ms,
        "min_note_ms": args.min_note_ms,
        "frame_ms": args.frame_ms,
    }


def _load_buzzer_notes(args: argparse.Namespace):
    if not args.input.exists():
        print(f"error: file not found: {args.input}", file=sys.stderr)
        return None

    print(f"Analyzing {args.input} with Basic Pitch...", file=sys.stderr)
    notes = audio_to_buzzer(args.input, **_convert_kwargs(args))
    print(f"Converted to {len(notes)} buzzer notes.", file=sys.stderr)
    return notes


def convert_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract melody from audio and convert to buzzer note arrays.",
    )
    _add_convert_args(parser)
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play buzzer preview after conversion",
    )
    parser.add_argument(
        "--gap-ms",
        type=int,
        default=20,
        help="Silence gap between notes when playing (default: 20)",
    )
    args = parser.parse_args(argv)

    notes = _load_buzzer_notes(args)
    if notes is None:
        return 1

    if args.format == "arduino":
        output = format_arduino(notes, use_note_names=not args.hz)
    else:
        output = format_text(notes)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    elif not args.play:
        print(output)

    if args.play:
        print("Playing buzzer preview...", file=sys.stderr)
        play_buzzer_sequence(notes, gap_ms=args.gap_ms)

    return 0


def play_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert audio to buzzer melody and play it.",
    )
    _add_convert_args(parser)
    parser.set_defaults(format="text", output=None, hz=False)
    parser.add_argument(
        "--gap-ms",
        type=int,
        default=20,
        help="Silence gap between notes (default: 20)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=1,
        help="Number of times to play the melody (default: 1)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Do not print note table",
    )
    args = parser.parse_args(argv)

    notes = _load_buzzer_notes(args)
    if notes is None:
        return 1
    if not notes:
        print("error: no playable notes detected", file=sys.stderr)
        return 1

    if not args.quiet:
        print(format_text(notes))

    print("Playing buzzer preview...", file=sys.stderr)
    play_buzzer_sequence(notes, gap_ms=args.gap_ms, loop=args.loop)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] == "play":
        return play_main(argv[1:])
    return convert_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
