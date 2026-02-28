import os
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame
from pygame.locals import (
    K_1,
    K_2,
    K_3,
    K_4,
    K_a,
    K_c,
    K_d,
    K_e,
    K_ESCAPE,
    K_f,
    K_q,
    K_r,
    K_s,
    K_v,
    K_w,
    K_x,
    K_z,
)

from .config import DEFAULT_ROM_PATH, DEFAULT_TONE_PATH, SCREEN_HEIGHT, SCREEN_WIDTH
from .core import execute_cycle
from .quirks import Chip8Quirks
from .state import EmulatorState, create_state, set_key_state

KEY_MAP = {
    K_1: 0x1,
    K_2: 0x2,
    K_3: 0x3,
    K_4: 0xC,
    K_q: 0x4,
    K_w: 0x5,
    K_e: 0x6,
    K_r: 0xD,
    K_a: 0x7,
    K_s: 0x8,
    K_d: 0x9,
    K_f: 0xE,
    K_z: 0xA,
    K_x: 0x0,
    K_c: 0xB,
    K_v: 0xF,
}


def draw_frame(state: EmulatorState, surface: pygame.Surface) -> None:
    if not state.should_draw:
        return

    for index, value in enumerate(state.screen_buffer):
        if value == 0:
            continue
        x = index % SCREEN_WIDTH
        y = index // SCREEN_WIDTH
        surface.set_at((x, y), (255, 255, 255))


def handle_input_event(state: EmulatorState, event: pygame.event.Event) -> None:
    mapped_key = KEY_MAP.get(event.key)
    if mapped_key is None:
        return

    if event.type == pygame.KEYDOWN:
        set_key_state(state, mapped_key, True)
    elif event.type == pygame.KEYUP:
        set_key_state(state, mapped_key, False)


def run_emulator(
    quirks: Chip8Quirks,
    rom_path: str | Path = DEFAULT_ROM_PATH,
    scale: int = 16,
) -> EmulatorState:
    pygame.init()

    primary_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    window = pygame.display.set_mode((SCREEN_WIDTH * scale, SCREEN_HEIGHT * scale))

    tone = pygame.mixer.Sound(str(DEFAULT_TONE_PATH))

    state = create_state(rom_path=rom_path)

    running = True
    while running and not state.exited:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN and event.key == K_ESCAPE:
                running = False
                break

            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                handle_input_event(state, event)

        if not running:
            break

        execute_cycle(state, quirks, sound_callback=tone.play)

        primary_surface.fill((0, 0, 0))
        draw_frame(state, primary_surface)

        window.blit(pygame.transform.scale(primary_surface, window.get_size()), (0, 0))
        pygame.display.flip()

    pygame.quit()
    return state
