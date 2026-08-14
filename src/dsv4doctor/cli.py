from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from . import __version__
from .render import render_json, render_sarif, render_text
from .stream import inspect_stream
from .validator import validate_request


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "check":
            report = validate_request(
                _read_json(args.input),
                source=args.input,
                thinking=args.thinking,
            )
        else:
            with _open_input(args.input) as stream:
                report = inspect_stream(stream, source=args.input)
    except (OSError, UnicodeError) as exc:
        print(f"dsv4-doctor: cannot read {args.input}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"dsv4-doctor: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 2

    output = {
        "text": render_text,
        "json": render_json,
        "sarif": render_sarif,
    }[args.format](report)
    print(output, end="")
    if report.errors or (args.fail_on_warning and report.warnings):
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dsv4-doctor",
        description="Offline protocol checks for DeepSeek V4-compatible request histories and SSE captures.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="validate a JSON request envelope or messages array")
    check.add_argument("input", help="JSON file, or - for stdin")
    check.add_argument("--thinking", choices=("auto", "enabled", "disabled"), default="auto")
    _add_output_options(check)

    stream = subparsers.add_parser("stream", help="inspect an OpenAI-compatible SSE/JSONL capture")
    stream.add_argument("input", help="SSE/JSONL file, or - for stdin")
    _add_output_options(stream)
    return parser


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    parser.add_argument("--fail-on-warning", action="store_true")


def _open_input(path: str) -> TextIO:
    if path == "-":
        return sys.stdin
    return Path(path).open("r", encoding="utf-8")


def _read_json(path: str) -> Any:
    with _open_input(path) as stream:
        return json.load(stream)
