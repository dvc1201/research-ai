# Plan: `gen_audio.py` — WAV synthesis via Edge-TTS

**Date:** 2026-08-14
**Status:** Implemented
**Platform:** Windows only
**Working directory:** `c:\work\github\research-ai\wav\`

---

## Overview

`gen_audio.py` is the **first stage** of the audio pipeline. It reads a
hand-authored mapping file (`<name>_mapping.properties`) of `filename=spoken
text` pairs and synthesises one clean Mandarin WAV per entry using the
Microsoft Edge-TTS API.

```
mapping file (manual)          gen_audio.py                output
──────────────────────   ──────────────────────   ─────────────────────────
yang85_mapping.properties  ───────────────▶         105 WAV files (edgetts/)
  85_01.wav=无极势                                    85_01.wav
  85_02.wav=太极起势                                   85_02.wav
  ...
```

The second stage (`wav_to_mp3.py`) consumes the produced WAVs — see
`plan_wav_to_mp3.md`.

## File roles (all manual inputs)

| File | Created | Purpose |
|---|---|---|
| `<name>_mapping.properties` | manually | `wav_filename=spoken Chinese text` pairs |
| WAV output dir (`edgetts/`) | by this script | synthesised speech files |

## Usage

```powershell
.\.venv\Scripts\python.exe gen_audio.py yang85_mapping.properties [--out-dir <path>]
```

- Positional: path to a `*_mapping.properties` file.
- `--out-dir` (optional): WAV output directory.
  Default: `G:\My Drive\Peter\Taichi\Confucius4\<stem>\edgetts`,
  where `<stem>` is the mapping filename without the `_mapping` suffix
  (`yang85_mapping.properties` → `yang85`).

## Input format

```properties
# Audio mapping — format: <wav_filename>=<spoken text>
85_01.wav=无极势
85_09_knee1.wav=搂膝拗步 一
85_52_jadelady4.wav=玉女穿梭 四
```

- Blank lines and `#` comments are ignored.
- Order is preserved (used for display; all entries are synthesised).
- Mapping files are **hand-authored** — the right-hand side is edited by the
  user to adjust pronunciation before synthesis.

## Synthesis configuration

| Setting | Value | Notes |
|---|---|---|
| Voice | `zh-CN-YunxiNeural` | Male Mandarin, calm instructional tone |
| Rate | `-10%` | Slightly slower for clarity |
| Concurrency | 5 parallel (`asyncio.Semaphore(5)`) | Bounded to avoid rate-limiting |

## How it works

1. Parse the mapping file into `(filename, text)` pairs.
2. For each pair (max 5 concurrent):
   - Call `edge_tts.Communicate(text, VOICE, rate=RATE)`.
   - Save the returned audio to a temporary `.tmp.mp3`.
   - Convert MP3 → WAV with `pydub` (Edge-TTS always returns MP3; the
     downstream pipeline expects WAV).
   - Delete the temporary MP3.
3. Write each WAV to `--out-dir` (or inferred default).

## Error handling

| Scenario | Handling |
|---|---|
| Mapping file not found | Print error, exit 1 |
| Edge-TTS network/API error | Exception propagates; re-run after connectivity is restored |
| Output dir missing | Created with `mkdir(parents=True, exist_ok=True)` |

## Notes

- Synthesised WAVs are the only programmatic step that requires network
  access. Everything downstream (`wav_to_mp3.py`) is local.
- Regenerating a single posture: edit the mapping file to a single line, run
  with `--out-dir`, then re-run the assembly stage.
- The legacy combined script `gen_edgetts.py` and the mapping-bootstrap
  script `gen_mapping.py` are superseded — mapping files are maintained
  manually.
