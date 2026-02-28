import argparse
from pathlib import Path

from .assembler import assemble_file
from .errors import AssemblerError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble CHIP-8 source into a ROM")
    parser.add_argument("source", help="Path to assembly source file")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output ROM path (default: <source>.ch8)",
    )
    parser.add_argument(
        "--origin",
        default="0x200",
        help="Program origin address in memory (default: 0x200)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source_path = Path(args.source)
    output_path = Path(args.output) if args.output else source_path.with_suffix(".ch8")

    try:
        origin = int(args.origin, 0)
    except ValueError as exc:
        raise SystemExit(f"invalid --origin value '{args.origin}'") from exc

    try:
        rom_bytes = assemble_file(source_path, origin=origin)
    except AssemblerError as exc:
        raise SystemExit(str(exc)) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(rom_bytes)
    print(f"wrote {len(rom_bytes)} bytes to {output_path}")


if __name__ == "__main__":
    main()
