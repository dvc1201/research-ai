# gen_audio.py — Synthesise MP3 files from a mapping file using pluggable generators
#
# Reads a control file (.tts, properties format) that selects the generator
# method (tts_class), the mapping file, the output directory, and any
# method-specific parameters. Generates one MP3 per mapping entry.
#
# Usage: python gen_audio.py <control_file>.tts
#
# The mapping file keeps the `filename=spoken text` structure. Each mapping
# key is used verbatim as the target filename (keys already end in .mp3).

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# -- ensure ffmpeg is on PATH (for pydub WAV→MP3 fallback) --
_FFMPEG_BIN = (
    Path(os.environ["LOCALAPPDATA"])
    / "Microsoft" / "WinGet" / "Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.1.2-full_build" / "bin"
)
os.environ["PATH"] = str(_FFMPEG_BIN) + os.pathsep + os.environ["PATH"]

from pydub import AudioSegment

from generators.base import ConfigError, Generator
from generators.edge_tts import EdgeTTS

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

# common keys read by the main logic (everything else is method-specific)
KEY_CLASS = "tts_class"
KEY_MAPPING = "mapping_file"
KEY_OUTPUT = "output_dir"
COMMON_KEYS = {KEY_CLASS, KEY_MAPPING, KEY_OUTPUT}

CONCURRENCY = 5

# registry: tts_class value → generator class
REGISTRY: dict[str, type[Generator]] = {
    "EdgeTTS": EdgeTTS,
}

# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def parse_properties(path: Path) -> dict[str, str]:
    """Parse a Java-style .properties file into a dict of key→value."""
    config: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            if key in config:
                print(f"Error: duplicate key '{key}' in {path} (line {lineno})")
                sys.exit(1)
            config[key] = val
    return config


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


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


def build_generator(config: dict[str, str]) -> Generator:
    """Instantiate the generator class named by tts_class."""
    class_name = config.get(KEY_CLASS, "").strip()
    if not class_name:
        print(f"Error: missing required key '{KEY_CLASS}' in the control file")
        sys.exit(1)

    generator_cls = REGISTRY.get(class_name)
    if generator_cls is None:
        known = ", ".join(sorted(REGISTRY))
        print(
            f"Error: unknown tts_class '{class_name}' — "
            f"known classes: {known}"
        )
        sys.exit(1)

    return generator_cls()


# ---------------------------------------------------------------------------
# conversion fallback
# ---------------------------------------------------------------------------


def convert_wav_to_mp3(wav_path: Path, target_mp3: Path) -> Path:
    """Convert a WAV produced by a generator into the target MP3."""
    audio = AudioSegment.from_wav(wav_path)
    audio.export(target_mp3, format="mp3")
    if wav_path != target_mp3 and wav_path.exists():
        wav_path.unlink()
    return target_mp3


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------


def generate_one(
    generator: Generator,
    filename: str,
    text: str,
    out_dir: Path,
) -> None:
    """Generate a single mapping entry, converting to MP3 if needed."""
    target_mp3 = out_dir / filename
    produced = generator.generate(text, target_mp3)

    if produced.suffix.lower() != ".mp3":
        # generator emitted a non-MP3 (e.g. WAV) — convert to the MP3 target
        produced = convert_wav_to_mp3(produced, target_mp3)

    print(f"  {filename:<28} → {text}  [{produced.name}]")


def generate_all(
    generator: Generator,
    entries: list[tuple[str, str]],
    out_dir: Path,
) -> None:
    """Generate all entries, max CONCURRENCY in parallel."""
    out_dir.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [
            pool.submit(generate_one, generator, fn, txt, out_dir)
            for fn, txt in entries
        ]
        for future in as_completed(futures):
            # propagate any exception raised in a worker thread
            future.result()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python gen_audio.py <control_file>.tts")
        print("Example: python gen_audio.py yang85_edge.tts")
        sys.exit(1)

    control_path = Path(sys.argv[1])
    if not control_path.is_file():
        print(f"Error: control file not found — {control_path}")
        sys.exit(1)

    # 1. parse the control file
    config = parse_properties(control_path)

    # 2. read common keys
    mapping_file = config.get(KEY_MAPPING, "").strip()
    output_dir = config.get(KEY_OUTPUT, "").strip()
    if not mapping_file:
        print(f"Error: missing required key '{KEY_MAPPING}' in {control_path}")
        sys.exit(1)
    if not output_dir:
        print(f"Error: missing required key '{KEY_OUTPUT}' in {control_path}")
        sys.exit(1)

    mapping_path = Path(mapping_file)
    if not mapping_path.is_file():
        print(f"Error: mapping file not found — {mapping_path}")
        sys.exit(1)

    out_dir = Path(output_dir)

    # 3. instantiate the generator and validate method-specific parameters
    generator = build_generator(config)
    try:
        generator.setup(config)
    except ConfigError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    # 4. read the mapping file
    entries = parse_mapping(mapping_path)
    if not entries:
        print(f"Error: no entries found in mapping file {mapping_path}")
        sys.exit(1)

    print(
        f"Generating {len(entries)} audio files with "
        f"tts_class={config[KEY_CLASS]} …\n"
    )

    # 5. generate all entries (parallel, bounded by CONCURRENCY)
    generate_all(generator, entries, out_dir)

    print(f"\nDone.  Files written to {out_dir}")


if __name__ == "__main__":
    main()