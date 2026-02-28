# chip8-emulator-python
CHIP-8 emulator project.

## Project Layout
- `src/chip8_emulator/`: emulator source code
- `assets/`: runtime assets (for example `tone.wav`)
- `roms/`: CHIP-8 ROMs and generated test ROM binaries
- `dumps/`: emulator memory dumps and debug output files
- `scripts/`: helper scripts
- `tests/`: test suite scaffold

### Source Modules
- `config.py`: constants and filesystem paths
- `quirks.py`: quirk profiles and profile loading
- `state.py`: emulator state + memory/input helpers
- `cpu.py`: opcode decode/execute and CPU cycle logic
- `app.py`: pygame input handling, rendering, and app loop
- `main.py`: CLI entrypoint

## UV Setup
```bash
uv sync
uv run chip8
```

Run with a specific ROM:
```bash
uv run chip8 --rom "roms/Sierpinski [Sergey Naydenov, 2010].ch8"
```

Run with modern quirk profile:
```bash
uv run chip8 --quirks modern
```

Generate the local opcode test binary:
```bash
uv run python scripts/create_test_binary.py
```

## CHIP-8 Compliance Target
Default profile is `original` (COSMAC VIP-style semantics). Set `CHIP8_QUIRKS=modern` for common CHIP-48/SCHIP-style quirks.

Implemented quirk switches:
- `shift_uses_vy`: `8XY6`/`8XYE` source register (`VY` in `original`, `VX` in `modern`)
- `load_store_increment_i`: whether `FX55`/`FX65` increment `I`
- `jump_with_vx`: `BNNN` (`V0 + NNN`) vs `BXNN`-style (`VX + XNN`) jump behavior
- `draw_wrap`: clip at screen edges vs wrap pixels across edges

Original profile behavior includes:
- `EX9E`/`EXA1` key-skip behavior
- `FX33` BCD storage at `I`, `I+1`, `I+2`
- `DXYN` collision flag semantics with modulo start coordinates and clipping at edges

## Archive Status

- Last known local work (file modification): `main.py` on 2023-10-31 20:31:46 -0500
- Last git commit: `3ed9d07` on 2022-09-14 22:10:17 +0900
