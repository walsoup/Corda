# Corda Protocol
## Universal Human Vocalization & Render Architecture

---

**Document Version:** 2.0.0
**File Extension:** `.crd`
**Status:** Final Specification
**Scope:** Complete cross-domain transcription of human vocalization (speech, singing, non-verbal utterances), binary serialization schemas, Digital Signal Processing (DSP) mathematical models, and React/Next.js Visual IDE rendering specifications.

---

## Table of Contents

1. [Executive Summary & Core Motivation](#1-executive-summary--core-motivation)
2. [Architecture Overview: The Six Pillars](#2-architecture-overview-the-six-pillars)
3. [Payload Architecture: JSON/BSON Dual Core](#3-payload-architecture-jsonbson-dual-core)
4. [Layer 1 — Phonetic & Articulation Notation (PAN)](#4-layer-1--phonetic--articulation-notation-pan)
5. [Layer 2 — Unanchored Vector Space (UVS)](#5-layer-2--unanchored-vector-space-uvs)
6. [Layer 3 — Speech-Rhythm Mapping (SRM)](#6-layer-3--speech-rhythm-mapping-srm)
7. [Layer 4 — Advanced Vocal Tract Modeling (AVT)](#7-layer-4--advanced-vocal-tract-modeling-avt)
8. [Layer 5 — NLP Semantic Syntax (NSS)](#8-layer-5--nlp-semantic-syntax-nss)
9. [Layer 6 — Visual Workspace DOM](#9-layer-6--visual-workspace-dom)
10. [Conflict Resolution Protocol](#10-conflict-resolution-protocol)
11. [Data Types & Enumerations](#11-data-types--enumerations)
12. [Streaming & WebAssembly Integration Protocol](#12-streaming--webassembly-integration-protocol)
13. [Appendix A: Full BSON Schema Definition](#13-appendix-a-full-bson-schema-definition)
14. [Appendix B: Example DSP Pipeline Trace](#14-appendix-b-example-dsp-pipeline-trace)

---

## 1. Executive Summary & Core Motivation

### 1.1 The Shift from Pitch-Centric to Vocal-Tract-Centric Modeling
The predecessor to Corda (HumScore v1) utilized a **Pitch-Centric Model**, enforcing discrete musical grids upon all vocal inputs. This inherently fails when modeling non-melodic speech, unpitched plosives/fricatives, and microtonal inflections, which constitute over 80% of human vocalization. 

Corda v2.0.0 introduces a **Vocal-Tract-Centric Model**. Instead of mapping vocalization to an abstraction of a musical instrument, it mathematically models the biological source: the lungs (air pressure), the glottis (oscillation source), and the oral/nasal cavities (dynamic resonant filter). Every `.crd` file is a rigid, frame-accurate recording of the mechanical state of the vocal tract.

### 1.2 Scope
Corda handles:
- **Continuous Speech:** Modeling micro-intonation, syllabic rubato, and emotional prosody.
- **Melodic Singing:** Tracking vibrato depth/rate, glissando, and belting formants.
- **Non-Verbal/Paralinguistic Utterances:** Laughter (pulsed aspiration), crying (tremolo tension), sighs, and vocal fry.
- **Unvoiced Consonants:** Broad-spectrum transient bursts (plosives) and band-limited turbulence (fricatives).

---

## 2. Architecture Overview: The Six Pillars

A `.crd` file is organized into **six discrete layers**. Each layer governs a separate domain of vocal mechanics or metadata. All layers operate on a unified temporal grid of **9,600 PPQ** (Pulses Per Quarter-note).

```text
┌───────────────────────────────────────────────────────┐
│  Layer 6: Visual Workspace DOM                        │  ← React Components / UI
├───────────────────────────────────────────────────────┤
│  Layer 5: NLP Semantic Syntax (NSS)                   │  ← Linguistics / Emotion
├───────────────────────────────────────────────────────┤
│  Layer 4: Advanced Vocal Tract Modeling (AVT)         │  ← Formants / LF Glottal
├───────────────────────────────────────────────────────┤
│  Layer 3: Speech-Rhythm Mapping (SRM)                 │  ← Prosody / IOI vectors
├───────────────────────────────────────────────────────┤
│  Layer 2: Unanchored Vector Space (UVS)               │  ← Continuous Pitch (Hz)
├───────────────────────────────────────────────────────┤
│  Layer 1: Phonetic & Articulation Notation (PAN)      │  ← Ground Truth (PEOs)
└───────────────────────────────────────────────────────┘
```

Lower layers supersede higher layers during synthesis conflict resolution. Layer 1 is the incontrovertible physical ground truth.

---

## 3. Payload Architecture: JSON/BSON Dual Core

Due to the extreme density of 9,600 PPQ frame data (often generating tens of millions of float values for formants and tension curves), pure JSON parsing becomes computationally unviable in browser/WASM environments. The `.crd` container employs a dual-payload specification.

### 3.1 Binary Container Layout

| Offset | Size (Bytes) | Type | Description |
|---|---|---|---|
| `0x00` | 4 | `char[4]` | Magic Header `CRD\x02` |
| `0x04` | 4 | `uint32_le` | Length of the JSON Header Block ($N$) |
| `0x08` | $N$ | `UTF-8` | JSON Header Payload |
| `0x08+N` | 4 | `uint32_le` | Length of BSON Vector Block ($M$) |
| `0x0C+N` | $M$ | `Binary` | BSON Vector Payload |

### 3.2 Header Block (JSON)
The header contains metadata, semantics (Layer 5), structural boundaries, and PEO metadata (Layer 1).
```json
{
  "corda_version": "2.0.0",
  "file_uuid": "f3a2c1d0-8b4e-4f7a-9c2d-1a3b5e7f9012",
  "created_at": "2025-06-01T14:32:00Z",
  "duration_ticks": 576000,
  "sample_rate_hz": 44100,
  "ppq_resolution": 9600,
  "mode": "SPEECH",
  "peos": [ ... ],
  "layer5_phrases": [ ... ]
}
```

### 3.3 Vector Payload (BSON)
The BSON block strictly contains typed continuous float arrays, perfectly aligned for direct memory mapping into NumPy or WebAssembly typed arrays without intermediate string coercion.
- `layer2_cvn_curves`: Complex nested structures of cubic bezier points.
- `layer4_glottal_curve`: High-density `Float32Array`.
- `layer4_formants`: Matrix of $N \times 5$ `Float32Array` values.
- `layer4_aspiration_curve`: High-density `Float32Array`.

---

## 4. Layer 1 — Phonetic & Articulation Notation (PAN)

The **Phonetic Event Object (PEO)** is the atomic unit of Corda. A PEO defines the mechanical category of a sound, its boundaries in ticks, and its base acoustic properties.

### 4.1 Base PEO Schema
```json
{
  "peo_id": "string",
  "articulation_class": "enum",
  "ipa_symbol": "string",
  "tick_onset": "integer",
  "tick_offset": "integer",
  "intensity": "float (0.0-1.0)",
  "flags": ["array of strings"]
}
```

### 4.2 Articulation Classes & Specific Overrides

#### 4.2.1 `VOICED` and `APPROXIMANT`
Sustained sounds utilizing the glottal source and vocal tract filters. Rely completely on Layer 2 and Layer 4.

#### 4.2.2 `PLOSIVE`
A transient, unpitched broadband burst. Bypasses Layer 2 (Pitch) entirely.
*Required Extensions:*
- `burst_duration_ms`: Duration of the transient attack envelope.
- `spectral_peak_hz`: Center frequency of the broadband burst energy.

#### 4.2.3 `FRICATIVE`
Continuous band-limited turbulence.
*Required Extensions:*
- `noise_floor_hz`: Lower bound of the high-pass filter.
- `noise_ceiling_hz`: Upper bound of the low-pass filter.
- `intensity_curve`: Temporal amplitude envelope shaping the noise.

#### 4.2.4 `NASAL`
Voiced sounds, but the synthesis engine engages deep anti-resonances (formant zeros) and widens F2/F3 bandwidths by $4.0\times$ to simulate the nasal cavity.

#### 4.2.5 `AFFRICATE`
Synthesized sequentially: A `PLOSIVE` algorithm for the first $25\%$ of the PEO duration, immediately crossfading into a `FRICATIVE` algorithm for the remainder.

---

## 5. Layer 2 — Unanchored Vector Space (UVS)

Pitch in Corda is not represented by notes, but by piecewise cubic bezier trajectories in continuous frequency space.

### 5.1 Contour Vector Notation (CVN) Curves
```json
{
  "curve_id": "cvn_001",
  "peo_ref": "peo_041",
  "anchor_hz": 220.0,
  "control_points": [
    { "tick": 14000, "hz": 215.5, "tension": 0.5 },
    { "tick": 15400, "hz": 230.1, "tension": 0.8 }
  ]
}
```

### 5.2 Mathematical Evaluation
To determine the instantaneous fundamental frequency $F_0(t)$ between two control points $P_0(t_0, hz_0, k_0)$ and $P_1(t_1, hz_1, k_1)$, Corda generates symmetric tangent handles based on the `tension` ($k$) parameter:

1. $\Delta hz = hz_1 - hz_0$
2. Outgoing Handle: $H_{out} = hz_0 + k_0 \times \frac{\Delta hz}{3}$
3. Incoming Handle: $H_{in} = hz_1 - k_1 \times \frac{\Delta hz}{3}$

The cubic evaluation over normalized time $u \in [0, 1]$ is:
$$B(u) = (1-u)^3 hz_0 + 3(1-u)^2 u H_{out} + 3(1-u) u^2 H_{in} + u^3 hz_1$$

---

## 6. Layer 3 — Speech-Rhythm Mapping (SRM)

SRM operates independent of the temporal grid, aggregating PEOs into `WordBoundary` structures to handle prosody, metric ambiguity, and IOI (Inter-Onset Interval) manipulation.

### 6.1 Prosodic Stress Vectors
Each `WordBoundary` can be assigned a `stress` modifier, which dictates automatic downstream temporal and acoustic scaling:
- **`PRIMARY`**: Ticks duration $\times 1.15$, Amplitude $\times 1.10$.
- **`CONTRASTIVE`**: Ticks duration $\times 1.25$, Amplitude $\times 1.20$, F0 curve $\times 1.15$.
- **`UNSTRESSED`**: Ticks duration $\times 0.90$, Formant Centralization applied (pulls F1/F2 towards 500/1500 Hz).

---

## 7. Layer 4 — Advanced Vocal Tract Modeling (AVT)

### 7.1 The Liljencrants-Fant (LF) Glottal Source Model
The vocal folds are modeled not as a simple oscillator, but as a complex fluid dynamics valve. The LF model parameterizes the derivative of the glottal flow ($dU_g/dt$).

Corda distills the highly complex LF parameters ($R_d, R_a, R_k, R_g$) into a single, user-facing parameter: **Glottal Tension** ($T \in [0.0, 1.0]$).

The mathematical conversion from Tension to the LF Shape Parameter ($R_d$) uses continuous piecewise linear interpolation:
- If $T \le 0.5$: $R_d = 3.0 - (\frac{T}{0.5}) \times (3.0 - 1.7)$
- If $0.5 < T \le 0.8$: $R_d = 1.7 - (\frac{T - 0.5}{0.3}) \times (1.7 - 0.9)$
- If $T > 0.8$: $R_d = 0.9 - (\frac{T - 0.8}{0.2}) \times (0.9 - 0.3)$

**Acoustic Equivalencies:**
- $T = 0.0$ ($R_d \approx 3.0$): Heavy breathiness, vast open phase.
- $T = 0.5$ ($R_d \approx 1.7$): Modal voice. Optimal resonant efficiency.
- $T \ge 0.9$ ($R_d \approx 0.3$): Vocal Fry. Causes the rendering engine to apply $\pm 15\%$ period jitter and suppress every $4^{th}$ glottal pulse to simulate subharmonics.

### 7.2 The Formant Cascade Filter Bank
The vocal tract acts as a series of 2nd-order Infinite Impulse Response (IIR) bandpass filters. Corda uses a 5-pole cascade arrangement. 
For a given Formant Center Frequency ($F_c$) and Bandwidth ($B_w$), the coefficients are calculated as:

1. Radius: $r = e^{-\pi \times \frac{B_w}{F_s}}$
2. Cosine Term: $\cos(\theta) = 2 \times r \times \cos(2\pi \times \frac{F_c}{F_s})$
3. Transfer Function: $H(z) = \frac{1 - r}{1 - \cos(\theta) z^{-1} + r^2 z^{-2}}$

**Lip Radiation:** Output is passed through a $+6\text{ dB/octave}$ highpass filter ($H(z) = 1 - z^{-1}$) to simulate the acoustic impedance at the lips.

---

## 8. Layer 5 — NLP Semantic Syntax (NSS)

Layer 5 bridges raw acoustics with linguistic intent. `WordBoundary` clusters are grouped into `SemanticPhrase` structures.

### 8.1 Emotion Matrices
The `emotion_inference` field applies macroeconomic DSP offsets to lower layers.
- **`excitement`**: Length scalar $0.85$, Pitch scalar $1.20$, Tension $+0.10$, Aspiration $-0.05$.
- **`grief`**: Length scalar $1.25$, Pitch scalar $0.90$, Tension $-0.05$, Aspiration $+0.15$.
- **`sarcasm`**: Flat pitch topology mapped to first $50\%$ of phrase, exponential pitch rise $1.0 \to 1.2$ applied to the terminal $50\%$. Tension $+0.07$.

### 8.2 The Semantic Spike
A highly specialized acoustic gesture tied to the `SEMANTIC_SPIKE` flag. Represents massive emotional emphasis.
1. **Pitch**: $1.25\times$ scalar multiplication.
2. **Vacuum Dip**: A 30ms window immediately preceding the spike where amplitude drops by $60\%$, maximizing psychoacoustic contrast.
3. **Formant Apex**: F2 center frequency dynamically boosted by $+200\text{ Hz}$ at the temporal center, reverting to baseline linearly.

---

## 9. Layer 6 — Visual Workspace DOM

The `Corda` protocol anticipates interaction via web-based Visual IDEs (React/Next.js/HTML5 Canvas).

### 9.1 Display Mapping
- **PEO Track:** Primary DOM timeline. `div` elements positioned via `left = tick_onset * zoom_factor`.
- **UVS Canvas:** WebGL or SVG overlay mapping the `CVNCurve` paths. Pitch space is normalized from $50\text{ Hz}$ to $1500\text{ Hz}$ logarithmic.
- **AVT Spectrogram:** Background canvas showing real-time F1-F5 curves.
- **NSS Text Lane:** Input fields mapped to `SemanticPhrase` boundaries for lyric editing and NLP tagging.

### 9.2 Memory Management Guidelines
Visual IDEs must never deserialize the full BSON payload into the React state tree. The BSON buffer must be held in an `ArrayBuffer` within a WebWorker or WASM instance. React components request bounded temporal windows (e.g., `get_cvn_range(start_tick, end_tick)`) to render visible data to the screen, ensuring $60\text{ FPS}$ performance even on 10-minute files.

---

## 10. Conflict Resolution Protocol

In a bidirectional IDE, users will inevitably create logical conflicts (e.g., drawing a pitch curve inside an unpitched consonant). The engine resolves conflicts via strict layer precedence:

1. **Articulation Overrules Pitch:** If a PEO is of class `PLOSIVE` or `FRICATIVE`, all UVS/Layer 2 data within its temporal boundaries is structurally ignored during DSP synthesis.
2. **Semantics Overrule Local Intensity:** A `SEMANTIC_SPIKE` generated amplitude dip overrides any user-defined `intensity` scalar inside the PEO.
3. **Temporal Anchoring:** If a user shortens a `SemanticPhrase`, the constituent PEOs are compressed via a percentage ratio, and all corresponding BSON float arrays are mathematically resampled (via linear interpolation) to the new sample lengths.

---

## 11. Data Types & Enumerations

### 11.1 Allowed IPA Symbols
- **Voiced:** `a`, `e`, `i`, `o`, `u`, `æ`, `ɛ`, `ɪ`, `ɔ`, `ʊ`, `ʌ`, `ə`
- **Plosive:** `p`, `b`, `t`, `d`, `k`, `g`
- **Fricative:** `f`, `v`, `θ`, `ð`, `s`, `z`, `ʃ`, `ʒ`, `h`
- **Nasal:** `m`, `n`, `ŋ`
- **Approximant:** `l`, `ɹ`, `j`, `w`

### 11.2 File Mode Configurations
- `SPEECH`: $6\text{ms}$ coarticulation crossfade default. Focuses on sharp transient boundaries.
- `MELODIC`: $15\text{ms}$ coarticulation crossfade. Implements heavy bezier formant smoothing.
- `HYBRID`: Adaptive crossfade calculation based on local temporal density.

---

## 12. Streaming & WebAssembly Integration Protocol

To support real-time audio playback within the IDE, the `.crd` file is compiled to PCM audio dynamically.

### 12.1 Generator Architecture
The downstream rendering engine must support a `stream(chunk_size)` interface.
Instead of allocating the entire file as a massive `Float32Array`, the synthesis engine evaluates exactly `chunk_size` samples (e.g., $1024$ samples $\approx 23\text{ms}$ at $44100\text{ Hz}$).

### 12.2 Neural Vocoder Pipeline Stub
For high-end configurations, the DSP output is piped into a secondary Neural Vocoder (HiFi-GAN topology). Since the raw model requires PyTorch, web implementations utilize a sophisticated DSP simulator passing the signal through:
1. **Harmonic Excitation:** $4\text{kHz}$ highpass $\to$ Non-linear $\tanh$ distortion $\to$ Bandpass filter to generate aliasing-free upper harmonics.
2. **Phase Dispersion:** $4^{\text{th}}$-order Elliptic low-pass utilized as an all-pass filter (coefficient flipping) to simulate natural vocal tract group-delay.
3. **Multiband Soft-Clipping:** Tightens the lower-mid frequencies ($<800\text{ Hz}$) to normalize bass resonance.

---

## 13. Appendix A: Full BSON Schema Definition

```typescript
type BSON_Payload = {
  layer2_cvn_curves: {
    curve_id: string;
    peo_ref: string;
    anchor_hz: double;
    control_points: { tick: int32, hz: double, tension: double }[];
    pitch_confidence: double;
  }[];
  layer4_formants: {
    tick: int32;
    f1_hz: double; f2_hz: double; f3_hz: double; f4_hz: double; f5_hz: double;
    aspiration_ratio: double;
  }[];
  layer4_glottal_curve: Float32Array;
  layer4_aspiration_curve: Float32Array;
};
```

---

## 14. Appendix B: Example DSP Pipeline Trace

A standard 10-millisecond synthesis frame traces through the following pipeline:
1. Query `peo_synth` for the current articulation class. (e.g., `VOICED`).
2. Sample `layer2_cvn_curves` via Bezier to find exact $F_0$.
3. Sample `layer4_glottal_curve` for Tension ($T$). Convert $T$ to LF parameter $R_d$.
4. Generate 441 samples of LF glottal flow derivative.
5. Apply Gaussian noise based on `layer4_aspiration_curve`.
6. Sample `layer4_formants`, calculate $r$ and $\cos(\theta)$ for 5 IIR filters.
7. Cascade filter the glottal pulse. Apply lip radiation differentiator.
8. Apply Phase 5 Semantic/Prosodic macros (Duration/Pitch scaling).
9. Apply Phase 4 Neural simulation (Excitation/Dispersion).
10. Soft-limit the resulting 441 samples. Submit to WASM AudioContext buffer. 
