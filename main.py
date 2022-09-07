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

import os
import random
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pygame import Vector2
from pygame.locals import (
    K_q,
    K_ESCAPE,
)

import logging
logging.basicConfig(level=logging.NOTSET)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class Chip8Emulator:
    MEMORY_SIZE = 4096
    SCREEN_WIDTH = 64
    SCREEN_HEIGHT = 32

    def __init__(self):
        self.current_rom_path = None
        self.reset()

    def reset(self):
        LOG.info("reset")
        self.key_inputs = [0]*16
        self._disp_clear()
        self.memory = [0]*Chip8Emulator.MEMORY_SIZE
        self.registers = [0]*16
        self.index = 0
        self.pc = 0x200 #512
        '''
        start of mem is 16 digit sprites, each 5 bytes, 
        '''
        self.stack = []

        self.sound_timer = 0
        self.delay_timer = 0
        self.should_draw = False

        self.font = [0]*80
        self.load_font()
        if self.current_rom_path:
            self.load_rom(self.current_rom_path)

    def load_font(self):
        LOG.info("load font")
        for i in range(80):
            self.memory[i] = self.font[i]

    def load_rom(self, path):
        self.current_rom_path = path
        LOG.info(f"loading rom at {path}")
        try:
            with open(path, "rb") as bin:
                rom = bin.read()
            for i, b in enumerate(rom):
                self.memory[i+0x200] = b
        except Exception as e:
            LOG.error("couldnt read rom")
            quit()

    def dispatch_events(self):
        pass

    def process(self, op):
        try:
            self.isa[op]()
        except:
            LOG.error(f"invalid instruction: 0x{op:02x}")
            quit()

    def inc_pc(self):
        self.pc += 2

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

    def cycle(self):
        if self.pc >= Chip8Emulator.MEMORY_SIZE:
            LOG.error("program counter exceeded program memory")
            quit()

        self.op = self.memory[self.pc]
        op_type = self.op & 0xf000
        self.process(op_type)
        
        self.inc_pc()    #   does this go after or before opcode fetching....
        self.delay_timer = max(0, self.delay_timer - 1)
        self.sound_timer = max(0, self.sound_timer - 1)
        if self.sound_timer == 0:
            # play a sound
            pass

    def _skip_eq_vx_nn(self):
        if self.registers[self.vx] == self.c2b:
            self.inc_pc()

    def _skip_neq_vx_nn(self):
        if self.registers[self.vx] != self.c2b:
            self.inc_pc()

    def _skip_eq_vx_vy(self):
        if self.registers[self.vx] == self.registers[self.vy]:
            self.inc_pc() 

    def _ld_vx_nn(self):
        self.registers[self.vx] == self.c2b

    def _add_vx_nn(self):
        self.registers[self.vx] += self.c2b

    def _8ZZZ(self):
        sub_op = (self.op & 0xF00F) + 0x001
        self.process(sub_op)

    def _ld_vx_vy(self):
        self.registers[self.vx] = self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _ldor_vx_vy(self):
        self.registers[self.vx] |= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _andor_vx_vy(self):
        self.registers[self.vx] &= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _xor_vx_vy(self):
        self.registers[self.vx] ^= self.registers[self.vy]
        self.registers[self.vx] &= 0x00FF

    def _cadd_vx_vy(self):
        rsum = self.registers[self.vx] + self.registers[self.vy]
        if rsum > 0x00ff:   #   overflow, set carry
            self.registers[0x000F] = 1
        else:
            self.registers[0x000F] = 0
            self.registers[self.vx] = rsum
            self.registers[self.vx] &= 0x00FF

    def _bsub_vx_vy(self):
        if self.registers[self.vy] > self.registers[self.vx]:   #   overflow, set borrow
            self.registers[0x000F] = 0
        else:
            self.registers[0x000F] = 1
            self.registers[self.vx] -= self.registers[self.vy]
            self.registers[self.vx] &= 0x00FF

    def _rshift_vx(self):
        self.registers[0x000F] = self.registers[self.vx] & 0x0001
        self.registers[self.vx] >>= 1

    def _bsub_vy_vx(self):
        if self.registers[self.vx] > self.registers[self.vy]:   #   overflow, set borrow
            self.registers[0x000F] = 0
        else:
            self.registers[0x000F] = 1
            self.registers[self.vx] = self.registers[self.vy] - self.registers[self.vx]
            self.registers[self.vx] &= 0xff

    def _lshift_vx(self):
        self.registers[0x000F] = (self.registers[self.vx] & 0x00F0) >> 7
        self.registers[self.vx] = self.registers[self.vx] << 1
        self.registers[self.vx] &= 0x00FF

    def _skip_neq_vx_vy(self):
        if self.registers[self.vx] != self.registers[self.vy]:
            self.inc_pc()

    def define_isa(self):
        self.isa = {
            0x0000: self._0ZZZ,
            0x1000: self._jump,
            0x2000: self._call,
            0x3000: self._skip_eq_vx_nn,
            0x4000: self._skip_neq_vx_nn,
            0x5000: self._skip_eq_vx_vy,
            0x6000: self._ld_vx_nn,
            0x7000: self._add_vx_nn,
            0x8000: self._8ZZZ,
            0x8001: self._ld_vx_vy,
            0x8002: self._ldor_vx_vy,
            0x8003: self._andor_vx_vy,
            0x8004: self._xor_vx_vy,
            0x8005: self._cadd_vx_vy,
            0x8006: self._bsub_vx_vy,
            0x8007: self._rshift_vx,
            0x8008: self._bsub_vy_vx,
            0x800F: self._lshift_vx,
            0x9000: self._skip_neq_vx_vy,
            0xA000: self._ldi,
            0xB000: self._jmi,
            0xC000: self._ld_vx_rand,
            0xD000: self._sprite,
            0xE000: self._EZZZ, #todo   
            0xF000: self._FZZZ, #todo
        }

    def _skip_vx_pressed(self):
        key = self.registers[self.vx] & 0x000F
        if self.key_inputs[key] == 1:
            self.inc_pc()

    def skip_not_vx_pressed(self):
        key = self.registers[self.vx] & 0x000F
        if self.key_inputs[key] == 0:
            self.inc_pc()

    def _EZZZ(self):
        if self.op == 0xE00E:
            self._skip_vx_pressed()
        elif self.op == 0xE001:
            self._skip_not_vx_pressed()

    def _sprite(self):
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
        self.index = self.c3b

    def _jmi(self):
        self.pc = self.c3b + self.registers[0x0000]

    def _ld_vx_rand(self):
        r = int(random.random() * 0x00FF)
        self.registers[self.vx] = r & self.c2b
        self.registers[self.vx] &= 0xff

    def _0ZZZ(self):
        if self.op == 0x00E0:
            self._disp_clear()
        elif self.op == 0x00EE:
            self._return_from_sub()
        else: # 0NNN
            self._call()
        
    def _disp_clear(self):
        self.screen_buffer = [0]*Chip8Emulator.SCREEN_WIDTH*Chip8Emulator.SCREEN_HEIGHT

    def _return_from_sub(self):
        self.pc = self.stack.pop()

    def _call(self):
        pass

    def _jump(self):
        self.pc = self.opcode & 0x0FFF

    
    

def main():
    pygame.init()
    screen_dims = Vector2(64, 32)
    window_dims = screen_dims * 4.0
    primary_surface = pygame.Surface(screen_dims)
    window = pygame.display.set_mode(window_dims)

    emu = Chip8Emulator()
    emu.load_rom("./f.bin")

    dt = 1.0 / 60.0
    time = pygame.time.get_ticks()
    last_time = time
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            else:
                if event.type == pygame.KEYDOWN and event.key in [K_ESCAPE, K_q]:
                    running = False
                    break
                # if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
                #     if event.type == pygame.KEYDOWN and event.key in [K_ESCAPE, K_q]:
        if running == False:
            break

        emu.dispatch_events()
        emu.cycle()

        primary_surface.fill((0, 0, 0))
        # draw the pixel buffer here
        blit = pygame.transform.scale(
            primary_surface, window.get_size()
        )
        window.blit(blit, (0, 0))
        pygame.display.flip()

        time = pygame.time.get_ticks()
        dt = (time - last_time) / 1000.0
        last_time = time
    pygame.quit()

if __name__ == "__main__":
    main()