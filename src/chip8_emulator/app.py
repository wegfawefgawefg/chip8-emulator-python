import os
from pathlib import Path

from .config import DEFAULT_ROM_PATH, DEFAULT_TONE_PATH, SCREEN_HEIGHT, SCREEN_WIDTH
from .cpu import execute_cycle
from .quirks import Chip8Quirks
from .state import EmulatorState, create_state, set_key_state

def draw_screen(state: EmulatorState, surface: object) -> None:
    if not state.should_draw:
        return

    for index, value in enumerate(state.screen_buffer):
        if value == 0:
            continue
        x = index % SCREEN_WIDTH
        y = index // SCREEN_WIDTH
        surface.set_at((x, y), (255, 255, 255))


def apply_input_event(
    state: EmulatorState,
    event: object,
    key_map: dict[int, int],
    keydown_event: int,
    keyup_event: int,
) -> None:
    mapped_key = key_map.get(event.key)
    if mapped_key is None:
        return

    if event.type == keydown_event:
        set_key_state(state, mapped_key, True)
    elif event.type == keyup_event:
        set_key_state(state, mapped_key, False)


def run_emulator_headless(
    quirks: Chip8Quirks,
    rom_path: str | Path = DEFAULT_ROM_PATH,
    max_cycles: int = 2000,
) -> EmulatorState:
    if max_cycles <= 0:
        raise ValueError("max_cycles must be > 0")

    state = create_state(rom_path=rom_path)

    for _ in range(max_cycles):
        if state.exited:
            break
        execute_cycle(state, quirks, sound_callback=None)

    return state


def run_emulator_app(
    quirks: Chip8Quirks,
    rom_path: str | Path = DEFAULT_ROM_PATH,
    scale: int = 16,
    cpu_hz: int = 240,
    target_fps: int = 60,
) -> EmulatorState:
    if cpu_hz <= 0:
        raise ValueError("cpu_hz must be > 0")
    if target_fps <= 0:
        raise ValueError("target_fps must be > 0")

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

    key_map = {
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

    pygame.init()
    clock = pygame.time.Clock()
    cycle_interval = 1.0 / float(cpu_hz)
    accumulated_time = 0.0

    primary_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    window = pygame.display.set_mode((SCREEN_WIDTH * scale, SCREEN_HEIGHT * scale))

    sound_callback = None
    try:
        tone = pygame.mixer.Sound(str(DEFAULT_TONE_PATH))
        sound_callback = tone.play
    except pygame.error:
        sound_callback = None

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
                apply_input_event(
                    state,
                    event,
                    key_map=key_map,
                    keydown_event=pygame.KEYDOWN,
                    keyup_event=pygame.KEYUP,
                )

        if not running:
            break

        frame_dt = clock.tick(target_fps) / 1000.0
        accumulated_time += frame_dt
        max_cycles_per_frame = max(1, cpu_hz // target_fps * 3)

        cycles_run = 0
        while (
            accumulated_time >= cycle_interval
            and cycles_run < max_cycles_per_frame
            and not state.exited
        ):
            execute_cycle(state, quirks, sound_callback=sound_callback)
            accumulated_time -= cycle_interval
            cycles_run += 1

        primary_surface.fill((0, 0, 0))
        draw_screen(state, primary_surface)
        window.blit(pygame.transform.scale(primary_surface, window.get_size()), (0, 0))
        pygame.display.flip()

    pygame.quit()
    return state
