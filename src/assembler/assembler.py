from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .encoding import encode_instruction, ensure_range, parse_numeric_literal, parse_value
from .errors import AssemblerError


@dataclass(slots=True)
class Statement:
    line_no: int
    address: int
    kind: str
    operation: str
    arguments: list[str]


def assemble_file(path: str | Path, origin: int = 0x200) -> bytes:
    source_path = Path(path)
    return assemble_text(source_path.read_text(), origin=origin)


def assemble_text(source: str, origin: int = 0x200) -> bytes:
    statements, labels = parse_source(source, origin)
    return encode_statements(statements, labels, origin)


def parse_source(source: str, origin: int) -> tuple[list[Statement], dict[str, int]]:
    statements: list[Statement] = []
    labels: dict[str, int] = {}
    program_counter = origin

    for line_no, raw_line in enumerate(source.splitlines(), start=1):
        content = strip_comments(raw_line).strip()
        if not content:
            continue

        line_labels, remainder = split_labels(content, line_no)
        for label in line_labels:
            if label in labels:
                raise AssemblerError(f"duplicate label '{label}'", line_no)
            labels[label] = program_counter

        if not remainder:
            continue

        operation, arguments = split_operation_and_arguments(remainder)
        normalized = normalize_operation(operation)
        kind = classify_operation(normalized)

        statements.append(
            Statement(
                line_no=line_no,
                address=program_counter,
                kind=kind,
                operation=normalized,
                arguments=arguments,
            )
        )

        if kind == "directive_org":
            if len(arguments) != 1:
                raise AssemblerError("ORG expects exactly one argument", line_no)
            target = parse_numeric_literal(arguments[0], line_no)
            if target < origin:
                raise AssemblerError(
                    f"ORG target 0x{target:03X} cannot be below origin 0x{origin:03X}",
                    line_no,
                )
            if target < program_counter:
                raise AssemblerError(
                    f"ORG target 0x{target:03X} cannot move backwards from 0x{program_counter:03X}",
                    line_no,
                )
            program_counter = target
        elif kind == "directive_db":
            if not arguments:
                raise AssemblerError("DB expects at least one argument", line_no)
            program_counter += count_db_bytes(arguments, line_no)
        elif kind == "directive_dw":
            if not arguments:
                raise AssemblerError("DW expects at least one argument", line_no)
            program_counter += 2 * len(arguments)
        else:
            program_counter += 2

    return statements, labels


def encode_statements(
    statements: list[Statement], labels: dict[str, int], origin: int
) -> bytes:
    output = bytearray()
    current_address = origin

    for statement in statements:
        if statement.kind == "directive_org":
            target = parse_value(statement.arguments[0], labels, statement.line_no)
            if target < current_address:
                raise AssemblerError(
                    f"ORG target 0x{target:03X} cannot move backwards from 0x{current_address:03X}",
                    statement.line_no,
                )
            output.extend(b"\x00" * (target - current_address))
            current_address = target
            continue

        if statement.kind == "directive_db":
            db_values = encode_db_values(statement.arguments, labels, statement.line_no)
            output.extend(db_values)
            current_address += len(db_values)
            continue

        if statement.kind == "directive_dw":
            for argument in statement.arguments:
                word = parse_value(argument, labels, statement.line_no)
                ensure_range(word, 0, 0xFFFF, "word", statement.line_no)
                output.append((word >> 8) & 0xFF)
                output.append(word & 0xFF)
                current_address += 2
            continue

        opcode = encode_instruction(
            statement.operation,
            statement.arguments,
            labels,
            statement.line_no,
        )
        output.append((opcode >> 8) & 0xFF)
        output.append(opcode & 0xFF)
        current_address += 2

    return bytes(output)


def strip_comments(line: str) -> str:
    in_quote: str | None = None
    for i, ch in enumerate(line):
        if ch in ("'", '"'):
            if in_quote is None:
                in_quote = ch
            elif in_quote == ch:
                in_quote = None
        elif ch in (";", "#") and in_quote is None:
            return line[:i]
    return line


def split_labels(content: str, line_no: int) -> tuple[list[str], str]:
    labels: list[str] = []
    remainder = content

    while True:
        colon_index = remainder.find(":")
        if colon_index < 0:
            return labels, remainder.strip()

        before_colon = remainder[:colon_index].strip()
        after_colon = remainder[colon_index + 1 :].strip()

        if not before_colon or any(ch.isspace() for ch in before_colon):
            return labels, remainder.strip()

        validate_label(before_colon, line_no)
        labels.append(before_colon)
        remainder = after_colon

        if not remainder:
            return labels, ""


def validate_label(label: str, line_no: int) -> None:
    if not (label[0].isalpha() or label[0] == "_"):
        raise AssemblerError(f"invalid label '{label}'", line_no)
    for ch in label[1:]:
        if not (ch.isalnum() or ch == "_"):
            raise AssemblerError(f"invalid label '{label}'", line_no)


def split_operation_and_arguments(text: str) -> tuple[str, list[str]]:
    parts = text.split(None, 1)
    operation = parts[0]
    if len(parts) == 1:
        return operation, []
    return operation, split_arguments(parts[1])


def split_arguments(text: str) -> list[str]:
    if not text:
        return []

    args: list[str] = []
    token: list[str] = []
    in_quote: str | None = None

    for ch in text:
        if ch in ("'", '"'):
            if in_quote is None:
                in_quote = ch
            elif in_quote == ch:
                in_quote = None
            token.append(ch)
            continue

        if ch == "," and in_quote is None:
            value = "".join(token).strip()
            if value:
                args.append(value)
            token = []
            continue

        token.append(ch)

    tail = "".join(token).strip()
    if tail:
        args.append(tail)

    return args


def normalize_operation(operation: str) -> str:
    op = operation.strip().upper()
    if op.startswith("."):
        op = op[1:]
    return op


def classify_operation(operation: str) -> str:
    if operation == "ORG":
        return "directive_org"
    if operation == "DB":
        return "directive_db"
    if operation == "DW":
        return "directive_dw"
    return "instruction"


def count_db_bytes(arguments: list[str], line_no: int) -> int:
    total = 0
    for argument in arguments:
        parsed_string = parse_string_literal(argument)
        if parsed_string is not None:
            total += len(parsed_string)
        else:
            total += 1
    if total <= 0:
        raise AssemblerError("DB produced no bytes", line_no)
    return total


def parse_string_literal(token: str) -> str | None:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        value = ast.literal_eval(token)
        if not isinstance(value, str):
            return None
        return value
    return None


def encode_db_values(
    arguments: list[str], labels: dict[str, int], line_no: int
) -> list[int]:
    values: list[int] = []
    for argument in arguments:
        parsed_string = parse_string_literal(argument)
        if parsed_string is not None:
            for ch in parsed_string:
                values.append(ord(ch) & 0xFF)
            continue

        byte = parse_value(argument, labels, line_no)
        ensure_range(byte, 0, 0xFF, "byte", line_no)
        values.append(byte)
    return values
