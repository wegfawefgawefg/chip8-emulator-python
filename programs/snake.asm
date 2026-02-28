; snake demo
; controls:
;   W = up, A = left, S = down, D = right

ORG 0x200

start:
    ; constants
    LD V7, 2        ; segment stride in bytes
    LD V8, 0x3E     ; ring index mask (0..62, even)
    LD V9, 1        ; one
    LD VD, 0x0F     ; nibble mask for score digits

    JP title_screen

title_screen:
    CLS

    ; "SNAKE" title
    LD V0, 8
    LD V1, 8
    LD I, glyph_s
    DRW V0, V1, 5

    LD V0, 16
    LD I, glyph_n
    DRW V0, V1, 5

    LD V0, 24
    LD I, glyph_a
    DRW V0, V1, 5

    LD V0, 32
    LD I, glyph_k
    DRW V0, V1, 5

    LD V0, 40
    LD I, glyph_e
    DRW V0, V1, 5

wait_title_key:
    ; accept only WASD-mapped CHIP-8 keys
    LD V6, K
    SNE V6, 0x5
    JP init_game
    SNE V6, 0x8
    JP init_game
    SNE V6, 0x7
    JP init_game
    SNE V6, 0x9
    JP init_game
    JP wait_title_key

init_game:
    ; head state
    LD V0, 32
    LD V1, 16
    LD V2, 0        ; direction: 0=right,1=down,2=left,3=up
    LD V3, 0        ; head index in ring buffer
    LD V4, 3        ; snake length (segments)
    LD V5, 0        ; score

    ; initialize first 3 segments in snake_data ring (head at index 0)
    LD I, snake_data
    LD [I], V1      ; seg0 = (32,16)

    LD V0, 31
    LD V1, 16
    LD V6, 62
    LD I, snake_data
    ADD I, V6
    LD [I], V1      ; seg62 = (31,16)

    LD V0, 30
    LD V1, 16
    LD V6, 60
    LD I, snake_data
    ADD I, V6
    LD [I], V1      ; seg60 = (30,16)

    ; restore head registers
    LD V0, 32
    LD V1, 16

spawn_food:
    RND VB, 63
    RND VC, 31

    LD VF, 2
    LD DT, VF

loop:
    ; input with reverse-direction guard
    LD V6, 0x5      ; W
    SKP V6
    JP check_s
    SNE V2, 1
    JP check_s
    LD V2, 3

check_s:
    LD V6, 0x8      ; S
    SKP V6
    JP check_a
    SNE V2, 3
    JP check_a
    LD V2, 1

check_a:
    LD V6, 0x7      ; A
    SKP V6
    JP check_d
    SNE V2, 0
    JP check_d
    LD V2, 2

check_d:
    LD V6, 0x9      ; D
    SKP V6
    JP maybe_update
    SNE V2, 2
    JP maybe_update
    LD V2, 0

maybe_update:
    LD VF, DT
    SNE VF, 0
    JP update
    JP draw

update:
    ; restore current head from ring buffer (V0, V1 are scratch in draw code)
    LD I, snake_data
    ADD I, V3
    LD V1, [I]

    ; move head
    SE V2, 0
    JP dir_down
    ADD V0, V9
    JP moved

dir_down:
    SE V2, 1
    JP dir_left
    ADD V1, V9
    JP moved

dir_left:
    SE V2, 2
    JP dir_up
    SUB V0, V9
    JP moved

dir_up:
    SUB V1, V9

moved:
    ; wrap coordinates
    LD V6, 63
    AND V0, V6
    LD V6, 31
    AND V1, V6

    ; advance head index and store new head segment
    ADD V3, V7
    AND V3, V8

    LD I, snake_data
    ADD I, V3
    LD [I], V1

    ; backup head for collision checks
    LD VA, V0
    LD VD, V1

    ; self-collision: check len-1 previous segments
    LD V6, V4
    SUB V6, V9      ; count = len - 1
    LD VE, V3
    SUB VE, V7      ; previous segment index
    AND VE, V8

collision_loop:
    SNE V6, 0
    JP check_food

collision_body:
    LD I, snake_data
    ADD I, VE
    LD V1, [I]      ; load segment coords into V0,V1

    SE V0, VA
    JP collision_next
    SE V1, VD
    JP collision_next
    JP game_over_screen

collision_next:
    SUB VE, V7
    AND VE, V8
    SUB V6, V9
    JP collision_loop

check_food:
    ; restore head registers
    LD V0, VA
    LD V1, VD

    SNE V0, VB
    JP set_delay
    SNE V1, VC
    JP set_delay

    ; eat food: score++, grow up to max length 24
    ADD V5, V9
    LD VA, 24
    SNE V4, VA
    JP spawn_food
    ADD V4, V9
    JP spawn_food

set_delay:
    LD VF, 2
    LD DT, VF


draw:
    CLS

    ; draw food
    LD I, pixel
    LD V0, VB
    LD V1, VC
    DRW V0, V1, 1

    ; draw snake from head backwards for V4 segments
    LD V6, V4
    LD VE, V3

draw_snake_loop:
    SNE V6, 0
    JP draw_score

draw_snake_body:
    LD I, snake_data
    ADD I, VE
    LD V1, [I]

    LD I, pixel
    DRW V0, V1, 1

    SUB VE, V7
    AND VE, V8
    SUB V6, V9
    JP draw_snake_loop


draw_score:
    LD VD, 0x0F
    ; high nibble at x=50,y=0
    LD V6, V5
    SHR V6
    SHR V6
    SHR V6
    SHR V6
    AND V6, VD
    LD V0, 50
    LD V1, 0
    LD F, V6
    DRW V0, V1, 5

    ; low nibble at x=56,y=0
    LD V6, V5
    AND V6, VD
    LD V0, 56
    LD V1, 0
    LD F, V6
    DRW V0, V1, 5

    JP loop


game_over_screen:
    CLS

    ; "GO" marker
    LD V0, 22
    LD V1, 8
    LD I, glyph_g
    DRW V0, V1, 5

    LD V0, 30
    LD I, glyph_o
    DRW V0, V1, 5

    ; show score in the same top-right area
    LD VD, 0x0F
    LD V6, V5
    SHR V6
    SHR V6
    SHR V6
    SHR V6
    AND V6, VD
    LD V0, 50
    LD V1, 0
    LD F, V6
    DRW V0, V1, 5

    LD V6, V5
    AND V6, VD
    LD V0, 56
    LD V1, 0
    LD F, V6
    DRW V0, V1, 5

wait_over_key:
    LD V6, K
    SNE V6, 0x5
    JP init_game
    SNE V6, 0x8
    JP init_game
    SNE V6, 0x7
    JP init_game
    SNE V6, 0x9
    JP init_game
    JP wait_over_key

pixel:
    DB 0x80

glyph_s:
    DB 0xF0, 0x80, 0xE0, 0x10, 0xF0
glyph_n:
    DB 0x90, 0xD0, 0xB0, 0x90, 0x90
glyph_a:
    DB 0x60, 0x90, 0xF0, 0x90, 0x90
glyph_k:
    DB 0x90, 0xA0, 0xC0, 0xA0, 0x90
glyph_e:
    DB 0xF0, 0x80, 0xE0, 0x80, 0xF0
glyph_g:
    DB 0x70, 0x80, 0xB0, 0x90, 0x70
glyph_o:
    DB 0x60, 0x90, 0x90, 0x90, 0x60

; ring buffer for up to 32 segments: [x0,y0,x1,y1,...]
snake_data:
    DB 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    DB 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    DB 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    DB 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
