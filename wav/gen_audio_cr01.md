# Human Input

I want to improve `gen_audio.py`:

- **More flexible audio generation.** Edge-TTS is currently hardcoded; I want to be able to try other TTS tools as well.
- **Keep the mapping structure as it is.**
- **Add a control file** that describes the audio generation:
  - the method (e.g. `edgeTTS`),
  - the output directory,
  - any other parameters used by the chosen audio generation method.
- `gen_audio.py` should accept control file name as argument.
- Audio generation methods should be subclasses of an Abstract Base Class (ABC).
- The Change Requests section should be authored by the AI.
- Any open questions should be added to the Q&A section.
- Once the Change Requests section is complete, `wav\plan_gen_audio.md` should be updated accordingly.

# Change Requests

Managed by AI

## Goal

Refactor `gen_audio.py` so that the audio generation method is pluggable.
Edge-TTS is currently hardcoded; after this change, new TTS tools can be
added by implementing a new generator subclass without modifying the main
program.

## Scope

**In scope**

- `gen_audio.py`
- The control-file example (`wav\yang85_edge.tts`)
- `wav\plan_gen_audio.md` (updated after the Change Requests are finalised)

**Out of scope (future change requests)**

- The `Confucius4 API` generator implementation (only the extension point is
  created now).
- `wav_to_mp3.py` refactoring to consume MP3 natively. Until then the
  assembly stage is not expected to run against MP3 output.

### Files changed

| File | Action |
|---|---|
| `wav\gen_audio.py` | Rewrite — single control-file argument, generator dispatch, mapping loop, WAV→MP3 fallback |
| `wav\generators\base.py` | New — `Generator` ABC (`setup`, `generate`) |
| `wav\generators\edge_tts.py` | New — `EdgeTTS(Generator)` implementation |
| `wav\yang85_edge.tts` | Update — full Edge-TTS parameters |
| `wav\plan_gen_audio.md` | Update — absorb finalised design |

## Design

### 1. CLI

`gen_audio.py` takes exactly **one argument** — the control file:

```powershell
.\.venv\Scripts\python.exe gen_audio.py yang85_edge.tts
```

- No `--out-dir`, no mapping-file positional argument.
- No backward compatibility with the current `mapping_file [--out-dir]` CLI.

### 2. Control file (`.tts`, properties format)

Example `wav\yang85_edge.tts`:

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
- The hardcoded defaults currently in `gen_audio.py` (`voice`, `rate`) move
  into the control file as method-specific keys.

### 3. Mapping file (unchanged structure)

- Mapping file keeps the `filename=spoken text` structure.
- Mapping keys already use the `.mp3` extension (e.g. `85_01.mp3=无极势`);
  `gen_audio.py` uses the mapping key verbatim as the target filename.
- No `.wav` → `.mp3` rewriting is needed.

### 4. Generator interface (ABC)

A `generators/` package is introduced:

```
generators/
├── base.py          # Abstract Base Class
└── edge_tts.py      # class EdgeTTS(Generator)
```

Abstract methods:

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

### 5. Instantiation / dispatch

- A builder method in `gen_audio.py` maps `tts_class` to the generator class
  via a hardcoded registry (e.g. `{"EdgeTTS": EdgeTTS}`).
- Adding a new method therefore requires one new generator module **and** one
  registry entry; no other change to `gen_audio.py` is needed.
- Dynamic import from the class name may be introduced later if methods
  become frequent.

### 6. Output format contract

- `gen_audio.py` is responsible for producing **MP3** files.
- Mapping keys already end in `.mp3`; the program uses them as the target
  filenames directly.
- A generator may natively produce MP3 or WAV:
  - If `generate()` returns an MP3 path → keep it.
  - If `generate()` returns a WAV path → `gen_audio.py` converts it to MP3
    (pydub + ffmpeg, kept in `gen_audio.py` as the shared WAV→MP3 fallback).
- `wav_to_mp3.py` will later be refactored to accept MP3 input directly
  (future CR); no WAV→MP3 conversion will then be needed there.

### 7. Concurrency

- The current 5-way parallel synthesis is `gen_audio.py` internal logic.
- Keep it as-is for now; may become a control-file parameter later.

## Implementation checklist

1. Create `generators/base.py` with the ABC and the `setup` / `generate`
   abstract methods.
2. Create `generators/edge_tts.py` with `class EdgeTTS(Generator)`, moving
   the current Edge-TTS logic (voice, rate, MP3 handling) into `setup` and
   `generate`.
3. Rewrite `gen_audio.py`:
   - single `control_file` argument;
   - parse the control file (properties format);
   - read common keys (`tts_class`, `mapping_file`, `output_dir`);
   - instantiate the generator via the builder;
   - call `setup(config)`;
   - read the mapping file (keys already end in `.mp3`);
   - call `generate(text, full_output_path)` per entry;
   - convert WAV → MP3 when `generate()` returns a WAV path;
   - keep the 5-way concurrency.
4. Update `wav\yang85_edge.tts` to contain the full set of Edge-TTS
   parameters (voice, rate, etc.) in addition to the common keys.
5. After sign-off, absorb this section into `wav\plan_gen_audio.md`.

## Acceptance criteria

- `gen_audio.py yang85_edge.tts` generates one MP3 per mapping entry, written
  to `output_dir`, using the mapping key as the target filename.
- A new generator can be added by writing a new module under `generators/`
  that subclasses the ABC and implements `setup` and `generate`, plus one
  registry entry in the builder.
- Missing/invalid method-specific parameters are reported by `setup()` with
  a clear `ConfigError`.


# Q&A

1. **"Three arguments" vs. two listed.** The input says `gen_audio.py` should
   accept *three* arguments, but only two are named (mapping file, control
   file). What is the third argument — an optional `--out-dir` override, a
   `--force`/`--verbose` flag, or something else?

>**Answer** One argument only, the control file. Everything else defined in the control file 

---

2. **Control file format.** Should the new control file keep the Java-style
   `.properties` format used by the rest of the project, or would JSON/YAML
   be preferred?

>**Answer** properties format. Example: wav\yang85_edge.tts

---

3. **Output directory precedence.** The control file will specify the output
   directory. Should the existing `--out-dir` CLI flag be removed, kept as an
   override, or is it the third CLI argument from question 1?

>**Answer** Control file only

---

4. **Which TTS methods are in scope?** For example: offline `pyttsx3`, `gTTS`,
   `Piper`, `Coqui`, or the Azure Speech SDK? The answer shapes the ABC
   interface and which parameters are common vs. method-specific.

>**Answer** EdgeTTS, Confucius4 API

---

5. **Method-specific parameters.** How should they be represented in the
   control file — prefixed by method (e.g. `edge.voice=`, `edge.rate=`), or a
   free-form block passed through to the method?

>**Answer** Example: wav\yang85_edge.tts. The control file itself is "method specific"

---

6. **Default values.** Should the current Edge-TTS defaults
   (voice `zh-CN-YunxiNeural`, rate `-10%`, concurrency `5`) remain the
   defaults when the control file omits them?

>**Answer** should be moved to the control file

---

7. **Control file naming convention.** Should the control file follow a
   pattern such as `<name>_gen.properties`, placed alongside the mapping file?

>**Answer** Example: wav\yang85_edge.tts

---

8. **Control file extension.** The example uses a `.tts` extension
   (`yang85_edge.tts`) rather than `.properties`. Is `.tts` the intended
   convention for all generation control files (e.g. `<name>_<method>.tts`)?

>**Answer** intended convention

---

9. **Path resolution.** `mapping_file=wav\yang85_mapping.properties` is a
   relative path. Should relative paths in the control file be resolved
   against the control file's own directory, or against the current working
   directory? Should `output_dir` also support relative paths?

>**Answer** Both absolute and relative paths are accepted. Relative is against the current working directory

---

10. **`bitrate` in the control file.** The example includes `bitrate=192k`,
   but the current `gen_audio.py` exports **WAV** files, where bitrate does
   not apply. Is the output format changing to MP3, or is `bitrate` a
   copy-paste leftover from the assembly control files?

>**Answer** It's and example only. The specific parameters will be read and interpreted by the selected audio conversion class.

---

11. **Method-specific parameters in the example.** The example control file
   (`yang85_edge.tts`) lists only `ttsmethod`, `mapping_file`, `output_dir`,
   and `bitrate` — but no `voice`, `rate`, or `concurrency`. Since Q&A #6
   says these defaults should move to the control file, should the example
   be extended with them, and are they required or optional (falling back to
   code defaults when omitted)?

>**Answer** It's an example only. All necessary parameters should be added finally there. Extend the example with the necessary EdgeTTS parameters

---

12. **Concurrency.** The current `gen_audio.py` hardcodes 5 parallel
   synthesis tasks. Should `concurrency` be a control-file parameter, and is
   it common to all methods or specific to Edge-TTS?

>**Answer** This concurrency is rather an gen_audio.py internal logic. Can be added later if it's necessary

---

13. **Confucius4 API details.** The second method in scope is "Confucius4
   API". What is its endpoint, authentication, and request/response format?
   Are there reference materials or existing code that document it?

>**Answer** Not important now. Implementing a new subclass to use this API is a next stage. The current goal is to perform the refactoring that creates the opportunity to implement different audio methods beyond EdgeTTS
---

14. **Method name mapping.** The control file uses `ttsmethod=edgeTTS`. What
   is the exact identifier for the Confucius4 API (e.g. `confucius4`), and
   should the identifiers be case-sensitive, hyphenated, or aliased?

>**Answer** If it's possible, it should be the name of the class that is the representation of the specific conversion method.

---

15. **Identifier case mismatch.** The example control file has
   `ttsmethod=edgeTTS`, but the class name (per Python convention and Q&A #14)
   would be `EdgeTTS`. Which exact value should the control file use —
   `edgeTTS`, `EdgeTTS`, or should the lookup be case-insensitive?

>**Answer** example is adjusted. tts_class=EdgeTTS

---

16. **Backward compatibility.** The current `gen_audio.py` takes a mapping
   file as a positional argument plus `--out-dir`. Should the new
   control-file-only interface fully replace the old CLI (no backward
   compatibility), or should the old form still be accepted for a while?

>**Answer** No backward compatibility is necessary

---

17. **Output format.** The current `gen_audio.py` always produces **WAV**
   (converting Edge-TTS's MP3 via pydub) because `wav_to_mp3.py` consumes WAV.
   Should the ABC contract require every method to emit WAV (methods may
   convert internally), or may a method emit MP3 directly?

>**Answer** gen_audio's responsibility is to generate the audio files only. The native output of a audio tool can be wav or mp3. `wav_to_mp3.py` will be adjusted later too to accept mp3 files as input.

---

18. **Canonical dispatch key name.** Q&A #15 says `tts_class=EdgeTTS`, but the
   on-disk example `wav\yang85_edge.tts` still uses `ttsmethod=edgeTTS`, and
   earlier questions refer to `ttsmethod`. Which key is canonical — `tts_class`
   or `ttsmethod` — and should the on-disk example file be updated to match?

>**Answer** tts_class re-read the `wav\yang85_edge.tts`

---

19. **Scope of this change request.** Q&A #17 says `wav_to_mp3.py` will be
   adjusted later to accept MP3 input. Is that adjustment part of this change
   request, or a separate future change request? In other words: does this CR
   only touch `gen_audio.py` (plus the control-file example and
   `plan_gen_audio.md`)?

>**Answer** this CR only touches `gen_audio.py` (plus the control-file example and
   `plan_gen_audio.md`)

---

20. **Dispatcher vs. method-specific keys.** Since the control file is
   method-specific (Q&A #5), which keys are "common" (read by `gen_audio.py`
   itself for dispatch and I/O) versus everything else (passed to the method
   class)? Proposed common keys: `tts_class`, `mapping_file`, `output_dir` —
   with all remaining keys forwarded to the method class as its parameters.

>**Answer** common keys are used by the main logic. After the specific tts_class is instanciated we can assume a setup(controlfile) method in it that is responsible to evaluate and save all other parameters in the conntrol file. And then the generate(pattern, output) called to perform the TTS. Setup can throw exception if the control file is not correct. e.g. mandatory parameter is missing

---

21. **Method-specific key prefix.** The updated example uses `tts.bitrate=192k`
   (a `tts.` prefix) for method-specific keys, while Q&A #20 says `setup()`
   receives the whole control file and evaluates "all other parameters". Is
   the `tts.` prefix a required convention (method classes must only read
   `tts.*` keys), or merely illustrative — may a method class read any
   non-common key directly?

>**Answer** No convention for tts specific parameter names. It's the setup() method's responsibility to find and use the parameters in the control file. 

---

22. **Output filename and extension.** The mapping structure is unchanged
   (Q&A: "keep mapping structure as it is"), so mapping keys end in `.wav`
   (e.g. `85_01.wav=无极势`). But Q&A #17 says a method may emit MP3 natively.
   If Edge-TTS now emits MP3, what filename should be written — the mapping
   key verbatim (`85_01.wav`), the key with the method's native extension
   (`85_01.mp3`), or something else?

>**Answer** generate(pattern, anyname.wav) can return with the anyname.mp3 generated filename. generate method should be clever enough to do this. gen_audio.py program's responsibility to instanciate the proper tts class, and then to call the setup and generate methods.

---

23. **Exact ABC interface.** Q&A #20 proposes `setup(controlfile)` and
   `generate(pattern, output)`. Please confirm the exact abstract methods and
   their signatures, e.g.:
   - `setup(config: dict) -> None`
   - `generate(entries: list[tuple[str, str]], output_dir: Path) -> None`
   or a different shape?

>**Answer** It's better if generate is responsible only for one transformation. generate(text, fulloutputpath) returns with the generated file name

---

24. **Method discovery.** How should `tts_class=EdgeTTS` map to the class?
   A hardcoded registry dict in `gen_audio.py` (e.g.
   `{"EdgeTTS": EdgeTTSGenerator}`), or dynamic import from the class name?

>**Answer** Dynamic import would be better, no code modification is necessary. But new new tts_class values will be created not so frequently. there can be a builder method in the main code that is responsible to instanciate the proper generator class based on the tts_class parameter. 

---

25. **Pipeline compatibility in this CR.** The current `gen_audio.py` converts
   Edge-TTS's MP3 to **WAV** via pydub, because `wav_to_mp3.py` (still
   WAV-only in this CR) expects `.wav` files per the form definitions. If the
   new Edge-TTS method emits MP3 natively, the existing `wav_to_mp3.py`
   pipeline breaks until it is updated (a future CR). Should the Edge-TTS
   method in **this** CR still convert MP3 → WAV (keeping the pipeline
   working), or may it emit MP3 natively (accepting that assembly breaks
   until `wav_to_mp3.py` is updated)?

>**Answer** Not necessary. In this change request I want to achieve only that new audio conversion tools can be added with implementing a new subclass with setup and generate methods. 

---

26. **pydub/ffmpeg dependency.** If a method emits its native format without
   conversion, does `gen_audio.py` still need the pydub/ffmpeg dependency in
   this CR, or should the conversion concern move entirely into the method
   classes (Edge-TTS keeps its MP3→WAV step internally if required by Q&A #25)?

>**Answer** Wait. If the native output of EdgeTTS is mp3 then it's fine. Any tts_class can generate it's native mp3 or wav format. wav_to_mp3.py will be adjusted later to be able to work with mp3 files directly without the wav -> mp3 conversion.

---

27. **Module / package layout.** Dynamic import from `tts_class=EdgeTTS` needs a
   known module path. Where should generator classes live, and how does the
   class name map to a module? Proposed convention:
   - a `generators/` package, one module per method (e.g. `generators/edge_tts.py`
     exposing `class EdgeTTS`), plus `generators/base.py` for the ABC;
   or a flat layout next to `gen_audio.py`?

>**Answer** Accepted.

---

28. **`generate` return value contract.** Q&A #22/#23 say
   `generate(text, fulloutputpath)` returns the generated filename (which may
   differ in extension, e.g. `.mp3`). Should the caller (main loop) do
   anything with this returned name beyond logging it in this CR, or is it
   only informational until `wav_to_mp3.py` learns to consume it?

>**Answer** Let's simpify the concept. **gen_audio.py is responsible** to generate mp3 files from text patterns listed in the mappings file. Read wav\yang85_mapping.properties. .wav extensions are modified to .mp3. If a `generate(text, fulloutputpath)` method returns with a .wav filename, then gen_audio converts it to mp3. wav_to_mp3.py will be refactored. No wav-mp3 conversion is necessary. The native input is always mp3. 

---
