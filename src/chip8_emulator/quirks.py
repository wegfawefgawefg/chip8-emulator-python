from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
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


def load_quirks_profile(profile: str) -> Chip8Quirks:
    normalized = profile.strip().lower()
    quirks = QUIRKS_BY_PROFILE.get(normalized)
    if quirks is None:
        accepted = ", ".join(sorted(QUIRKS_BY_PROFILE.keys()))
        raise ValueError(f"invalid CHIP8_QUIRKS '{normalized}', expected one of: {accepted}")
    return quirks


def load_quirks_profile_from_env() -> tuple[str, Chip8Quirks]:
    profile = os.getenv("CHIP8_QUIRKS", "original")
    return profile.strip().lower(), load_quirks_profile(profile)
