"""Custom exception classes for AIDA.

This module provides AIDA-specific exception classes for consistent error
handling and user-friendly error messages across all installation scripts.
"""


class AidaError(Exception):
    """Base exception class for all AIDA errors.

    All AIDA-specific exceptions should inherit from this class to allow
    for consistent error handling throughout the application.
    """

    def __init__(self, message: str, suggestion: str = None):
        """Initialize the error with a message and optional suggestion.

        Args:
            message: The error message describing what went wrong
            suggestion: Optional suggestion for how to fix the issue
        """
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the error message with optional suggestion.

        Returns:
            Formatted error message string
        """
        if self.suggestion:
            return f"{self.message}\n\nSuggestion: {self.suggestion}"
        return self.message


class VersionError(AidaError):
    """Raised when Python version requirements are not met.

    This error is raised when the Python version is too old or incompatible
    with AIDA's requirements.
    """
    pass


class PathError(AidaError):
    """Raised when there are issues with path operations.

    This includes permission errors, invalid paths, or path creation failures.
    """
    pass


class FileOperationError(AidaError):
    """Raised when file operations fail.

    This includes read/write errors, missing files, or JSON parsing errors.
    """
    pass


class ConfigurationError(AidaError):
    """Raised when configuration is invalid or missing.

    This includes invalid JSON, missing required fields, or incompatible settings.
    """
    pass


class InstallationError(AidaError):
    """Raised when installation or setup fails.

    This is a general error for installation-related failures that don't fit
    into more specific categories.
    """
    pass
