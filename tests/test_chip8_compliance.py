from pathlib import Path
import sys
import types

import pytest

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    fake_pygame = types.ModuleType("pygame")
    fake_locals = types.ModuleType("pygame.locals")

    class FakeVector2:
        def __init__(self, *_args):
            pass

        def __mul__(self, _other):
            return self

    fake_pygame.Vector2 = FakeVector2
    fake_pygame.KEYUP = 1
    fake_pygame.KEYDOWN = 2
    fake_pygame.QUIT = 3
    fake_pygame.mixer = types.SimpleNamespace(Sound=lambda *_args, **_kwargs: None)
    fake_pygame.key = types.SimpleNamespace(name=lambda key: str(key))
    fake_pygame.Surface = object
    fake_pygame.display = types.SimpleNamespace(set_mode=lambda *_args, **_kwargs: None, flip=lambda: None)
    fake_pygame.transform = types.SimpleNamespace(scale=lambda surface, _size: surface)
    fake_pygame.time = types.SimpleNamespace(get_ticks=lambda: 0)
    fake_pygame.event = types.SimpleNamespace(get=lambda: [])
    fake_pygame.init = lambda: None
    fake_pygame.quit = lambda: None

    local_keys = {
        "K_1": 1,
        "K_2": 2,
        "K_3": 3,
        "K_4": 4,
        "K_q": 5,
        "K_w": 6,
        "K_e": 7,
        "K_r": 8,
        "K_a": 9,
        "K_s": 10,
        "K_d": 11,
        "K_f": 12,
        "K_z": 13,
        "K_x": 14,
        "K_c": 15,
        "K_v": 16,
        "K_ESCAPE": 27,
    }
    for key, value in local_keys.items():
        setattr(fake_locals, key, value)
        setattr(fake_pygame, key, value)

    sys.modules["pygame"] = fake_pygame
    sys.modules["pygame.locals"] = fake_locals

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from chip8_emulator.main import Chip8Emulator, MODERN_QUIRKS


class DummySound:
    def play(self):
        return None


@pytest.fixture
def emu(monkeypatch):
    monkeypatch.setattr("chip8_emulator.main.pygame.mixer.Sound", lambda *_args, **_kwargs: DummySound())
    emulator = Chip8Emulator()
    emulator.print_loaded_ops = False
    return emulator


@pytest.fixture
def emu_modern(monkeypatch):
    monkeypatch.setattr("chip8_emulator.main.pygame.mixer.Sound", lambda *_args, **_kwargs: DummySound())
    emulator = Chip8Emulator(quirks=MODERN_QUIRKS)
    emulator.print_loaded_ops = False
    return emulator


def test_ex9e_skips_when_key_pressed(emu):
    emu.op = 0xE19E
    emu.registers[1] = 0xA
    emu.key_inputs[0xA] = 1
    start_pc = emu.pc

    emu._EZZZ()

    assert emu.pc == start_pc + 2


def test_exa1_skips_when_key_not_pressed(emu):
    emu.op = 0xE1A1
    emu.registers[1] = 0xA
    emu.key_inputs[0xA] = 0
    start_pc = emu.pc

    emu._EZZZ()

    assert emu.pc == start_pc + 2


def test_fx33_stores_bcd_digits(emu):
    emu.op = 0xF233
    emu.registers[2] = 231
    emu.index = 0x300

    emu._store_vx_decimal()

    assert emu.memory[0x300:0x303] == [2, 3, 1]


def test_fx65_reads_registers_and_increments_i(emu):
    emu.op = 0xF265
    emu.index = 0x300
    emu.memory[0x300:0x303] = [0xAA, 0xBB, 0xCC]

    emu._read_ld_registers_i_to_vx()

    assert emu.registers[0:3] == [0xAA, 0xBB, 0xCC]
    assert emu.index == 0x303


def test_7xnn_wraps_at_8_bits(emu):
    emu.op = 0x7002
    emu.registers[0] = 0xFF

    emu._ld_add_vx_nn()

    assert emu.registers[0] == 0x01


def test_8xy6_uses_vy_as_source(emu):
    emu.op = 0x8126
    emu.registers[1] = 0x00
    emu.registers[2] = 0x03

    emu._8ZZZ()

    assert emu.registers[1] == 0x01
    assert emu.registers[2] == 0x03
    assert emu.registers[0xF] == 0x01


def test_8xye_uses_vy_as_source(emu):
    emu.op = 0x812E
    emu.registers[1] = 0x00
    emu.registers[2] = 0x80

    emu._8ZZZ()

    assert emu.registers[1] == 0x00
    assert emu.registers[2] == 0x80
    assert emu.registers[0xF] == 0x01


def test_dxyn_sets_collision_flag_without_losing_it(emu):
    emu.op = 0xD011
    emu.registers[0] = 2
    emu.registers[1] = 3
    emu.index = 0x300
    emu.memory[0x300] = 0x80
    loc = 2 + 3 * emu.SCREEN_WIDTH
    emu.screen_buffer[loc] = 1

    emu._sprite()

    assert emu.registers[0xF] == 1
    assert emu.screen_buffer[loc] == 0


def test_dxyn_wraps_start_coordinates(emu):
    emu.op = 0xD011
    emu.registers[0] = 66
    emu.registers[1] = 33
    emu.index = 0x300
    emu.memory[0x300] = 0x80

    emu._sprite()

    wrapped_loc = 2 + 1 * emu.SCREEN_WIDTH
    assert emu.screen_buffer[wrapped_loc] == 1


def test_8xy6_uses_vx_source_in_modern_profile(emu_modern):
    emu_modern.op = 0x8126
    emu_modern.registers[1] = 0x03
    emu_modern.registers[2] = 0x00

    emu_modern._8ZZZ()

    assert emu_modern.registers[1] == 0x01
    assert emu_modern.registers[0xF] == 0x01


def test_fx65_does_not_increment_i_in_modern_profile(emu_modern):
    emu_modern.op = 0xF265
    emu_modern.index = 0x300
    emu_modern.memory[0x300:0x303] = [0xAA, 0xBB, 0xCC]

    emu_modern._read_ld_registers_i_to_vx()

    assert emu_modern.registers[0:3] == [0xAA, 0xBB, 0xCC]
    assert emu_modern.index == 0x300


def test_fx55_does_not_increment_i_in_modern_profile(emu_modern):
    emu_modern.op = 0xF255
    emu_modern.index = 0x300
    emu_modern.registers[0:3] = [0x11, 0x22, 0x33]

    emu_modern._store_registers_0_to_vx()

    assert emu_modern.memory[0x300:0x303] == [0x11, 0x22, 0x33]
    assert emu_modern.index == 0x300


def test_bxnn_jump_uses_vx_in_modern_profile(emu_modern):
    emu_modern.op = 0xB123
    emu_modern.registers[0] = 0x05
    emu_modern.registers[1] = 0x10

    emu_modern._jmi()

    assert emu_modern.pc == 0x133


def test_dxyn_wraps_pixels_in_modern_profile(emu_modern):
    emu_modern.op = 0xD011
    emu_modern.registers[0] = 63
    emu_modern.registers[1] = 31
    emu_modern.index = 0x300
    emu_modern.memory[0x300] = 0xC0

    emu_modern._sprite()

    pixel_a = 63 + 31 * emu_modern.SCREEN_WIDTH
    pixel_b = 0 + 31 * emu_modern.SCREEN_WIDTH
    assert emu_modern.screen_buffer[pixel_a] == 1
    assert emu_modern.screen_buffer[pixel_b] == 1
