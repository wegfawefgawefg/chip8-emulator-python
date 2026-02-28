# Assembler Enhancements

## Current Support

- Comments are supported with `;` and `#`.
- Labels are supported for jumps and calls.
- Subroutines are supported through `CALL label` and `RET`.
- Data directives are supported: `ORG`, `DB`, `DW`.
- Core CHIP-8 instruction forms used by this project are supported.

## What Is Not Included Yet

- No macro system.
- No `PROC` / `ENDP` style subroutine declarations.
- No local-label scoping under a parent label.
- No include/import directive for splitting assembly across files.
- No conditional-assembly features.

## Why Subroutine-Oriented Style Helps

- Reduces repeated branch-heavy code.
- Makes game logic easier to read and reason about.
- Lowers risk of skip/jump inversion bugs in long blocks.
- Improves testability by isolating logic into callable sections.

## Suggested Next Enhancements

1. Add local labels (for example, `.loop` scoped under a parent label).
2. Add simple macros for repeated instruction patterns.
3. Add `INCLUDE` support for shared sprites/constants.
4. Add optional linter checks for suspicious skip/jump patterns.
5. Add an assembler listing output mode (address + opcode + source).
