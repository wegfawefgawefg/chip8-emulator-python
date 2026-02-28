from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    DEFAULT_DUMP_PATH,
    FONT_BYTES,
    KEY_COUNT,
    MEMORY_SIZE,
    PROGRAM_START,
    REGISTER_COUNT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


@dataclass(slots=True)
class EmulatorState:
    memory: list[int] = field(default_factory=lambda: [0] * MEMORY_SIZE)
    registers: list[int] = field(default_factory=lambda: [0] * REGISTER_COUNT)
    stack: list[int] = field(default_factory=list)
    key_inputs: list[int] = field(default_factory=lambda: [0] * KEY_COUNT)
    screen_buffer: list[int] = field(
        default_factory=lambda: [0] * (SCREEN_WIDTH * SCREEN_HEIGHT)
    )
    pc: int = PROGRAM_START
    index: int = 0
    delay_timer: int = 0
    sound_timer: int = 0
    should_draw: bool = True
    exited: bool = False
    op: int = 0
    rom_path: Path | None = None


def create_state(rom_path: str | Path | None = None) -> EmulatorState:
    state = EmulatorState()
    reset_state(state, rom_path=rom_path)
    return state


def reset_state(state: EmulatorState, rom_path: str | Path | None = None) -> None:
    state.memory = [0] * MEMORY_SIZE
    state.registers = [0] * REGISTER_COUNT
    state.stack = []
    state.key_inputs = [0] * KEY_COUNT
    clear_display(state)

    state.pc = PROGRAM_START
    state.index = 0
    state.delay_timer = 0
    state.sound_timer = 0
    state.exited = False
    state.op = 0

    load_font(state)

    if rom_path is not None:
        state.rom_path = Path(rom_path)
    if state.rom_path is not None:
        load_rom(state, state.rom_path)


def clear_display(state: EmulatorState) -> None:
    state.screen_buffer = [0] * (SCREEN_WIDTH * SCREEN_HEIGHT)
    state.should_draw = True


def load_font(state: EmulatorState) -> None:
    state.memory[: len(FONT_BYTES)] = FONT_BYTES


def load_rom(state: EmulatorState, path: str | Path) -> None:
    rom_path = Path(path)
    rom_bytes = rom_path.read_bytes()

    max_size = MEMORY_SIZE - PROGRAM_START
    if len(rom_bytes) > max_size:
        raise ValueError(f"ROM too large: {len(rom_bytes)} bytes (max {max_size})")

    for i, value in enumerate(rom_bytes):
        state.memory[PROGRAM_START + i] = value

    state.rom_path = rom_path


def dump_memory(state: EmulatorState, path: str | Path = DEFAULT_DUMP_PATH) -> None:
    dump_path = Path(path)
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    with dump_path.open("wb") as out:
        out.write(bytes(state.memory))


def first_pressed_key(state: EmulatorState) -> int:
    for key, pressed in enumerate(state.key_inputs):
        if pressed == 1:
            return key
    return -1


def set_key_state(state: EmulatorState, key_index: int, is_pressed: bool) -> None:
    if key_index < 0 or key_index >= KEY_COUNT:
        return
    state.key_inputs[key_index] = 1 if is_pressed else 0
