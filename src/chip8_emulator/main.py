import logging
import argparse
import os
from pathlib import Path

from .app import run_emulator_app, run_emulator_headless
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
    parser.add_argument(
        "--hz",
        type=int,
        default=240,
        help="CPU cycles per second in windowed mode (default: 240)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Render frames per second in windowed mode (default: 60)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without pygame window (useful for smoke tests)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=2000,
        help="Max cycles in headless mode (default: 2000)",
    )
    return parser.parse_args()


def resolve_quirks_profile(cli_quirks: str | None) -> tuple[str, Chip8Quirks]:
    if cli_quirks:
        return cli_quirks, load_quirks_profile(cli_quirks)
    env_profile = os.getenv("CHIP8_QUIRKS", "original").strip().lower()
    return env_profile, load_quirks_profile(env_profile)


def main() -> None:
    args = parse_args()

    logging.basicConfig(level=logging.INFO)
    profile, quirks = resolve_quirks_profile(args.quirks)
    rom_path = Path(args.rom)
    logging.getLogger(__name__).info("quirks profile: %s", profile)
    logging.getLogger(__name__).info("rom: %s", rom_path)

    if args.headless:
        state = run_emulator_headless(
            quirks=quirks,
            rom_path=rom_path,
            max_cycles=args.max_cycles,
        )
        logging.getLogger(__name__).info(
            "headless finished: exited=%s pc=0x%03x",
            state.exited,
            state.pc,
        )
        return

    run_emulator_app(
        quirks=quirks,
        rom_path=rom_path,
        scale=args.scale,
        cpu_hz=args.hz,
        target_fps=args.fps,
    )


if __name__ == "__main__":
    main()
