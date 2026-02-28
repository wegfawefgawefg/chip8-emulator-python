from __future__ import annotations

from .errors import AssemblerError


def parse_numeric_literal(token: str, line_no: int) -> int:
    token = token.strip()
    if token.startswith("$"):
        token = "0x" + token[1:]

    if len(token) >= 3 and token[0] == token[-1] == "'":
        inner = token[1:-1]
        if len(inner) == 1:
            return ord(inner)

    try:
        return int(token, 0)
    except ValueError as exc:
        raise AssemblerError(f"invalid value '{token}'", line_no) from exc


def parse_value(token: str, labels: dict[str, int], line_no: int) -> int:
    token = token.strip()
    if token in labels:
        return labels[token]
    return parse_numeric_literal(token, line_no)


def ensure_range(value: int, minimum: int, maximum: int, label: str, line_no: int) -> None:
    if value < minimum or value > maximum:
        raise AssemblerError(
            f"{label} out of range: {value} (expected {minimum}..{maximum})",
            line_no,
        )


def parse_register(token: str, line_no: int) -> int:
    value = token.strip().upper()
    if not value.startswith("V"):
        raise AssemblerError(f"expected register, got '{token}'", line_no)

    reg_text = value[1:]
    if len(reg_text) == 1 and reg_text in "0123456789ABCDEF":
        return int(reg_text, 16)

    if reg_text.isdigit():
        reg = int(reg_text, 10)
        if 0 <= reg <= 15:
            return reg

    raise AssemblerError(f"invalid register '{token}'", line_no)


def is_register(token: str) -> bool:
    token = token.strip().upper()
    if not token.startswith("V"):
        return False
    try:
        reg = parse_register(token, 0)
    except AssemblerError:
        return False
    return 0 <= reg <= 15


def expect_arg_count(
    mnemonic: str, arguments: list[str], expected: int, line_no: int
) -> None:
    if len(arguments) != expected:
        raise AssemblerError(
            f"{mnemonic} expects {expected} argument(s), got {len(arguments)}",
            line_no,
        )


def encode_instruction(
    mnemonic: str, arguments: list[str], labels: dict[str, int], line_no: int
) -> int:
    op = mnemonic.upper()

    if op == "CLS":
        expect_arg_count(op, arguments, 0, line_no)
        return 0x00E0

    if op == "RET":
        expect_arg_count(op, arguments, 0, line_no)
        return 0x00EE

    if op == "EXIT":
        expect_arg_count(op, arguments, 0, line_no)
        return 0x00FD

    if op == "JP":
        if len(arguments) == 1:
            address = parse_value(arguments[0], labels, line_no)
            ensure_range(address, 0, 0x0FFF, "address", line_no)
            return 0x1000 | address
        if len(arguments) == 2:
            x_reg = parse_register(arguments[0], line_no)
            nn = parse_value(arguments[1], labels, line_no)
            ensure_range(nn, 0, 0x00FF, "byte", line_no)
            return 0xB000 | (x_reg << 8) | nn
        raise AssemblerError("JP expects one or two arguments", line_no)

    if op == "CALL":
        expect_arg_count(op, arguments, 1, line_no)
        address = parse_value(arguments[0], labels, line_no)
        ensure_range(address, 0, 0x0FFF, "address", line_no)
        return 0x2000 | address

    if op == "SE":
        expect_arg_count(op, arguments, 2, line_no)
        x_reg = parse_register(arguments[0], line_no)
        if is_register(arguments[1]):
            y_reg = parse_register(arguments[1], line_no)
            return 0x5000 | (x_reg << 8) | (y_reg << 4)
        nn = parse_value(arguments[1], labels, line_no)
        ensure_range(nn, 0, 0x00FF, "byte", line_no)
        return 0x3000 | (x_reg << 8) | nn

    if op == "SNE":
        expect_arg_count(op, arguments, 2, line_no)
        x_reg = parse_register(arguments[0], line_no)
        if is_register(arguments[1]):
            y_reg = parse_register(arguments[1], line_no)
            return 0x9000 | (x_reg << 8) | (y_reg << 4)
        nn = parse_value(arguments[1], labels, line_no)
        ensure_range(nn, 0, 0x00FF, "byte", line_no)
        return 0x4000 | (x_reg << 8) | nn

    if op == "LD":
        expect_arg_count(op, arguments, 2, line_no)
        dest = arguments[0].strip().upper()
        src = arguments[1].strip().upper()

        if is_register(dest):
            x_reg = parse_register(dest, line_no)
            if is_register(src):
                y_reg = parse_register(src, line_no)
                return 0x8000 | (x_reg << 8) | (y_reg << 4)
            if src == "DT":
                return 0xF007 | (x_reg << 8)
            if src == "K":
                return 0xF00A | (x_reg << 8)
            if src == "[I]":
                return 0xF065 | (x_reg << 8)
            nn = parse_value(arguments[1], labels, line_no)
            ensure_range(nn, 0, 0x00FF, "byte", line_no)
            return 0x6000 | (x_reg << 8) | nn

        if dest == "I":
            address = parse_value(arguments[1], labels, line_no)
            ensure_range(address, 0, 0x0FFF, "address", line_no)
            return 0xA000 | address

        if dest == "DT":
            x_reg = parse_register(arguments[1], line_no)
            return 0xF015 | (x_reg << 8)

        if dest == "ST":
            x_reg = parse_register(arguments[1], line_no)
            return 0xF018 | (x_reg << 8)

        if dest == "F":
            x_reg = parse_register(arguments[1], line_no)
            return 0xF029 | (x_reg << 8)

        if dest == "B":
            x_reg = parse_register(arguments[1], line_no)
            return 0xF033 | (x_reg << 8)

        if dest == "[I]":
            x_reg = parse_register(arguments[1], line_no)
            return 0xF055 | (x_reg << 8)

        raise AssemblerError(f"unsupported LD form: {arguments[0]}, {arguments[1]}", line_no)

    if op == "ADD":
        expect_arg_count(op, arguments, 2, line_no)
        dest = arguments[0].strip().upper()

        if dest == "I":
            x_reg = parse_register(arguments[1], line_no)
            return 0xF01E | (x_reg << 8)

        x_reg = parse_register(arguments[0], line_no)
        if is_register(arguments[1]):
            y_reg = parse_register(arguments[1], line_no)
            return 0x8004 | (x_reg << 8) | (y_reg << 4)

        nn = parse_value(arguments[1], labels, line_no)
        ensure_range(nn, 0, 0x00FF, "byte", line_no)
        return 0x7000 | (x_reg << 8) | nn

    if op in ("OR", "AND", "XOR", "SUB", "SUBN"):
        expect_arg_count(op, arguments, 2, line_no)
        x_reg = parse_register(arguments[0], line_no)
        y_reg = parse_register(arguments[1], line_no)
        tail_by_op = {
            "OR": 0x1,
            "AND": 0x2,
            "XOR": 0x3,
            "SUB": 0x5,
            "SUBN": 0x7,
        }
        return 0x8000 | (x_reg << 8) | (y_reg << 4) | tail_by_op[op]

    if op in ("SHR", "SHL"):
        if len(arguments) not in (1, 2):
            raise AssemblerError(f"{op} expects one or two arguments", line_no)
        x_reg = parse_register(arguments[0], line_no)
        if len(arguments) == 2:
            y_reg = parse_register(arguments[1], line_no)
        else:
            y_reg = x_reg
        tail = 0x6 if op == "SHR" else 0xE
        return 0x8000 | (x_reg << 8) | (y_reg << 4) | tail

    if op == "RND":
        expect_arg_count(op, arguments, 2, line_no)
        x_reg = parse_register(arguments[0], line_no)
        nn = parse_value(arguments[1], labels, line_no)
        ensure_range(nn, 0, 0x00FF, "byte", line_no)
        return 0xC000 | (x_reg << 8) | nn

    if op == "DRW":
        expect_arg_count(op, arguments, 3, line_no)
        x_reg = parse_register(arguments[0], line_no)
        y_reg = parse_register(arguments[1], line_no)
        n = parse_value(arguments[2], labels, line_no)
        ensure_range(n, 0, 0x000F, "nibble", line_no)
        return 0xD000 | (x_reg << 8) | (y_reg << 4) | n

    if op == "SKP":
        expect_arg_count(op, arguments, 1, line_no)
        x_reg = parse_register(arguments[0], line_no)
        return 0xE09E | (x_reg << 8)

    if op == "SKNP":
        expect_arg_count(op, arguments, 1, line_no)
        x_reg = parse_register(arguments[0], line_no)
        return 0xE0A1 | (x_reg << 8)

    raise AssemblerError(f"unknown instruction '{mnemonic}'", line_no)
