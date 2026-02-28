# Project Working Rules

## Architecture
- Keep source files between 300 and 500 lines max; prefer smaller focused modules.
- Use a flat package structure under `src/chip8_emulator/`.
- Group code by concern:
  - `config` for constants/paths
  - `quirks` for behavior profiles
  - `state` for emulator state + state helpers
  - `core` for opcode execution logic
  - `runtime` for pygame/input/render loop
- Keep opcode logic and CPU behavior separate from UI/render code.

## Style
- Prefer functional code over OOP.
- Avoid large classes; use plain functions and simple data containers.
- Keep naming direct and boring; avoid clever abstractions.
- Keep control flow obvious and branch logic local.

## Readability
- De-brain the code: fewer layers, fewer hidden side effects.
- Side effects should be at boundaries (file IO, pygame, audio).
- Add comments only where behavior is non-obvious.

## Testing
- Add/adjust tests for every opcode behavior change.
- Keep tests independent of pygame when possible.
