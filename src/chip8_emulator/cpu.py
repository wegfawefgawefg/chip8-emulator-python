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
    family_handler = OPCODE_FAMILY_HANDLERS.get(family)
    if family_handler is None:
        raise ValueError(f"invalid opcode: 0x{opcode:04x}")

    family_handler(state, opcode, quirks)


def opcode_00e0_clear_screen(state: EmulatorState, _opcode: int, _quirks: Chip8Quirks) -> None:
    # 00E0 CLS
    clear_display(state)


def opcode_00ee_return(state: EmulatorState, _opcode: int, _quirks: Chip8Quirks) -> None:
    # 00EE RET
    if not state.stack:
        raise ValueError("return instruction with empty stack")
    state.pc = state.stack.pop()


def opcode_00fd_exit(state: EmulatorState, _opcode: int, _quirks: Chip8Quirks) -> None:
    # 00FD EXIT
    state.exited = True


def handle_family_0(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    handler = OPCODE_0_EXACT_HANDLERS.get(opcode)
    if handler is not None:
        handler(state, opcode, quirks)


def handle_opcode_1nnn_jump(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 1NNN JP addr
    state.pc = address_nnn(opcode)


def handle_opcode_2nnn_call(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 2NNN CALL addr
    state.stack.append(state.pc)
    state.pc = address_nnn(opcode)


def handle_opcode_3xnn_skip_eq_byte(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 3XNN SE Vx, byte
    if state.registers[x_register_index(opcode)] == byte_nn(opcode):
        state.pc += 2


def handle_opcode_4xnn_skip_neq_byte(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 4XNN SNE Vx, byte
    if state.registers[x_register_index(opcode)] != byte_nn(opcode):
        state.pc += 2


def handle_opcode_5xy0_skip_eq_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 5XY0 SE Vx, Vy
    if nibble_n(opcode) != 0:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 5XY0")

    if state.registers[x_register_index(opcode)] == state.registers[y_register_index(opcode)]:
        state.pc += 2


def handle_opcode_6xnn_load_byte(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 6XNN LD Vx, byte
    state.registers[x_register_index(opcode)] = byte_nn(opcode)


def handle_opcode_7xnn_add_byte(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 7XNN ADD Vx, byte
    x_reg = x_register_index(opcode)
    state.registers[x_reg] = (state.registers[x_reg] + byte_nn(opcode)) & 0xFF


def opcode_8xy0_load_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY0 LD Vx, Vy
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    state.registers[x_reg] = state.registers[y_reg]


def opcode_8xy1_or_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY1 OR Vx, Vy
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    state.registers[x_reg] |= state.registers[y_reg]


def opcode_8xy2_and_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY2 AND Vx, Vy
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    state.registers[x_reg] &= state.registers[y_reg]


def opcode_8xy3_xor_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY3 XOR Vx, Vy
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    state.registers[x_reg] ^= state.registers[y_reg]


def opcode_8xy4_add_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY4 ADD Vx, Vy (VF = carry)
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    result = state.registers[x_reg] + state.registers[y_reg]
    state.registers[0xF] = 1 if result > 0xFF else 0
    state.registers[x_reg] = result & 0xFF


def opcode_8xy5_sub_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY5 SUB Vx, Vy (VF = NOT borrow)
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    state.registers[0xF] = 0 if state.registers[y_reg] > state.registers[x_reg] else 1
    state.registers[x_reg] = (state.registers[x_reg] - state.registers[y_reg]) & 0xFF


def opcode_8xy6_shift_right(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    # 8XY6 SHR Vx {, Vy}
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    source = y_reg if quirks.shift_uses_vy else x_reg
    value = state.registers[source]
    state.registers[0xF] = value & 0x1
    state.registers[x_reg] = (value >> 1) & 0xFF


def opcode_8xy7_subn_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 8XY7 SUBN Vx, Vy (Vx = Vy - Vx)
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    state.registers[0xF] = 0 if state.registers[x_reg] > state.registers[y_reg] else 1
    state.registers[x_reg] = (state.registers[y_reg] - state.registers[x_reg]) & 0xFF


def opcode_8xye_shift_left(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    # 8XYE SHL Vx {, Vy}
    x_reg = x_register_index(opcode)
    y_reg = y_register_index(opcode)
    source = y_reg if quirks.shift_uses_vy else x_reg
    value = state.registers[source]
    state.registers[0xF] = (value & 0x80) >> 7
    state.registers[x_reg] = (value << 1) & 0xFF


def handle_family_8(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    handler = OPCODE_8_SUB_HANDLERS.get(nibble_n(opcode))
    if handler is None:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 8XY*")
    handler(state, opcode, quirks)


def handle_opcode_9xy0_skip_neq_register(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # 9XY0 SNE Vx, Vy
    if nibble_n(opcode) != 0:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for 9XY0")

    if state.registers[x_register_index(opcode)] != state.registers[y_register_index(opcode)]:
        state.pc += 2


def handle_opcode_annn_load_i(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # ANNN LD I, addr
    state.index = address_nnn(opcode)


def handle_opcode_bnnn_jump_with_offset(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    # BNNN/BXNN jump with quirk profile
    jump_register = x_register_index(opcode) if quirks.jump_with_vx else 0
    state.pc = (address_nnn(opcode) + state.registers[jump_register]) & 0x0FFF


def handle_opcode_cxnn_random_and(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # CXNN RND Vx, byte
    state.registers[x_register_index(opcode)] = random.randint(0, 0xFF) & byte_nn(opcode)


def handle_opcode_dxyn_draw(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    # DXYN DRW Vx, Vy, nibble
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


def opcode_ex9e_skip_if_key_pressed(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # EX9E SKP Vx
    key = state.registers[x_register_index(opcode)] & 0x0F
    if state.key_inputs[key] == 1:
        state.pc += 2


def opcode_exa1_skip_if_key_not_pressed(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # EXA1 SKNP Vx
    key = state.registers[x_register_index(opcode)] & 0x0F
    if state.key_inputs[key] == 0:
        state.pc += 2


def handle_family_e(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    handler = OPCODE_E_TAIL_HANDLERS.get(byte_nn(opcode))
    if handler is None:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for EX**")
    handler(state, opcode, quirks)


def opcode_fx07_load_vx_from_delay(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX07 LD Vx, DT
    state.registers[x_register_index(opcode)] = state.delay_timer


def opcode_fx0a_wait_for_key(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX0A LD Vx, K
    key = first_pressed_key(state)
    if key >= 0:
        state.registers[x_register_index(opcode)] = key
    else:
        state.pc -= 2


def opcode_fx15_set_delay_from_vx(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX15 LD DT, Vx
    state.delay_timer = state.registers[x_register_index(opcode)]


def opcode_fx18_set_sound_from_vx(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX18 LD ST, Vx
    state.sound_timer = state.registers[x_register_index(opcode)]


def opcode_fx1e_add_vx_to_i(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX1E ADD I, Vx
    state.index = (state.index + state.registers[x_register_index(opcode)]) & 0x0FFF


def opcode_fx29_select_font_sprite(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX29 LD F, Vx
    state.index = (state.registers[x_register_index(opcode)] & 0x0F) * 5


def opcode_fx33_store_bcd(state: EmulatorState, opcode: int, _quirks: Chip8Quirks) -> None:
    # FX33 LD B, Vx
    value = state.registers[x_register_index(opcode)]
    state.memory[state.index] = value // 100
    state.memory[state.index + 1] = (value % 100) // 10
    state.memory[state.index + 2] = value % 10


def opcode_fx55_store_registers(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    # FX55 LD [I], V0..Vx
    x_reg = x_register_index(opcode)
    for i in range(x_reg + 1):
        state.memory[state.index + i] = state.registers[i]
    if quirks.load_store_increment_i:
        state.index = (state.index + x_reg + 1) & 0x0FFF


def opcode_fx65_load_registers(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    # FX65 LD V0..Vx, [I]
    x_reg = x_register_index(opcode)
    for i in range(x_reg + 1):
        state.registers[i] = state.memory[state.index + i]
    if quirks.load_store_increment_i:
        state.index = (state.index + x_reg + 1) & 0x0FFF


def handle_family_f(state: EmulatorState, opcode: int, quirks: Chip8Quirks) -> None:
    handler = OPCODE_F_TAIL_HANDLERS.get(byte_nn(opcode))
    if handler is None:
        raise ValueError(f"invalid opcode: 0x{opcode:04x} for FX**")
    handler(state, opcode, quirks)


OPCODE_0_EXACT_HANDLERS = {
    0x00E0: opcode_00e0_clear_screen,
    0x00EE: opcode_00ee_return,
    0x00FD: opcode_00fd_exit,
}

OPCODE_8_SUB_HANDLERS = {
    0x0: opcode_8xy0_load_register,
    0x1: opcode_8xy1_or_register,
    0x2: opcode_8xy2_and_register,
    0x3: opcode_8xy3_xor_register,
    0x4: opcode_8xy4_add_register,
    0x5: opcode_8xy5_sub_register,
    0x6: opcode_8xy6_shift_right,
    0x7: opcode_8xy7_subn_register,
    0xE: opcode_8xye_shift_left,
}

OPCODE_E_TAIL_HANDLERS = {
    0x9E: opcode_ex9e_skip_if_key_pressed,
    0xA1: opcode_exa1_skip_if_key_not_pressed,
}

OPCODE_F_TAIL_HANDLERS = {
    0x07: opcode_fx07_load_vx_from_delay,
    0x0A: opcode_fx0a_wait_for_key,
    0x15: opcode_fx15_set_delay_from_vx,
    0x18: opcode_fx18_set_sound_from_vx,
    0x1E: opcode_fx1e_add_vx_to_i,
    0x29: opcode_fx29_select_font_sprite,
    0x33: opcode_fx33_store_bcd,
    0x55: opcode_fx55_store_registers,
    0x65: opcode_fx65_load_registers,
}

OPCODE_FAMILY_HANDLERS = {
    0x0000: handle_family_0,
    0x1000: handle_opcode_1nnn_jump,
    0x2000: handle_opcode_2nnn_call,
    0x3000: handle_opcode_3xnn_skip_eq_byte,
    0x4000: handle_opcode_4xnn_skip_neq_byte,
    0x5000: handle_opcode_5xy0_skip_eq_register,
    0x6000: handle_opcode_6xnn_load_byte,
    0x7000: handle_opcode_7xnn_add_byte,
    0x8000: handle_family_8,
    0x9000: handle_opcode_9xy0_skip_neq_register,
    0xA000: handle_opcode_annn_load_i,
    0xB000: handle_opcode_bnnn_jump_with_offset,
    0xC000: handle_opcode_cxnn_random_and,
    0xD000: handle_opcode_dxyn_draw,
    0xE000: handle_family_e,
    0xF000: handle_family_f,
}
