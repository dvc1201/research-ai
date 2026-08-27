"""Base classes for pluggable audio generators.

Each TTS/audio method is represented by a subclass of :class:`Generator`
that implements :meth:`Generator.setup` and :meth:`Generator.generate`.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ConfigError(Exception):
    """Raised when a generator's control-file parameters are invalid."""


class Generator(ABC):
    """Abstract base class for audio generation methods."""

    @abstractmethod
    def setup(self, config: dict[str, str]) -> None:
        """Read and validate method-specific parameters from *config*.

        *config* is the full parsed control file (common keys included).
        Raise :class:`ConfigError` if a mandatory parameter is missing or
        invalid.
        """

    @abstractmethod
    def generate(self, text: str, full_output_path: Path) -> Path:
        """Synthesise *text* and write it to *full_output_path*.

        Return the path of the file actually produced. The returned path may
        differ from *full_output_path* in extension (e.g. a method that
        natively emits WAV may return a ``.wav`` path even though a ``.mp3``
        path was requested).
        """
