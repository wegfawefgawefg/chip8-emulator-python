"""
resources:
    - http://omokute.blogspot.com/2012/06/emulation-basics-write-your-own-chip-8.html

TODO:
    finish the remaining instructions
        mostly F category
    setup input keys
    write graphics stuff 
        transfer screen buffer to pygame
    try a rom
"""

from cmath import inf
from dataclasses import dataclass
import os
from pathlib import Path
import random

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame
from pygame import Vector2
from pygame.locals import (
    K_1,
    K_2,
    K_3,
    K_4,
    K_q,
    K_w,
    K_e,
    K_r,
    K_a,
    K_s,
    K_d,
    K_f,
    K_z,
    K_x,
    K_c,
    K_v,
    K_ESCAPE,
)

import logging

logging.basicConfig(level=logging.NOTSET)
LOG = logging.getLogger(":")
INSTRUCTION_LOGGING = False
CYCLE_LOGGING = True
CHECKING_KEYPRESS_LOGGING = True
# LOG.setLevel(logging.DEBUG)
# LOG.setLevel(logging.ERROR)


def fbhs(h):
    return "0x{:02x}".format(h)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"
ROMS_DIR = PROJECT_ROOT / "roms"
DUMPS_DIR = PROJECT_ROOT / "dumps"


@dataclass(frozen=True)
class Chip8Quirks:
    shift_uses_vy: bool
    load_store_increment_i: bool
    jump_with_vx: bool
    draw_wrap: bool


ORIGINAL_QUIRKS = Chip8Quirks(
    shift_uses_vy=True,
    load_store_increment_i=True,
    jump_with_vx=False,
    draw_wrap=False,
)

MODERN_QUIRKS = Chip8Quirks(
    shift_uses_vy=False,
    load_store_increment_i=False,
    jump_with_vx=True,
    draw_wrap=True,
)

QUIRKS_BY_PROFILE = {
    "original": ORIGINAL_QUIRKS,
    "modern": MODERN_QUIRKS,
}


def load_quirks_profile_from_env() -> tuple[str, Chip8Quirks]:
    profile = os.getenv("CHIP8_QUIRKS", "original").strip().lower()
    quirks = QUIRKS_BY_PROFILE.get(profile)
    if quirks is None:
        accepted = ", ".join(sorted(QUIRKS_BY_PROFILE.keys()))
        raise ValueError(f"invalid CHIP8_QUIRKS '{profile}', expected one of: {accepted}")
    return profile, quirks


class Chip8Emulator:
    MEMORY_SIZE = 4096
    SCREEN_WIDTH = 64
    SCREEN_HEIGHT = 32

    def __init__(self, quirks: Chip8Quirks | None = None):
        self.quirks = quirks or ORIGINAL_QUIRKS
        self.print_loaded_ops = True

        self.tone = pygame.mixer.Sound(str(ASSETS_DIR / "tone.wav"))
        self.current_rom_path = None
        self.reset()
        self.define_isa()

    def reset(self):
        LOG.info("reset")
        self._disp_clear()

        self.key_inputs = [0] * 16
        self.memory = [0] * Chip8Emulator.MEMORY_SIZE
        self.pc = 0x0200  # 512
        self.index = 0
        self.registers = [0] * 16
        self.stack = []

        self.sound_timer = 0
        self.delay_timer = 0
        self.should_draw = False

        self.exited = False

        """
        start of mem is 16 digit sprites, each 5 bytes"""
        self.font = [
            0xF0,
            0x90,
            0x90,
            0x90,
            0xF0,  # 0
            0x20,
            0x60,
            0x20,
            0x20,
            0x70,  # 1
            0xF0,
            0x10,
            0xF0,
            0x80,
            0xF0,  # 2
            0xF0,
            0x10,
            0xF0,
            0x10,
            0xF0,  # 3
            0x90,
            0x90,
            0xF0,
            0x10,
            0x10,  # 4
            0xF0,
            0x80,
            0xF0,
            0x10,
            0xF0,  # 5
            0xF0,
            0x80,
            0xF0,
            0x90,
            0xF0,  # 6
            0xF0,
            0x10,
            0x20,
            0x40,
            0x40,  # 7
            0xF0,
            0x90,
            0xF0,
            0x90,
            0xF0,  # 8
            0xF0,
            0x90,
            0xF0,
            0x10,
            0xF0,  # 9
            0xF0,
            0x90,
            0xF0,
            0x90,
            0x90,  # A
            0xE0,
            0x90,
            0xE0,
            0x90,
            0xE0,  # B
            0xF0,
            0x80,
            0x80,
            0x80,
            0xF0,  # C
            0xE0,
            0x90,
            0x90,
            0x90,
            0xE0,  # D
            0xF0,
            0x80,
            0xF0,
            0x80,
            0xF0,  # E
            0xF0,
            0x80,
            0xF0,
            0x80,
            0x80,  # F
        ]
        self.key_map = {
            K_1: 0x01,
            K_2: 0x02,
            K_3: 0x03,
            K_4: 0x0C,
            K_q: 0x04,
            K_w: 0x05,
            K_e: 0x06,
            K_r: 0x0D,
            K_a: 0x07,
            K_s: 0x08,
            K_d: 0x09,
            K_f: 0x0E,
            K_z: 0x0A,
            K_x: 0x00,
            K_c: 0x0B,
            K_v: 0x0F,
        }
        self.load_font()
        if self.current_rom_path:
            self.load_rom(self.current_rom_path)

    def dump_mem(self):
        fname = DUMPS_DIR / "memory_dump.bin"
        with open(fname, "wb") as f:
            for byte in self.memory:
                f.write(bytes([byte]))

    def load_font(self):
        LOG.info("load font")
        for i in range(80):
            self.memory[i] = self.font[i]

    def load_rom(self, path):
        self.current_rom_path = path
        with open(path, "rb") as bin:
            rom = bin.read()

        bts = []
        bts_row = []
        rom_size = os.path.getsize(path)
        for i, b in enumerate(rom):
            hex_str = "0x{:02x}".format(b)
            bts_row.append(f"{hex_str} ")
            if ((i + 1) % 16) == 0:
                bts.append(bts_row)
                bts_row = []
            self.memory[0x0200 + i] = b
        bts.append(bts_row)
        info_str = (
            f"loading rom at {path}:" + "\n" + "\n".join(["".join(r) for r in bts])
        )
        LOG.info(info_str)

        start = 0x0200
        end = 0x0200 + os.path.getsize(path)
        LOG.info(f"loaded rom into mem starting at {hex(start)} - to {hex(end)}")
        # except Exception as e:
        #     LOG.error("couldnt read rom")
        #     quit()

    def process(self, op):
        try:
            self.isa[op]()
        except KeyError as exc:
            raise ValueError(f"invalid instruction: 0x{self.op:04x}") from exc

    def inc_pc(self):
        self.pc += 2

    def dec_pc(self):
        self.pc -= 2

    @property
    def vx(self):
        return (self.op & 0x0F00) >> 8

    @property
    def vy(self):
        return (self.op & 0x00F0) >> 4

    @property
    def c3b(self):
        return self.op & 0x0FFF

    @property
    def c2b(self):
        return self.op & 0x00FF

    @property
    def c1b(self):
        return self.op & 0x000F

    def print_stack(self):
        stack_dump = []
        for ptr in self.stack:
            stack_dump.append(fbhs(ptr))
        stack_dump = ", ".join(stack_dump)

        LOG.info(f"======== stack_height: {len(self.stack)}") if CYCLE_LOGGING else None
        LOG.info(f"======== stack: [{stack_dump}]") if CYCLE_LOGGING else None

    def print_registers(self):
        reg_dump = []
        for ptr in self.registers:
            reg_dump.append(fbhs(ptr))
        reg_dump = ", ".join(reg_dump)
        LOG.info(f"======== registers: [{reg_dump}]") if CYCLE_LOGGING else None

    def print_keys(self):
        key_dump = [" "]
        for y in range(0, 4):
            line = []
            for x in range(4):
                i = (y * 4) + x
                k = self.key_inputs[i]
                line.append(f"{k}")
            key_dump.append(", ".join(line))
        key_dump = "\t\t\n ".join(key_dump)
        LOG.info(f"======== keys: [{key_dump}]") if CYCLE_LOGGING else None

    def cycle(self):
        LOG.info(
            "========================= cycle ================================"
        ) if CYCLE_LOGGING else None
        if self.pc > (Chip8Emulator.MEMORY_SIZE - 2):
            LOG.error(
                "program counter exceeded program memory"
            ) if CYCLE_LOGGING else None
            raise RuntimeError("program counter exceeded program memory")

        self.op = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.inc_pc()

        if self.print_loaded_ops:
            LOG.info(f"======== pc: {fbhs(self.pc)}") if CYCLE_LOGGING else None
            self.print_registers() if CYCLE_LOGGING else None
            self.print_stack() if CYCLE_LOGGING else None
            self.print_keys() if CYCLE_LOGGING else None
            LOG.info(f"======== current op: {fbhs(self.op)}") if CYCLE_LOGGING else None

        op_type = self.op & 0xF000
        self.process(op_type)

        self.delay_timer = max(0, self.delay_timer - 1)
        self.sound_timer = max(0, self.sound_timer - 1)
        if self.sound_timer > 0:
            self.tone.play()

    def get_first_pressed_key(self):
        LOG.info("get_first_pressed_key") if INSTRUCTION_LOGGING else None
        for i in range(16):
            if self.key_inputs[i] == 1:
                return i
        return -1

    def draw(self, pygame_surface):
        # LOG.info("draw")
        if self.should_draw:
            for i in range(2048):
                if self.screen_buffer[i] == 1:
                    x = i % Chip8Emulator.SCREEN_WIDTH
                    y = int(i / Chip8Emulator.SCREEN_WIDTH)
                    pygame_surface.set_at((x, y), (255, 255, 255))

    def handle_input_event(self, event):
        if event.key not in self.key_map:
            LOG.error("invalid chip8 key")
            return
        if event.type == pygame.KEYUP:
            LOG.info(f"key released: {pygame.key.name(event.key)}")
            key_mem_address = self.key_map[event.key]
            self.key_inputs[key_mem_address] = 0
        elif event.type == pygame.KEYDOWN:
            LOG.info(f"key pressed: {pygame.key.name(event.key)}")
            key_mem_address = self.key_map[event.key]
            self.key_inputs[key_mem_address] = 1

    ################################################################################
    ###############                 INSTRUCTION SET                 ################
    ################################################################################
    def define_isa(self):
        LOG.info("define_isa")
        self.isa = {
            0x0000: self._0ZZZ,
            0x1000: self._jump,
            0x2000: self._call,
            0x3000: self._skip_eq_vx_nn,
            0x4000: self._skip_neq_vx_nn,
            0x5000: self._skip_eq_vx_vy,
            0x6000: self._ld_vx_nn,
            0x7000: self._ld_add_vx_nn,
            0x8000: self._8ZZZ,  # 8 - dispatch
            0x9000: self._skip_neq_vx_vy,
            0xA000: self._ldi,
            0xB000: self._jmi,
            0xC000: self._ld_vx_rand,
            0xD000: self._sprite,
            0xE000: self._EZZZ,
            0xF000: self._FZZZ,  # F - dispatch
        }

    def _ld_vx_delay_tmr(self):
        LOG.info("_ld_vx_delay_tmr") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] = self.delay_timer

    def _skip_eq_vx_nn(self):
        LOG.info("_skip_eq_vx_nn") if INSTRUCTION_LOGGING else None
        if self.registers[self.vx] == self.c2b:
            LOG.info(
                f"    skipping bc {self.registers[self.vx]} == {self.c2b}"
            ) if INSTRUCTION_LOGGING else None
            self.inc_pc()

    def _skip_neq_vx_nn(self):
        LOG.info("_skip_neq_vx_nn") if INSTRUCTION_LOGGING else None
        if self.registers[self.vx] != self.c2b:
            self.inc_pc()

    def _skip_eq_vx_vy(self):
        LOG.info("_skip_eq_vx_vy") if INSTRUCTION_LOGGING else None
        if self.c1b != 0:
            raise ValueError(f"invalid opcode 0x{self.op:04x} for 5XY0")
        if self.registers[self.vx] == self.registers[self.vy]:
            self.inc_pc()

    def _ld_vx_nn(self):
        LOG.info("_ld_vx_nn") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] = self.c2b
        LOG.info(
            f"    loads {fbhs(self.c2b)} into {fbhs(self.vx)}'th register"
        ) if INSTRUCTION_LOGGING else None

    def _ld_add_vx_nn(self):
        LOG.info("_ld_add_vx_nn") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] += self.c2b
        self.registers[self.vx] &= 0x00FF

    def _8ZZZ(self):
        LOG.info("_8ZZZ") if INSTRUCTION_LOGGING else None
        op = self.c1b
        if op == 0x0:
            self._ld_vx_vy()
        elif op == 0x1:
            self._ldor_vx_vy()
        elif op == 0x2:
            self._ldand_vx_vy()
        elif op == 0x3:
            self._ldxor_vx_vy()
        elif op == 0x4:
            self._ldcadd_vx_vy()
        elif op == 0x5:
            self._bsub_vx_vy()
        elif op == 0x6:
            self._rshift_vx()
        elif op == 0x7:
            self._bsub_vy_vx()
        elif op == 0xE:
            self._lshift_vx()
        else:
            raise ValueError(f"invalid opcode 0x{self.op:04x} for 8XY*")

    def _ld_vx_vy(self):
        LOG.info("_ld_vx_vy") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] = self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldor_vx_vy(self):
        LOG.info("_ldor_vx_vy") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] |= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldand_vx_vy(self):
        LOG.info("_ldand_vx_vy") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] &= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldxor_vx_vy(self):
        LOG.info("_ldxor_vx_vy") if INSTRUCTION_LOGGING else None
        self.registers[self.vx] ^= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldcadd_vx_vy(self):
        LOG.info("_ldcadd_vx_vy") if INSTRUCTION_LOGGING else None
        rsum = self.registers[self.vx] + self.registers[self.vy]
        self.registers[0x000F] = 1 if rsum > 0x00FF else 0  #   overflow, set carry
        self.registers[self.vx] = rsum
        self.registers[self.vx] &= 0x00FF

    def _bsub_vx_vy(self):
        LOG.info("_bsub_vx_vy") if INSTRUCTION_LOGGING else None
        self.registers[0x000F] = (
            0 if self.registers[self.vy] > self.registers[self.vx] else 1
        )  #   overflow, set borrow
        self.registers[self.vx] -= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _rshift_vx(self):
        LOG.info("_rshift_vx") if INSTRUCTION_LOGGING else None
        source_register = self.vy if self.quirks.shift_uses_vy else self.vx
        src = self.registers[source_register]
        self.registers[0x000F] = src & 0x0001
        self.registers[self.vx] = (src >> 1) & 0x00FF

    def _bsub_vy_vx(self):
        LOG.info("_bsub_vy_vx") if INSTRUCTION_LOGGING else None
        self.registers[0x000F] = (
            0 if self.registers[self.vx] > self.registers[self.vy] else 1
        )  #   overflow, set borrow
        self.registers[self.vx] = self.registers[self.vy] - self.registers[self.vx]
        self.registers[self.vx] &= 0xFF

    def _lshift_vx(self):
        #   8xyE
        LOG.info("_lshift_vx") if INSTRUCTION_LOGGING else None
        source_register = self.vy if self.quirks.shift_uses_vy else self.vx
        src = self.registers[source_register]
        self.registers[0x000F] = (src & 0x0080) >> 7
        self.registers[self.vx] = (src << 1) & 0x00FF

    def _skip_neq_vx_vy(self):
        LOG.info("_skip_neq_vx_vy") if INSTRUCTION_LOGGING else None
        if self.c1b != 0:
            raise ValueError(f"invalid opcode 0x{self.op:04x} for 9XY0")
        if self.registers[self.vx] != self.registers[self.vy]:
            self.inc_pc()

    def _skip_vx_pressed(self):
        LOG.info("_skip_vx_pressed") if INSTRUCTION_LOGGING else None
        LOG.info(
            "checking keypress skip_vx_if_pressed"
        ) if CHECKING_KEYPRESS_LOGGING else None
        key = self.registers[self.vx] & 0x000F
        if self.key_inputs[key] == 1:
            self.inc_pc()

    def _skip_not_vx_pressed(self):
        LOG.info("_skip_not_vx_pressed") if INSTRUCTION_LOGGING else None
        LOG.info(
            "checking keypress skip_vx_if_not_pressed"
        ) if CHECKING_KEYPRESS_LOGGING else None
        key = self.registers[self.vx] & 0x000F
        if self.key_inputs[key] == 0:
            self.inc_pc()

    def _EZZZ(self):
        LOG.info("_EZZZ") if INSTRUCTION_LOGGING else None
        op = self.op & 0x00FF
        if op == 0x9E:
            self._skip_vx_pressed()
        elif op == 0xA1:
            self._skip_not_vx_pressed()
        else:
            raise ValueError(f"invalid opcode 0x{self.op:04x} for EX**")

    def _FZZZ(self):
        LOG.info("_FZZZ") if INSTRUCTION_LOGGING else None
        sub_op = self.op & 0xF0FF
        if sub_op == 0xF007:
            self._ld_vx_delay_tmr()
        elif sub_op == 0xF00A:
            self._wt_kp_ld_vx()
        elif sub_op == 0xF015:
            self._ld_delay_tmr_vx()
        elif sub_op == 0xF018:
            self._ld_sound_tmr_vx()
        elif sub_op == 0xF01E:
            self._add_vx_i_wc()
        elif sub_op == 0xF029:
            self._ld_i_vx_sprite_pos()
        elif sub_op == 0xF033:
            self._store_vx_decimal()
        elif sub_op == 0xF055:
            self._store_registers_0_to_vx()
        elif sub_op == 0xF065:
            self._read_ld_registers_i_to_vx()
        else:
            raise ValueError(f"invalid opcode 0x{self.op:04x} for FX**")

    def _wt_kp_ld_vx(self):
        LOG.info("_wt_kp_ld_vx") if INSTRUCTION_LOGGING else None
        LOG.info("waiting keypress") if CHECKING_KEYPRESS_LOGGING else None
        fpk = self.get_first_pressed_key()
        if fpk >= 0:
            self.registers[self.vx] = fpk
        else:
            self.dec_pc()

    def _ld_delay_tmr_vx(self):
        LOG.info("_ld_delay_tmr_vx") if INSTRUCTION_LOGGING else None
        self.delay_timer = self.registers[self.vx]

    def _ld_sound_tmr_vx(self):
        LOG.info("_ld_sound_tmr_vx") if INSTRUCTION_LOGGING else None
        self.sound_timer = self.registers[self.vx]

    def _add_vx_i_wc(self):
        LOG.info("_add_vx_i_wc") if INSTRUCTION_LOGGING else None
        self.index = (self.index + self.registers[self.vx]) & 0x0FFF

    def _ld_i_vx_sprite_pos(self):
        LOG.info("_ld_i_vx_sprite_pos") if INSTRUCTION_LOGGING else None
        selected_sprite_pos = 5 * (self.registers[self.vx] & 0x000F)
        self.index = selected_sprite_pos & 0x0FFF

    def _store_vx_decimal(self):
        LOG.info("_store_vx_decimal") if INSTRUCTION_LOGGING else None
        value = self.registers[self.vx]
        self.memory[self.index] = value // 100
        self.memory[self.index + 1] = (value % 100) // 10
        self.memory[self.index + 2] = value % 10

    def _store_registers_0_to_vx(self):
        LOG.info("_store_registers_0_to_vx") if INSTRUCTION_LOGGING else None
        for i in range(self.vx + 1):
            self.memory[self.index + i] = self.registers[i]
        if self.quirks.load_store_increment_i:
            self.index = (self.index + self.vx + 1) & 0x0FFF

    def _read_ld_registers_i_to_vx(self):
        LOG.info("_read_ld_registers_i_to_vx") if INSTRUCTION_LOGGING else None
        for i in range(self.vx + 1):
            self.registers[i] = self.memory[self.index + i]
        if self.quirks.load_store_increment_i:
            self.index = (self.index + self.vx + 1) & 0x0FFF

    def _sprite(self):
        LOG.info("_sprite") if INSTRUCTION_LOGGING else None
        self.registers[0x000F] = 0
        x = (self.registers[self.vx] & 0x00FF) % Chip8Emulator.SCREEN_WIDTH
        y = (self.registers[self.vy] & 0x00FF) % Chip8Emulator.SCREEN_HEIGHT
        height = self.op & 0x000F
        for row in range(height):
            y_pos = y + row
            if self.quirks.draw_wrap:
                y_pos %= Chip8Emulator.SCREEN_HEIGHT
            elif y_pos >= Chip8Emulator.SCREEN_HEIGHT:
                break

            sprite_row = self.memory[self.index + row]
            for pixel_offset in range(8):
                x_pos = x + pixel_offset
                if self.quirks.draw_wrap:
                    x_pos %= Chip8Emulator.SCREEN_WIDTH
                elif x_pos >= Chip8Emulator.SCREEN_WIDTH:
                    break

                curr_pixel = (sprite_row >> (7 - pixel_offset)) & 0x1
                if curr_pixel == 0:
                    continue

                loc = x_pos + (y_pos * Chip8Emulator.SCREEN_WIDTH)
                if self.screen_buffer[loc] == 1:
                    self.registers[0xF] = 1
                self.screen_buffer[loc] ^= 1
        self.should_draw = True

    def _ldi(self):
        LOG.info("_ldi") if INSTRUCTION_LOGGING else None
        self.index = self.c3b

    def _jmi(self):
        LOG.info("_jmi") if INSTRUCTION_LOGGING else None
        jump_register = self.vx if self.quirks.jump_with_vx else 0x0
        self.pc = (self.c3b + self.registers[jump_register]) & 0x0FFF

    def _ld_vx_rand(self):
        LOG.info("_ld_vx_rand") if INSTRUCTION_LOGGING else None
        r = random.randint(0, 0x00FF)
        self.registers[self.vx] = r & self.c2b
        self.registers[self.vx] &= 0xFF

    def _EXIT(self):
        LOG.info("_EXIT'ed") if INSTRUCTION_LOGGING else None
        self.exited = True

    def _0ZZZ(self):
        LOG.info("_0ZZZ") if INSTRUCTION_LOGGING else None
        if self.op == 0x00E0:
            self._disp_clear()
        elif self.op == 0x00EE:
            self._return_from_sub()
        elif self.op == 0x00FD:
            self._EXIT()
        else:  # 0NNN
            LOG.info(
                "\t dispatch fell through, 0NNN hardware _call is outmoded operation"
            ) if INSTRUCTION_LOGGING else None
            # self._call()

    def _disp_clear(self):
        LOG.info("_disp_clear") if INSTRUCTION_LOGGING else None
        self.screen_buffer = (
            [0] * Chip8Emulator.SCREEN_WIDTH * Chip8Emulator.SCREEN_HEIGHT
        )
        self.should_draw = True

    def _return_from_sub(self):
        LOG.info("_return_from_sub") if INSTRUCTION_LOGGING else None
        self.pc = self.stack.pop()

    def _call(self):
        LOG.info("_call") if INSTRUCTION_LOGGING else None
        LOG.info(
            f"\tstoring current pc {fbhs(self.pc)} to stack"
        ) if INSTRUCTION_LOGGING else None
        self.stack.append(self.pc)
        LOG.info(f"\tjumping to {fbhs(self.c3b)}") if INSTRUCTION_LOGGING else None
        self.pc = self.c3b

    def _jump(self):
        LOG.info("_jump") if INSTRUCTION_LOGGING else None
        LOG.info(f"\tjumping to {fbhs(self.c3b)}") if INSTRUCTION_LOGGING else None
        self.pc = self.c3b


def main():
    pygame.init()
    screen_dims = Vector2(64, 32)
    window_dims = screen_dims * 16.0
    primary_surface = pygame.Surface(screen_dims)
    window = pygame.display.set_mode(window_dims)

    quirks_profile, quirks = load_quirks_profile_from_env()
    LOG.info(f"quirks profile: {quirks_profile}")
    emu = Chip8Emulator(quirks=quirks)
    emu.reset()
    # emu.load_rom(str(ROMS_DIR / "test.bin"))
    # emu.load_rom(str(ROMS_DIR / "Maze (alt) [David Winter, 199x].ch8"))
    # emu.load_rom(str(ROMS_DIR / "Sierpinski [Sergey Naydenov, 2010].ch8"))
    # emu.load_rom(str(ROMS_DIR / "output.ch8"))
    emu.load_rom(str(ROMS_DIR / "chip8-test-suite.ch8"))

    dt = 1.0 / 60.0
    time = pygame.time.get_ticks()
    last_time = time
    running = True
    steps = 0
    max_steps = inf
    while running and steps <= max_steps and emu.exited == False:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            else:
                if event.type == pygame.KEYDOWN and event.key in [K_ESCAPE]:
                    running = False
                    break
                else:
                    if event.type in [pygame.KEYUP, pygame.KEYDOWN]:
                        emu.handle_input_event(event)

        if running == False:
            break

        # emu.dispatch_events()
        emu.cycle()

        primary_surface.fill((0, 0, 0))
        emu.draw(primary_surface)
        blit = pygame.transform.scale(primary_surface, window.get_size())
        window.blit(blit, (0, 0))
        pygame.display.flip()

        time = pygame.time.get_ticks()
        dt = (time - last_time) / 1000.0
        last_time = time
        steps += 1
    pygame.quit()


if __name__ == "__main__":
    main()
