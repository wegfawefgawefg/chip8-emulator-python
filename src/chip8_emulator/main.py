import logging
import argparse
import os
from pathlib import Path

from .config import DEFAULT_ROM_PATH
from .quirks import Chip8Quirks, QUIRKS_BY_PROFILE, load_quirks_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CHIP-8 emulator")
    parser.add_argument(
        "--rom",
        default=str(DEFAULT_ROM_PATH),
        help="Path to ROM file (default: roms/chip8-test-suite.ch8)",
    )
    parser.add_argument(
        "--quirks",
        choices=sorted(QUIRKS_BY_PROFILE.keys()),
        default=None,
        help="Quirk profile override (default: CHIP8_QUIRKS env or original)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=16,
        help="Window scaling factor (default: 16)",
    )
    return parser.parse_args()


def resolve_quirks_profile(cli_quirks: str | None) -> tuple[str, Chip8Quirks]:
    if cli_quirks:
        return cli_quirks, load_quirks_profile(cli_quirks)
    env_profile = os.getenv("CHIP8_QUIRKS", "original").strip().lower()
    return env_profile, load_quirks_profile(env_profile)


def main() -> None:
    args = parse_args()
    from .app import run_emulator_app

    logging.basicConfig(level=logging.INFO)
    profile, quirks = resolve_quirks_profile(args.quirks)
    rom_path = Path(args.rom)
    logging.getLogger(__name__).info("quirks profile: %s", profile)
    logging.getLogger(__name__).info("rom: %s", rom_path)
    run_emulator_app(quirks=quirks, rom_path=rom_path, scale=args.scale)


if __name__ == "__main__":
    main()
