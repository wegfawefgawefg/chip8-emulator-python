import pygame
from pygame import Vector2
from pygame.locals import (
    K_q,
    K_ESCAPE,
)

class Chip8Emulator:
    def __init__(self):
        self.inputs = [0]*16
        self.sbuff = [0]*32*64
        self.mem = [0]*4096
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

    def load_fonts(self):
        pass

    def load_rom(self, path):
        with open(path, "rb") as binary:
            while 

    def dispatch_events(self):
        pass

    def cycle(self):
        pass

pygame.init()
screen_dims = Vector2(64, 32)
window_dims = screen_dims * 4.0
primary_surface = pygame.Surface(screen_dims)
window = pygame.display.set_mode(window_dims)

emu = Chip8Emulator()
emu.load_rom()

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