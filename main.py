import pygame
from pygame import Vector2
from pygame.locals import (
    K_q,
    K_ESCAPE,
)
inputs = [0]*16
sbuff = [0]*32*64
mem = [0]*4096
registers = [0]*16
sound_timer = 0
delay_timer = 0
index = 0
pc = 0
stack = []

pygame.init()
screen_dims = Vector2(64, 32)
window_dims = screen_dims * 4.0
primary_surface = pygame.Surface(screen_dims)
window = pygame.display.set_mode(window_dims)

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