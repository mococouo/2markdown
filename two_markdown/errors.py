class ConversionError(Exception):
    """A file could not be converted by the selected converter."""


class MissingDependencyError(ConversionError):
    """A converter requires an optional dependency that is not installed."""

    def __init__(self, package: str, feature: str) -> None:
        super().__init__(
            f"{feature} requires optional package '{package}'. "
            f"Install all optional converters with: python -m pip install -e .[all]"
        )
        self.package = package
        self.feature = feature
