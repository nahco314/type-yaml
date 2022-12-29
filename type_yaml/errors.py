import builtins

from yaml.error import Mark


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class Warning(builtins.Warning):
    """Base class for warnings in this module."""

    pass


class YamlError(Error):
    """Errors related to YAML notation, etc."""

    pass


class YamlTypeError(YamlError):
    """Errors related to YAML type."""

    def __init__(self, mark: Mark, message: str) -> None:
        self.mark = mark
        self.message = message

    def __str__(self) -> str:
        return f"{self.message}\n{self.mark}"
