"""Command line interface: `metamoult scan` and `metamoult clean`."""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

from . import __version__
from .cleaner import clean_file
from .core import Finding, Risk, UnsupportedFormatError, detect_format, scan_file

_COLORS = {Risk.HIGH: "31", Risk.MEDIUM: "33", Risk.LOW: "32"}  # red, yellow, green
_MAX_VALUE = 90


def _use_color(stream) -> bool:
    return stream.isatty() and "NO_COLOR" not in os.environ


def _paint(text: str, code: str, color: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if color else text


def _expand(patterns: list[str]) -> list[Path]:
    """Expand wildcards ourselves, because PowerShell does not."""
    paths: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern) if glob.has_magic(pattern) else [pattern]
        paths.extend(Path(m) for m in (matches or [pattern]))
    return paths


def summary(findings: list[Finding]) -> str:
    if not findings:
        return "no metadata found"
    counts = {risk: sum(f.risk is risk for f in findings) for risk in Risk}
    parts = [f"{counts[r]} {r.value}" for r in Risk if counts[r]]
    return f"{len(findings)} findings ({', '.join(parts)})"


def _short(value: str) -> str:
    value = " ".join(value.split())
    return value if len(value) <= _MAX_VALUE else value[:_MAX_VALUE - 1] + "…"


def render_findings(findings: list[Finding], color: bool) -> str:
    """Format findings as a traffic-light list with a plain-language explanation."""
    width = max((len(f.field) for f in findings), default=0)
    lines = []
    for f in findings:
        label = _paint(f"{f.risk.value.upper():<6}", _COLORS[f.risk] + ";1", color)
        lines.append(f"  {label} {f.field:<{width}}  {_short(f.value)}")
        lines.append(f"  {'':<6} {'':<{width}}  " + _paint(f.explanation, "2", color))
    return "\n".join(lines)


def _header(path: Path, findings: list[Finding], color: bool) -> str:
    try:
        fmt = f" [{detect_format(path)}]"
    except (UnsupportedFormatError, OSError):
        fmt = ""
    return _paint(f"{path}{fmt}", "1", color) + f" - {summary(findings)}"


def _scan(paths: list[Path]) -> int:
    color, failed = _use_color(sys.stdout), False
    for path in paths:
        try:
            findings = scan_file(path)
        except Exception as exc:  # report and continue with the next file
            print(f"{path}: error: {exc}", file=sys.stderr)
            failed = True
            continue
        print(_header(path, findings, color))
        if findings:
            print(render_findings(findings, color))
        print()
    return 1 if failed else 0


def _clean(paths: list[Path], out_dir: Path | None) -> int:
    color, failed = _use_color(sys.stdout), False
    for path in paths:
        try:
            result = clean_file(path, out_dir)
        except Exception as exc:
            print(f"{path}: error: {exc}", file=sys.stderr)
            failed = True
            continue
        print(_header(path, result.before, color))
        print("  " + _paint(f"Saved cleaned copy: {result.output}", "1", color))
        print(f"  Re-scan of the copy: {summary(result.after)}")
        if result.after:
            print(render_findings(result.after, color))
        print()
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metamoult",
        description="See and remove hidden metadata from photos, PDFs and Office files. "
                    "Works fully offline.")
    parser.add_argument("--version", action="version", version=f"metamoult {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="show the metadata found in files")
    scan.add_argument("files", nargs="+", metavar="file")

    clean = sub.add_parser(
        "clean", help="write a cleaned copy (name_clean.ext); the original is never changed")
    clean.add_argument("files", nargs="+", metavar="file")
    clean.add_argument("--out", metavar="folder", type=Path,
                       help="put the cleaned copies in this folder")
    return parser


def main(argv: list[str] | None = None) -> int:
    if os.name == "nt":
        os.system("")  # switches on ANSI colours in the Windows console
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")  # never crash on odd characters
    args = build_parser().parse_args(argv)
    paths = _expand(args.files)
    if args.command == "scan":
        return _scan(paths)
    return _clean(paths, args.out)


if __name__ == "__main__":
    sys.exit(main())
