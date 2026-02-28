from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from assembler import AssemblerError, assemble_text


def test_assemble_basic_program_with_label_jump():
    source = """
        ORG 0x200
    start:
        LD V0, 1
        ADD V0, 2
        JP start
    """

    rom = assemble_text(source)

    assert rom == bytes([0x60, 0x01, 0x70, 0x02, 0x12, 0x00])


def test_assemble_data_directives_db_and_dw():
    source = """
        ORG 0x200
        DB 0x12, 34, 'A'
        DB "BC"
        DW 0xABCD
    """

    rom = assemble_text(source)

    assert rom == bytes([0x12, 34, 0x41, 0x42, 0x43, 0xAB, 0xCD])


def test_assemble_ld_variants_and_draw():
    source = """
        LD I, sprite
        LD V1, DT
        LD DT, V1
        LD ST, V1
        LD F, V1
        LD B, V1
        LD [I], V1
        LD V1, [I]
        DRW V1, V2, 5
    sprite:
        DB 0xFF
    """

    rom = assemble_text(source)

    expected = bytes(
        [
            0xA2,
            0x12,
            0xF1,
            0x07,
            0xF1,
            0x15,
            0xF1,
            0x18,
            0xF1,
            0x29,
            0xF1,
            0x33,
            0xF1,
            0x55,
            0xF1,
            0x65,
            0xD1,
            0x25,
            0xFF,
        ]
    )
    assert rom == expected


def test_assemble_org_pads_rom():
    source = """
        ORG 0x200
        JP 0x206
        ORG 0x206
        RET
    """

    rom = assemble_text(source)

    assert rom == bytes([0x12, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0xEE])


def test_assemble_errors_on_invalid_register():
    with pytest.raises(AssemblerError):
        assemble_text("LD V16, 1")
