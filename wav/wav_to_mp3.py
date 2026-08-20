# wav_to_mp3.py — Convert WAV files to MP3 and assemble into a timed final MP3
#
# Reads a single .properties file (config + track timeline).
# Usage: python wav_to_mp3.py yang42.properties [--force] [--cache-dir <path>]

import argparse
import os
import re
import shutil
import sys
from collections import namedtuple
from pathlib import Path

# -- ensure ffmpeg is on PATH (for pydub) --
_FFMPEG_BIN = (
    Path(os.environ["LOCALAPPDATA"])
    / "Microsoft" / "WinGet" / "Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.1.2-full_build" / "bin"
)
os.environ["PATH"] = str(_FFMPEG_BIN) + os.pathsep + os.environ["PATH"]

from pydub import AudioSegment
from tqdm import tqdm

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

CONFIG_KEYS = {"input_dir", "output_dir", "output_filename", "bitrate", "formlength", "form", "intro", "cache_dir"}
BITRATE_RE = re.compile(r"^\d+k$")

Track = namedtuple("Track", ["filename", "weight", "start_sec"])

# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def parse_properties(properties_path: Path) -> "tuple[dict, list[Track]]":
    """Parse <name>.properties into (config dict, sorted list of Track).
    
    If 'form' attribute is present, load track entries from the referenced
    form file instead of the main properties file.
    """
    if not properties_path.is_file():
        print(f"Error: file not found — {properties_path}")
        sys.exit(1)

    config: dict[str, str] = {}
    tracks: list[Track] = []
    seen_filenames: set[str] = set()

    # First pass: extract config keys only
    with open(properties_path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()

            # skip blank lines and #-comments
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                print(f"Error: malformed line {lineno} (missing '=') — {line!r}")
                sys.exit(1)

            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()

            # strip optional surrounding double quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]

            if key in CONFIG_KEYS:
                config[key] = val

    # Second pass: load tracks (either from main file or form file)
    if "form" in config:
        # Modular mode: load tracks from form file
        form_path = properties_path.parent / config["form"]
        if not form_path.is_file():
            print(f"Error: form file not found — {form_path}")
            sys.exit(1)
        
        with open(form_path, encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                
                # skip blank lines and #-comments
                if not line or line.startswith("#"):
                    continue
                
                if "=" not in line:
                    continue  # skip malformed lines in form file
                
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                
                # skip config keys (form file should ideally only have tracks,
                # but we'll be tolerant and skip config keys if present)
                if key in CONFIG_KEYS:
                    continue
                
                # form file should only contain filename=weight pairs
                try:
                    weight = float(val)
                except ValueError:
                    continue  # skip non-numeric entries
                
                if weight < 0:
                    print(
                        f"Error: form file {form_path.name} line {lineno}: "
                        f"negative weight for '{key}' — {weight}"
                    )
                    sys.exit(1)
                
                if key in seen_filenames:
                    print(
                        f"Error: form file {form_path.name}: "
                        f"duplicate track filename '{key}' (line {lineno})"
                    )
                    sys.exit(1)
                seen_filenames.add(key)
                
                tracks.append(Track(filename=key, weight=weight, start_sec=0.0))
    else:
        # Legacy mode: load tracks from main properties file
        with open(properties_path, encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()

                # skip blank lines and #-comments
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()

                # skip config keys
                if key in CONFIG_KEYS:
                    continue

                try:
                    weight = float(val)
                except ValueError:
                    print(
                        f"Error: line {lineno}: value for '{key}' is not a "
                        f"recognised config key and not a number — {val!r}"
                    )
                    sys.exit(1)

                if weight < 0:
                    print(
                        f"Error: line {lineno}: negative weight "
                        f"for '{key}' — {weight}"
                    )
                    sys.exit(1)

                # check duplicate filename
                if key in seen_filenames:
                    print(
                        f"Error: duplicate track filename '{key}' "
                        f"(line {lineno})"
                    )
                    sys.exit(1)
                seen_filenames.add(key)

                # start_sec is computed later from weights; placeholder 0.0
                tracks.append(Track(filename=key, weight=weight, start_sec=0.0))

    # ------------------------------------------------------------------
    # determine output name
    # ------------------------------------------------------------------
    if "output_filename" in config:
        config["output_name"] = config["output_filename"]
    else:
        config["output_name"] = properties_path.stem + ".mp3"

    # ------------------------------------------------------------------
    # validate config
    # ------------------------------------------------------------------
    for required_key in ("input_dir", "output_dir", "bitrate"):
        if required_key not in config:
            print(
                f"Error: missing required key '{required_key}' "
                f"in {properties_path}"
            )
            sys.exit(1)

    if "formlength" not in config:
        print(
            f"Error: missing required key 'formlength' "
            f"in {properties_path}"
        )
        sys.exit(1)

    try:
        formlength = float(config["formlength"])
        if formlength <= 0:
            raise ValueError
    except ValueError:
        print(
            f"Error: 'formlength' must be a positive number — "
            f"got {config['formlength']!r}"
        )
        sys.exit(1)

    if not BITRATE_RE.match(config["bitrate"]):
        print(
            f"Error: invalid bitrate format '{config['bitrate']}' — "
            f"expected pattern like '128k', '192k', '320k'"
        )
        sys.exit(1)

    if not tracks:
        print("Error: no track entries found — nothing to assemble")
        sys.exit(1)

    # ------------------------------------------------------------------
    # compute start times from weights + formlength
    # ------------------------------------------------------------------
    total_weight = sum(t.weight for t in tracks)
    time_per_weight = formlength / total_weight

    current_time = 0.0
    for i, track in enumerate(tracks):
        new_start = current_time
        tracks[i] = track._replace(start_sec=new_start)
        current_time += track.weight * time_per_weight

    # sort by start_sec ascending (already in weight order, but just in case
    # the user mixed up insertion order — weights are the governing factor)
    tracks.sort(key=lambda t: t.start_sec)

    return config, tracks

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def validate_ffmpeg() -> None:
    """Abort if ffmpeg.exe or ffprobe.exe are not on PATH."""
    missing = []
    for exe in ("ffmpeg.exe", "ffprobe.exe"):
        if shutil.which(exe) is None:
            missing.append(exe)
    if missing:
        print(
            "Error: the following required executables were not found on PATH:\n"
            f"  {', '.join(missing)}\n\n"
            "Install FFmpeg on Windows:\n"
            "  winget install --id=Gyan.FFmpeg\n"
            "Then add the bin\\ directory to your user PATH."
        )
        sys.exit(1)


def validate_tracks_pre(tracks: list[Track], input_dir: Path) -> None:
    """Pre-conversion checks: file existence."""
    for track in tracks:
        wav_path = input_dir / track.filename
        if not wav_path.is_file():
            print(
                f"Error: WAV file not found — {wav_path}\n"
                f"  (referenced by track '{track.filename}')"
            )
            sys.exit(1)

# ---------------------------------------------------------------------------
# conversion
# ---------------------------------------------------------------------------


def convert_wav_to_mp3(wav_path: Path, cache_dir: Path, bitrate: str) -> Path:
    """Convert a single WAV to MP3. Return path to the output MP3."""
    audio = AudioSegment.from_wav(wav_path)
    mp3_path = cache_dir / (wav_path.stem + ".mp3")
    audio.export(mp3_path, format="mp3", bitrate=bitrate)
    return mp3_path


def ensure_cache(
    tracks: list[Track],
    input_dir: Path,
    cache_dir: Path,
    bitrate: str,
    force: bool,
) -> None:
    """Convert missing/stale WAVs to MP3 in cache_dir; reuse the rest.

    A cached MP3 is considered fresh when it exists and its mtime is >= the
    source WAV's mtime. `force=True` reconverts everything.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    to_convert: list[Track] = []
    reused = 0

    for track in tracks:
        wav_path = input_dir / track.filename
        mp3_path = cache_dir / (Path(track.filename).stem + ".mp3")

        if force:
            to_convert.append(track)
            continue

        if not mp3_path.is_file():
            to_convert.append(track)
            continue

        if wav_path.stat().st_mtime > mp3_path.stat().st_mtime:
            to_convert.append(track)
        else:
            reused += 1

    for track in tqdm(to_convert, desc="Converting to MP3", unit="file"):
        wav_path = input_dir / track.filename
        convert_wav_to_mp3(wav_path, cache_dir, bitrate)

    print(
        f"MP3 cache: {len(to_convert)} converted, {reused} reused "
        f"({cache_dir})"
    )

# ---------------------------------------------------------------------------
# overlap check (post-conversion)
# ---------------------------------------------------------------------------


def validate_overlap(
    tracks: list[Track],
    durations: dict[str, float],
) -> None:
    """Check no two tracks overlap based on known durations."""
    for idx in range(1, len(tracks)):
        prev = tracks[idx - 1]
        cur = tracks[idx]
        prev_end = prev.start_sec + durations[prev.filename]
        if cur.start_sec < prev_end:
            overlap = prev_end - cur.start_sec
            print(
                f"Error: track overlap detected:\n"
                f"  '{prev.filename}' ends at {prev_end:.3f}s\n"
                f"  '{cur.filename}'  starts at {cur.start_sec:.3f}s\n"
                f"  Overlap: {overlap:.3f}s"
            )
            sys.exit(1)

# ---------------------------------------------------------------------------
# timeline assembly
# ---------------------------------------------------------------------------


def build_timeline(
    tracks: list[Track],
    cache_dir: Path,
) -> AudioSegment:
    """Build the final assembled AudioSegment with silence between clips."""
    assembled = AudioSegment.empty()
    durations: dict[str, float] = {}

    # load all MP3s first to get durations
    audio_map: dict[str, AudioSegment] = {}
    for track in tracks:
        mp3_path = cache_dir / (Path(track.filename).stem + ".mp3")
        seg = AudioSegment.from_mp3(mp3_path)
        audio_map[track.filename] = seg
        durations[track.filename] = len(seg) / 1000.0

    # assemble with silence
    for idx, track in enumerate(tracks):
        if idx == 0:
            silence_sec = track.start_sec
        else:
            prev = tracks[idx - 1]
            silence_sec = (
                track.start_sec
                - (prev.start_sec + durations[prev.filename])
            )

        if silence_sec > 0:
            assembled += AudioSegment.silent(
                duration=int(silence_sec * 1000)
            )
        elif silence_sec < 0:
            # double-check — should have been caught by validate_overlap
            prev_track = tracks[idx - 1]
            print(
                f"Error: unexpected overlap at track {idx + 1} "
                f"('{track.filename}')"
            )
            sys.exit(1)

        assembled += audio_map[track.filename]

    return assembled, durations


def export_final(
    audio: AudioSegment,
    output_path: Path,
    bitrate: str,
) -> None:
    """Export the assembled AudioSegment to an MP3 file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate=bitrate)

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


def print_summary(
    tracks: list[Track],
    durations: dict[str, float],
    output_path: Path,
    formlength: float,
    offset: float = 0.0,
) -> None:
    """Print a formatted summary of the assembled timeline.

    *offset* is the intro duration to add to every track's start time
    so the displayed times match the actual MP3 timeline.
    """
    print("\nTimeline assembled:")
    total_weight = sum(t.weight for t in tracks)
    for track in tracks:
        start = track.start_sec + offset
        duration = durations[track.filename]
        if track == tracks[0]:
            silence = track.start_sec
        else:
            prev = tracks[tracks.index(track) - 1]
            silence = (
                track.start_sec
                - (prev.start_sec + durations[prev.filename])
            )
        start_str = f"{int(start)//60}:{int(start)%60:02d}"
        print(
            f"  [{start_str}]  "
            f"{track.filename:<24}"
            f"(w:{track.weight:4.0f}  "
            f"clip:{duration:4.1f}s  "
            f"gap:{silence:5.1f}s)"
        )

    last = tracks[-1]
    total = last.start_sec + durations[last.filename] + offset
    total_str = f"{int(total)//60}:{int(total)%60:02d}"
    print(f"\nTotal duration: {total:.1f}s  ({total_str})")
    print(f"Total weight: {total_weight:.0f}")
    print(f"Form length (target): {formlength:.0f}s")
    print(f"Output: {output_path}")
# ---------------------------------------------------------------------------
# timeline text file
# ---------------------------------------------------------------------------


def write_timeline_txt(
    tracks: list[Track],
    durations: dict[str, float],
    output_path: Path,
    offset: float = 0.0,
) -> None:
    """Write a simple timeline index file next to the MP3.

    *offset* is the intro duration so the file lists the actual time
    in the final MP3 rather than the form-relative start time.
    """
    txt_path = output_path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# Timeline for {output_path.name}\n")
        f.write(f"# Format: filename  start_time\n\n")
        for track in tracks:
            actual_start = track.start_sec + offset
            ts = f"{int(actual_start)//60}:{int(actual_start)%60:02d}"
            f.write(f"{track.filename}  {ts}\n")
    print(f"Timeline: {txt_path}")
# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble WAV clips into a timed MP3"
    )
    parser.add_argument(
        "properties_file",
        help="Path to the control .properties file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the MP3 cache and reconvert all WAV files",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Override the MP3 cache directory (default: <input_dir>/mp3cache)",
    )
    args = parser.parse_args()

    properties_path = Path(args.properties_file)

    # 1. parse the control .properties file
    config, tracks = parse_properties(properties_path)

    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    bitrate = config["bitrate"]
    formlength = float(config["formlength"])
    output_name = config["output_name"]
    output_path = output_dir / output_name

    # resolve cache dir: CLI flag > config key > default
    if args.cache_dir:
        cache_dir = Path(args.cache_dir)
    elif "cache_dir" in config:
        cache_dir = Path(config["cache_dir"])
    else:
        cache_dir = input_dir / "mp3cache"

    # 2. validate environment
    validate_ffmpeg()

    # 3. pre-conversion track validation (file existence)
    validate_tracks_pre(tracks, input_dir)

    # 4. ensure every WAV has a fresh MP3 in the cache (converts only what's
    #    missing or stale — a one-time cost, reused across merges)
    ensure_cache(tracks, input_dir, cache_dir, bitrate, args.force)

    # 5. build timeline & validate overlap
    assembled, durations = build_timeline(tracks, cache_dir)
    validate_overlap(tracks, durations)

    # 6. prepend intro MP3 if specified
    intro_duration = 0.0
    if "intro" in config:
        intro_path = properties_path.parent / config["intro"]
        if not intro_path.is_file():
            print(f"Error: intro file not found — {intro_path}")
            sys.exit(1)

        print(f"\nPrepending intro: {intro_path.name}")
        intro_audio = AudioSegment.from_mp3(intro_path)
        intro_duration = len(intro_audio) / 1000.0
        print(f"  Intro duration: {intro_duration:.1f}s")

        # prepend intro to assembled timeline
        assembled = intro_audio + assembled

    # 7. export final MP3
    export_final(assembled, output_path, bitrate)

    # 8. print summary
    print_summary(tracks, durations, output_path, formlength, offset=intro_duration)

    # 9. write timeline txt alongside the MP3
    write_timeline_txt(tracks, durations, output_path, offset=intro_duration)


if __name__ == "__main__":
    main()
