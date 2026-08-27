# gen_form.py — Assemble MP3 posture files into a timed practice MP3
#
# Reads a control .properties file, loads the referenced MP3 files, assembles
# them into one timed MP3 with silence gaps, and optionally prepends an intro.
#
# Usage: python gen_form.py <control>.properties
#
# No format conversion and no caching are performed — the source files are
# already MP3. The only encode step is the single final export (192 kbps).

import os
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

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

CONFIG_KEYS = {
    "input_dir", "output_dir", "form", "intro", "output_filename", "formlength",
}

BITRATE = "192k"  # hardcoded — not a control-file key

Track = namedtuple("Track", ["filename", "weight", "start_sec"])

# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def parse_control(control_path: Path) -> dict[str, str]:
    """Parse the control file into a config dict, validating required keys."""
    config: dict[str, str] = {}
    with open(control_path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                print(f"Error: malformed line {lineno} (missing '=') — {line!r}")
                sys.exit(1)
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            config[key] = val

    for required in ("input_dir", "output_dir", "form", "output_filename", "formlength"):
        if required not in config:
            print(f"Error: missing required key '{required}' in {control_path}")
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
    config["formlength"] = formlength

    return config


def parse_form(form_path: Path) -> list[Track]:
    """Parse the form definition into an ordered list of (filename, weight)."""
    tracks: list[Track] = []
    seen: set[str] = set()

    with open(form_path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()

            try:
                weight = float(val)
            except ValueError:
                print(
                    f"Error: {form_path.name} line {lineno}: "
                    f"non-numeric weight for '{key}' — {val!r}"
                )
                sys.exit(1)

            if weight < 0:
                print(
                    f"Error: {form_path.name} line {lineno}: "
                    f"negative weight for '{key}' — {weight}"
                )
                sys.exit(1)

            if key in seen:
                print(
                    f"Error: {form_path.name} line {lineno}: "
                    f"duplicate track filename '{key}'"
                )
                sys.exit(1)
            seen.add(key)

            tracks.append(Track(filename=key, weight=weight, start_sec=0.0))

    if not tracks:
        print(f"Error: no track entries found in {form_path}")
        sys.exit(1)

    return tracks


def compute_starts(tracks: list[Track], formlength: float) -> list[Track]:
    """Replace start_sec on each track based on weights + formlength."""
    total_weight = sum(t.weight for t in tracks)
    if total_weight <= 0:
        print("Error: total weight must be greater than zero")
        sys.exit(1)

    time_per_weight = formlength / total_weight
    current = 0.0
    result: list[Track] = []
    for track in tracks:
        result.append(track._replace(start_sec=current))
        current += track.weight * time_per_weight
    return result

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def validate_tracks(tracks: list[Track], input_dir: Path) -> None:
    """Abort if any referenced MP3 does not exist in input_dir."""
    for track in tracks:
        mp3_path = input_dir / track.filename
        if not mp3_path.is_file():
            print(
                f"Error: MP3 file not found — {mp3_path}\n"
                f"  (referenced by track '{track.filename}')"
            )
            sys.exit(1)


def validate_overlap(
    tracks: list[Track],
    durations: dict[str, float],
) -> None:
    """Abort if any two tracks overlap based on their durations."""
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
    input_dir: Path,
) -> tuple[AudioSegment, dict[str, float]]:
    """Load MP3s from input_dir and assemble them with silence gaps."""
    assembled = AudioSegment.empty()
    durations: dict[str, float] = {}
    audio_map: dict[str, AudioSegment] = {}

    for track in tracks:
        mp3_path = input_dir / track.filename
        seg = AudioSegment.from_mp3(mp3_path)
        audio_map[track.filename] = seg
        durations[track.filename] = len(seg) / 1000.0

    for idx, track in enumerate(tracks):
        if idx == 0:
            silence_sec = track.start_sec
        else:
            prev = tracks[idx - 1]
            silence_sec = track.start_sec - (prev.start_sec + durations[prev.filename])

        if silence_sec > 0:
            assembled += AudioSegment.silent(duration=int(silence_sec * 1000))
        elif silence_sec < 0:
            print(
                f"Error: unexpected overlap at track {idx + 1} "
                f"('{track.filename}')"
            )
            sys.exit(1)

        assembled += audio_map[track.filename]

    return assembled, durations


def export_final(audio: AudioSegment, output_path: Path) -> None:
    """Export the assembled audio as MP3 at a fixed bitrate."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate=BITRATE)

# ---------------------------------------------------------------------------
# summary + timeline
# ---------------------------------------------------------------------------


def format_mmss(seconds: float) -> str:
    """Return 'm:ss' with seconds truncated to whole values."""
    whole = int(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def print_summary(
    tracks: list[Track],
    durations: dict[str, float],
    output_path: Path,
    formlength: float,
    offset: float,
) -> None:
    """Print the assembled timeline summary."""
    print("\nTimeline assembled:")
    total_weight = sum(t.weight for t in tracks)
    for track in tracks:
        start = track.start_sec + offset
        duration = durations[track.filename]
        if track == tracks[0]:
            silence = track.start_sec
        else:
            prev = tracks[tracks.index(track) - 1]
            silence = track.start_sec - (prev.start_sec + durations[prev.filename])
        print(
            f"  [{format_mmss(start)}]  "
            f"{track.filename:<24}"
            f"(w:{track.weight:4.0f}  "
            f"clip:{duration:4.1f}s  "
            f"gap:{silence:5.1f}s)"
        )

    last = tracks[-1]
    total = last.start_sec + durations[last.filename] + offset
    print(f"\nTotal duration: {total:.1f}s  ({format_mmss(total)})")
    print(f"Total weight: {total_weight:.0f}")
    print(f"Form length (target): {formlength:.0f}s")
    print(f"Output: {output_path}")


def write_timeline_txt(
    tracks: list[Track],
    output_path: Path,
    offset: float,
) -> None:
    """Write a timeline index file next to the MP3."""
    txt_path = output_path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# Timeline for {output_path.name}\n")
        f.write(f"# Format: filename  start_time\n\n")
        for track in tracks:
            actual_start = track.start_sec + offset
            f.write(f"{track.filename}  {format_mmss(actual_start)}\n")
    print(f"Timeline: {txt_path}")

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python gen_form.py <control>.properties")
        print("Example: python gen_form.py yang85pigua.properties")
        sys.exit(1)

    control_path = Path(sys.argv[1])
    if not control_path.is_file():
        print(f"Error: control file not found — {control_path}")
        sys.exit(1)

    # 1. parse control file
    config = parse_control(control_path)

    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    output_name = config["output_filename"]
    formlength = float(config["formlength"])
    output_path = output_dir / output_name

    # 2. parse form definition (paths relative to CWD)
    form_path = Path(config["form"])
    if not form_path.is_file():
        print(f"Error: form file not found — {form_path}")
        sys.exit(1)
    tracks = parse_form(form_path)

    # 3. compute start times
    tracks = compute_starts(tracks, formlength)

    # 4. validate MP3 files exist
    validate_tracks(tracks, input_dir)

    # 5. build timeline + validate overlap
    assembled, durations = build_timeline(tracks, input_dir)
    validate_overlap(tracks, durations)

    # 6. prepend intro if present
    offset = 0.0
    if "intro" in config:
        intro_path = Path(config["intro"])
        if not intro_path.is_file():
            print(f"Error: intro file not found — {intro_path}")
            sys.exit(1)
        print(f"\nPrepending intro: {intro_path.name}")
        intro_audio = AudioSegment.from_mp3(intro_path)
        offset = len(intro_audio) / 1000.0
        print(f"  Intro duration: {offset:.1f}s")
        assembled = intro_audio + assembled

    # 7. export
    export_final(assembled, output_path)

    # 8. summary
    print_summary(tracks, durations, output_path, formlength, offset)

    # 9. timeline txt
    write_timeline_txt(tracks, output_path, offset)


if __name__ == "__main__":
    main()
