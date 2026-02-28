"""CHIP-8 assembler package."""

from .assembler import assemble_file, assemble_text
from .errors import AssemblerError

__all__ = ["AssemblerError", "assemble_file", "assemble_text"]
