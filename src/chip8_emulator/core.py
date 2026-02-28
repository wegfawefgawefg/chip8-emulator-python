import random
from typing import Callable

from .config import MEMORY_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH
from .quirks import Chip8Quirks
from .state import EmulatorState, clear_display, first_pressed_key


def _x(opcode: int) -> int:
    return (opcode & 0x0F00) >> 8


def _y(opcode: int) -> int:
    return (opcode & 0x00F0) >> 4


def _nnn(opcode: int) -> int:
    return opcode & 0x0FFF


def _nn(opcode: int) -> int:
    return opcode & 0x00FF


def _n(opcode: int) -> int:
    return opcode & 0x000F


def execute_cycle(
    state: EmulatorState,
    quirks: Chip8Quirks,
    sound_callback: Callable[[], None] | None = None,
) -> None:
    if state.pc > (MEMORY_SIZE - 2):
        raise RuntimeError("program counter exceeded program memory")

    opcode = (state.memory[state.pc] << 8) | state.memory[state.pc + 1]
    state.pc += 2

    execute_opcode(state, opcode, quirks)

    state.delay_timer = max(0, state.delay_timer - 1)
    state.sound_timer = max(0, state.sound_timer - 1)

    if state.sound_timer > 0 and sound_callback is not None:
        sound_callback()


def execute_opcode(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    state.op = opcode
    family = opcode & 0xF000

    if family == 0x0000:
        _exec_0_group(state, opcode)
    elif family == 0x1000:
        state.pc = _nnn(opcode)
    elif family == 0x2000:
        state.stack.append(state.pc)
        state.pc = _nnn(opcode)
    elif family == 0x3000:
        if state.registers[_x(opcode)] == _nn(opcode):
            state.pc += 2
    elif family == 0x4000:
        if state.registers[_x(opcode)] != _nn(opcode):
            state.pc += 2
    elif family == 0x5000:
        _exec_5_group(state, opcode)
    elif family == 0x6000:
        state.registers[_x(opcode)] = _nn(opcode)
    elif family == 0x7000:
        x_reg = _x(opcode)
        state.registers[x_reg] = (state.registers[x_reg] + _nn(opcode)) & 0xFF
    elif family == 0x8000:
        _exec_8_group(state, opcode, quirks)
    elif family == 0x9000:
        _exec_9_group(state, opcode)
    elif family == 0xA000:
        state.index = _nnn(opcode)
    elif family == 0xB000:
        x_reg = _x(opcode) if quirks.jump_with_vx else 0
        state.pc = (_nnn(opcode) + state.registers[x_reg]) & 0x0FFF
    elif family == 0xC000:
        state.registers[_x(opcode)] = random.randint(0, 0xFF) & _nn(opcode)
    elif family == 0xD000:
        _draw_sprite(state, opcode, quirks)
    elif family == 0xE000:
        _exec_e_group(state, opcode)
    elif family == 0xF000:
        _exec_f_group(state, opcode, quirks)
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x}")


def _exec_0_group(state: EmulatorState, opcode: int) -> None:
    if opcode == 0x00E0:
        clear_display(state)
    elif opcode == 0x00EE:
        if not state.stack:
            raise ValueError("return instruction with empty stack")
        state.pc = state.stack.pop()
    elif opcode == 0x00FD:
        state.exited = True
    else:
        # 0NNN is ignored on modern interpreters.
        return


def _exec_5_group(state: EmulatorState, opcode: int) -> None:
    if _n(opcode) != 0:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 5XY0")

    if state.registers[_x(opcode)] == state.registers[_y(opcode)]:
        state.pc += 2


def _exec_8_group(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    x_reg = _x(opcode)
    y_reg = _y(opcode)
    op = _n(opcode)

    if op == 0x0:
        state.registers[x_reg] = state.registers[y_reg]
    elif op == 0x1:
        state.registers[x_reg] |= state.registers[y_reg]
    elif op == 0x2:
        state.registers[x_reg] &= state.registers[y_reg]
    elif op == 0x3:
        state.registers[x_reg] ^= state.registers[y_reg]
    elif op == 0x4:
        result = state.registers[x_reg] + state.registers[y_reg]
        state.registers[0xF] = 1 if result > 0xFF else 0
        state.registers[x_reg] = result & 0xFF
    elif op == 0x5:
        state.registers[0xF] = 0 if state.registers[y_reg] > state.registers[x_reg] else 1
        state.registers[x_reg] = (state.registers[x_reg] - state.registers[y_reg]) & 0xFF
    elif op == 0x6:
        source = y_reg if quirks.shift_uses_vy else x_reg
        value = state.registers[source]
        state.registers[0xF] = value & 0x1
        state.registers[x_reg] = (value >> 1) & 0xFF
    elif op == 0x7:
        state.registers[0xF] = 0 if state.registers[x_reg] > state.registers[y_reg] else 1
        state.registers[x_reg] = (state.registers[y_reg] - state.registers[x_reg]) & 0xFF
    elif op == 0xE:
        source = y_reg if quirks.shift_uses_vy else x_reg
        value = state.registers[source]
        state.registers[0xF] = (value & 0x80) >> 7
        state.registers[x_reg] = (value << 1) & 0xFF
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 8XY*")


def _exec_9_group(state: EmulatorState, opcode: int) -> None:
    if _n(opcode) != 0:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 9XY0")

    if state.registers[_x(opcode)] != state.registers[_y(opcode)]:
        state.pc += 2


def _exec_e_group(state: EmulatorState, opcode: int) -> None:
    x_reg = _x(opcode)
    key = state.registers[x_reg] & 0x0F
    tail = _nn(opcode)

    if tail == 0x9E:
        if state.key_inputs[key] == 1:
            state.pc += 2
    elif tail == 0xA1:
        if state.key_inputs[key] == 0:
            state.pc += 2
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for EX**")


def _exec_f_group(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    x_reg = _x(opcode)
    tail = _nn(opcode)

    if tail == 0x07:
        state.registers[x_reg] = state.delay_timer
    elif tail == 0x0A:
        key = first_pressed_key(state)
        if key >= 0:
            state.registers[x_reg] = key
        else:
            state.pc -= 2
    elif tail == 0x15:
        state.delay_timer = state.registers[x_reg]
    elif tail == 0x18:
        state.sound_timer = state.registers[x_reg]
    elif tail == 0x1E:
        state.index = (state.index + state.registers[x_reg]) & 0x0FFF
    elif tail == 0x29:
        state.index = (state.registers[x_reg] & 0x0F) * 5
    elif tail == 0x33:
        value = state.registers[x_reg]
        state.memory[state.index] = value // 100
        state.memory[state.index + 1] = (value % 100) // 10
        state.memory[state.index + 2] = value % 10
    elif tail == 0x55:
        for i in range(x_reg + 1):
            state.memory[state.index + i] = state.registers[i]
        if quirks.load_store_increment_i:
            state.index = (state.index + x_reg + 1) & 0x0FFF
    elif tail == 0x65:
        for i in range(x_reg + 1):
            state.registers[i] = state.memory[state.index + i]
        if quirks.load_store_increment_i:
            state.index = (state.index + x_reg + 1) & 0x0FFF
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for FX**")


def _draw_sprite(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    x_start = state.registers[_x(opcode)] % SCREEN_WIDTH
    y_start = state.registers[_y(opcode)] % SCREEN_HEIGHT
    height = _n(opcode)

    collision = 0

    for row in range(height):
        y_pos = y_start + row
        if quirks.draw_wrap:
            y_pos %= SCREEN_HEIGHT
        elif y_pos >= SCREEN_HEIGHT:
            break

        sprite_row = state.memory[state.index + row]

        for bit in range(8):
            x_pos = x_start + bit
            if quirks.draw_wrap:
                x_pos %= SCREEN_WIDTH
            elif x_pos >= SCREEN_WIDTH:
                break

            pixel = (sprite_row >> (7 - bit)) & 0x1
            if pixel == 0:
                continue

            index = x_pos + (y_pos * SCREEN_WIDTH)
            if state.screen_buffer[index] == 1:
                collision = 1
            state.screen_buffer[index] ^= 1

    state.registers[0xF] = collision
    state.should_draw = True
