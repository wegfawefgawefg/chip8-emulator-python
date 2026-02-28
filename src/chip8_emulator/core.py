import random
from typing import Callable

from .config import MEMORY_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH
from .quirks import Chip8Quirks
from .state import EmulatorState, clear_display, first_pressed_key


def x_register_index(opcode: int) -> int:
    return (opcode & 0x0F00) >> 8


def y_register_index(opcode: int) -> int:
    return (opcode & 0x00F0) >> 4


def address_nnn(opcode: int) -> int:
    return opcode & 0x0FFF


def byte_nn(opcode: int) -> int:
    return opcode & 0x00FF


def nibble_n(opcode: int) -> int:
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
        # 00E0 CLS, 00EE RET, 00FD EXIT
        execute_family_0(state, opcode)
    elif family == 0x1000:
        # 1NNN JP addr
        state.pc = address_nnn(opcode)
    elif family == 0x2000:
        # 2NNN CALL addr
        state.stack.append(state.pc)
        state.pc = address_nnn(opcode)
    elif family == 0x3000:
        # 3XNN SE Vx, byte
        if state.registers[x_register_index(opcode)] == byte_nn(opcode):
            state.pc += 2
    elif family == 0x4000:
        # 4XNN SNE Vx, byte
        if state.registers[x_register_index(opcode)] != byte_nn(opcode):
            state.pc += 2
    elif family == 0x5000:
        # 5XY0 SE Vx, Vy
        execute_family_5(state, opcode)
    elif family == 0x6000:
        # 6XNN LD Vx, byte
        state.registers[x_register_index(opcode)] = byte_nn(opcode)
    elif family == 0x7000:
        # 7XNN ADD Vx, byte
        x_reg = x_register_index(opcode)
        state.registers[x_reg] = (state.registers[x_reg] + byte_nn(opcode)) & 0xFF
    elif family == 0x8000:
        # 8XY* arithmetic and logic group
        execute_family_8(state, opcode, quirks)
    elif family == 0x9000:
        # 9XY0 SNE Vx, Vy
        execute_family_9(state, opcode)
    elif family == 0xA000:
        # ANNN LD I, addr
        state.index = address_nnn(opcode)
    elif family == 0xB000:
        # BNNN/BXNN jump with quirk profile
        jump_register = x_register_index(opcode) if quirks.jump_with_vx else 0
        state.pc = (address_nnn(opcode) + state.registers[jump_register]) & 0x0FFF
    elif family == 0xC000:
        # CXNN RND Vx, byte
        state.registers[x_register_index(opcode)] = random.randint(0, 0xFF) & byte_nn(opcode)
    elif family == 0xD000:
        # DXYN DRW Vx, Vy, nibble
        draw_sprite(state, opcode, quirks)
    elif family == 0xE000:
        # EX9E / EXA1 key skip group
        execute_family_e(state, opcode)
    elif family == 0xF000:
        # FX** timers, memory, and key group
        execute_family_f(state, opcode, quirks)
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x}")


def execute_family_0(state: EmulatorState, opcode: int) -> None:
    if opcode == 0x00E0:
        clear_display(state)
    elif opcode == 0x00EE:
        if not state.stack:
            raise ValueError("return instruction with empty stack")
        state.pc = state.stack.pop()
    elif opcode == 0x00FD:
        state.exited = True


def execute_family_5(state: EmulatorState, opcode: int) -> None:
    if nibble_n(opcode) != 0:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 5XY0")

    if state.registers[x_register_index(opcode)] == state.registers[y_register_index(opcode)]:
        state.pc += 2


def execute_family_8(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    sub_op = nibble_n(opcode)

    if sub_op == 0x0:
        # 8XY0 LD Vx, Vy
        state.registers[x_reg] = state.registers[y_reg]
    elif sub_op == 0x1:
        # 8XY1 OR Vx, Vy
        state.registers[x_reg] |= state.registers[y_reg]
    elif sub_op == 0x2:
        # 8XY2 AND Vx, Vy
        state.registers[x_reg] &= state.registers[y_reg]
    elif sub_op == 0x3:
        # 8XY3 XOR Vx, Vy
        state.registers[x_reg] ^= state.registers[y_reg]
    elif sub_op == 0x4:
        # 8XY4 ADD Vx, Vy (VF = carry)
        result = state.registers[x_reg] + state.registers[y_reg]
        state.registers[0xF] = 1 if result > 0xFF else 0
        state.registers[x_reg] = result & 0xFF
    elif sub_op == 0x5:
        # 8XY5 SUB Vx, Vy (VF = NOT borrow)
        state.registers[0xF] = 0 if state.registers[y_reg] > state.registers[x_reg] else 1
        state.registers[x_reg] = (state.registers[x_reg] - state.registers[y_reg]) & 0xFF
    elif sub_op == 0x6:
        # 8XY6 SHR Vx {, Vy}
        source = y_reg if quirks.shift_uses_vy else x_reg
        value = state.registers[source]
        state.registers[0xF] = value & 0x1
        state.registers[x_reg] = (value >> 1) & 0xFF
    elif sub_op == 0x7:
        # 8XY7 SUBN Vx, Vy (Vx = Vy - Vx)
        state.registers[0xF] = 0 if state.registers[x_reg] > state.registers[y_reg] else 1
        state.registers[x_reg] = (state.registers[y_reg] - state.registers[x_reg]) & 0xFF
    elif sub_op == 0xE:
        # 8XYE SHL Vx {, Vy}
        source = y_reg if quirks.shift_uses_vy else x_reg
        value = state.registers[source]
        state.registers[0xF] = (value & 0x80) >> 7
        state.registers[x_reg] = (value << 1) & 0xFF
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 8XY*")


def execute_family_9(state: EmulatorState, opcode: int) -> None:
    if nibble_n(opcode) != 0:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 9XY0")

    if state.registers[x_register_index(opcode)] != state.registers[y_register_index(opcode)]:
        state.pc += 2


def execute_family_e(state: EmulatorState, opcode: int) -> None:
    x_reg = x_register_index(opcode)
    key = state.registers[x_reg] & 0x0F
    tail = byte_nn(opcode)

    if tail == 0x9E:
        # EX9E SKP Vx
        if state.key_inputs[key] == 1:
            state.pc += 2
    elif tail == 0xA1:
        # EXA1 SKNP Vx
        if state.key_inputs[key] == 0:
            state.pc += 2
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for EX**")


def execute_family_f(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    x_reg = x_register_index(opcode)
    tail = byte_nn(opcode)

    if tail == 0x07:
        # FX07 LD Vx, DT
        state.registers[x_reg] = state.delay_timer
    elif tail == 0x0A:
        # FX0A LD Vx, K
        key = first_pressed_key(state)
        if key >= 0:
            state.registers[x_reg] = key
        else:
            state.pc -= 2
    elif tail == 0x15:
        # FX15 LD DT, Vx
        state.delay_timer = state.registers[x_reg]
    elif tail == 0x18:
        # FX18 LD ST, Vx
        state.sound_timer = state.registers[x_reg]
    elif tail == 0x1E:
        # FX1E ADD I, Vx
        state.index = (state.index + state.registers[x_reg]) & 0x0FFF
    elif tail == 0x29:
        # FX29 LD F, Vx
        state.index = (state.registers[x_reg] & 0x0F) * 5
    elif tail == 0x33:
        # FX33 LD B, Vx
        value = state.registers[x_reg]
        state.memory[state.index] = value // 100
        state.memory[state.index + 1] = (value % 100) // 10
        state.memory[state.index + 2] = value % 10
    elif tail == 0x55:
        # FX55 LD [I], V0..Vx
        for i in range(x_reg + 1):
            state.memory[state.index + i] = state.registers[i]
        if quirks.load_store_increment_i:
            state.index = (state.index + x_reg + 1) & 0x0FFF
    elif tail == 0x65:
        # FX65 LD V0..Vx, [I]
        for i in range(x_reg + 1):
            state.registers[i] = state.memory[state.index + i]
        if quirks.load_store_increment_i:
            state.index = (state.index + x_reg + 1) & 0x0FFF
    else:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for FX**")


def draw_sprite(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    x_start = state.registers[x_register_index(opcode)] % SCREEN_WIDTH
    y_start = state.registers[y_register_index(opcode)] % SCREEN_HEIGHT
    height = nibble_n(opcode)

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

            location = x_pos + (y_pos * SCREEN_WIDTH)
            if state.screen_buffer[location] == 1:
                collision = 1
            state.screen_buffer[location] ^= 1

    state.registers[0xF] = collision
    state.should_draw = True
