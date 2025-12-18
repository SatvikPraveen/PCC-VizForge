"""Custom exceptions for PCC-VizForge."""


class PccVizForgeError(Exception):
    """Base exception for PCC-VizForge."""

    pass


class ConfigurationError(PccVizForgeError):
    """Raised when configuration is invalid or missing."""

    pass


class DataGenerationError(PccVizForgeError):
    """Raised when data generation fails."""

    pass


class ValidationError(PccVizForgeError):
    """Raised when input validation fails."""

    pass


class VisualizationError(PccVizForgeError):
    """Raised when visualization creation fails."""

    pass


class IOError(PccVizForgeError):
    """Raised when file I/O operations fail."""

    pass


class ExportError(PccVizForgeError):
    """Raised when export operations fail."""

    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Raised when configuration file is not found."""

    pass


class InvalidParameterError(ValidationError):
    """Raised when invalid parameters are provided."""

    pass


class DataShapeError(DataGenerationError):
    """Raised when generated data has unexpected shape."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration format is invalid."""

    pass
