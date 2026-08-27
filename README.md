# research-ai

Research on AI topics — currently focused on **audio timeline assembly** for
taiji practice guides (Yang-style 85 form).

---

## `wav/` — Audio Timeline Merger

A Python toolbox for generating spoken posture-name MP3s and merging them
into a single timed practice audio.

### Pipeline

Two scripts, three hand-authored input files:

| Stage | Tool | Input (manual) | Output |
|---|---|---|---|
| 1. Synthesis | `gen_audio.py` | control `.tts` (method, paths, params) + `*_mapping.properties` (filename=spoken text) | MP3 speech files |
| 2. Assembly | `gen_form.py` | control `*.properties` (paths, `form=`, `intro=`, `formlength=`) + `*form*.properties` (filename=weight) | merged MP3 + timeline `.txt` |

### Quickstart

```powershell
# Prerequisites (one-time)
winget install Python.Python.3.12
winget install Gyan.FFmpeg
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Generate the posture MP3s
.\.venv\Scripts\python.exe gen_audio.py yang85_edge.tts

# Merge them into a practice MP3 (full form, pigua speed, with intro)
.\.venv\Scripts\python.exe gen_form.py yang85pigua.properties
```

### Scripts

| Script | Purpose |
|---|---|
| `gen_audio.py` | Reads a `.tts` control file, dispatches to a pluggable TTS generator (e.g. Edge-TTS), and produces one MP3 per mapping entry |
| `gen_form.py` | Reads a control `.properties`, loads the referenced MP3 files, assembles them into a timed MP3 with silence gaps, exports the merged MP3 + timeline `.txt` |

### Generation control file (`.tts`, properties format)

```properties
# yang85_edge.tts
tts_class=EdgeTTS
mapping_file=yang85_mapping.properties
output_dir=G:\path\to\edgetts
tts.voice=zh-CN-YunxiNeural
tts.rate=-10%
```

| Key | Meaning |
|---|---|
| `tts_class` | Generator class (e.g. `EdgeTTS`) |
| `mapping_file` | Path to the mapping file (relative to CWD) |
| `output_dir` | Output directory for the MP3 speech files |

All other keys are method-specific and interpreted by the generator. New
generators are added by implementing a subclass in the `generators/` package
and registering it in the builder.

### Assembly control file (`.properties`)

```properties
# yang85pigua.properties
input_dir=G:\path\to\edgetts
output_dir=G:\path\to\mp3
form=yang85form.properties           # form definition, relative to CWD
intro=pigua.mp3                      # optional intro, relative to CWD
output_filename=yang85_pigua.mp3     # mandatory output name
formlength=480                       # target form seconds (intro excluded)
```

| Key | Required | Meaning |
|---|---|---|
| `input_dir` | Yes | Directory containing the source MP3 files |
| `output_dir` | Yes | Directory for the merged output MP3 |
| `form` | Yes | Form definition file (`.mp3` keys, `filename=weight`) |
| `output_filename` | Yes | Output MP3 filename |
| `formlength` | Yes | Target form duration in seconds (intro excluded) |
| `intro` | No | Intro MP3 prepended before the form |

- Paths are resolved relative to the current working directory.
- No bitrate key — the final export is always 192 kbps.
- `mm:ss` timeline `.txt` is written alongside the MP3, with start times
  offset by the intro duration.

### Bitrate design

Source MP3s keep whatever bitrate the generator produces (Edge-TTS: ~48 kbps
mono speech). The assembly stage (`gen_form.py`) normalizes the merged output
to 192 kbps at export time — no bitrate handling is needed in the synthesis
stage.

### Yang 85-form files

Form definitions and assembly control files live in [`forms/`](forms/README.md).
See that directory for the full file listing and per-form documentation.

### Environment

- **Python:** 3.12 — Python 3.13 removed the `audioop` module that `pydub`
  depends on; a fix is in progress ([jiaaro/pydub#881](https://github.com/jiaaro/pydub/pull/881)),
  so stay on 3.12 until a new `pydub` release lands.
- **FFmpeg:** Gyan build 8.1.2
- **Edge-TTS** voice: `zh-CN-YunxiNeural` (male, calm, instructional tone)
- **`requirements.txt`:** `pydub`, `tqdm`, `edge-tts`, `aiohttp` (and transitive deps)
