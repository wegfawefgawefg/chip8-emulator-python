# chip8-emulator-python
CHIP-8 emulator project.

## Project Layout
- `src/chip8_emulator/`: emulator source code
- `assets/`: runtime assets (for example `tone.wav`)
- `roms/`: CHIP-8 ROMs and generated test ROM binaries
- `dumps/`: emulator memory dumps and debug output files
- `scripts/`: helper scripts
- `tests/`: test suite scaffold

## UV Setup
```bash
uv sync
uv run chip8
```

Generate the local opcode test binary:
```bash
uv run python scripts/create_test_binary.py
```

## Archive Status
This repository is archived.

- Last known local work (file modification): `main.py` on 2023-10-31 20:31:46 -0500
- Last git commit: `3ed9d07` on 2022-09-14 22:10:17 +0900
