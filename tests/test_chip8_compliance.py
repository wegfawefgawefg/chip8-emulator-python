from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from chip8_emulator.cpu import execute_cycle, execute_opcode, tick_timers
from chip8_emulator.quirks import MODERN_QUIRKS, ORIGINAL_QUIRKS
from chip8_emulator.state import create_state


def test_ex9e_skips_when_key_pressed():
    state = create_state()
    state.registers[1] = 0xA
    state.key_inputs[0xA] = 1
    start_pc = state.pc

    execute_opcode(state, 0xE19E, ORIGINAL_QUIRKS)

    assert state.pc == start_pc + 2


def test_exa1_skips_when_key_not_pressed():
    state = create_state()
    state.registers[1] = 0xA
    state.key_inputs[0xA] = 0
    start_pc = state.pc

    execute_opcode(state, 0xE1A1, ORIGINAL_QUIRKS)

    assert state.pc == start_pc + 2


def test_fx33_stores_bcd_digits():
    state = create_state()
    state.registers[2] = 231
    state.index = 0x300

    execute_opcode(state, 0xF233, ORIGINAL_QUIRKS)

    assert state.memory[0x300:0x303] == [2, 3, 1]


def test_fx65_reads_registers_and_increments_i():
    state = create_state()
    state.index = 0x300
    state.memory[0x300:0x303] = [0xAA, 0xBB, 0xCC]

    execute_opcode(state, 0xF265, ORIGINAL_QUIRKS)

    assert state.registers[0:3] == [0xAA, 0xBB, 0xCC]
    assert state.index == 0x303


def test_7xnn_wraps_at_8_bits():
    state = create_state()
    state.registers[0] = 0xFF

    execute_opcode(state, 0x7002, ORIGINAL_QUIRKS)

    assert state.registers[0] == 0x01


def test_8xy6_uses_vy_as_source():
    state = create_state()
    state.registers[1] = 0x00
    state.registers[2] = 0x03

    execute_opcode(state, 0x8126, ORIGINAL_QUIRKS)

    assert state.registers[1] == 0x01
    assert state.registers[2] == 0x03
    assert state.registers[0xF] == 0x01


def test_8xye_uses_vy_as_source():
    state = create_state()
    state.registers[1] = 0x00
    state.registers[2] = 0x80

    execute_opcode(state, 0x812E, ORIGINAL_QUIRKS)

    assert state.registers[1] == 0x00
    assert state.registers[2] == 0x80
    assert state.registers[0xF] == 0x01


def test_dxyn_sets_collision_flag_without_losing_it():
    state = create_state()
    state.registers[0] = 2
    state.registers[1] = 3
    state.index = 0x300
    state.memory[0x300] = 0x80
    loc = 2 + 3 * 64
    state.screen_buffer[loc] = 1

    execute_opcode(state, 0xD011, ORIGINAL_QUIRKS)

    assert state.registers[0xF] == 1
    assert state.screen_buffer[loc] == 0


def test_dxyn_wraps_start_coordinates():
    state = create_state()
    state.registers[0] = 66
    state.registers[1] = 33
    state.index = 0x300
    state.memory[0x300] = 0x80

    execute_opcode(state, 0xD011, ORIGINAL_QUIRKS)

    wrapped_loc = 2 + 1 * 64
    assert state.screen_buffer[wrapped_loc] == 1


def test_8xy6_uses_vx_source_in_modern_profile():
    state = create_state()
    state.registers[1] = 0x03
    state.registers[2] = 0x00

    execute_opcode(state, 0x8126, MODERN_QUIRKS)

    assert state.registers[1] == 0x01
    assert state.registers[0xF] == 0x01


def test_fx65_does_not_increment_i_in_modern_profile():
    state = create_state()
    state.index = 0x300
    state.memory[0x300:0x303] = [0xAA, 0xBB, 0xCC]

    execute_opcode(state, 0xF265, MODERN_QUIRKS)

    assert state.registers[0:3] == [0xAA, 0xBB, 0xCC]
    assert state.index == 0x300


def test_fx55_does_not_increment_i_in_modern_profile():
    state = create_state()
    state.index = 0x300
    state.registers[0:3] = [0x11, 0x22, 0x33]

    execute_opcode(state, 0xF255, MODERN_QUIRKS)

    assert state.memory[0x300:0x303] == [0x11, 0x22, 0x33]
    assert state.index == 0x300


def test_bxnn_jump_uses_vx_in_modern_profile():
    state = create_state()
    state.registers[0] = 0x05
    state.registers[1] = 0x10

    execute_opcode(state, 0xB123, MODERN_QUIRKS)

    assert state.pc == 0x133


def test_dxyn_wraps_pixels_in_modern_profile():
    state = create_state()
    state.registers[0] = 63
    state.registers[1] = 31
    state.index = 0x300
    state.memory[0x300] = 0xC0

    execute_opcode(state, 0xD011, MODERN_QUIRKS)

    pixel_a = 63 + 31 * 64
    pixel_b = 0 + 31 * 64
    assert state.screen_buffer[pixel_a] == 1
    assert state.screen_buffer[pixel_b] == 1


def test_execute_cycle_does_not_tick_timers():
    state = create_state()
    state.delay_timer = 5
    state.sound_timer = 5
    state.memory[state.pc] = 0x00
    state.memory[state.pc + 1] = 0xE0

    execute_cycle(state, ORIGINAL_QUIRKS, sound_callback=None)

    assert state.delay_timer == 5
    assert state.sound_timer == 5


def test_tick_timers_decrements_sound_and_delay():
    state = create_state()
    state.delay_timer = 2
    state.sound_timer = 2
    beep_count = 0

    def fake_beep() -> None:
        nonlocal beep_count
        beep_count += 1

    tick_timers(state, sound_callback=fake_beep)
    tick_timers(state, sound_callback=fake_beep)

    assert state.delay_timer == 0
    assert state.sound_timer == 0
    assert beep_count == 2
