class ApplicationError(Exception):
    """Base exception for expected application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class CSVValidationError(ApplicationError):
    """Raised when the uploaded CSV has an invalid structure."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            error_code="INVALID_CSV",
            status_code=400,
        )

class CSVFileTooLargeError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            message="CSV file size must not exceed 5 MB.",
            error_code="FILE_TOO_LARGE",
            status_code=413,
        )
