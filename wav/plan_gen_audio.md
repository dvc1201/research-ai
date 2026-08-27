# Plan: `gen_audio.py` — Audio synthesis (pluggable generators)

**Date:** 2026-08-27
**Status:** In progress
**Platform:** Windows only
**Working directory:** `c:\work\github\research-ai\wav\`

---

## Overview

`gen_audio.py` is the **first stage** of the audio pipeline. It reads a
hand-authored mapping file of `filename=spoken text` pairs and synthesises
one MP3 per entry. The synthesis method is pluggable: a control file selects
a generator class, and new TTS tools are added by implementing a new
generator subclass.

```
control file (.tts)          gen_audio.py                    output
─────────────────────   ──────────────────────   ─────────────────────────
yang85_edge.tts  ────────────────────────▶         105 MP3 files (edgetts/)
  tts_class=EdgeTTS                                    85_01.mp3
  mapping_file=...                                     85_02.mp3
  output_dir=...                                       ...
```

The second stage (`wav_to_mp3.py`) consumes the produced MP3s — see
`plan_wav_to_mp3.md`.

## File roles (all manual inputs)

| File | Created | Purpose |
|---|---|---|
| `<name>_mapping.properties` | manually | `mp3_filename=spoken Chinese text` pairs |
| `<name>_<method>.tts` | manually | control file: method, paths, method params |
| MP3 output dir (`edgetts/`) | by this script | synthesised speech files |

## Usage

```powershell
.\.venv\Scripts\python.exe gen_audio.py yang85_edge.tts
```

- Single argument: path to the control file.
- No `--out-dir`, no mapping-file positional argument.
- No backward compatibility with the old `mapping_file [--out-dir]` CLI.

## Control file format (`.tts`, properties format)

```properties
tts_class=EdgeTTS
mapping_file=wav\yang85_mapping.properties
output_dir=G:\My Drive\Peter\Taichi\yang85\edgetts
tts.voice=zh-CN-YunxiNeural
tts.rate=-10%
```

- `.tts` extension is the intended convention (not `.properties`).
- **Common keys** (read by `gen_audio.py` main logic):

  | Key | Meaning |
  |---|---|
  | `tts_class` | Name of the generator class (e.g. `EdgeTTS`) |
  | `mapping_file` | Path to the mapping file (absolute, or relative to CWD) |
  | `output_dir` | Directory for the generated files (absolute or CWD-relative) |

- **Method-specific keys** (e.g. `tts.voice`, `tts.rate`): no naming
  convention is imposed. They are consumed by the generator's `setup()`.
- Relative paths are resolved against the current working directory.

## Mapping file format (unchanged structure)

```properties
# Audio mapping — format: <mp3_filename>=<spoken text>
85_01.mp3=无极势
85_09_knee1.mp3=搂膝拗步 一
85_52_jadelady4.mp3=玉女穿梭 四
```

- Blank lines and `#` comments are ignored.
- Order is preserved.
- Mapping files are **hand-authored** — the right-hand side is edited by the
  user to adjust pronunciation before synthesis.
- Keys already use the `.mp3` extension and are used verbatim as the target
  filenames.

## Generator interface (ABC)

A `generators/` package:

```
generators/
├── base.py          # Generator ABC + ConfigError
└── edge_tts.py      # class EdgeTTS(Generator)
```

```python
class Generator(ABC):
    @abstractmethod
    def setup(self, config: dict) -> None:
        """Read/validate method-specific parameters from the control file.
        Raise ConfigError if a mandatory parameter is missing or invalid."""

    @abstractmethod
    def generate(self, text: str, full_output_path: Path) -> Path:
        """Synthesise *text* and write it to *full_output_path*.
        Return the path of the file actually produced (its extension may
        differ, e.g. .mp3 vs .wav)."""
```

### Instantiation / dispatch

- A builder method in `gen_audio.py` maps `tts_class` to the generator class
  via a hardcoded registry (e.g. `{"EdgeTTS": EdgeTTS}`).
- Adding a new method requires one new generator module **and** one registry
  entry; no other change to `gen_audio.py`.

### Output format contract

- `gen_audio.py` is responsible for producing **MP3** files.
- Mapping keys already end in `.mp3`; used as target filenames directly.
- A generator may natively produce MP3 or WAV:
  - MP3 path returned → keep it.
  - WAV path returned → `gen_audio.py` converts it to MP3 (pydub + ffmpeg,
    kept in `gen_audio.py` as the shared WAV→MP3 fallback).
- **No bitrate normalization** is performed in this stage. Generators write
  at their native bitrate (e.g. Edge-TTS produces ~48 kbps mono speech).
  The assembly stage (`gen_form.py`) normalizes the merged output to a fixed
  192 kbps at export time.

### Concurrency

- The current 5-way parallel synthesis is `gen_audio.py` internal logic.
- Keep it as-is; may become a control-file parameter later.

## How it works

1. Parse the control file (properties format).
2. Read common keys (`tts_class`, `mapping_file`, `output_dir`).
3. Instantiate the generator via the builder registry.
4. Call `setup(config)` — validates method-specific parameters.
5. Read the mapping file into `(filename, text)` pairs.
6. For each pair (max 5 concurrent):
   - Call `generate(text, full_output_path)`.
   - If the returned path is a WAV, convert it to MP3.
7. Write each MP3 to `output_dir`.

## Error handling

| Scenario | Handling |
|---|---|
| Control file not found | Print error, exit 1 |
| Unknown `tts_class` | Builder raises, exit 1 with a clear message |
| Missing mandatory method parameter | `setup()` raises `ConfigError`, exit 1 |
| Mapping file not found | Print error, exit 1 |
| Edge-TTS network/API error | Exception propagates; re-run after connectivity is restored |
| Output dir missing | Created with `mkdir(parents=True, exist_ok=True)` |

## Files

| File | Action |
|---|---|
| `wav\gen_audio.py` | Rewrite — single control-file argument, dispatch, mapping loop, WAV→MP3 fallback |
| `wav\generators\base.py` | New — `Generator` ABC + `ConfigError` |
| `wav\generators\edge_tts.py` | New — `EdgeTTS(Generator)` |
| `wav\yang85_edge.tts` | Update — full Edge-TTS parameters |
| `wav\plan_gen_audio.md` | This file (absorbed change requests) |

## Acceptance criteria

- `gen_audio.py yang85_edge.tts` generates one MP3 per mapping entry, written
  to `output_dir`, using the mapping key as the target filename.
- A new generator can be added by writing a new module under `generators/`
  that subclasses the ABC and implements `setup` and `generate`, plus one
  registry entry in the builder.
- Missing/invalid method-specific parameters are reported by `setup()` with a
  clear `ConfigError`.

## Notes

- Synthesised MP3s are the only programmatic step that requires network
  access. Everything downstream (`wav_to_mp3.py`) is local.
- Regenerating a single posture: edit the mapping file to a single line, run
  with the same control file, then re-run the assembly stage.
- The legacy combined script `gen_edgetts.py` and the mapping-bootstrap
  script `gen_mapping.py` are superseded — mapping files are maintained
  manually.
