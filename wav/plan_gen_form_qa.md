# Human input

- This is a new plan, after the changes described in `gen_audio_cr01.md`
- Read `plan_gen_audio.md` - mp3 files are provided by this program. e.g. `yang85_edge.tts`
- Read `plan_wav_to_mp3.md` - this is the current concept. Initial wav is assumed, mp3 cache is built. **I want to keep this as it is now**.
- Read `wav_to_mp3.py` - this is a working implementation with no errors. Code examples from this code can be reused.
- This file is a new plan to create a simplified `gen_form.py` program. Same functionality as in `wav_to_mp3.py` **BUT**:
  - Input files are in mp3 format. example: `yang85form.properties`
  - No wav to mp3 conversion is necessary
  - No mp3 cache is necessary
- Based on the `plan_wav_to_mp3.md` create a plan in the `# Plan:` section 
- Plan: `gen_form.py` — MP3 assembly & timeline merge - final name
- Add your questions to the Q&A section in this file

# Plan: `gen_form.py` — MP3 assembly & timeline merge (simplified)

**Date:** 2026-08-27 | **Status:** Planned | **Platform:** Windows only

---

## Overview

`gen_form.py` is the simplified successor to `wav_to_mp3.py` for the
MP3-native pipeline. It loads MP3 posture files, assembles them into one
timed MP3 with silence gaps, and optionally prepends an intro MP3. No
WAV-to-MP3 conversion, no cache.

```
control file (manual)            gen_form.py                    output
──────────────────────   ──────────────────────   ──────────────────────────
yang85pigua.properties ──────────────────────▶    yang85_pigua.mp3
  form=yang85form.properties                         (+ timeline .txt)
  intro=pigua.mp3 / formlength=480
```

`wav_to_mp3.py` remains for the legacy workflow (removed manually later).

## File roles (all manual inputs)

| File | Purpose |
|---|---|
| `<name>form.properties` | `mp3_filename=weight` pairs (form definition) |
| `<name>_*.properties` | control file (paths, `form=`, `intro=`, `formlength=`) |
| intro MP3 | optional audio prepended before the form |

## Usage

```powershell
.\.venv\Scripts\python.exe gen_form.py yang85pigua.properties
```

Single positional argument — no flags.

## Control file format (modular only, no legacy unified mode)

```properties
input_dir=G:\My Drive\Peter\Taichi\yang85\edgetts
output_dir=G:\My Drive\Peter\Taichi\yang85\mp3
form=yang85form.properties           # relative to CWD
intro=pigua.mp3                      # optional
output_filename=yang85_pigua.mp3     # mandatory
formlength=480                       # excludes intro
```

### Config keys

| Key | Required | Description |
|---|---|---|
| `input_dir` | Yes | Source **MP3** directory |
| `output_dir` | Yes | Final merged MP3 directory |
| `form` | Yes | Form definition (`.mp3` keys), relative to CWD |
| `output_filename` | Yes | Output filename (no fallback) |
| `formlength` | Yes | Target form seconds (intro excluded) |
| `intro` | No | Intro MP3, relative to CWD |

All relative paths resolve against the current working directory.

## Form definition file format

```properties
85_01.mp3=10
85_02.mp3=5
85_03_lrtail.mp3=18
```

All form files use `.mp3` keys (migrated).

## Timing model

Identical to `wav_to_mp3.py`:

```
total_weight = sum w[i]
time_per_weight = formlength / total_weight
start[i] = sum w[j] * time_per_weight   (j < i)
silence_before[i] = start[i] - (start[i-1] + duration[i-1])
```

- `formlength` applies to the **form only**; intro is outside.

## Merge flow

```
parse control -> parse form -> compute starts -> validate MP3s exist
  -> build_timeline from input_dir -> validate_overlap
  -> prepend intro (if present) -> export final MP3 (hardcoded 192k)
```

No WAV conversion. No cache directory. Final export uses pydub/ffmpeg at
hardcoded `BITRATE = "192k"`.

## Output

- Final MP3: `output_dir/<output_filename>`.
- Timeline `.txt`: `mm:ss` format, intro offset included.
- Console summary: identical to `wav_to_mp3.py`.

## Implementation notes

- Reuse from `wav_to_mp3.py`: `parse_properties`, `build_timeline`,
  `validate_overlap`, `export_final`, `print_summary`, `write_timeline_txt`.
- Remove: WAV-conversion functions, cache logic, `--force`/`--cache-dir`,
  legacy unified mode, `bitrate` config key.
- `build_timeline`: source is `input_dir` directly (no temp/cache dir).
- `output_filename` is mandatory (no fallback to `<control_stem>.mp3`).

## Error handling

| Scenario | Handling |
|---|---|
| Bad CLI / missing control file | Print error, exit 1 |
| Missing required config key | Report key, exit 1 |
| `formlength` not positive | Report value, exit 1 |
| Form / intro file not found | Report path, exit 1 |
| MP3 missing from `input_dir` | Report path + track, exit 1 |
| Track overlap | Report tracks + amount, exit 1 |
| ffmpeg/ffprobe not on PATH | Install hint, exit 1 |

## Testing approach

1. `gen_form.py yang85pigua.properties` -> verify MP3 + timeline `.txt`.
2. Verify first track start time = intro duration.
3. Verify `.txt` in `mm:ss` format.
4. Compare timeline against `wav_to_mp3.py` output — timings should match.


# Q&A

1. **Form file extension.** The form definition files have been migrated to
   `.mp3` keys (e.g. `85_01.mp3=10` in `yang85form.properties`). Will
   `gen_form.py` assume the form file keys are already `.mp3`, or should it
   tolerate/rewrite `.wav` keys for compatibility with the older form files?

>**Answer** all form files will be migrated to .mp3 references

---

2. **Control file reuse.** `gen_form.py` is described as "same functionality
   as `wav_to_mp3.py`". Should it reuse the existing control files verbatim
   (e.g. `yang85pigua.properties` with `input_dir`, `output_dir`, `bitrate`,
   `form`, `intro`, `formlength`), or does the simplified version drop any of
   these keys (e.g. `bitrate`, `input_dir`)?

>**Answer** Read `yang85pigua.properties` this is a reference control file. All parameters listed here remain. TTS specific parameters e.g. bitrate will be removed. Control files will be adjusted manually.

---

3. **`bitrate` key.** `wav_to_mp3.py` re-encodes MP3s at `bitrate` (e.g.
   `192k`). Since `gen_form.py` takes MP3 input and does no WAV→MP3
   conversion, is `bitrate` still needed for the final MP3 export, or should
   it be removed from the control file?

>**Answer** bitrate for the final output can remain hard coded 192k. It's not necessary in the control file 

---

4. **Final MP3 export.** Does `gen_form.py` export the assembled timeline to
   MP3 using pydub/ffmpeg (re-encoding at `bitrate`), or does it concatenate
   MP3s losslessly (bitstream concatenation, no re-encode)? The former keeps
   `bitrate`; the latter drops it.

>**Answer** `gen_audio.py` provides (or will provide) the input files with bitrate=192k.

---

5. **`input_dir` semantics.** In `wav_to_mp3.py`, `input_dir` holds WAVs and
   the cache lives under it. In `gen_form.py`, `input_dir` should hold the
   source MP3s (e.g. `...\yang85\edgetts`). Should the key remain `input_dir`,
   or be renamed (e.g. `mp3_dir` / `input_mp3_dir`)?

>**Answer** input_dir points to a dir where mp3 files ara available

---

6. **`--force` / `--cache-dir` CLI flags.** Since there is no cache,
   should `gen_form.py` drop both flags (single positional control-file
   argument), or keep `--force`/`--cache-dir` for parity even though unused?

>**Answer** drop unnecessary arguments

---

7. **Legacy unified mode.** `wav_to_mp3.py` supports a legacy unified mode
   (no `form=`, tracks inline in the control file). Should `gen_form.py` also
   support this mode, or only the modular `form=` mode?

>**Answer** only the modular `form=` mode

---

8. **Intro and timeline offset.** Should `gen_form.py` keep the intro
   prepending and the `mm:ss` timeline offset behavior exactly as in
   `wav_to_mp3.py` (intro duration added to all start times in the `.txt`)?

>**Answer** Current timeline handling is perfect in `wav_to_mp3.py`. (intro duration added to all start times in the `.txt`)

---

9. **Naming / coexistence.** Should `gen_form.py` coexist with
   `wav_to_mp3.py` (the latter kept for legacy WAV-based workflows), or is it
   intended to replace it eventually? The plan says "keep `wav_to_mp3.py` as
   it is now", suggesting coexistence.

>**Answer** For a while `wav_to_mp3.py` remains. I'll remove it later manually.

---

10. **Output filename default.** Keep the same default (`<control_stem>.mp3`)
   and `output_filename` override as `wav_to_mp3.py`?

>**Answer** `output_filename` is mandatory in control file. No fallback is necessary.

---

11. **`input_dir` contents.** The reference control file still points to
   `G:\...\Confucius4\yang85\edgetts`, but `gen_audio.py` (via
   `yang85_edge.tts`) writes MP3s to `G:\...\Peter\Taichi\yang85\edgetts`.
   Should `gen_form.py` simply trust whatever `input_dir` says, with the
   control files being manually updated to the new MP3 directory?

>**Answer** Read `yang85pigua.properties`

---

12. **Relative path base.** In `wav_to_mp3.py`, `form` and `intro` are
   resolved relative to the control file's directory, while `gen_audio.py`
   resolves paths relative to the CWD. Which base should `gen_form.py` use
   for `form`, `intro`, and `input_dir`?

>**Answer** relative to the CWD

---

13. **Assembly method (quality).** `wav_to_mp3.py` builds the timeline with
   pydub (`AudioSegment`), which decodes each MP3 and re-encodes the final
   output at `bitrate`. This is a lossy re-encode even when the input MP3s
   are already 192k. Should `gen_form.py` keep this pydub-based assembly
   (simple, consistent with `wav_to_mp3.py`, but lossy), or use lossless
   bitstream concatenation via ffmpeg's concat demuxer (no re-encode, no
   generation loss)?

>**Answer** Default 192k bitrate will be provided by gen_audio. No more corrections are necessary.

---

# Future ideas (not part of the current implementation)

Recorded for later consideration — not required by the accepted plan.

1. **ID3 / metadata tags.** Embed title, artist, or album tags in the final
   MP3 so players show a friendly name instead of the filename.
2. **Dry-run mode.** A `--dry-run` flag to print the computed timeline
   without exporting — useful for validating weights before a full run.
   (Currently the CLI intentionally has no flags.)
3. **`docs/mp3/` sync note.** Clarify which directory is canonical for the
   merged MP3s (`output_dir` vs. the practice copies in `docs/mp3/`).
4. **Non-zero first-track start.** The timing model always starts the form at
   0; document/decide whether leading silence before the first cue should
   ever be supported.
