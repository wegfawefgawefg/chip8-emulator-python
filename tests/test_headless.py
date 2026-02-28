from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from chip8_emulator.app import run_emulator_headless
from chip8_emulator.quirks import ORIGINAL_QUIRKS


def test_headless_stops_on_exit_opcode(tmp_path):
    rom_path = tmp_path / "exit.ch8"
    rom_path.write_bytes(bytes([0x00, 0xFD]))

    state = run_emulator_headless(
        quirks=ORIGINAL_QUIRKS,
        rom_path=rom_path,
        max_cycles=10,
    )

    assert state.exited is True
