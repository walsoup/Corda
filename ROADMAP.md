# corda-synth: Development Roadmap
## Making the Library Real

---

## Where We Are Now

`corda_synth v0.1.0` is a complete signal-processing synthesizer. It reads a
`.crd` file and produces audio using:

- A simplified LF glottal source model
- A 5-pole cascade formant filter bank (Klatt-style)
- Cubic bezier pitch interpolation from CVN curves
- Per-class synthesis dispatch for all 9 articulation classes
- Coarticulation crossfading between adjacent PEOs

**Current ceiling:** intelligible but robotic. This is exactly where Klatt
synthesizers from the 1980s landed. The path to human-quality output is
below.

---

## Phase 1 — Foundation & Testability (Weeks 1–6)

**Goal:** A working, installable Python package that produces intelligible
audio from real `.crd` files, with a test suite.

### 1.1 Package Infrastructure

- [ ] `pyproject.toml` with proper metadata, dependencies, and entry points
- [ ] Publish to PyPI as `corda-synth` (`pip install corda-synth`)
- [ ] Dependency pins: `numpy`, `scipy`, `pymongo` (for BSON)
- [ ] Optional: `soundfile` for high-quality WAV/FLAC output

```toml
# pyproject.toml
[project]
name = "corda-synth"
version = "0.1.0"
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10",
    "pymongo>=4.0",      # provides bson
    "soundfile>=0.12",   # optional, for WAV I/O
]
```

### 1.2 Test Corpus

The library needs real `.crd` files to test against. Build a small corpus
of hand-authored `.crd.json` files (the pure-JSON development format)
covering:

| File | Contents | Tests |
|---|---|---|
| `vowel_ah.crd.json` | Single VOICED /a/ PEO, static formants | Basic formant output |
| `word_stop.crd.json` | PLOSIVE + VOICED sequence | Burst + coarticulation |
| `sentence_hello.crd.json` | 5-PEO "hello" utterance | Full pipeline |
| `fricative_sss.crd.json` | Long FRICATIVE /s/ | Noise band accuracy |
| `fry_test.crd.json` | High-tension glottal curve | Vocal fry output |
| `hesitation_um.crd.json` | HESITATION PEO | Nasal murmur |

### 1.3 Automated Tests

```python
# tests/test_engine.py
def test_hello_renders_without_error():
    synth = CordaSynthesizer()
    audio = synth.render("corpus/sentence_hello.crd.json")
    assert audio.dtype == np.float32
    assert len(audio) > 0
    assert np.max(np.abs(audio)) <= 1.0

def test_silent_peo_produces_silence():
    # PEO with intensity = 0.0 should produce near-silent output
    ...

def test_plosive_burst_is_short():
    # Plosive synthesis should be < 25ms
    ...
```

### 1.4 CLI

```bash
# Render a .crd file from the command line
corda-synth render input.crd -o output.wav --sample-rate 44100

# Render a single PEO (debugging)
corda-synth render-peo input.crd --peo-id peo_042 -o peo_042.wav

# Print file summary
corda-synth info input.crd
```

---

## Phase 2 — Acoustic Quality (Weeks 6–14)

**Goal:** Natural-sounding neutral speech. A listener should recognize the
words without straining.

### 2.1 Proper LF Glottal Model

Replace the current approximation with the full 4-parameter LF model.
The four LF parameters (Rd, Ra, Rk, Rg) give fine-grained control over
voice quality and map cleanly onto the Corda glottal tension scalar.

Key resource: *Fant, Liljencrants & Lin (1985)* — the original paper.

Implementation target: a closed-form inverse-LF ODE solver that generates
the glottal flow derivative analytically rather than from a shaped envelope.

**Tension → LF parameter mapping:**

| Tension | Rd | Voice Quality |
|---|---|---|
| 0.0–0.2 | 3.0 | Breathy / whisper |
| 0.3–0.5 | 1.7 | Modal (neutral speech) |
| 0.6–0.8 | 0.9 | Pressed / strained |
| 0.9–1.0 | 0.3 | Vocal fry / creak |

### 2.2 Formant Bandwidth Estimation

Currently all bandwidths are hardcoded defaults. Phase 2 should derive
bandwidths from the data:

- **Nasals / nasalized vowels:** F2/F3 bandwidth × 3–5 (heavy anti-resonance)
- **High-tension (pressed) voice:** narrower F1 bandwidth (less open glottis)
- **Breathy voice:** wider bandwidths across all formants
- Parse `flags` array on each PEO for `"NASALIZED"`, `"ASPIRATED"`, etc.

### 2.3 Coarticulation: Formant Interpolation

The current engine applies per-PEO formant specs with a short crossfade.
Phase 2 replaces this with **proper formant interpolation across PEO
boundaries** using the 3rd-order bezier model:

```
PEO_n offset formants → [bezier blend] → PEO_(n+1) onset formants
```

This is the single biggest quality jump available without a neural model.

### 2.4 Non-Verbal PEO Synthesis

Phase 1 stubs non-verbal events as modulated aspiration noise.
Phase 2 gives each non-verbal type a proper model:

| Type | Model |
|---|---|
| Laughter | Pulsed aspiration at 4–8 Hz with rising F0 |
| Sigh | Long, slow aspiration with falling intensity curve |
| Cough | Short high-energy plosive burst + frication |
| Cry | High-F0 VOICED with trembling glottal curve |
| Vocal Fry | Already handled via tension ≥ 0.90 |

---

## Phase 3 — Expressiveness & Semantics (Weeks 14–26)

**Goal:** Layer 5 semantic data should audibly affect synthesis output.

### 3.1 Emotion → Synthesis Parameter Mapping

The `emotion_inference` field on SemanticPhrase objects should influence
synthesis defaults for the PEOs within that phrase:

| Emotion | F0 shift | Rate | Tension | Aspiration |
|---|---|---|---|---|
| `neutral` | baseline | baseline | 0.45 | 0.10 |
| `excitement` | +20% | +15% | 0.55 | 0.05 |
| `sudden_realization` | +35% spike | — | 0.50 | 0.08 |
| `questioning` | +15% final syllable | — | 0.48 | 0.10 |
| `grief` | −10% | −20% | 0.40 | 0.25 |
| `sarcasm` | flat, then spike | −5% | 0.52 | 0.06 |

These are applied as **offsets** on top of the raw CVN curve data —
they do not replace it.

### 3.2 Semantic Spike Rendering

`SEMANTIC_SPIKE` gesture class PEOs get special synthesis treatment:
- F0 is rendered at ×1.5 speed through the spike (rapid pitch movement)
- Intensity dips at the spike onset (natural de-emphasis before emphasis)
- Spike apex gets a brief formant brightening (+200 Hz on F2)

### 3.3 Prosodic Stress

`WordBoundary.stress` values drive amplitude and duration scaling:

- Primary stress: +15% duration, +10% amplitude
- Contrastive stress: +25% duration, +20% amplitude, higher F0
- Unstressed: −10% duration, slightly centralized formants (schwa-shift)

---

## Phase 4 — Neural Vocoder Backend (Months 6–12)

**Goal:** Near-human quality. The signal-processing chain is replaced (or
supplemented) with a neural vocoder conditioned on Corda parameters.

### 4.1 Architecture Choice

**HiFi-GAN** is the recommended starting point:
- Fast (real-time capable on consumer GPU)
- Conditioning on acoustic features is well-understood
- Pre-trained weights available for fine-tuning

Corda's synthesis parameters map naturally onto mel-spectrogram features,
which HiFi-GAN already uses as conditioning:

```
CVN Hz curve + FormantFrames → synthetic mel-spectrogram
                                        ↓
                              HiFi-GAN vocoder
                                        ↓
                                 waveform output
```

### 4.2 Training Data Requirements

To fine-tune the vocoder on Corda-parametrized features:

1. Record a multi-speaker speech dataset (or license an existing one:
   VCTK, LibriTTS)
2. Run the existing signal-processing engine to produce `.crd` parameter
   tracks for each recording (analysis → synthesis round-trip)
3. Train the neural vocoder to reconstruct the original waveform from
   the Corda parameters

This creates a "Corda codec" — the `.crd` file is the compressed
representation, and the neural vocoder is the decoder.

### 4.3 ONNX Export

Export the trained vocoder to ONNX for cross-platform deployment:

```bash
python -m corda_synth.neural.export --checkpoint vocoder.ckpt --output vocoder.onnx
```

The ONNX model runs on CPU, GPU, or browser (via ONNX Runtime Web).

---

## Phase 5 — Real-Time & Browser (Months 12+)

**Goal:** Live synthesis in the Corda IDE as the user scrubs the timeline.

### 5.1 Python Streaming API

```python
synth = CordaSynthesizer(mode="streaming")
for chunk in synth.stream(corda, chunk_size=1024):
    audio_output_device.write(chunk)   # PyAudio / sounddevice
```

The streaming API processes one synthesis frame at a time, maintaining
filter state across frames, enabling real-time playback at low latency.

### 5.2 WebAssembly (Browser)

Compile the signal-processing core (Phases 1–3) to WebAssembly via
**Emscripten** or **Pyodide** for use in the React IDE:

```javascript
// In the Corda IDE (Layer 6)
import { CordaSynth } from "@corda/synth-wasm";

const synth = await CordaSynth.init();
const audioBuffer = await synth.render(cordaPayload);
audioContext.decodeAudioData(audioBuffer);
```

The ONNX neural vocoder can run in-browser via **ONNX Runtime Web**
(`ort-web`), enabling full Phase 4 quality in the IDE without a server.

### 5.3 React Native Bridge

For mobile use (recording + immediate playback):

```
iOS/Android: AVAudioEngine (native) ← corda-synth-mobile (RN bridge)
```

---

## Dependency Map

```
Phase 1   numpy, scipy, pymongo, soundfile
Phase 2   + (no new deps — pure DSP improvements)
Phase 3   + (no new deps — uses existing data)
Phase 4   + torch, torchaudio, onnx, onnxruntime
Phase 5   + onnxruntime-web (npm), pyodide or emscripten
```

---

## Milestone Summary

| Milestone | Output | ETA |
|---|---|---|
| v0.1.0 | Working synthesizer, installable, test corpus | Week 6 |
| v0.2.0 | Full LF model, formant interpolation, CLI | Week 14 |
| v0.3.0 | Emotion mapping, semantic spike rendering, stress | Week 26 |
| v1.0.0 | Neural vocoder, ONNX export, streaming API | Month 12 |
| v2.0.0 | Browser WASM build, React IDE integration | Month 18 |

---

## Open Questions

1. **Analysis pipeline:** The synthesizer assumes `.crd` files already exist.
   A companion `corda-analyze` library (audio → `.crd`) is needed to close
   the loop. Pitch tracking (CREPE or pYIN), formant extraction (Praat
   via `parselmouth`), and IPA forced alignment (Montreal Forced Aligner)
   are the key pieces.

2. **Voice cloning:** Once the neural vocoder exists, speaker identity can
   be embedded as a conditioning vector. A `.crd` file could specify
   a `speaker_embedding` in the header and the vocoder renders in that
   voice.

3. **BSON vs MessagePack:** BSON requires `pymongo` as a dependency.
   MessagePack (`msgpack`) is lighter. Consider migrating the vector
   payload format in v0.2.0 before the format stabilizes.

4. **Licensing:** If training data is used for the neural vocoder, its
   license must be compatible with the intended distribution of the
   trained model weights.
