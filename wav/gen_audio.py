# gen_audio.py — Synthesise WAV files from a mapping file using Edge-TTS
#
# Reads <name>_mapping.properties (filename=spoken text pairs) and calls the
# Microsoft Edge-TTS API to generate clean Mandarin speech WAV files.
#
# Usage: python gen_audio.py yang85_mapping.properties [--out-dir <path>]
# Default output: G:\My Drive\Peter\Taichi\Confucius4\<stem_without_mapping>\edgetts

import argparse
import asyncio
import os
import sys
from pathlib import Path

# -- ensure ffmpeg is on PATH (for pydub MP3→WAV conversion) --
_FFMPEG_BIN = (
    Path(os.environ["LOCALAPPDATA"])
    / "Microsoft" / "WinGet" / "Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.1.2-full_build" / "bin"
)
os.environ["PATH"] = str(_FFMPEG_BIN) + os.pathsep + os.environ["PATH"]

import edge_tts
from pydub import AudioSegment

# ---------------------------------------------------------------------------
# defaults
# ---------------------------------------------------------------------------

DEFAULT_BASE = Path(r"G:\My Drive\Peter\Taichi\Confucius4")
VOICE = "zh-CN-YunxiNeural"
RATE = "-10%"

# ---------------------------------------------------------------------------
# core logic
# ---------------------------------------------------------------------------


def parse_mapping(mapping_path: Path) -> list[tuple[str, str]]:
    """Return a list of (filename, spoken_text) tuples, preserving order."""
    entries: list[tuple[str, str]] = []
    with open(mapping_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            entries.append((key.strip(), val.strip()))
    return entries


def infer_output_dir(mapping_path: Path, cli_dir: str | None) -> Path:
    """Determine where to write the generated WAV files."""
    if cli_dir:
        return Path(cli_dir)

    # yang85_mapping.properties  →  yang85
    stem = mapping_path.stem
    if stem.endswith("_mapping"):
        form_name = stem[: -len("_mapping")]
    else:
        form_name = stem

    return DEFAULT_BASE / form_name / "edgetts"


async def generate_one(text: str, out_path: Path) -> None:
    """Synthesise *text* into a real WAV file at *out_path*."""
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    tmp = str(out_path) + ".tmp.mp3"
    await communicate.save(tmp)
    audio = AudioSegment.from_mp3(tmp)
    audio.export(out_path, format="wav")
    os.remove(tmp)


async def generate_all(entries: list[tuple[str, str]], out_dir: Path) -> None:
    """Generate all WAV files, max 5 in parallel."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(5)

    async def _worker(filename: str, text: str) -> None:
        async with sem:
            out_path = out_dir / filename
            print(f"  {filename:<28} → {text}")
            await generate_one(text, out_path)

    tasks = [_worker(fn, txt) for fn, txt in entries]
    await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate WAV audio from a filename→text mapping file"
    )
    parser.add_argument(
        "mapping_file",
        help="Path to *_mapping.properties file",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: infer from mapping file name)",
    )
    args = parser.parse_args()

    mapping_path = Path(args.mapping_file)
    if not mapping_path.is_file():
        print(f"Error: {mapping_path} not found")
        sys.exit(1)

    entries = parse_mapping(mapping_path)
    out_dir = infer_output_dir(mapping_path, args.out_dir)

    print(
        f"Generating {len(entries)} WAV files with "
        f"voice={VOICE} rate={RATE} …\n"
    )

    await generate_all(entries, out_dir)

    print(f"\nDone.  Files written to {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())