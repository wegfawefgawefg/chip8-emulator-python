; simple snake demo
; controls:
;   W = up, A = left, S = down, D = right

ORG 0x200

start:
    ; constants
    LD VC, 1
    LD VD, 63
    LD VE, 31

    ; head at center
    LD V0, 32
    LD V1, 16

    ; initial direction: right (0)
    LD V2, 0

    ; initial tail (3 segments)
    LD V4, 31
    LD V5, 16
    LD V6, 30
    LD V7, 16
    LD V8, 29
    LD V9, 16

    ; food
    RND VA, 63
    RND VB, 31

    ; movement timer seed
    LD V3, 8
    LD DT, V3

loop:
    ; input
    LD V3, 0x5
    SKP V3
    JP check_s
    LD V2, 3
check_s:
    LD V3, 0x8
    SKP V3
    JP check_a
    LD V2, 1
check_a:
    LD V3, 0x7
    SKP V3
    JP check_d
    LD V2, 2
check_d:
    LD V3, 0x9
    SKP V3
    JP maybe_update
    LD V2, 0

maybe_update:
    ; only update snake when delay timer reaches 0
    LD V3, DT
    SNE V3, 0
    JP update
    JP draw

update:
    ; shift tail
    LD V8, V6
    LD V9, V7
    LD V6, V4
    LD V7, V5
    LD V4, V0
    LD V5, V1

    ; move head by direction
    SE V2, 0
    JP dir_down
    ADD V0, VC
    JP moved

dir_down:
    SE V2, 1
    JP dir_left
    ADD V1, VC
    JP moved

dir_left:
    SE V2, 2
    JP dir_up
    SUB V0, VC
    JP moved

dir_up:
    SUB V1, VC

moved:
    ; wrap position
    AND V0, VD
    AND V1, VE

    ; check food collision
    SE V0, VA
    JP set_delay
    SE V1, VB
    JP set_delay
    RND VA, 63
    RND VB, 31

set_delay:
    LD V3, 8
    LD DT, V3

draw:
    CLS
    LD I, pixel
    DRW VA, VB, 1
    DRW V0, V1, 1
    DRW V4, V5, 1
    DRW V6, V7, 1
    DRW V8, V9, 1
    JP loop

pixel:
    DB 0x80
