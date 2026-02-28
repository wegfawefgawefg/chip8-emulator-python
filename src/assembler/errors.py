class AssemblerError(Exception):
    def __init__(self, message: str, line_no: int | None = None):
        if line_no is None:
            super().__init__(message)
        else:
            super().__init__(f"line {line_no}: {message}")
        self.line_no = line_no
