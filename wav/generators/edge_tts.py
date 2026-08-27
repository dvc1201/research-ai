"""Edge-TTS generator implementation."""

import asyncio
import os
from pathlib import Path

import edge_tts

from .base import ConfigError, Generator

# ---------------------------------------------------------------------------
# method-specific parameter names (read from the control file)
# ---------------------------------------------------------------------------

PARAM_VOICE = "tts.voice"
PARAM_RATE = "tts.rate"

# defaults applied when the control file omits a parameter
DEFAULT_VOICE = "zh-CN-YunxiNeural"
DEFAULT_RATE = "-10%"


class EdgeTTS(Generator):
    """Generate audio via the Microsoft Edge-TTS service."""

    def __init__(self) -> None:
        self.voice: str = DEFAULT_VOICE
        self.rate: str = DEFAULT_RATE

    def setup(self, config: dict[str, str]) -> None:
        """Read ``tts.voice`` and ``tts.rate`` from the control file."""
        self.voice = config.get(PARAM_VOICE, DEFAULT_VOICE).strip()
        self.rate = config.get(PARAM_RATE, DEFAULT_RATE).strip()

        if not self.voice:
            raise ConfigError(f"'{PARAM_VOICE}' must not be empty")
        if not self.rate:
            raise ConfigError(f"'{PARAM_RATE}' must not be empty")

    def generate(self, text: str, full_output_path: Path) -> Path:
        """Synthesise *text* into an MP3 and return the produced path.

        Edge-TTS natively writes MP3 regardless of the requested extension,
        so the produced file always has an ``.mp3`` suffix.
        """
        mp3_path = full_output_path.with_suffix(".mp3")
        asyncio.run(self._async_generate(text, mp3_path))
        return mp3_path

    async def _async_generate(self, text: str, mp3_path: Path) -> None:
        """Run the Edge-TTS request and write the MP3 to *mp3_path*."""
        # save to a temporary name first so a failed request never leaves a
        # half-written target behind
        tmp_path = mp3_path.with_suffix(".tmp.mp3")
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        try:
            await communicate.save(str(tmp_path))
            os.replace(tmp_path, mp3_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
