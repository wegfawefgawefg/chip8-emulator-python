; white dot movement demo
; controls (physical keyboard):
;   W = up, A = left, S = down, D = right

ORG 0x200

start:
    LD V0, 32
    LD V1, 16
    LD V3, 1

loop:
    CLS
    LD I, dot
    DRW V0, V1, 1

    ; W key (chip-8 key 0x5)
    LD V2, 0x5
    SKP V2
    JP no_up
    SUB V1, V3
no_up:

    ; S key (chip-8 key 0x8)
    LD V2, 0x8
    SKP V2
    JP no_down
    ADD V1, V3
no_down:

    ; A key (chip-8 key 0x7)
    LD V2, 0x7
    SKP V2
    JP no_left
    SUB V0, V3
no_left:

    ; D key (chip-8 key 0x9)
    LD V2, 0x9
    SKP V2
    JP no_right
    ADD V0, V3
no_right:

    JP loop

; 1-pixel sprite (leftmost bit set)
dot:
    DB 0x80
