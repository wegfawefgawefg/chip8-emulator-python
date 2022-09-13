'''
resources:
    - http://omokute.blogspot.com/2012/06/emulation-basics-write-your-own-chip-8.html

TODO:
    finish the remaining instructions
        mostly F category
    setup input keys
    write graphics stuff 
        transfer screen buffer to pygame
    try a rom
'''

from cmath import inf
import os
import random
from turtle import delay
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
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
# LOG.setLevel(logging.DEBUG)
# LOG.setLevel(logging.ERROR)

def fbhs(h):
    return "0x{:02x}".format(h)

class Chip8Emulator:
    MEMORY_SIZE = 4096
    SCREEN_WIDTH = 64
    SCREEN_HEIGHT = 32

    def __init__(self):
        self.print_loaded_ops = True

        self.tone = pygame.mixer.Sound("tone.wav")
        self.current_rom_path = None
        self.reset()
        self.define_isa()

    def reset(self):
        LOG.info("reset")
        self._disp_clear()

        self.key_inputs = [0]*16
        self.memory = [0]*Chip8Emulator.MEMORY_SIZE
        self.pc = 0x0200 #512
        self.index = 0
        self.registers = [0]*16
        self.stack = []

        self.sound_timer = 0
        self.delay_timer = 0
        self.should_draw = False

        self.exited = False

        '''
        start of mem is 16 digit sprites, each 5 bytes'''
        self.font = [
            0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
            0x20, 0x60, 0x20, 0x20, 0x70, # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
            0x90, 0x90, 0xF0, 0x10, 0x10, # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
            0xF0, 0x10, 0x20, 0x40, 0x40, # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90, # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
            0xF0, 0x80, 0x80, 0x80, 0xF0, # C
            0xE0, 0x90, 0x90, 0x90, 0xE0, # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
            0xF0, 0x80, 0xF0, 0x80, 0x80  # F
        ]
        self.key_map = {
            K_1: 0x01,
            K_2: 0x02,
            K_3: 0x03,
            K_4: 0x0c,
            K_q: 0x04,
            K_w: 0x05,
            K_e: 0x06,
            K_r: 0x0d,
            K_a: 0x07,
            K_s: 0x08,
            K_d: 0x09,
            K_f: 0x0e,
            K_z: 0x0a,
            K_x: 0x00,
            K_c: 0x0b,
            K_v: 0x0f,
        }
        self.load_font()
        if self.current_rom_path:
            self.load_rom(self.current_rom_path)

    def dump_mem(self):
        fname = "memory_dump.bin"
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
            if ((i+1) % 16) == 0:
                bts.append(bts_row)
                bts_row = []
            self.memory[0x0200 + i] = b
        bts.append(bts_row)
        info_str = f"loading rom at {path}:" + "\n"+"\n".join(["".join(r) for r in bts])
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
        except:
            LOG.error(f"invalid instruction: 0x{op:02x}")
            quit()

    def inc_pc(self):
        self.pc += 2

    def dec_pc(self):
        self.pc -= 2

    @property
    def vx(self):
        return (self.op & 0x0f00) >> 8

    @property
    def vy(self):
        return (self.op & 0x00f0) >> 4
    
    @property
    def c3b(self):
        return (self.op & 0x0fff)

    @property
    def c2b(self):
        return (self.op & 0x00ff)
    
    @property
    def c1b(self):
        return (self.op & 0x000f)

    def print_stack(self):
        stack_dump = []
        for ptr in self.stack:
            stack_dump.append(fbhs(ptr))
        stack_dump = ", ".join(stack_dump)
            
        LOG.info(f"======== stack_height: {len(self.stack)}")
        LOG.info(f"======== stack: [{stack_dump}]")

    def print_registers(self):
        reg_dump = []
        for ptr in self.registers:
            reg_dump.append(fbhs(ptr))
        reg_dump = ", ".join(reg_dump)
        LOG.info(f"======== registers: [{reg_dump}]")
        


    def cycle(self):
        LOG.info("========================= cycle ================================")
        if self.pc >= Chip8Emulator.MEMORY_SIZE:
            LOG.error("program counter exceeded program memory")
            quit()


        self.op = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.inc_pc()

        if self.print_loaded_ops:
            LOG.info(f"======== pc: {fbhs(self.pc)}")
            self.print_registers()
            self.print_stack()
            LOG.info(f"======== current op: {fbhs(self.op)}")

        op_type = self.op & 0xf000
        self.process(op_type)
        
        self.delay_timer = max(0, self.delay_timer - 1)
        self.sound_timer = max(0, self.sound_timer - 1)
        if self.sound_timer > 0:
            self.tone.play()

    def get_first_pressed_key(self):
        LOG.info("get_first_pressed_key")
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
            LOG.info(f"key released: {event.key}")
            key_mem_address = self.key_map[event.key]
            self.key_inputs[key_mem_address] = 1
        elif event.type == pygame.KEYDOWN:
            LOG.info(f"key released: {event.key}")
            key_mem_address = self.key_map[event.key]
            self.key_inputs[key_mem_address] = 0

    ################################################################################
    ###############                 INSTRUCTION SET                 ################
    ################################################################################
    def define_isa(self):
        LOG.info("define_isa")
        self.isa = {
            0x0000: self._0ZZZ,
            0x00FD: self._EXIT,
            0x1000: self._jump,
            0x2000: self._call,
            0x3000: self._skip_eq_vx_nn,
            0x4000: self._skip_neq_vx_nn,
            0x5000: self._skip_eq_vx_vy,
            0x6000: self._ld_vx_nn,
            0x7000: self._ld_add_vx_nn,

            0x8000: self._8ZZZ, #   8 - dispatch
            0x8001: self._ld_vx_vy,             #   actualy 0x8000
            0x8002: self._ldor_vx_vy,           #   actualy 0x8001
            0x8003: self._ldand_vx_vy,          #   actualy 0x8002
            0x8004: self._ldxor_vx_vy,          #   actualy 0x8003
            0x8005: self._ldcadd_vx_vy,         #   actualy 0x8004
            0x8006: self._bsub_vx_vy,           #   actualy 0x8005
            0x8007: self._rshift_vx,            #   actualy 0x8006
            0x8008: self._bsub_vy_vx,           #   actualy 0x8007
            0x800F: self._lshift_vx,            #   actualy 0x800E

            0x9000: self._skip_neq_vx_vy,
            0xA000: self._ldi,
            0xB000: self._jmi,
            0xC000: self._ld_vx_rand,
            0xD000: self._sprite,
            0xE000: self._EZZZ,

            0xF000: self._FZZZ, #   F - dispatch
            0xF007: self._ld_vx_delay_tmr,
            0xF00A: self._wt_kp_ld_vx,
            0xF015: self._ld_delay_tmr_vx,
            0xF018: self._ld_sound_tmr_vx,
            0xF01E: self._add_vx_i_wc,
            0xF029: self._ld_i_vx_sprite_pos,
            0xF033: self._store_vx_decimal,
            0xF055: self._store_registers_0_to_vx,
            0xF065: self._read_ld_registers_i_to_vx,
        }
    
    def _ld_vx_delay_tmr(self):
        LOG.info("_ld_vx_delay_tmr")
        self.registers[self.vx] = self.delay_timer

    def _skip_eq_vx_nn(self):
        LOG.info("_skip_eq_vx_nn")
        if self.registers[self.vx] == self.c2b:
            LOG.info(f"    skipping bc {self.registers[self.vx]} == {self.c2b}")
            self.inc_pc()

    def _skip_neq_vx_nn(self):
        LOG.info("_skip_neq_vx_nn")
        if self.registers[self.vx] != self.c2b:

            self.inc_pc()

    def _skip_eq_vx_vy(self):
        LOG.info("_skip_eq_vx_vy")
        if self.registers[self.vx] == self.registers[self.vy]:
            self.inc_pc() 

    def _ld_vx_nn(self):
        LOG.info("_ld_vx_nn")
        self.registers[self.vx] = self.c2b
        LOG.info(f"    loads {fbhs(self.c2b)} into {fbhs(self.vx)}'th register")

    def _ld_add_vx_nn(self):
        LOG.info("_ld_add_vx_nn")
        self.registers[self.vx] += self.c2b

    def _8ZZZ(self):
        LOG.info("_8ZZZ")
        sub_op = (self.op & 0xF00F) + 0x001
        self.process(sub_op)

    def _ld_vx_vy(self):
        LOG.info("_ld_vx_vy")
        self.registers[self.vx] = self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldor_vx_vy(self):
        LOG.info("_ldor_vx_vy")
        self.registers[self.vx] |= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldand_vx_vy(self):
        LOG.info("_ldand_vx_vy")
        self.registers[self.vx] &= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldxor_vx_vy(self):
        LOG.info("_ldxor_vx_vy")
        self.registers[self.vx] ^= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldcadd_vx_vy(self):
        LOG.info("_ldcadd_vx_vy")
        rsum = self.registers[self.vx] + self.registers[self.vy]
        self.registers[0x000F] = 1 if rsum > 0x00ff else 0 #   overflow, set carry
        self.registers[self.vx] = rsum
        self.registers[self.vx] &= 0x00FF

    def _bsub_vx_vy(self):
        LOG.info("_bsub_vx_vy")
        self.registers[0x000F] = 0 if self.registers[self.vy] > self.registers[self.vx] else 1  #   overflow, set borrow
        self.registers[self.vx] -= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _rshift_vx(self):
        LOG.info("_rshift_vx")
        self.registers[0x000F] = self.registers[self.vx] & 0x0001
        self.registers[self.vx] >>= 1

    def _bsub_vy_vx(self):
        LOG.info("_bsub_vy_vx")
        self.registers[0x000F] = 0 if self.registers[self.vx] > self.registers[self.vy] else 1  #   overflow, set borrow
        self.registers[self.vx] = self.registers[self.vy] - self.registers[self.vx]
        self.registers[self.vx] &= 0xff

    def _lshift_vx(self):
        LOG.info("_lshift_vx")
        self.registers[0x000F] = (self.registers[self.vx] & 0x00F0) >> 7
        self.registers[self.vx] = self.registers[self.vx] << 1
        self.registers[self.vx] &= 0x00FF

    def _skip_neq_vx_vy(self):
        LOG.info("_skip_neq_vx_vy")
        if self.registers[self.vx] != self.registers[self.vy]:
            self.inc_pc()

    def _skip_vx_pressed(self):
        LOG.info("_skip_vx_pressed")
        key = self.registers[self.vx] & 0x000F
        if self.key_inputs[key] == 1:
            self.inc_pc()

    def _skip_not_vx_pressed(self):
        LOG.info("_skip_not_vx_pressed")
        key = self.registers[self.vx] & 0x000F
        if self.key_inputs[key] == 0:
            self.inc_pc()

    def _EZZZ(self):
        LOG.info("_EZZZ")
        if self.op == 0xE00E:
            self._skip_vx_pressed()
        elif self.op == 0xE001:
            self._skip_not_vx_pressed()

    def _FZZZ(self):
        LOG.info("_FZZZ")
        sub_op = (self.op & 0xF0FF)
        self.process(sub_op)

    def _wt_kp_ld_vx(self):
        LOG.info("_wt_kp_ld_vx")
        fpk = self.get_first_pressed_key()
        if fpk >= 0:
            self.registers[self.vx] = fpk
        else:
            self.dec_pc()

    def _ld_delay_tmr_vx(self):
        LOG.info("_ld_delay_tmr_vx")
        self.delay_timer = self.registers[self.vx]

    def _ld_sound_tmr_vx(self):
        LOG.info("_ld_sound_tmr_vx")
        self.sound_timer = self.registers[self.vx]

    def _add_vx_i_wc(self):
        LOG.info("_add_vx_i_wc")
        self.index += self.registers[self.vx]
        if self.index > 0x0FFF:
            self.registers[0x000F] = 1
            self.index &= 0x0FFF
        else:
            self.registers[0x000F] = 0

    def _ld_i_vx_sprite_pos(self):
        LOG.info("_ld_i_vx_sprite_pos")
        selected_sprite_pos = 5*(self.registers[self.vx])
        self.index = selected_sprite_pos & 0x0FFF

    def _store_vx_decimal(self):
        LOG.info("_store_vx_decimal")
        self.memory[self.index]   = self.registers[self.vx] / 100
        self.memory[self.index+1] = (self.registers[self.vx] % 100) / 10
        self.memory[self.index+2] = self.registers[self.vx] % 10

    def _store_registers_0_to_vx(self):
        LOG.info("_store_registers_0_to_vx")
        for i in range(self.vx+1):
            self.memory[self.index + i] = self.registers[i]
        self.index += self.vx + 1

    def _read_ld_registers_i_to_vx(self):
        LOG.info("_read_ld_registers_i_to_vx")
        for i in range(self.vx+1):
            self.registers[i] == self.memory[self.index + 1]
        self.index += self.vx + 1

    def _sprite(self):
        LOG.info("_sprite")
        #   TODO: refactor
        self.registers[0x000F] = 0
        x = self.registers[self.vx] & 0x00FF
        y = self.registers[self.vy] & 0x00FF
        height = self.op & 0x000F
        row = 0
        while row < height:
            curr_row = self.memory[row + self.index]
            pixel_offset = 0
            while pixel_offset < 8:
                loc = x + pixel_offset + ((y + row) * 64)
                pixel_offset += 1
                if (y + row) >= 32 or (x + pixel_offset - 1) >= 64:
                    continue
                mask = 1 << 8-pixel_offset
                curr_pixel = (curr_row & mask) >> (8-pixel_offset)
                self.screen_buffer[loc] ^= curr_pixel
                if self.screen_buffer[loc] == 0:
                    self.registers[0xf] = 1
                else:
                    self.registers[0xf] = 0
            row += 1
        self.should_draw = True

    def _ldi(self):
        LOG.info("_ldi")
        self.index = self.c3b

    def _jmi(self):
        LOG.info("_jmi")
        self.pc = self.c3b + self.registers[0x0000]

    def _ld_vx_rand(self):
        LOG.info("_ld_vx_rand")
        r = int(random.random() * 0x00FF)
        self.registers[self.vx] = r & self.c2b
        self.registers[self.vx] &= 0xff

    def _EXIT(self):
        LOG.info("_EXIT'ed")
        self.exited = True

    def _0ZZZ(self):
        LOG.info("_0ZZZ")
        if self.op == 0x00E0:
            self._disp_clear()
        elif self.op == 0x00EE:
            self._return_from_sub()
        elif self.op == 0x00FD:
            self._EXIT()
        else: # 0NNN
            LOG.info("\t dispatch fell through, 0NNN hardware _call is outmoded operation")
            # self._call()
        
    def _disp_clear(self):
        LOG.info("_disp_clear")
        self.screen_buffer = [0]*Chip8Emulator.SCREEN_WIDTH*Chip8Emulator.SCREEN_HEIGHT
        self.should_draw = True

    def _return_from_sub(self):
        LOG.info("_return_from_sub")
        self.pc = self.stack.pop()

    def _call(self):
        LOG.info("_call")
        LOG.info(f"\tstoring current pc {fbhs(self.pc)} to stack")
        self.stack.append(self.pc)
        LOG.info(f"\tjumping to {fbhs(self.c3b)}")
        self.pc = self.c3b

    def _jump(self):
        LOG.info("_jump")
        LOG.info(f"\tjumping to {fbhs(self.c3b)}")
        self.pc = self.c3b

def main():
    pygame.init()
    screen_dims = Vector2(64, 32)
    window_dims = screen_dims * 16.0
    primary_surface = pygame.Surface(screen_dims)
    window = pygame.display.set_mode(window_dims)

    emu = Chip8Emulator()
    emu.reset()
    emu.load_rom("test.bin")
    # emu.load_rom("./Maze (alt) [David Winter, 199x].ch8")
    # emu.load_rom("./Sierpinski [Sergey Naydenov, 2010].ch8")
    # emu.load_rom("./output.ch8")

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
                    
                # if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
                #     if event.type == pygame.KEYDOWN and event.key in [K_ESCAPE, K_q]:
        if running == False:
            break

        # emu.dispatch_events()
        emu.cycle()

        primary_surface.fill((0, 0, 0))
        emu.draw(primary_surface)
        blit = pygame.transform.scale(
            primary_surface, window.get_size()
        )
        window.blit(blit, (0, 0))
        pygame.display.flip()

        time = pygame.time.get_ticks()
        dt = (time - last_time) / 1000.0
        last_time = time
        steps += 1
    pygame.quit()

if __name__ == "__main__":
    main()