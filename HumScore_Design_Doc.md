# HumScore: A Multi-Layer Notation Architecture for Complete Humming Transcription

**Document Version:** 1.0.0  
**Status:** Specification Draft  
**Scope:** Data representation only — audio capture and signal processing are explicitly out of scope.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design Philosophy](#2-design-philosophy)
3. [Core Architecture Overview](#3-core-architecture-overview)
4. [The Common Timeline Model](#4-the-common-timeline-model)
5. [Layer 0 — ABC Notation (Anchor Layer)](#5-layer-0--abc-notation-anchor-layer)
6. [Layer 1 — HumScript (HS): Extended Pitch-Precise Linear Notation](#6-layer-1--humscript-hs-extended-pitch-precise-linear-notation)
7. [Layer 2 — Contour Vector Notation (CVN): Gesture-First Melodic Description](#7-layer-2--contour-vector-notation-cvn-gesture-first-melodic-description)
8. [Layer 3 — Microtemporal Rhythm Notation (MRN): Sub-Beat Timing Grid](#8-layer-3--microtemporal-rhythm-notation-mrn-sub-beat-timing-grid)
9. [Layer 4 — Spectro-Timbral Annotation (STA): Timbre and Envelope Layer](#9-layer-4--spectro-timbral-annotation-sta-timbre-and-envelope-layer)
10. [Layer 5 — Semantic-Structural Notation (SSN): Musical Meaning Layer](#10-layer-5--semantic-structural-notation-ssn-musical-meaning-layer)
11. [The HumScore Master Schema (JSON)](#11-the-humscore-master-schema-json)
12. [Inter-Layer Synchronization Protocol](#12-inter-layer-synchronization-protocol)
13. [Conflict Resolution and Layer Precedence](#13-conflict-resolution-and-layer-precedence)
14. [Song Reconstruction Guide](#14-song-reconstruction-guide)
15. [Edge Cases and Special Conditions](#15-edge-cases-and-special-conditions)
16. [Appendix A — Full HumScript Token Reference](#appendix-a--full-humscript-token-reference)
17. [Appendix B — CVN Direction Primitives](#appendix-b--cvn-direction-primitives)
18. [Appendix C — STA Formant Vowel Color Table](#appendix-c--sta-formant-vowel-color-table)
19. [Appendix D — SSN Harmonic Function Tags](#appendix-d--ssn-harmonic-function-tags)
20. [Appendix E — Complete Worked Example](#appendix-e--complete-worked-example)

---

## 1. Executive Summary

Humming is arguably the most information-dense form of raw musical expression a human can produce without an instrument. A single hummed phrase encodes pitch, rhythm, tempo, dynamics, timbre, emotion, phrasing, harmonic intent, and melodic gesture — all simultaneously and often implicitly. Standard music notation systems (including ABC, MIDI, MusicXML) were designed to *describe* music that has already been composed and discretized. They are catastrophically lossy when applied directly to humming, which is inherently continuous, microtonal, expressive, and ambiguous.

**HumScore** is a six-layer notation architecture designed to capture *everything* a hum contains, at every level of musical abstraction — from sub-cent pitch deviations to high-level phrase structure — in a lossless, machine-readable, and human-interpretable format. Its six layers are:

| Layer | Name | Abstraction Level | Primary Concern |
|-------|------|-------------------|-----------------|
| 0 | ABC Notation | Standard | Discrete pitch & rhythm scaffold |
| 1 | HumScript (HS) | Extended Linear | Microtonal pitch, vibrato, portamento, breath |
| 2 | Contour Vector Notation (CVN) | Gestural | Melodic shape, direction, curvature |
| 3 | Microtemporal Rhythm Notation (MRN) | Sub-beat | Exact timing, tempo curves, rubato |
| 4 | Spectro-Timbral Annotation (STA) | Sonic | Timbre, envelope, resonance, dynamics |
| 5 | Semantic-Structural Notation (SSN) | Semantic | Phrase meaning, motifs, harmonic function, emotion |

Together, these six layers create a complete, lossless representation of any hummed performance that can be deterministically reconstructed into a full musical score.

---

## 2. Design Philosophy

### 2.1 The Losslessness Imperative

The central design mandate of HumScore is **losslessness at every level of musical meaning**. This means:

- **Acoustic losslessness:** Nothing that is perceivable in the hum is discarded. Pitch deviations smaller than a semitone, timing deviations smaller than a 32nd note, timbral qualities, and dynamic shapes within a single note are all preserved.
- **Gestural losslessness:** The *shape* of a musical gesture — a rising sweep, a rounded arch, a sharp angular jump — is preserved independently of whether it maps cleanly to discrete pitches.
- **Semantic losslessness:** The *intent* behind a phrase — its emotional character, its role in an implied song structure, its relationship to earlier motifs — is preserved as annotation, not inference.

### 2.2 Layer Independence with Tight Coupling

Each layer is independently valid and useful. A system consuming only Layer 0 gets a rough but playable melody. A system consuming only Layer 4 gets timbral data. But the layers are *tightly coupled* through a shared timeline, meaning any event in any layer can be precisely correlated to events in every other layer.

This design enables:
- Partial consumption (use only the layers you need)
- Incremental enrichment (add layers over time as more analysis is done)
- Cross-layer querying (find all notes where vibrato depth > 0.5 semitones AND harmonic function is dominant)

### 2.3 Discrete vs. Continuous Representation

Standard music notation assumes discreteness: a note is either C or C#, it lasts either a quarter beat or an eighth. Humming is fundamentally *not discrete*. HumScore's design philosophy treats:

- **Layer 0 and Layer 1** as the *discretized* domain (snapped to notes and beats, with deviation annotations)
- **Layer 2 and Layer 3** as the *continuous* domain (raw gesture and timing curves)
- **Layer 4** as the *physical* domain (acoustic properties)
- **Layer 5** as the *semantic* domain (musical meaning)

This dual representation allows downstream tools to choose their working domain — a sheet music renderer works in the discrete domain; a synthesis engine works in the continuous and physical domains; a music analysis tool works in the semantic domain.

### 2.4 Human Readability

Despite its complexity, HumScore is designed to be legible to a human musician without a decoder. Layer 0 produces standard ABC notation that any trained musician can read. Layer 1 extends it with a small set of intuitive tokens. Layers 2–5 use structured data formats but include human-readable label fields. The system must never sacrifice human interpretability for machine precision.

### 2.5 Extensibility

Every layer defines a `custom_extensions` field. HumScore is a versioned specification. New token types, new timbral parameters, and new semantic tags can be added in minor versions without breaking parsers that ignore unknown fields.

---

## 3. Core Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HUMSCORE DOCUMENT                               │
│                                                                         │
│  ┌─────────────┐                                                        │
│  │  METADATA   │  title, hummerID, recordingRef, key, tempo, time_sig  │
│  └─────────────┘                                                        │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   COMMON TIMELINE MODEL                          │   │
│  │   tempoMap[]  ·  timeSignatureMap[]  ·  keyMap[]  ·  barMap[]   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│           │              │              │              │                 │
│  ┌────────▼──────────────▼──────────────▼──────────────▼────────────┐   │
│  │                    LAYER SYNCHRONIZATION BUS                     │   │
│  │         All layers anchor events to: tick position (480/beat)   │   │
│  └───────┬──────────┬──────────┬──────────┬──────────┬─────────────┘   │
│          │          │          │          │          │                  │
│     ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐            │
│     │LAYER 0 │ │LAYER 1 │ │LAYER 2 │ │LAYER 3 │ │LAYER 4 │ ┌─LAYER 5─┐ │
│     │  ABC   │ │  HS    │ │  CVN   │ │  MRN   │ │  STA   │ │  SSN    │ │
│     └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Primary Data Flows

```
Raw Hum
   │
   ├──► [Pitch Quantization] ──────────────► Layer 0 (ABC)
   │         │ residuals
   │         └────────────────────────────► Layer 1 (HS) [deviations + ornaments]
   │
   ├──► [Gesture Extraction] ──────────────► Layer 2 (CVN)
   │
   ├──► [Timing Analysis] ─────────────────► Layer 3 (MRN)
   │
   ├──► [Timbral Analysis] ────────────────► Layer 4 (STA)
   │
   └──► [Musical Interpretation] ──────────► Layer 5 (SSN)
```

---

## 4. The Common Timeline Model

Every event in every layer is anchored to the **Common Timeline**, which is defined in absolute *ticks*. This ensures perfect synchronization across all layers.

### 4.1 Tick Resolution

The default tick resolution is **480 ticks per quarter note (PPQ)**. This value is chosen because it is evenly divisible by all standard note values including triplets:

| Note Value | Ticks (at 480 PPQ) |
|---|---|
| Whole note | 1920 |
| Half note | 960 |
| Quarter note | 480 |
| 8th note | 240 |
| 16th note | 120 |
| 32nd note | 60 |
| 64th note | 30 |
| Triplet quarter | 320 |
| Triplet 8th | 160 |
| Triplet 16th | 80 |
| Quintuplet 16th | 96 |
| Septuplet 16th | ~68.57 (floor: 68) |

For sub-30-tick accuracy (capturing extremely fine timing nuances), a **high-resolution mode** of **9600 PPQ** is available, and the tick resolution is stored in the document header.

### 4.2 The Tempo Map

The tempo map is a sorted array of tempo change events. Tempo is NOT assumed constant — humming almost never has a perfectly constant tempo.

```json
"tempoMap": [
  { "tick": 0,    "bpm": 92.0,  "confidence": 0.95 },
  { "tick": 1920, "bpm": 88.5,  "confidence": 0.87 },
  { "tick": 3840, "bpm": 94.2,  "confidence": 0.91 }
]
```

Between tempo map events, tempo is **linearly interpolated** unless `"interpolation": "step"` is set on a given entry.

**Fields:**
- `tick` — Position on the timeline
- `bpm` — Beats per minute at this point
- `confidence` — How confident the system is in this tempo reading (0.0–1.0); a confidence below 0.6 flags that the tempo here is unreliable
- `interpolation` — Optional: `"linear"` (default) or `"step"` (sudden change)

### 4.3 The Time Signature Map

```json
"timeSignatureMap": [
  { "tick": 0,    "numerator": 4, "denominator": 4, "inferred": true },
  { "tick": 7680, "numerator": 3, "denominator": 4, "inferred": false }
]
```

`inferred: true` means the time signature was algorithmically deduced, not explicitly indicated. This is the common case with humming.

### 4.4 The Key Map

```json
"keyMap": [
  { "tick": 0,    "key": "G", "mode": "major",  "confidence": 0.88 },
  { "tick": 5760, "key": "E", "mode": "minor",  "confidence": 0.73 }
]
```

### 4.5 The Bar Map

For convenience, the bar map pre-computes the tick position of every barline. This allows human-readable "bar:beat" addressing across all layers.

```json
"barMap": [
  { "bar": 1, "tick": 0    },
  { "bar": 2, "tick": 1920 },
  { "bar": 3, "tick": 3840 }
]
```

### 4.6 Tick-to-Wall-Clock Conversion

Given the tempo map, any tick position can be converted to a wall-clock time in milliseconds. The conversion is stored as a computed lookup table in the `clockMap` field to avoid real-time computation:

```json
"clockMap": [
  { "tick": 0,    "ms": 0.0    },
  { "tick": 480,  "ms": 652.17 },
  { "tick": 960,  "ms": 1304.3 }
]
```

---

## 5. Layer 0 — ABC Notation (Anchor Layer)

### 5.1 Purpose and Role

Layer 0 serves as the **human-readable anchor** of the entire system. It is the most lossy layer by design — its job is not to capture every nuance of the hum, but to provide a clean, standard, immediately playable representation that:

1. Can be rendered by any standard ABC notation tool
2. Gives a musician a playable scaffold to start from
3. Establishes the discrete pitch and rhythmic "skeleton" that all other layers annotate

Layer 0 is generated by **quantizing** the continuous pitch and timing data to the nearest standard pitch class and rhythmic duration. It is the *floor* of the representation, not the ceiling.

### 5.2 ABC Header Block

HumScore uses a standard ABC header with the following mandatory and HumScore-specific extension fields:

```abc
X:1
T:HumScore Export - Untitled Session
C:Hummer (Human)
M:4/4
L:1/8
Q:1/4=92
K:G
%%humscore-version 1.0.0
%%humscore-session-id a3f7c2d1-9b4e-4f6a-8c1d-2e5f0a7b3c9d
%%humscore-ppq 480
%%humscore-layers HS CVN MRN STA SSN
```

The `%%humscore-*` directives are extension comments in standard ABC format and are ignored by non-HumScore parsers.

### 5.3 Pitch Quantization Rules

The following rules govern how continuous pitch is snapped to discrete ABC notation:

1. **Nearest semitone rule:** A pitch is snapped to the nearest semitone. If a pitch is within 49 cents of a semitone, it maps to that semitone. If it sits exactly between two semitones (50 cents), it maps to the higher semitone.

2. **Key signature preference rule:** Within a context where the key signature is established, pitches within 65 cents of a diatonic scale degree are snapped to that degree rather than to a chromatic neighbor that is closer in absolute cents. Example: in G major, a pitch at 755 cents (between E and F, but closer to F which is 700) would be snapped to E (702 cents) if the diatonic preference weight is active.

3. **Inflection memory rule:** If a pitch sequence has been consistently flat or sharp in the same direction for 3 or more consecutive notes, the quantization bias shifts in that direction by up to 15 cents to reflect a humming style that consistently sings flat or sharp.

4. **Held-note anchoring rule:** For notes held for more than 480 ticks (one beat), the anchor pitch is determined from the *central* 60% of the note's duration, discarding the attack and release phases which may be microtonal.

### 5.4 Rhythm Quantization Rules

1. **Grid snap:** Note durations are snapped to the nearest value in the standard grid: {whole, half, dotted-half, quarter, dotted-quarter, 8th, dotted-8th, 16th, 32nd}.

2. **Triplet detection:** If a sequence of three notes fits within a 2-beat window with total duration deviation less than 10%, they are notated as triplets.

3. **Tuplet detection:** Extended tuplet groups (5, 6, 7 against 4) are detected if three or more consecutive notes have equal or near-equal sub-division of a standard beat value (deviation < 8%).

4. **Rubato marking:** If a note's raw duration deviates from its quantized duration by more than 20%, an ABC `!tenuto!` or `!fermata!` decoration is added, and the deviation is fully recorded in Layer 3.

5. **Rest detection:** Silences below 30ms are treated as note-to-note transitions (covered by Layer 1 portamento tags), not rests. Silences of 30–200ms are notated as short rests. Silences above 200ms are notated as full rests with an ABC `z` token.

### 5.5 ABC Ornamentation

Standard ABC ornamentation symbols are used for gross ornaments where applicable:

| Symbol | Meaning |
|---|---|
| `!trill!` | Trill detected (pitch oscillation > 0.8 semitones, rate > 5Hz) |
| `!mordent!` | Lower mordent (single pitch dip and return) |
| `!pralltriller!` | Upper mordent (single pitch rise and return) |
| `!slide!` | Portamento (glide from previous note) |
| `!emphasis!` | Dynamic accent on this note |

Fine-grained ornament data is fully captured in Layer 1.

### 5.6 Example ABC Output

```abc
X:1
T:HumScore Export - Session 001
M:4/4
L:1/8
Q:1/4=92
K:G
%%humscore-version 1.0.0
|: G2 AB c2 BA | G4 !slide!d2 e2 | !trill!f2 ed c2 BA | G6 z2 :|
```

---

## 6. Layer 1 — HumScript (HS): Extended Pitch-Precise Linear Notation

### 6.1 Purpose and Role

HumScript is a superset of ABC notation. It operates in the same linear, note-by-note domain as ABC but adds the *residuals* — everything that ABC's quantization threw away. HumScript is the system for musicians who want to read a "performance score" rather than a "composition score." It answers the question: *"Exactly how was this note hummed, as opposed to what note it was?"*

HumScript is expressed as a **parallel annotation track** alongside the ABC text, using structured token strings. Each note in the ABC score has a corresponding HumScript annotation block.

### 6.2 The HumScript Note Object

Every note in the Layer 0 ABC output maps to a HumScript Note Object (HNO). The HNO contains:

```
HS[<note_id>] {
  pitch_dev    : <cents offset from quantized pitch>
  onset_quality: <onset descriptor>
  offset_quality: <offset descriptor>
  vibrato      : <vibrato block or null>
  portamento   : <portamento block or null>
  glottal      : <glottal descriptor or null>
  dynamic      : <dynamic descriptor>
  nasality     : <float 0.0–1.0>
}
```

#### 6.2.1 pitch_dev — Pitch Deviation

The `pitch_dev` field records the **signed cent offset** from the quantized ABC pitch. This is the most important field in Layer 1.

Format: `+N` or `-N` where N is 0–99.

- `+0` means the pitch was perfectly centered on the semitone
- `+35` means the note was hummed 35 cents sharp
- `-20` means the note was hummed 20 cents flat

For notes where the pitch is not stable (i.e., it moves within the note), `pitch_dev` becomes a **deviation curve** rather than a scalar:

```
pitch_dev_curve: [
  { tick_offset: 0,   cents: +12 },
  { tick_offset: 120, cents: +8  },
  { tick_offset: 240, cents: +18 },
  { tick_offset: 360, cents: +15 }
]
```

This describes how the pitch deviation evolves across the note's duration.

#### 6.2.2 onset_quality — Attack Descriptor

How does the note begin?

| Token | Description |
|---|---|
| `CLEAN` | Note begins directly on the target pitch |
| `GLIDE_FROM` | Pitch glides up from below (portamento from silence) |
| `FALL_INTO` | Pitch falls down from above (portamento from silence) |
| `GLOTTAL_HARD` | Hard glottal stop onset (abrupt, percussive beginning) |
| `GLOTTAL_SOFT` | Soft glottal onset (breathy, gradual start) |
| `BREATHY` | Onset blurred by breath noise |
| `SCOOP` | Brief upward pitch scoop before landing on target (common in pop/jazz) |
| `DIP` | Brief downward pitch dip before landing on target |

#### 6.2.3 offset_quality — Release Descriptor

How does the note end?

| Token | Description |
|---|---|
| `CLEAN` | Note ends cleanly |
| `FADE` | Note fades out in volume |
| `FALLOFF` | Pitch drops at the end (common jazz/blues gesture) |
| `LIFT` | Pitch rises slightly at the end |
| `CUTOFF_HARD` | Abrupt, consonant-like stop |
| `INTO_NEXT` | Legato — pitch slides directly into the next note |
| `TRAIL` | Note continues slightly past its notated duration (time stretching) |

#### 6.2.4 vibrato — Vibrato Block

Vibrato is a periodic pitch oscillation. The HumScript vibrato block fully parameterizes it:

```
vibrato: {
  present     : true,
  onset_delay : 180,     // ticks after note start before vibrato begins
  rate_hz     : 5.8,     // oscillations per second
  depth_cents : 35,      // peak-to-peak amplitude in cents
  depth_curve : "growing",  // how depth changes: "steady" | "growing" | "fading" | "arch"
  rate_curve  : "steady",   // how rate changes: "steady" | "accelerating" | "decelerating"
  shape       : "sine"      // oscillation shape: "sine" | "asymmetric_up" | "asymmetric_down"
}
```

**depth_curve options:**
- `steady` — Vibrato depth stays constant
- `growing` — Vibrato depth starts small and increases
- `fading` — Vibrato depth decreases toward the end
- `arch` — Vibrato depth increases then decreases

#### 6.2.5 portamento — Glide Block

Portamento (glissando, slide) between two consecutive notes:

```
portamento: {
  present     : true,
  direction   : "up",     // "up" | "down"
  duration    : 60,       // ticks (how long the glide takes)
  curve       : "linear", // "linear" | "exponential" | "logarithmic" | "s_curve"
  start_pitch_cents: -80, // pitch at start of glide relative to departure note
  end_pitch_cents  : 0    // pitch at end of glide relative to destination note
}
```

When `portamento.present` is true, the glide *overlaps* both the preceding note's offset and this note's onset. The `duration` describes how many ticks of glide time are "consumed" from the note transition.

#### 6.2.6 glottal — Glottal Descriptor

Glottal events are vocal events generated at the larynx — clicks, creaks, and vocal fry. In humming, these can appear as intentional ornaments or as natural vocal articulation.

```
glottal: {
  type   : "creak",    // "click" | "creak" | "fry" | "vocal_creak" | "breath_catch"
  tick   : 240,        // tick offset within the note
  intensity: 0.6       // 0.0–1.0 relative intensity
}
```

If multiple glottal events occur within a single note, `glottal` becomes an array.

#### 6.2.7 dynamic — Dynamic Descriptor

```
dynamic: {
  level       : "mf",   // pp | p | mp | mf | f | ff | fff
  peak_position: 0.4,   // fraction of note duration where loudest point is
  shape       : "flat"  // "flat" | "swell" | "diminuendo" | "crescendo" | "accent_front" | "accent_back"
}
```

#### 6.2.8 nasality — Resonance Index

A float from 0.0 to 1.0 representing the degree of nasal resonance:
- `0.0` — fully oral resonance (open, bright hum)
- `0.5` — balanced
- `1.0` — fully nasal resonance (closed, buzzy, "mmmm" hum)

### 6.3 The Breath Mark Object

Breath marks record actual breaths taken during the hum. These are musically significant because they divide the melody into *breath phrases* — the fundamental unit of a singer's experience.

```
BREATH {
  tick       : 2880,
  duration   : 95,      // ms
  type       : "normal", // "normal" | "catch_breath" | "gasping" | "nasal_inhale"
  after_note : "n_007"  // note ID of the note preceding this breath
}
```

### 6.4 Trill and Ornament Detail Block

When a trill or ornament is detected and notated in Layer 0, Layer 1 provides the full parametric description:

```
ORNAMENT {
  note_id    : "n_012",
  type       : "trill",
  upper_pitch_dev : +20,    // how far above the main pitch the trill goes
  lower_pitch_dev : 0,
  rate_hz    : 7.2,
  cycle_count: 3.5,
  resolution : "turn_down"  // how the ornament resolves: "clean" | "turn_up" | "turn_down" | "fade"
}
```

### 6.5 HumScript Full Example

Below is a short passage in combined ABC + HumScript representation:

```
ABC:  G2 AB c2 BA

HS[n_001] { note:"G", pitch_dev:+18, onset_quality:CLEAN, offset_quality:INTO_NEXT,
            vibrato:null, portamento:null, dynamic:{level:"mp", shape:"flat"}, nasality:0.7 }

HS[n_002] { note:"G", pitch_dev:+15, onset_quality:CLEAN, offset_quality:INTO_NEXT,
            vibrato:null, portamento:null, dynamic:{level:"mp", shape:"swell"}, nasality:0.7 }

HS[n_003] { note:"A", pitch_dev:-8,  onset_quality:SCOOP, offset_quality:INTO_NEXT,
            portamento:{ present:true, direction:"up", duration:40, curve:"logarithmic",
                         start_pitch_cents:-30, end_pitch_cents:0 },
            dynamic:{level:"mf", shape:"flat"}, nasality:0.6 }

BREATH { tick:960, duration:72, type:"catch_breath", after_note:"n_002" }
```

---

## 7. Layer 2 — Contour Vector Notation (CVN): Gesture-First Melodic Description

### 7.1 Purpose and Role

Human beings don't experience music as a sequence of discrete pitches. They experience it as a sequence of *gestures* — a rise here, a fall there, a plateau, an arch. The Contour Vector Notation layer captures this gestural reality directly.

CVN is entirely **pitch-continuous and time-continuous**. It treats the melody as a path through a 2D space of (pitch × time) and describes that path as a sequence of **vector segments**, each with:

- A starting pitch (in continuous semitones, not discrete)
- A direction and endpoint
- A curvature profile
- A timing relationship

CVN is the layer most useful for:
- Reconstructing the **shape** of a melody when pitch quantization is uncertain
- Identifying repeated melodic gestures that may have different discrete notes but the same shape
- Driving synthesis engines that work in the frequency domain rather than the note domain
- Generating melodic variations that preserve shape while changing notes

### 7.2 Continuous Pitch Units

CVN uses **semitone-decimal notation (SDN)** where 0.0 = C4 (middle C), and each integer increment is one semitone. Thus:

- C4 = 0.00
- C#4 = 1.00
- D4 = 2.00
- A4 = 9.00 (440 Hz)
- G4 = 7.00
- G4 + 18 cents = 7.18
- E4 - 35 cents = 4.65

This allows fully continuous pitch representation without any quantization.

### 7.3 The CVN Segment Object

A CVN segment is the fundamental unit of gesture description:

```json
{
  "seg_id"      : "cvn_003",
  "tick_start"  : 480,
  "tick_end"    : 720,
  "pitch_start" : 7.18,
  "pitch_end"   : 9.05,
  "curvature"   : {
    "type"      : "concave_up",
    "strength"  : 0.6
  },
  "gesture_class" : "RISE",
  "confidence"    : 0.92,
  "energy"        : 0.75,
  "anchored"      : true
}
```

**Fields:**

- `seg_id` — Unique segment identifier
- `tick_start / tick_end` — Timeline positions
- `pitch_start / pitch_end` — Continuous SDN pitch at segment boundaries
- `curvature.type` — Shape of the pitch path between start and end (see Section 7.4)
- `curvature.strength` — How pronounced the curvature is, 0.0 (straight line) to 1.0 (maximum curve)
- `gesture_class` — The top-level gesture primitive (see Section 7.5)
- `confidence` — Confidence in this segmentation (0.0–1.0)
- `energy` — Relative RMS energy of this segment (0.0–1.0), providing amplitude context
- `anchored` — Whether this segment's pitch_start and pitch_end map cleanly to semitones

### 7.4 Curvature Types

Between any two pitch endpoints, the path taken can vary significantly:

| Type | Description | Visual Analogy |
|---|---|---|
| `straight` | Linear interpolation between start and end | A diagonal line |
| `concave_up` | Path bows upward (above the straight line) | An arch |
| `concave_down` | Path bows downward (below the straight line) | A valley |
| `s_curve_up` | Starts concave-down, ends concave-up | An S-shape, rising overall |
| `s_curve_down` | Starts concave-up, ends concave-down | A reverse S-shape, falling overall |
| `stepped_up` | Fast jump followed by approach from below | A stair step up |
| `stepped_down` | Fast jump followed by approach from above | A stair step down |
| `plateau` | Rises quickly, holds flat, releases | A mesa |
| `spike` | Rises to a peak and returns (note: start ≈ end pitch) | A spike |
| `dip` | Falls to a trough and returns (note: start ≈ end pitch) | A valley |
| `oscillating` | Multiple up-down cycles (vibrato, trill) | A sine wave |

### 7.5 Gesture Class Primitives

Every CVN segment is assigned a gesture class from the following taxonomy:

```
GESTURE_CLASS {
  PRIMARY   : RISE | FALL | HOLD | ARCH | VALLEY | OSCILLATE | LEAP_UP | LEAP_DOWN
  SECONDARY : GRADUAL | RAPID | SMOOTH | ANGULAR
  QUALIFIER : PARTIAL | COMPLETE | EXTENDED | COMPRESSED
}
```

A full gesture class tag is written as: `RISE.GRADUAL.COMPLETE`

This three-part tag creates a rich vocabulary: `LEAP_UP.RAPID.PARTIAL` describes a sudden upward jump that doesn't land cleanly on the expected pitch; `ARCH.SMOOTH.EXTENDED` describes a long, flowing rise-and-fall gesture.

### 7.6 Phrase-Level Contour (PLC)

Above the segment level, CVN aggregates segments into **Phrase Contours** — the overall shape of a musical phrase as a single compressed descriptor.

```json
{
  "plc_id"     : "plc_001",
  "tick_start" : 0,
  "tick_end"   : 1920,
  "segments"   : ["cvn_001", "cvn_002", "cvn_003", "cvn_004", "cvn_005"],
  "shape_code" : "ARC_DOWN",
  "ambitus"    : {
    "lowest_pitch"  : 5.15,
    "highest_pitch" : 11.72,
    "range_semitones": 6.57
  },
  "net_motion" : -3.20,
  "shape_summary": "A rising gesture in the first third, plateau in the middle, descent to a point below the start"
}
```

**shape_code** values describe the overall contour:

| Shape Code | Description |
|---|---|
| `FLAT` | Minimal pitch movement, generally stable |
| `ARC_UP` | Rises overall across the phrase |
| `ARC_DOWN` | Falls overall across the phrase |
| `ARCH` | Rises and falls, ends near start pitch |
| `VALLEY` | Falls and rises, ends near start pitch |
| `RISE_PLATEAU` | Rises and holds |
| `PLATEAU_FALL` | Holds and then falls |
| `COMPLEX` | Multiple direction changes, no simple summary |
| `WAVE` | 2+ full rise-fall cycles |

### 7.7 Contour Similarity Index

CVN includes a **Contour Similarity Index (CSI)** that computes pairwise similarity between phrase contours. This is critical for motif detection and song structure inference.

The CSI between two phrase contours `PLCa` and `PLCb` is computed as:

```
CSI(a, b) = weighted_average(
  shape_code_match    × 0.30,
  net_motion_delta    × 0.15,
  ambitus_overlap     × 0.20,
  segment_sequence_match × 0.35
)
```

A CSI above 0.80 indicates strong contour similarity (same melodic shape). A CSI above 0.60 indicates recognizable similarity (same gesture family).

---

## 8. Layer 3 — Microtemporal Rhythm Notation (MRN): Sub-Beat Timing Grid

### 8.1 Purpose and Role

Standard notation, including ABC, quantizes timing to a grid. A quarter note is a quarter note — it either lasts exactly 480 ticks or it doesn't. But human humming is never perfectly on the grid. The Microtemporal Rhythm Notation layer captures the *actual* timing of every note event at full tick resolution, separately from the quantized grid.

MRN answers the question: *"When exactly did this note start, how long exactly did it last, and how does the tempo actually flow moment by moment?"*

This layer is the one most responsible for making a reconstruction *feel* human rather than robotic. The groove, the swing, the slight delay on an offbeat, the natural push before a climactic phrase — all of this lives in Layer 3.

### 8.2 The MRN Event Object

Every note is represented as an MRN Event:

```json
{
  "event_id"         : "mrn_004",
  "note_id"          : "n_004",
  "tick_onset_raw"   : 1442,
  "tick_onset_grid"  : 1440,
  "tick_offset_raw"  : 1678,
  "tick_offset_grid" : 1680,
  "onset_deviation"  : +2,
  "offset_deviation" : -2,
  "duration_raw"     : 236,
  "duration_grid"    : 240,
  "duration_ratio"   : 0.983,
  "ioi_raw"          : 243,
  "ioi_grid"         : 240,
  "velocity"         : 74,
  "velocity_curve"   : null
}
```

**Fields:**

- `tick_onset_raw` — Exact tick at which the note began
- `tick_onset_grid` — Nearest grid position (from Layer 0 quantization)
- `onset_deviation` — `raw - grid` in ticks; positive = played late, negative = played early
- `tick_offset_raw` — Exact tick at which the note ended
- `duration_raw` — Actual note duration in ticks
- `duration_ratio` — `raw / grid`; values below 0.85 indicate a clipped/short note; above 1.15 indicate a stretched note
- `ioi_raw` — Inter-Onset Interval: ticks from this note's onset to the next note's onset (raw)
- `ioi_grid` — Expected IOI from the quantized grid
- `velocity` — Normalized amplitude (0–127 MIDI scale)
- `velocity_curve` — If not null, an array of `{tick_offset, velocity}` points describing the dynamic shape within the note

### 8.3 The Tempo Curve

Layer 3 stores the **local instantaneous tempo** at every beat position as a continuous curve, not just at tempo change events. This is computed from the raw IOI measurements and represents the actual experienced tempo moment by moment.

```json
"tempoCurve": [
  { "tick": 0,    "bpm_local": 91.2  },
  { "tick": 480,  "bpm_local": 90.8  },
  { "tick": 960,  "bpm_local": 89.4  },
  { "tick": 1440, "bpm_local": 88.1  },
  { "tick": 1920, "bpm_local": 92.7  },
  { "tick": 2400, "bpm_local": 94.1  }
]
```

The tempo curve reveals rubato patterns, accelerandos, ritardandos, and phrase-level tempo shaping.

### 8.4 Groove Vector

The **Groove Vector** captures systematic timing tendencies — the consistent way this humming pushes or pulls against the grid. It is computed per-beat-position within the bar.

For a 4/4 time signature, the groove vector has 16 entries (one per 16th note position):

```json
"grooveVector": {
  "resolution"  : "16th",
  "bar_length"  : 4,
  "offsets_ticks": [0, +3, -2, +5, +1, -4, +7, +2, 0, +6, -3, +4, +2, -1, +8, +3],
  "swing_ratio" : 1.18,
  "description" : "Consistently late on offbeats (positions 2, 4, 6...), strong laid-back feel"
}
```

`swing_ratio` captures the ratio of the first 8th note duration to the second in each beat pair. A value of 1.0 is straight 8ths; 1.5 is full swing (triplet swing); 1.18 is a light swung feel.

### 8.5 Rubato Zones

Zones of pronounced tempo deviation are explicitly tagged:

```json
"rubatoZones": [
  {
    "zone_id"       : "rub_001",
    "tick_start"    : 3600,
    "tick_end"      : 4320,
    "type"          : "ritardando",
    "tempo_change"  : -14.2,
    "recovery"      : true,
    "recovery_ticks": 480
  }
]
```

**type** values: `ritardando`, `accelerando`, `fermata`, `a_tempo_delay`, `agogic_accent`

`recovery: true` means the tempo returns to baseline after the zone. `recovery_ticks` is how many ticks after the zone ends before baseline tempo is re-established.

### 8.6 Metric Ambiguity Zones

Humming sometimes drifts between metric interpretations — a passage that could be heard in 3/4 or 6/8, for instance, or a syncopated passage where the beat becomes unclear. These are recorded:

```json
"metricAmbiguityZones": [
  {
    "zone_id"        : "maz_001",
    "tick_start"     : 5760,
    "tick_end"       : 7680,
    "primary_interp" : { "numerator": 6, "denominator": 8, "confidence": 0.61 },
    "alt_interp"     : { "numerator": 3, "denominator": 4, "confidence": 0.55 },
    "note"           : "Ambiguous hemiola figure; both interpretations are viable"
  }
]
```

### 8.7 Rhythmic Motif Registry

Layer 3 also contains a registry of recurring **rhythmic cells** — short rhythmic patterns that repeat. These are identified by their IOI ratio sequence.

```json
"rhythmicMotifs": [
  {
    "motif_id"      : "rm_001",
    "ioi_ratios"    : [1.0, 0.5, 0.5, 1.0],
    "description"   : "Long-short-short-long (heartbeat rhythm)",
    "occurrences"   : [
      { "tick": 0,    "variation": "straight" },
      { "tick": 1920, "variation": "swung"    },
      { "tick": 5760, "variation": "augmented" }
    ]
  }
]
```

---

## 9. Layer 4 — Spectro-Timbral Annotation (STA): Timbre and Envelope Layer

### 9.1 Purpose and Role

Two hummed notes on the same pitch can sound completely different — one bright and resonant, one dark and nasal; one with a clean attack, one with a slow breathy swell; one held with a flat dynamic, one shaped into a swell-and-fade. Standard notation has no way to represent this. Layer 4 captures the **sonic character** of every note event at a level of detail sufficient to reconstruct or synthesize it.

STA deals with the acoustic *quality* of the hum: the timbre, the envelope, the resonance character, the formant profile (the vowel color), and the harmonic content. It is the layer most relevant to synthesis, vocal arrangement, and production.

### 9.2 The STA Note Profile

Every note has a corresponding STA Note Profile:

```json
{
  "sta_id"          : "sta_007",
  "note_id"         : "n_007",
  "envelope"        : { ... },
  "formant_profile" : { ... },
  "harmonic_profile": { ... },
  "nasality_curve"  : { ... },
  "breathiness"     : 0.22,
  "brightness"      : 0.68,
  "roughness"       : 0.05,
  "strain"          : 0.10,
  "registration"    : "chest"
}
```

### 9.3 The Envelope Block

The envelope describes how the note's loudness evolves over time, using a modified ADSR model tailored to humming:

```json
"envelope": {
  "model"          : "ADSR_extended",
  "attack_ms"      : 28,
  "attack_curve"   : "logarithmic",
  "decay_ms"       : 45,
  "decay_curve"    : "exponential",
  "sustain_level"  : 0.82,
  "sustain_shape"  : "slight_swell",
  "release_ms"     : 38,
  "release_curve"  : "exponential",
  "peak_velocity"  : 87,
  "peak_position"  : 0.35,
  "rms_curve"      : [
    { "tick_offset": 0,   "rms": 0.0  },
    { "tick_offset": 30,  "rms": 0.62 },
    { "tick_offset": 60,  "rms": 0.81 },
    { "tick_offset": 120, "rms": 0.83 },
    { "tick_offset": 240, "rms": 0.79 },
    { "tick_offset": 360, "rms": 0.45 }
  ]
}
```

**sustain_shape** values: `flat`, `slight_swell`, `strong_swell`, `slight_diminuendo`, `strong_diminuendo`, `undulating`

### 9.4 The Formant Profile

Formants are the resonant frequency bands of the vocal tract that give a sung or hummed note its characteristic "vowel color." Even in humming, the mouth and throat shape influence the formant structure and thus the timbre.

```json
"formant_profile": {
  "vowel_color"  : "UH",
  "vowel_color_confidence" : 0.78,
  "f1_hz"        : 620,
  "f2_hz"        : 1080,
  "f3_hz"        : 2540,
  "f1_bandwidth" : 80,
  "f2_bandwidth" : 120,
  "f3_bandwidth" : 200,
  "singer_formant_present": false,
  "formant_curve": [
    { "tick_offset": 0,   "f1": 580, "f2": 1020 },
    { "tick_offset": 120, "f1": 640, "f2": 1100 },
    { "tick_offset": 240, "f1": 620, "f2": 1080 }
  ]
}
```

The `vowel_color` field maps to a standard IPA vowel category (see Appendix C for the full mapping table). This is critical for music production — it tells a vocalist, synthesist, or arranger what mouth position and vowel sound will most closely reproduce this note.

**vowel_color values (abbreviated):** `EE`, `IH`, `EH`, `AH`, `AW`, `OH`, `OO`, `UH`, `UW`, `ER`, `HUM_CLOSED`, `HUM_OPEN`

### 9.5 The Harmonic Profile

The harmonic profile describes the relative strengths of the overtones above the fundamental frequency. This is what distinguishes a "thin" hum from a "rich" hum.

```json
"harmonic_profile": {
  "fundamental_strength"  : 0.88,
  "harmonic_rolloff"      : "moderate",
  "harmonic_richness"     : 0.65,
  "odd_even_ratio"        : 1.35,
  "harmonics": [
    { "harmonic": 1, "relative_amplitude": 1.00 },
    { "harmonic": 2, "relative_amplitude": 0.62 },
    { "harmonic": 3, "relative_amplitude": 0.48 },
    { "harmonic": 4, "relative_amplitude": 0.31 },
    { "harmonic": 5, "relative_amplitude": 0.28 },
    { "harmonic": 6, "relative_amplitude": 0.18 },
    { "harmonic": 7, "relative_amplitude": 0.15 },
    { "harmonic": 8, "relative_amplitude": 0.09 }
  ],
  "inharmonicity_coefficient": 0.004
}
```

`odd_even_ratio`: Values above 1.0 indicate stronger odd harmonics (more nasal, clarinet-like character); values below 1.0 indicate stronger even harmonics (more flute-like, round character).

`inharmonicity_coefficient`: A measure of how much the overtones deviate from perfect integer multiples of the fundamental. Higher values (>0.01) indicate a "rougher" or "more strained" hum.

### 9.6 The Nasality Curve

Nasality is a continuous parameter that changes within a note. The nasality curve records this evolution:

```json
"nasality_curve": [
  { "tick_offset": 0,   "nasality": 0.85 },
  { "tick_offset": 120, "nasality": 0.72 },
  { "tick_offset": 240, "nasality": 0.68 },
  { "tick_offset": 360, "nasality": 0.70 }
]
```

### 9.7 Scalar Timbral Parameters

Four scalar parameters provide a quick timbral fingerprint of a note:

| Parameter | Range | Description |
|---|---|---|
| `breathiness` | 0.0–1.0 | Amount of aperiodic noise in the signal (breathy vs. clear) |
| `brightness` | 0.0–1.0 | Spectral centroid position (dark vs. bright/thin) |
| `roughness` | 0.0–1.0 | Degree of voice roughness, creak, or hoarseness |
| `strain` | 0.0–1.0 | Detected vocal effort/strain (relaxed vs. strained) |

### 9.8 Vocal Registration

The `registration` field tags which part of the vocal range the note appears to be placed in:

| Value | Description |
|---|---|
| `chest` | Chest voice (modal register, typical speaking range) |
| `mixed` | Mixed chest-head voice |
| `head` | Head voice (lighter, higher register) |
| `falsetto` | Falsetto (thin, breathy upper register) |
| `fry` | Vocal fry (creaky, very low register) |
| `whistle` | Whistle register (extremely high, rare in humming) |
| `unclear` | Cannot be determined with confidence |

### 9.9 Phrase-Level Timbral Summary

For each phrase (as defined by Layer 5), STA computes a **Phrase Timbral Fingerprint** — a single averaged timbral descriptor for the phrase. This allows quick classification of phrases by character:

```json
"phraseTimbralFingerprint": {
  "phrase_id"           : "phr_002",
  "avg_brightness"      : 0.62,
  "avg_nasality"        : 0.71,
  "avg_breathiness"     : 0.18,
  "avg_roughness"       : 0.04,
  "vowel_color_dominant": "UH",
  "registration_mode"   : "chest",
  "character_tags"      : ["warm", "rounded", "legato", "smooth"],
  "character_tags_neg"  : ["not_bright", "not_strained"]
}
```

---

## 10. Layer 5 — Semantic-Structural Notation (SSN): Musical Meaning Layer

### 10.1 Purpose and Role

Layer 5 is the most abstract layer. It encodes **musical meaning** — not what pitches were hummed, not when they happened, but *why* they sound the way they do musically. It is the "editor's layer": the layer that a human musician or music analyst would fill in after listening carefully to the whole performance.

SSN organizes the hum into a hierarchical structure:

```
Song Section
  └── Phrase Group
        └── Phrase
              └── Sub-phrase / Motif Instance
```

And for each level, it records: harmonic function, emotional character, structural role, and relationships to other elements.

This layer is essential for **song reconstruction**: it tells the composer what the hum is *trying to be* — which part of the song is this, what chord does this phrase imply, how does this melody feel, what motif is being varied here.

### 10.2 The Phrase Object

The Phrase is the fundamental unit of SSN. A phrase is a bounded musical thought — typically 2–8 bars, ending with some sense of punctuation or pause.

```json
{
  "phrase_id"       : "phr_004",
  "tick_start"      : 5760,
  "tick_end"        : 7680,
  "bar_start"       : 7,
  "bar_end"         : 10,
  "phrase_type"     : "consequent",
  "phrase_length"   : "4bar",
  "cadence"         : { ... },
  "harmonic_context": { ... },
  "emotional_profile": { ... },
  "motif_instances" : [ ... ],
  "breath_boundaries": [5760, 6720, 7680],
  "energy_arc"      : "arch",
  "narrative_label" : "Resolving phrase — answers the question of phr_003"
}
```

#### 10.2.1 phrase_type

| Value | Description |
|---|---|
| `antecedent` | A "question" phrase — ends on tension, expects continuation |
| `consequent` | An "answer" phrase — resolves the antecedent |
| `continuation` | A developmental phrase — neither questions nor answers, carries forward |
| `cadential` | A phrase whose primary function is harmonic closure |
| `introductory` | An opening phrase establishing key/mood |
| `transitional` | A phrase connecting two sections |
| `climactic` | The phrase with highest energy, typically the peak of the song |
| `fragmentary` | An incomplete phrase — a motif fragment, not a complete thought |

#### 10.2.2 The Cadence Object

```json
"cadence": {
  "type"          : "authentic",
  "strength"      : "full",
  "tick"          : 7680,
  "approach"      : "stepwise_down",
  "harmonic_motion": "V_to_I",
  "melodic_motion" : "2_to_1",
  "confidence"    : 0.84
}
```

**Cadence types:**

| Type | Description |
|---|---|
| `authentic` | V → I (strongest closure) |
| `half` | Any chord → V (open, expecting more) |
| `plagal` | IV → I (Amen cadence, gentle closure) |
| `deceptive` | V → not-I (surprise, continuation) |
| `interrupted` | Strong move blocked, phrase extends |
| `elided` | Cadence merged with start of next phrase |
| `breath_only` | No harmonic cadence, only breath marks phrase end |
| `melodic_goal` | Cadence by melodic arrival (e.g., reaching tonic note) without harmonic clarity |

**Cadence strength:**

| Value | Description |
|---|---|
| `full` | Complete harmonic + melodic closure |
| `harmonic_only` | Harmonic closure but melody doesn't land on root |
| `melodic_only` | Melody reaches tonic note but harmony unclear |
| `implied` | Neither is clear but the phrase feels complete |
| `weak` | Very minimal sense of ending |

#### 10.2.3 The Harmonic Context Object

Since humming is monophonic, harmonic function is *inferred* from melodic content — the notes present and the structural positions they occupy.

```json
"harmonic_context": {
  "implied_key"     : "G_major",
  "confidence"      : 0.87,
  "bar_by_bar_function": [
    { "bar": 7, "function": "I",   "implied_chord": "Gmaj",  "confidence": 0.91 },
    { "bar": 8, "function": "V7",  "implied_chord": "D7",    "confidence": 0.78 },
    { "bar": 9, "function": "IV",  "implied_chord": "Cmaj",  "confidence": 0.82 },
    { "bar": 10,"function": "I",   "implied_chord": "Gmaj",  "confidence": 0.93 }
  ],
  "harmonic_rhythm" : "one_per_bar",
  "modal_color"     : "major_with_blues_inflection",
  "notes": "Bar 8's implied dominant is supported by the F# leading tone and A neighbor tone."
}
```

**modal_color values:** `major`, `natural_minor`, `harmonic_minor`, `melodic_minor`, `dorian`, `mixolydian`, `lydian`, `phrygian`, `major_pentatonic`, `minor_pentatonic`, `blues`, `major_with_blues_inflection`, `chromatic`, `ambiguous`

#### 10.2.4 The Emotional Profile Object

Emotional descriptors are tags applied to a phrase based on its melodic, timbral, rhythmic, and dynamic content. These are derived from a cross-analysis of all lower layers.

```json
"emotional_profile": {
  "primary_emotion"   : "longing",
  "secondary_emotion" : "tentative",
  "valence"           : -0.3,
  "arousal"           : 0.4,
  "energy_label"      : "moderate",
  "character_tags"    : ["expressive", "searching", "unresolved"],
  "antonym_tags"      : ["not_triumphant", "not_bright"],
  "confidence"        : 0.72
}
```

**valence**: -1.0 (most negative/sad) to +1.0 (most positive/joyful)  
**arousal**: 0.0 (most calm) to 1.0 (most agitated/excited)

**Recognized primary emotion tags:** `joy`, `sadness`, `longing`, `tenderness`, `triumph`, `tension`, `wonder`, `nostalgia`, `determination`, `grief`, `playfulness`, `solemnity`, `anxiety`, `serenity`, `anticipation`, `release`, `ambivalent`

### 10.3 The Motif Registry

The Motif Registry is one of the most powerful features of Layer 5. It identifies recurring melodic cells — the building blocks of the implied song — and tracks every occurrence, variation, and transformation.

#### 10.3.1 Motif Definition

```json
{
  "motif_id"         : "m_001",
  "name"             : "Opening Cell",
  "tick_first_seen"  : 0,
  "defining_segment" : "phr_001:tick_0:tick_480",
  "interval_pattern" : ["+2", "+2", "-1"],
  "contour_code"     : "RISE.GRADUAL.COMPLETE",
  "rhythm_pattern"   : [1.0, 0.5, 0.5, 1.0],
  "abstract_description": "Three stepwise ascending notes followed by a step down",
  "occurrences"      : [ ... ]
}
```

`interval_pattern` is expressed in semitones relative to the first note of the motif.

#### 10.3.2 Motif Occurrences and Transformations

Each occurrence of a motif records:

```json
{
  "occurrence_id"   : "m_001_occ_003",
  "tick_start"      : 5760,
  "phrase_id"       : "phr_004",
  "transformation"  : "sequence_down",
  "transposition"   : -3,
  "rhythmic_variant": "augmented",
  "completeness"    : "full",
  "confidence"      : 0.88
}
```

**transformation types:**

| Type | Description |
|---|---|
| `exact` | Exact repetition (same pitch, same rhythm) |
| `transposition` | Same intervals, different starting pitch |
| `inversion` | Intervals flipped (ascending becomes descending) |
| `retrograde` | Played backwards |
| `augmentation` | Rhythm doubled (twice as slow) |
| `diminution` | Rhythm halved (twice as fast) |
| `sequence_up` | Repeated at a higher pitch level |
| `sequence_down` | Repeated at a lower pitch level |
| `fragmentation` | Only part of the motif used |
| `extension` | Motif extended beyond its normal endpoint |
| `compression` | Motif compressed/shortened |
| `rhythmic_displacement` | Same pitches, different rhythmic position |
| `contour_variant` | Similar shape but with pitch substitutions |
| `free_variant` | Recognizable family resemblance but freely varied |

### 10.4 Song Section Inference

Layer 5 groups phrases into inferred song sections, using a combination of key changes, timbral shifts, motif patterns, and energy arcs.

```json
"songSections": [
  {
    "section_id"    : "sec_001",
    "inferred_label": "verse",
    "confidence"    : 0.79,
    "tick_start"    : 0,
    "tick_end"      : 7680,
    "bar_start"     : 1,
    "bar_end"       : 16,
    "phrases"       : ["phr_001", "phr_002", "phr_003", "phr_004"],
    "key"           : "G_major",
    "avg_energy"    : 0.52,
    "dominant_motifs": ["m_001", "m_002"],
    "notes": "Lower energy, stepwise motion, consistent timbral quality — characteristic verse texture"
  },
  {
    "section_id"    : "sec_002",
    "inferred_label": "chorus",
    "confidence"    : 0.85,
    "tick_start"    : 7680,
    "tick_end"      : 15360,
    "bar_start"     : 17,
    "bar_end"       : 32,
    "phrases"       : ["phr_005", "phr_006", "phr_007", "phr_008"],
    "key"           : "G_major",
    "avg_energy"    : 0.78,
    "dominant_motifs": ["m_001_augmented", "m_003"],
    "notes": "Higher energy, wider ambitus, stronger dynamic profile — characteristic chorus texture"
  }
]
```

**inferred_label values:** `intro`, `verse`, `pre_chorus`, `chorus`, `post_chorus`, `bridge`, `instrumental`, `outro`, `vamp`, `breakdown`, `solo_section`, `unknown`

### 10.5 The Harmonic Skeleton

Layer 5 concludes with a **Harmonic Skeleton** — a bar-by-bar chord chart inferred from the melodic content. This is the single most useful artifact for song reconstruction.

```json
"harmonicSkeleton": {
  "key"   : "G_major",
  "bars"  : [
    { "bar": 1,  "chord": "Gmaj",  "function": "I",    "confidence": 0.93 },
    { "bar": 2,  "chord": "Gmaj",  "function": "I",    "confidence": 0.91 },
    { "bar": 3,  "chord": "Cmaj",  "function": "IV",   "confidence": 0.84 },
    { "bar": 4,  "chord": "D7",    "function": "V7",   "confidence": 0.88 },
    { "bar": 5,  "chord": "Gmaj",  "function": "I",    "confidence": 0.90 },
    { "bar": 6,  "chord": "Emin",  "function": "vi",   "confidence": 0.76 },
    { "bar": 7,  "chord": "Cmaj",  "function": "IV",   "confidence": 0.82 },
    { "bar": 8,  "chord": "D7",    "function": "V7",   "confidence": 0.89 }
  ],
  "alternative_readings": [
    { "bar": 6, "chord_alt": "Gmaj/B", "function_alt": "I6", "confidence": 0.48 }
  ],
  "notes": "Standard I-IV-V-vi progression. Bar 6 could be vi or I6 — melody note B is ambiguous."
}
```

---

## 11. The HumScore Master Schema (JSON)

The complete HumScore document is a single JSON object. Below is the full schema definition.

```json
{
  "$schema"     : "https://humscore.io/schema/v1.0.0",
  "document_type": "HumScore",
  "version"     : "1.0.0",

  "metadata": {
    "session_id"   : "string (UUID)",
    "created_at"   : "ISO 8601 datetime",
    "title"        : "string",
    "hummer_id"    : "string",
    "recording_ref": "string (optional path/URI to source audio)",
    "duration_ms"  : "number",
    "total_ticks"  : "number",
    "ppq"          : "integer (default 480)",
    "layers_present": ["layer0", "layer1", "layer2", "layer3", "layer4", "layer5"],
    "generation_notes": "string"
  },

  "timeline": {
    "tempoMap"          : [ /* tempo map entries */ ],
    "timeSignatureMap"  : [ /* time sig entries */ ],
    "keyMap"            : [ /* key map entries */ ],
    "barMap"            : [ /* bar map entries */ ],
    "clockMap"          : [ /* tick-to-ms entries */ ]
  },

  "layers": {

    "layer0": {
      "abc_text"  : "string (complete ABC notation)",
      "note_ids"  : [ /* ordered list of note IDs matching ABC notes */ ]
    },

    "layer1": {
      "notes"     : [ /* HumScript Note Objects */ ],
      "breaths"   : [ /* Breath Mark Objects */ ],
      "ornaments" : [ /* Ornament Detail Blocks */ ],
      "custom_extensions": {}
    },

    "layer2": {
      "segments"          : [ /* CVN Segment Objects */ ],
      "phraseContours"    : [ /* Phrase-Level Contour Objects */ ],
      "similarityMatrix"  : [ /* pairwise CSI values */ ],
      "custom_extensions" : {}
    },

    "layer3": {
      "events"              : [ /* MRN Event Objects */ ],
      "tempoCurve"          : [ /* tempo curve points */ ],
      "grooveVector"        : { /* groove vector */ },
      "rubatoZones"         : [ /* rubato zone objects */ ],
      "metricAmbiguityZones": [ /* ambiguity zone objects */ ],
      "rhythmicMotifs"      : [ /* rhythmic motif objects */ ],
      "custom_extensions"   : {}
    },

    "layer4": {
      "noteProfiles"           : [ /* STA Note Profile objects */ ],
      "phraseTimbralFingerprints": [ /* phrase fingerprint objects */ ],
      "custom_extensions"      : {}
    },

    "layer5": {
      "phrases"          : [ /* Phrase Objects */ ],
      "motifRegistry"    : [ /* Motif objects */ ],
      "songSections"     : [ /* Song Section objects */ ],
      "harmonicSkeleton" : { /* Harmonic Skeleton object */ },
      "overallProfile"   : {
        "inferred_genre"    : "string",
        "genre_confidence"  : "number",
        "overall_key"       : "string",
        "overall_tempo_feel": "string",
        "overall_character" : "string",
        "song_form_inferred": "string",
        "notes"             : "string"
      },
      "custom_extensions": {}
    }
  }
}
```

---

## 12. Inter-Layer Synchronization Protocol

### 12.1 The Note Identity Chain

Every note has a single `note_id` (format: `n_NNN`, e.g., `n_007`) that persists across all layers. Given a note_id, a system can look up that note's data in any layer:

| Layer | Field containing note_id |
|---|---|
| Layer 0 | `layer0.note_ids[i]` |
| Layer 1 | `layer1.notes[i].note_id` |
| Layer 2 | Derived from segment tick ranges |
| Layer 3 | `layer3.events[i].note_id` |
| Layer 4 | `layer4.noteProfiles[i].note_id` |
| Layer 5 | Via phrase membership |

### 12.2 Tick Anchoring

All events in all layers are anchored to the Common Timeline via tick position. This enables:

- **Note-to-note queries:** "What is the timbre (STA) of the note that has the highest timing deviation (MRN)?"
- **Phrase-level queries:** "What is the groove vector (MRN) during the chorus section (SSN)?"
- **Cross-layer correlation:** "Are notes with high breathiness (STA) associated with late onsets (MRN)?"

### 12.3 Phrase ID Propagation

Phrase IDs from Layer 5 are propagated down into Layers 3 and 4 for phrase-level aggregation queries. A `phrase_id` field appears in:
- `layer3.rubatoZones` (which phrase contains this zone)
- `layer4.phraseTimbralFingerprints` (maps to a phrase)

### 12.4 Validation Rules

A valid HumScore document must satisfy:

1. Every `note_id` in Layer 1 must exist in `layer0.note_ids`
2. Every `note_id` in Layer 3 must exist in Layer 1
3. Every `note_id` in Layer 4 must exist in Layer 1
4. All tick values must be within `[0, metadata.total_ticks]`
5. All `bar:beat` references must resolve correctly via `barMap`
6. The `layer0.note_ids` list must have the same count as Layer 1 notes
7. `motifRegistry` occurrence `tick_start` values must fall within the named `phrase_id`'s tick range
8. `harmonicSkeleton.bars` must have one entry per bar in the `barMap`

---

## 13. Conflict Resolution and Layer Precedence

When layers contain contradictory information (which can happen when analysis at different levels disagrees), the following precedence rules apply:

### 13.1 Pitch Conflicts

If Layer 1's `pitch_dev` corrected note disagrees with Layer 5's implied harmonic function:

- **Trust Layer 1** for note-level representation (what was actually hummed)
- **Flag a conflict** in Layer 5's harmonic context with a `pitch_conflict: true` field
- **Do not** override Layer 1 data to satisfy Layer 5 analysis

### 13.2 Timing Conflicts

If Layer 0's quantized rhythmic notation suggests a pattern that Layer 3's raw timing contradicts heavily (deviation > 30%):

- **Trust Layer 3** for timing reconstruction
- **Flag** the relevant note in Layer 0 with an `%%hs-timing-conflict` comment
- The quantization in Layer 0 is acknowledged as an approximation

### 13.3 Structural Conflicts

If Layer 5's section inference is uncertain (confidence < 0.65):

- The `inferred_label` is marked with a `low_confidence: true` field
- Alternative labels are listed in an `alternatives` array
- The data is never deleted; only confidence is flagged

### 13.4 Timbral vs. Harmonic Conflicts

If Layer 4's vowel color suggests a note should sound like an "EE" vowel but Layer 5's emotional profile suggests a dark, warm character:

- Both are preserved without conflict; these operate in different domains
- Production notes in Layer 4's fingerprint may note the cross-domain tension

---

## 14. Song Reconstruction Guide

This section describes the recommended workflow for using a HumScore document to construct a full song.

### 14.1 Reconstruction Priority Stack

When making decisions about the reconstructed song, consult layers in this priority order depending on the question:

| Decision Type | Primary Layer | Secondary Layer | Tertiary Layer |
|---|---|---|---|
| What note to write | Layer 1 (corrected) | Layer 0 (scaffold) | Layer 2 (contour) |
| How long the note is | Layer 3 (raw timing) | Layer 0 (quantized) | — |
| What chord to imply | Layer 5 (skeleton) | Layer 1 (notes present) | — |
| How to articulate | Layer 1 (onset/offset) | Layer 4 (envelope) | — |
| What register/instrument | Layer 4 (registration) | Layer 5 (character tags) | — |
| Song structure | Layer 5 (sections) | Layer 5 (phrases) | Layer 3 (energy) |
| Arrangement feel | Layer 3 (groove) | Layer 4 (character) | Layer 5 (emotion) |
| Ornaments | Layer 1 (ornament blocks) | Layer 0 (ABC decorations) | — |

### 14.2 Step-by-Step Reconstruction Workflow

#### Step 1: Establish the Framework
Start with Layer 0 to get a readable melody skeleton. Import the ABC text into any notation software. This gives you a rough but complete draft.

#### Step 2: Correct Pitch
Apply Layer 1 `pitch_dev` values to adjust note pitches where deviations are significant (>25 cents). Consider whether large deviations indicate intentional microtonal expression or should be snapped to adjacent notes.

#### Step 3: Build the Chord Chart
Use `layer5.harmonicSkeleton` as your chord chart. Cross-reference with Layer 1 notes to resolve ambiguous chords. Pay attention to `alternative_readings` for bars where the harmony is genuinely uncertain.

#### Step 4: Restore Timing Feel
Apply Layer 3's `grooveVector` and `tempoCurve` to restore the human feel of the performance. The groove vector tells you how to push/pull notes from the grid. The rubato zones identify where tempo changes are musically intentional.

#### Step 5: Assign Articulation
Use Layer 1's `onset_quality` and `offset_quality` to add articulation markings. `INTO_NEXT` → legato slurs. `FALLOFF` → portamento markings. `SCOOP` → grace note before the main note. `CLEAN` + `CUTOFF_HARD` → staccato.

#### Step 6: Write Dynamics
Use Layer 4's `envelope.sustain_shape` and `rms_curve` to write dynamic markings within phrases. Use `layer4.phraseTimbralFingerprints[i].avg_brightness` and `character_tags` to guide orchestration and instrument choice.

#### Step 7: Identify Motifs and Structure
Use `layer5.motifRegistry` to identify the song's thematic material. Map where each motif appears, where it's transformed, and build the song architecture from `layer5.songSections`.

#### Step 8: Add Harmony
Flesh out the chord chart into a full arrangement. Use `layer5.phrases[i].harmonic_context.modal_color` to choose the harmonic language. Use emotional profiles to guide harmonic density (tense phrases → complex chords; simple phrases → open chords).

#### Step 9: Ornament
Re-introduce ornaments from Layer 1 `ORNAMENT` blocks. Use Layer 2 contour data to guide where fills, runs, or ornamental passages should happen in the accompaniment.

#### Step 10: Validate
Cross-check your reconstructed score against the CVN phrase contours (Layer 2). The melodic shape of every phrase in your score should closely match the corresponding phrase contour. If a phrase's contour shape doesn't match, the reconstruction has diverged from the original intent.

---

## 15. Edge Cases and Special Conditions

### 15.1 Unvoiced Pitch Events

Occasionally a hum will include unvoiced periods where the hummer is clearly communicating rhythm or texture without a clear pitch. These are represented in all layers as:

- Layer 0: `z` rest token with appropriate duration
- Layer 1: A note marked `pitch_class: "NOISE"` with `onset_quality: BREATHY` and full timbral annotation in Layer 4
- Layer 3: Full timing event with `type: "unpitched"` flag
- Layer 4: Breathiness = 1.0, harmonic_richness = 0.0

### 15.2 Pitch Slides with No Discrete Notes

Some passages of humming are pure portamento — continuous pitch motion from one landmark to another with no discrete note articulation between them. These are represented as:

- Layer 0: Two notes connected by an ABC slur
- Layer 1: The intermediate note events are `virtual_note: true`, generated by the quantization process
- Layer 2: A single CVN segment spanning the entire passage with appropriate curvature

### 15.3 Multiphonics and Throat Singing

In rare cases, a hummer may produce two simultaneous pitches (circular breathing, throat singing technique). When detected:

- Both pitches receive separate `note_id`s marked `register: "overtone"` and `register: "fundamental"`
- Layer 1 contains a `multiphonic: true` flag with a `multiphonic_group_id` linking the two notes
- Layer 4 contains separate profiles for each component

### 15.4 Very Long Held Notes

Notes held for more than 8 beats create analytical challenges because vibrato, timbre, and dynamics evolve significantly. For notes longer than 1920 ticks:

- Layer 3 divides the note into **sub-events** of 480 ticks each, each with their own velocity
- Layer 4 provides curve data at higher resolution (one point per 60 ticks minimum)
- Layer 1 provides a full `pitch_dev_curve` with at least 8 points

### 15.5 Ambiguous Start and End

Humming often trails off at the start and end. The first and last notes may be below the confidence threshold for pitch detection. These are flagged:

- `confidence` below 0.5 on any Layer 3 event triggers a `low_confidence: true` flag across all layers for that note
- Layer 0 replaces the note with a grace note or `!pppp!` marking
- Layer 5 includes a `boundary_notes_uncertain: true` flag on the enclosing phrase

### 15.6 No Clear Key or Mode

For highly chromatic or atonal humming where key cannot be reliably inferred:

- Layer 5 `keyMap` entries with `confidence` below 0.4 are marked `key: "ambiguous"`
- `layer5.overallProfile.inferred_genre` is set to `"chromatic_or_atonal"`
- `harmonicSkeleton.bars` entries receive `chord: null` and `function: "none"` where harmony is not inferrable

---

## Appendix A — Full HumScript Token Reference

### Onset Quality Tokens
| Token | Abbreviation | Description |
|---|---|---|
| `CLEAN` | CL | Direct onset, no approach |
| `GLIDE_FROM` | GF | Pitch rises from below |
| `FALL_INTO` | FI | Pitch falls from above |
| `GLOTTAL_HARD` | GH | Hard glottal stop attack |
| `GLOTTAL_SOFT` | GS | Soft glottal, breathy start |
| `BREATHY` | BR | Breath noise precedes pitch |
| `SCOOP` | SC | Upward scoop to target pitch |
| `DIP` | DP | Downward dip to target pitch |
| `FLUTTER_ONSET` | FL | Onset from vibrato already in motion |
| `PRESSED` | PR | Hyperfunctional, tight onset |

### Offset Quality Tokens
| Token | Abbreviation | Description |
|---|---|---|
| `CLEAN` | CL | Neutral, clean release |
| `FADE` | FD | Dynamic fade |
| `FALLOFF` | FO | Pitch drops at end |
| `LIFT` | LI | Pitch rises at end |
| `CUTOFF_HARD` | CH | Abrupt cutoff |
| `INTO_NEXT` | IN | Legato to next note |
| `TRAIL` | TR | Note bleeds past its duration |
| `SWALLOW` | SW | Note ends with a gulp/swallow sound |
| `NASAL_CLOSE` | NC | Mouth closes into nasal consonant |

### Dynamic Shape Tokens
| Token | Description |
|---|---|
| `flat` | Constant dynamic throughout |
| `swell` | Soft → loud → soft |
| `diminuendo` | Loud → soft |
| `crescendo` | Soft → loud |
| `accent_front` | Accent at start, falls off |
| `accent_back` | Builds to accent at end |
| `accent_mid` | Accent at center |
| `terraced` | Sudden step louder or quieter within note |

---

## Appendix B — CVN Direction Primitives

The complete gesture class hierarchy:

```
GESTURE_CLASSES:
  RISE
    RISE.GRADUAL        — steady ascending motion
    RISE.RAPID          — fast upward motion
    RISE.ANGULAR        — stepwise with corners
    RISE.SMOOTH         — arched, curved upward motion
  FALL
    FALL.GRADUAL        — steady descending motion
    FALL.RAPID          — fast downward motion
    FALL.ANGULAR        — stepwise descending
    FALL.SMOOTH         — curved downward motion
  HOLD
    HOLD.EXACT          — pitch perfectly stable
    HOLD.APPROXIMATE    — pitch nominally stable with small drift
    HOLD.VIBRATO        — nominally stable with oscillation
  ARCH
    ARCH.SYMMETRIC      — equal rise and fall
    ARCH.EARLY_PEAK     — peak in first third
    ARCH.LATE_PEAK      — peak in last third
  VALLEY
    VALLEY.SYMMETRIC    — equal fall and rise
    VALLEY.EARLY_TROUGH — trough in first third
    VALLEY.LATE_TROUGH  — trough in last third
  LEAP_UP
    LEAP_UP.CLEAN       — lands cleanly on target
    LEAP_UP.OVERSHOOT   — momentarily above target
    LEAP_UP.UNDERSHOOT  — approaches target from below
  LEAP_DOWN
    LEAP_DOWN.CLEAN     — lands cleanly on target
    LEAP_DOWN.OVERSHOOT — momentarily below target
    LEAP_DOWN.UNDERSHOOT— approaches target from above
  OSCILLATE
    OSCILLATE.TRILL     — rapid, small-interval oscillation
    OSCILLATE.VIBRATO   — periodic pitch oscillation on held note
    OSCILLATE.WAVE      — slow, large oscillation

QUALIFIERS:
  PARTIAL    — gesture does not fully complete (cut off or faded)
  COMPLETE   — gesture resolves fully
  EXTENDED   — gesture takes longer than expected
  COMPRESSED — gesture is rushed
```

---

## Appendix C — STA Formant Vowel Color Table

| Token | IPA Symbol | Example Word | F1 (Hz) Range | F2 (Hz) Range |
|---|---|---|---|---|
| `EE` | /iː/ | "see" | 280–370 | 2200–2800 |
| `IH` | /ɪ/ | "sit" | 380–480 | 1800–2200 |
| `EH` | /ɛ/ | "bed" | 520–650 | 1600–2000 |
| `AE` | /æ/ | "cat" | 650–800 | 1500–2000 |
| `AH` | /ɑ/ | "father" | 700–900 | 900–1300 |
| `AW` | /ɔ/ | "saw" | 560–680 | 700–1000 |
| `OH` | /oʊ/ | "go" | 400–500 | 700–1000 |
| `OO` | /uː/ | "too" | 280–380 | 800–1200 |
| `UH` | /ʌ/ | "cup" | 580–720 | 1000–1400 |
| `UW` | /ʊ/ | "book" | 380–480 | 1000–1400 |
| `ER` | /ɜː/ | "bird" | 480–580 | 1400–1700 |
| `HUM_CLOSED` | — | Lips-closed hum | 280–400 | 900–1100 |
| `HUM_OPEN` | — | Open-mouth hum | 480–650 | 1000–1500 |
| `HUM_NASAL` | — | Deep nasal hum | 200–320 | 800–1000 |

---

## Appendix D — SSN Harmonic Function Tags

Full list of recognized harmonic function codes used in the SSN layer:

| Code | Roman Numeral | Description |
|---|---|---|
| `I` | I | Tonic (major) |
| `i` | i | Tonic (minor) |
| `ii` | ii | Supertonic |
| `II` | II | Secondary dominant / major supertonic |
| `iii` | iii | Mediant |
| `III` | III | Mediant (relative major in minor key) |
| `IV` | IV | Subdominant |
| `iv` | iv | Subdominant (minor) |
| `V` | V | Dominant |
| `V7` | V7 | Dominant seventh |
| `V/V` | V/V | Secondary dominant (of the dominant) |
| `vi` | vi | Submediant |
| `VII` | VII | Subtonic (in minor) |
| `viidim` | vii° | Leading-tone diminished |
| `bVII` | ♭VII | Flat seventh (borrowed, mixolydian flavor) |
| `bVI` | ♭VI | Flat sixth (borrowed, Aeolian flavor) |
| `bIII` | ♭III | Flat third (borrowed) |
| `N6` | N6 | Neapolitan sixth |
| `Aug6` | It/Ger/Fr | Augmented sixth chord |
| `pedal_I` | I pedal | Pedal point on tonic |
| `pedal_V` | V pedal | Pedal point on dominant |
| `none` | — | No harmonic function inferrable |

---

## Appendix E — Complete Worked Example

The following is a complete HumScore document for a short 4-bar hummed phrase: "G G A B | c B A G | A B c d | G4"

```json
{
  "$schema"      : "https://humscore.io/schema/v1.0.0",
  "document_type": "HumScore",
  "version"      : "1.0.0",

  "metadata": {
    "session_id"    : "f4a2c8e1-3b7d-4f9a-a2c1-d5e6f0b8a3c2",
    "created_at"    : "2026-05-12T14:32:00Z",
    "title"         : "Worked Example — 4-bar G major phrase",
    "hummer_id"     : "anonymous",
    "recording_ref" : null,
    "duration_ms"   : 10434,
    "total_ticks"   : 7680,
    "ppq"           : 480,
    "layers_present": ["layer0", "layer1", "layer2", "layer3", "layer4", "layer5"],
    "generation_notes": "Manually composed worked example for spec illustration"
  },

  "timeline": {
    "tempoMap": [
      { "tick": 0,    "bpm": 92.0, "confidence": 0.95, "interpolation": "linear" },
      { "tick": 3840, "bpm": 89.5, "confidence": 0.88, "interpolation": "linear" }
    ],
    "timeSignatureMap": [
      { "tick": 0, "numerator": 4, "denominator": 4, "inferred": false }
    ],
    "keyMap": [
      { "tick": 0, "key": "G", "mode": "major", "confidence": 0.91 }
    ],
    "barMap": [
      { "bar": 1, "tick": 0    },
      { "bar": 2, "tick": 1920 },
      { "bar": 3, "tick": 3840 },
      { "bar": 4, "tick": 5760 }
    ]
  },

  "layers": {

    "layer0": {
      "abc_text": "X:1\nT:Worked Example\nM:4/4\nL:1/8\nQ:1/4=92\nK:G\n%%humscore-version 1.0.0\n|G2 G2 A2 B2|c2 B2 A2 G2|A2 B2 c2 d2|G8|",
      "note_ids": [
        "n_001","n_002","n_003","n_004",
        "n_005","n_006","n_007","n_008",
        "n_009","n_010","n_011","n_012",
        "n_013"
      ]
    },

    "layer1": {
      "notes": [
        { "note_id":"n_001", "pitch_dev":+18, "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "vibrato":null, "portamento":null,
          "dynamic":{"level":"mp","shape":"flat"}, "nasality":0.75 },
        { "note_id":"n_002", "pitch_dev":+16, "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "vibrato":null, "portamento":null,
          "dynamic":{"level":"mp","shape":"swell"}, "nasality":0.73 },
        { "note_id":"n_003", "pitch_dev":-8,  "onset_quality":"SCOOP",
          "offset_quality":"INTO_NEXT",
          "portamento":{"present":true,"direction":"up","duration":40,
                        "curve":"logarithmic","start_pitch_cents":-30,
                        "end_pitch_cents":0},
          "dynamic":{"level":"mf","shape":"flat"}, "nasality":0.68 },
        { "note_id":"n_004", "pitch_dev":+5,  "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "vibrato":{"present":true,"onset_delay":180,"rate_hz":5.8,
                     "depth_cents":35,"depth_curve":"growing","rate_curve":"steady",
                     "shape":"sine"},
          "dynamic":{"level":"mf","shape":"crescendo"}, "nasality":0.65 },
        { "note_id":"n_005", "pitch_dev":-12, "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "vibrato":{"present":true,"onset_delay":120,"rate_hz":6.1,
                     "depth_cents":42,"depth_curve":"steady","rate_curve":"steady",
                     "shape":"sine"},
          "dynamic":{"level":"f","shape":"accent_front"}, "nasality":0.60 },
        { "note_id":"n_006", "pitch_dev":+10, "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "dynamic":{"level":"mf","shape":"flat"}, "nasality":0.62 },
        { "note_id":"n_007", "pitch_dev":-5,  "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "dynamic":{"level":"mf","shape":"flat"}, "nasality":0.65 },
        { "note_id":"n_008", "pitch_dev":+20, "onset_quality":"CLEAN",
          "offset_quality":"FALLOFF",
          "dynamic":{"level":"mp","shape":"diminuendo"}, "nasality":0.72 },
        { "note_id":"n_009", "pitch_dev":-3,  "onset_quality":"SCOOP",
          "offset_quality":"INTO_NEXT",
          "dynamic":{"level":"mf","shape":"crescendo"}, "nasality":0.66 },
        { "note_id":"n_010", "pitch_dev":+8,  "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "dynamic":{"level":"mf","shape":"flat"}, "nasality":0.64 },
        { "note_id":"n_011", "pitch_dev":-10, "onset_quality":"CLEAN",
          "offset_quality":"INTO_NEXT",
          "dynamic":{"level":"f","shape":"swell"}, "nasality":0.60 },
        { "note_id":"n_012", "pitch_dev":+15, "onset_quality":"CLEAN",
          "offset_quality":"LIFT",
          "vibrato":{"present":true,"onset_delay":240,"rate_hz":5.5,
                     "depth_cents":28,"depth_curve":"fading","rate_curve":"decelerating",
                     "shape":"sine"},
          "dynamic":{"level":"f","shape":"diminuendo"}, "nasality":0.58 },
        { "note_id":"n_013", "pitch_dev":+22, "onset_quality":"GLIDE_FROM",
          "offset_quality":"FADE",
          "vibrato":{"present":true,"onset_delay":480,"rate_hz":5.2,
                     "depth_cents":50,"depth_curve":"arch","rate_curve":"steady",
                     "shape":"sine"},
          "dynamic":{"level":"mf","shape":"swell"}, "nasality":0.78 }
      ],
      "breaths": [
        { "tick": 1920, "duration": 85, "type": "catch_breath", "after_note": "n_004" },
        { "tick": 3840, "duration": 110,"type": "normal",       "after_note": "n_008" },
        { "tick": 5760, "duration": 92, "type": "catch_breath", "after_note": "n_012" }
      ],
      "ornaments": [],
      "custom_extensions": {}
    },

    "layer2": {
      "segments": [
        { "seg_id":"cvn_001","tick_start":0,   "tick_end":960,
          "pitch_start":7.18,"pitch_end":7.16,
          "curvature":{"type":"straight","strength":0.1},
          "gesture_class":"HOLD.APPROXIMATE.COMPLETE",
          "confidence":0.94,"energy":0.60,"anchored":true },
        { "seg_id":"cvn_002","tick_start":960, "tick_end":1440,
          "pitch_start":7.16,"pitch_end":8.92,
          "curvature":{"type":"concave_down","strength":0.45},
          "gesture_class":"RISE.SMOOTH.COMPLETE",
          "confidence":0.91,"energy":0.68,"anchored":true },
        { "seg_id":"cvn_003","tick_start":1440,"tick_end":1920,
          "pitch_start":8.92,"pitch_end":11.05,
          "curvature":{"type":"straight","strength":0.2},
          "gesture_class":"RISE.GRADUAL.COMPLETE",
          "confidence":0.89,"energy":0.75,"anchored":true },
        { "seg_id":"cvn_004","tick_start":1920,"tick_end":2880,
          "pitch_start":11.05,"pitch_end":9.10,
          "curvature":{"type":"concave_up","strength":0.55},
          "gesture_class":"FALL.SMOOTH.COMPLETE",
          "confidence":0.92,"energy":0.70,"anchored":true },
        { "seg_id":"cvn_005","tick_start":2880,"tick_end":3840,
          "pitch_start":9.10,"pitch_end":7.20,
          "curvature":{"type":"straight","strength":0.15},
          "gesture_class":"FALL.GRADUAL.COMPLETE",
          "confidence":0.88,"energy":0.60,"anchored":true },
        { "seg_id":"cvn_006","tick_start":3840,"tick_end":5280,
          "pitch_start":7.20,"pitch_end":14.15,
          "curvature":{"type":"concave_down","strength":0.60},
          "gesture_class":"RISE.SMOOTH.EXTENDED",
          "confidence":0.87,"energy":0.82,"anchored":true },
        { "seg_id":"cvn_007","tick_start":5280,"tick_end":5760,
          "pitch_start":14.15,"pitch_end":14.15,
          "curvature":{"type":"oscillating","strength":0.5},
          "gesture_class":"HOLD.VIBRATO.PARTIAL",
          "confidence":0.84,"energy":0.85,"anchored":true },
        { "seg_id":"cvn_008","tick_start":5760,"tick_end":7680,
          "pitch_start":7.22,"pitch_end":7.22,
          "curvature":{"type":"oscillating","strength":0.7},
          "gesture_class":"HOLD.VIBRATO.EXTENDED",
          "confidence":0.93,"energy":0.72,"anchored":true }
      ],
      "phraseContours": [
        { "plc_id":"plc_001","tick_start":0,"tick_end":1920,
          "segments":["cvn_001","cvn_002","cvn_003"],
          "shape_code":"ARC_UP","net_motion":+3.87,
          "ambitus":{"lowest_pitch":7.16,"highest_pitch":11.05,"range_semitones":3.89},
          "shape_summary":"Steady on G, gentle rise to A, step to B — ascending line" },
        { "plc_id":"plc_002","tick_start":1920,"tick_end":3840,
          "segments":["cvn_004","cvn_005"],
          "shape_code":"ARC_DOWN","net_motion":-3.85,
          "ambitus":{"lowest_pitch":7.20,"highest_pitch":11.05,"range_semitones":3.85},
          "shape_summary":"Mirror of plc_001 — falling from c back down to G" },
        { "plc_id":"plc_003","tick_start":3840,"tick_end":5760,
          "segments":["cvn_006","cvn_007"],
          "shape_code":"RISE_PLATEAU","net_motion":+6.95,
          "ambitus":{"lowest_pitch":7.20,"highest_pitch":14.15,"range_semitones":6.95},
          "shape_summary":"Wide ascending sweep to d, held with vibrato — climactic phrase" },
        { "plc_id":"plc_004","tick_start":5760,"tick_end":7680,
          "segments":["cvn_008"],
          "shape_code":"FLAT","net_motion":0.0,
          "ambitus":{"lowest_pitch":7.22,"highest_pitch":7.22,"range_semitones":0.0},
          "shape_summary":"Long held G with vibrato — resolution and release" }
      ],
      "custom_extensions": {}
    },

    "layer3": {
      "events": [
        {"event_id":"mrn_001","note_id":"n_001","tick_onset_raw":2,"tick_onset_grid":0,"tick_offset_raw":478,"tick_offset_grid":480,"onset_deviation":+2,"offset_deviation":-2,"duration_raw":476,"duration_grid":480,"duration_ratio":0.992,"ioi_raw":481,"ioi_grid":480,"velocity":68},
        {"event_id":"mrn_002","note_id":"n_002","tick_onset_raw":483,"tick_onset_grid":480,"tick_offset_raw":959,"tick_offset_grid":960,"onset_deviation":+3,"offset_deviation":-1,"duration_raw":476,"duration_grid":480,"duration_ratio":0.992,"ioi_raw":478,"ioi_grid":480,"velocity":72},
        {"event_id":"mrn_003","note_id":"n_003","tick_onset_raw":961,"tick_onset_grid":960,"tick_offset_raw":1441,"tick_offset_grid":1440,"onset_deviation":+1,"offset_deviation":+1,"duration_raw":480,"duration_grid":480,"duration_ratio":1.000,"ioi_raw":479,"ioi_grid":480,"velocity":76},
        {"event_id":"mrn_004","note_id":"n_004","tick_onset_raw":1440,"tick_onset_grid":1440,"tick_offset_raw":1924,"tick_offset_grid":1920,"onset_deviation":0,"offset_deviation":+4,"duration_raw":484,"duration_grid":480,"duration_ratio":1.008,"ioi_raw":482,"ioi_grid":480,"velocity":80},
        {"event_id":"mrn_005","note_id":"n_005","tick_onset_raw":1922,"tick_onset_grid":1920,"tick_offset_raw":2399,"tick_offset_grid":2400,"onset_deviation":+2,"offset_deviation":-1,"duration_raw":477,"duration_grid":480,"duration_ratio":0.994,"ioi_raw":480,"ioi_grid":480,"velocity":88},
        {"event_id":"mrn_006","note_id":"n_006","tick_onset_raw":2402,"tick_onset_grid":2400,"tick_offset_raw":2879,"tick_offset_grid":2880,"onset_deviation":+2,"offset_deviation":-1,"duration_raw":477,"duration_grid":480,"duration_ratio":0.994,"ioi_raw":476,"ioi_grid":480,"velocity":82},
        {"event_id":"mrn_007","note_id":"n_007","tick_onset_raw":2878,"tick_onset_grid":2880,"tick_offset_raw":3357,"tick_offset_grid":3360,"onset_deviation":-2,"offset_deviation":-3,"duration_raw":479,"duration_grid":480,"duration_ratio":0.998,"ioi_raw":482,"ioi_grid":480,"velocity":78},
        {"event_id":"mrn_008","note_id":"n_008","tick_onset_raw":3360,"tick_onset_grid":3360,"tick_offset_raw":3852,"tick_offset_grid":3840,"onset_deviation":0,"offset_deviation":+12,"duration_raw":492,"duration_grid":480,"duration_ratio":1.025,"ioi_raw":488,"ioi_grid":480,"velocity":68},
        {"event_id":"mrn_009","note_id":"n_009","tick_onset_raw":3848,"tick_onset_grid":3840,"tick_offset_raw":4319,"tick_offset_grid":4320,"onset_deviation":+8,"offset_deviation":-1,"duration_raw":471,"duration_grid":480,"duration_ratio":0.981,"ioi_raw":474,"ioi_grid":480,"velocity":76},
        {"event_id":"mrn_010","note_id":"n_010","tick_onset_raw":4322,"tick_onset_grid":4320,"tick_offset_raw":4802,"tick_offset_grid":4800,"onset_deviation":+2,"offset_deviation":+2,"duration_raw":480,"duration_grid":480,"duration_ratio":1.000,"ioi_raw":480,"ioi_grid":480,"velocity":82},
        {"event_id":"mrn_011","note_id":"n_011","tick_onset_raw":4802,"tick_onset_grid":4800,"tick_offset_raw":5284,"tick_offset_grid":5280,"onset_deviation":+2,"offset_deviation":+4,"duration_raw":482,"duration_grid":480,"duration_ratio":1.004,"ioi_raw":476,"ioi_grid":480,"velocity":90},
        {"event_id":"mrn_012","note_id":"n_012","tick_onset_raw":5278,"tick_onset_grid":5280,"tick_offset_raw":5768,"tick_offset_grid":5760,"onset_deviation":-2,"offset_deviation":+8,"duration_raw":490,"duration_grid":480,"duration_ratio":1.021,"ioi_raw":488,"ioi_grid":480,"velocity":86},
        {"event_id":"mrn_013","note_id":"n_013","tick_onset_raw":5766,"tick_onset_grid":5760,"tick_offset_raw":7694,"tick_offset_grid":7680,"onset_deviation":+6,"offset_deviation":+14,"duration_raw":1928,"duration_grid":1920,"duration_ratio":1.004,"ioi_raw":null,"ioi_grid":null,"velocity":78,
          "velocity_curve":[
            {"tick_offset":0,"velocity":66},
            {"tick_offset":480,"velocity":78},
            {"tick_offset":960,"velocity":82},
            {"tick_offset":1440,"velocity":74},
            {"tick_offset":1920,"velocity":55}
          ]
        }
      ],
      "tempoCurve": [
        {"tick":0,    "bpm_local":92.4},
        {"tick":480,  "bpm_local":92.1},
        {"tick":960,  "bpm_local":91.8},
        {"tick":1440, "bpm_local":91.5},
        {"tick":1920, "bpm_local":90.8},
        {"tick":2400, "bpm_local":90.4},
        {"tick":2880, "bpm_local":89.8},
        {"tick":3360, "bpm_local":89.2},
        {"tick":3840, "bpm_local":90.1},
        {"tick":4320, "bpm_local":91.2},
        {"tick":4800, "bpm_local":92.0},
        {"tick":5280, "bpm_local":92.8},
        {"tick":5760, "bpm_local":90.2},
        {"tick":6240, "bpm_local":88.5},
        {"tick":6720, "bpm_local":87.0},
        {"tick":7200, "bpm_local":85.5}
      ],
      "grooveVector": {
        "resolution":"8th",
        "bar_length":4,
        "offsets_ticks":[0,+3,-1,+4,+2,-2,+5,+2],
        "swing_ratio":1.06,
        "description":"Consistently slightly late on offbeats; very light swing feel"
      },
      "rubatoZones": [
        { "zone_id":"rub_001","tick_start":5760,"tick_end":7680,
          "type":"ritardando","tempo_change":-7.0,"recovery":false,
          "notes":"Final long G slows gradually — natural dying phrase" }
      ],
      "metricAmbiguityZones": [],
      "rhythmicMotifs": [
        { "motif_id":"rm_001","ioi_ratios":[1.0,1.0,1.0,1.0],
          "description":"Four even quarter notes — basic walking pulse",
          "occurrences":[
            {"tick":0,    "variation":"straight"},
            {"tick":1920, "variation":"straight"},
            {"tick":3840, "variation":"straight"}
          ]
        }
      ],
      "custom_extensions": {}
    },

    "layer4": {
      "noteProfiles": [
        { "sta_id":"sta_001","note_id":"n_001",
          "envelope":{"model":"ADSR_extended","attack_ms":22,"attack_curve":"logarithmic","decay_ms":30,"decay_curve":"exponential","sustain_level":0.80,"sustain_shape":"flat","release_ms":30,"release_curve":"exponential","peak_velocity":68,"peak_position":0.15},
          "formant_profile":{"vowel_color":"HUM_CLOSED","confidence":0.82,"f1_hz":320,"f2_hz":980,"f1_bandwidth":90,"f2_bandwidth":140},
          "harmonic_profile":{"fundamental_strength":0.90,"harmonic_rolloff":"moderate","harmonic_richness":0.58,"odd_even_ratio":1.22,"inharmonicity_coefficient":0.003},
          "breathiness":0.12,"brightness":0.55,"roughness":0.03,"strain":0.05,"registration":"chest"
        },
        { "sta_id":"sta_013","note_id":"n_013",
          "envelope":{"model":"ADSR_extended","attack_ms":85,"attack_curve":"logarithmic","decay_ms":200,"decay_curve":"exponential","sustain_level":0.75,"sustain_shape":"swell","release_ms":320,"release_curve":"exponential","peak_velocity":82,"peak_position":0.45,
            "rms_curve":[
              {"tick_offset":0,   "rms":0.0 },
              {"tick_offset":120, "rms":0.52},
              {"tick_offset":240, "rms":0.68},
              {"tick_offset":480, "rms":0.78},
              {"tick_offset":960, "rms":0.82},
              {"tick_offset":1440,"rms":0.76},
              {"tick_offset":1920,"rms":0.45}
            ]
          },
          "formant_profile":{"vowel_color":"HUM_CLOSED","confidence":0.88,"f1_hz":310,"f2_hz":960,"f1_bandwidth":85,"f2_bandwidth":130,
            "formant_curve":[
              {"tick_offset":0,   "f1":340,"f2":1010},
              {"tick_offset":480, "f1":310,"f2":960},
              {"tick_offset":960, "f1":305,"f2":950},
              {"tick_offset":1440,"f1":310,"f2":960}
            ]
          },
          "harmonic_profile":{"fundamental_strength":0.88,"harmonic_rolloff":"moderate","harmonic_richness":0.63,"odd_even_ratio":1.28,"inharmonicity_coefficient":0.004,
            "harmonics":[
              {"harmonic":1,"relative_amplitude":1.00},
              {"harmonic":2,"relative_amplitude":0.58},
              {"harmonic":3,"relative_amplitude":0.47},
              {"harmonic":4,"relative_amplitude":0.28},
              {"harmonic":5,"relative_amplitude":0.24},
              {"harmonic":6,"relative_amplitude":0.15},
              {"harmonic":7,"relative_amplitude":0.12},
              {"harmonic":8,"relative_amplitude":0.07}
            ]
          },
          "nasality_curve":[
            {"tick_offset":0,   "nasality":0.82},
            {"tick_offset":480, "nasality":0.78},
            {"tick_offset":960, "nasality":0.75},
            {"tick_offset":1440,"nasality":0.78},
            {"tick_offset":1920,"nasality":0.80}
          ],
          "breathiness":0.08,"brightness":0.52,"roughness":0.02,"strain":0.03,"registration":"chest"
        }
      ],
      "phraseTimbralFingerprints": [
        { "phrase_id":"phr_001",
          "avg_brightness":0.58,"avg_nasality":0.70,"avg_breathiness":0.14,"avg_roughness":0.03,
          "vowel_color_dominant":"HUM_CLOSED","registration_mode":"chest",
          "character_tags":["warm","rounded","legato","intimate"],
          "character_tags_neg":["not_bright","not_strained"] },
        { "phrase_id":"phr_002",
          "avg_brightness":0.62,"avg_nasality":0.63,"avg_breathiness":0.13,"avg_roughness":0.03,
          "vowel_color_dominant":"HUM_CLOSED","registration_mode":"chest",
          "character_tags":["warm","expressive","full"],
          "character_tags_neg":["not_thin","not_strained"] },
        { "phrase_id":"phr_003",
          "avg_brightness":0.66,"avg_nasality":0.61,"avg_breathiness":0.12,"avg_roughness":0.04,
          "vowel_color_dominant":"HUM_CLOSED","registration_mode":"chest",
          "character_tags":["bright","energetic","building","climactic"],
          "character_tags_neg":["not_dark","not_subdued"] },
        { "phrase_id":"phr_004",
          "avg_brightness":0.52,"avg_nasality":0.79,"avg_breathiness":0.09,"avg_roughness":0.02,
          "vowel_color_dominant":"HUM_CLOSED","registration_mode":"chest",
          "character_tags":["dark","warm","resolved","peaceful"],
          "character_tags_neg":["not_bright","not_tense"] }
      ],
      "custom_extensions": {}
    },

    "layer5": {
      "phrases": [
        { "phrase_id":"phr_001","tick_start":0,"tick_end":1920,"bar_start":1,"bar_end":2,
          "phrase_type":"antecedent","phrase_length":"2bar",
          "cadence":{"type":"half","strength":"harmonic_only","tick":1920,
                     "harmonic_motion":"I_to_V","melodic_motion":"1_to_3","confidence":0.81},
          "harmonic_context":{"implied_key":"G_major","confidence":0.91,
            "bar_by_bar_function":[
              {"bar":1,"function":"I","implied_chord":"Gmaj","confidence":0.93},
              {"bar":2,"function":"V","implied_chord":"Dmaj","confidence":0.80}
            ],
            "harmonic_rhythm":"one_per_bar","modal_color":"major"},
          "emotional_profile":{"primary_emotion":"serenity","secondary_emotion":"anticipation",
                               "valence":0.6,"arousal":0.35,"energy_label":"moderate",
                               "character_tags":["open","gentle","hopeful"],"confidence":0.78},
          "motif_instances":[
            {"motif_id":"m_001","occurrence_id":"m_001_occ_001","transformation":"exact","confidence":0.95}
          ],
          "energy_arc":"arch","narrative_label":"Opening statement — rises, implying continuation" },
        { "phrase_id":"phr_002","tick_start":1920,"tick_end":3840,"bar_start":3,"bar_end":4,
          "phrase_type":"consequent","phrase_length":"2bar",
          "cadence":{"type":"authentic","strength":"melodic_only","tick":3840,
                     "harmonic_motion":"V_to_I","melodic_motion":"2_to_1","confidence":0.85},
          "harmonic_context":{"implied_key":"G_major","confidence":0.89,
            "bar_by_bar_function":[
              {"bar":3,"function":"IV","implied_chord":"Cmaj","confidence":0.78},
              {"bar":4,"function":"I","implied_chord":"Gmaj","confidence":0.88}
            ],
            "harmonic_rhythm":"one_per_bar","modal_color":"major"},
          "emotional_profile":{"primary_emotion":"tenderness","secondary_emotion":"serenity",
                               "valence":0.65,"arousal":0.30,"energy_label":"moderate",
                               "character_tags":["resolving","warm","closing"],"confidence":0.81},
          "motif_instances":[
            {"motif_id":"m_001","occurrence_id":"m_001_occ_002","transformation":"inversion",
             "transposition":0,"confidence":0.88}
          ],
          "energy_arc":"valley","narrative_label":"Mirror phrase — answers and settles phr_001" },
        { "phrase_id":"phr_003","tick_start":3840,"tick_end":5760,"bar_start":5,"bar_end":6,
          "phrase_type":"climactic","phrase_length":"2bar",
          "cadence":{"type":"half","strength":"implied","tick":5760,
                     "harmonic_motion":"I_to_V","melodic_motion":"5_to_5","confidence":0.74},
          "harmonic_context":{"implied_key":"G_major","confidence":0.86,
            "bar_by_bar_function":[
              {"bar":5,"function":"I","implied_chord":"Gmaj","confidence":0.85},
              {"bar":6,"function":"V7","implied_chord":"D7","confidence":0.82}
            ],
            "harmonic_rhythm":"one_per_bar","modal_color":"major"},
          "emotional_profile":{"primary_emotion":"anticipation","secondary_emotion":"triumph",
                               "valence":0.72,"arousal":0.75,"energy_label":"high",
                               "character_tags":["climbing","building","expectant"],"confidence":0.82},
          "motif_instances":[
            {"motif_id":"m_001","occurrence_id":"m_001_occ_003","transformation":"sequence_up",
             "transposition":+5,"confidence":0.81}
          ],
          "energy_arc":"rise","narrative_label":"The climax — widest range, highest energy, peaks on d" },
        { "phrase_id":"phr_004","tick_start":5760,"tick_end":7680,"bar_start":7,"bar_end":8,
          "phrase_type":"cadential","phrase_length":"2bar",
          "cadence":{"type":"authentic","strength":"full","tick":7680,
                     "harmonic_motion":"V_to_I","melodic_motion":"1_to_1","confidence":0.94},
          "harmonic_context":{"implied_key":"G_major","confidence":0.94,
            "bar_by_bar_function":[
              {"bar":7,"function":"V7","implied_chord":"D7","confidence":0.88},
              {"bar":8,"function":"I","implied_chord":"Gmaj","confidence":0.96}
            ],
            "harmonic_rhythm":"one_per_bar","modal_color":"major"},
          "emotional_profile":{"primary_emotion":"serenity","secondary_emotion":"release",
                               "valence":0.80,"arousal":0.15,"energy_label":"low",
                               "character_tags":["resolved","peaceful","complete"],"confidence":0.90},
          "motif_instances":[],
          "energy_arc":"fall","narrative_label":"Full cadential resolution — long held tonic, all tension released" }
      ],

      "motifRegistry": [
        { "motif_id":"m_001","name":"Rising Step Cell",
          "tick_first_seen":0,
          "interval_pattern":["+2","+2"],
          "contour_code":"RISE.GRADUAL.COMPLETE",
          "rhythm_pattern":[1.0,1.0,1.0],
          "abstract_description":"Three notes in stepwise ascent — the primary motivic cell of this hum",
          "occurrences":[
            {"occurrence_id":"m_001_occ_001","tick_start":960, "phrase_id":"phr_001","transformation":"exact","transposition":0,"completeness":"full","confidence":0.95},
            {"occurrence_id":"m_001_occ_002","tick_start":1920,"phrase_id":"phr_002","transformation":"inversion","transposition":0,"completeness":"full","confidence":0.88},
            {"occurrence_id":"m_001_occ_003","tick_start":3840,"phrase_id":"phr_003","transformation":"sequence_up","transposition":+5,"completeness":"full","confidence":0.81}
          ]
        }
      ],

      "songSections": [
        { "section_id":"sec_001","inferred_label":"verse","confidence":0.80,
          "tick_start":0,"tick_end":7680,"bar_start":1,"bar_end":8,
          "phrases":["phr_001","phr_002","phr_003","phr_004"],
          "key":"G_major","avg_energy":0.58,
          "dominant_motifs":["m_001"],
          "notes":"Single 8-bar period (antecedent+consequent+climax+cadence). Classic period structure." }
      ],

      "harmonicSkeleton": {
        "key": "G_major",
        "bars": [
          {"bar":1,"chord":"Gmaj","function":"I",   "confidence":0.93},
          {"bar":2,"chord":"Dmaj","function":"V",   "confidence":0.80},
          {"bar":3,"chord":"Cmaj","function":"IV",  "confidence":0.78},
          {"bar":4,"chord":"Gmaj","function":"I",   "confidence":0.88},
          {"bar":5,"chord":"Gmaj","function":"I",   "confidence":0.85},
          {"bar":6,"chord":"D7",  "function":"V7",  "confidence":0.82},
          {"bar":7,"chord":"D7",  "function":"V7",  "confidence":0.88},
          {"bar":8,"chord":"Gmaj","function":"I",   "confidence":0.96}
        ],
        "alternative_readings": [],
        "notes":"Classic I-V-IV-I / I-V-V-I structure. Bars 5-7 drive strongly to the final tonic. Harmonic rhythm straightforward throughout."
      },

      "overallProfile": {
        "inferred_genre"    : "folk_or_pop_ballad",
        "genre_confidence"  : 0.72,
        "overall_key"       : "G_major",
        "overall_tempo_feel": "moderato_with_slight_ritardando",
        "overall_character" : "warm, intimate, gently expressive",
        "song_form_inferred": "8-bar period (AABA')",
        "notes"             : "A complete, well-formed 8-bar melody. Rising step motif drives forward, wide-range climax in bars 5-6, full resolution on held tonic. Suitable for expansion into verse or chorus of a folk/pop song."
      },

      "custom_extensions": {}
    }
  }
}
```

---

*End of HumScore Specification v1.0.0*

*This document describes the data representation system only. Audio capture, signal processing, machine learning inference, and rendering pipeline specifications are addressed in separate companion documents: HumScore-Capture-Spec, HumScore-Inference-Spec, and HumScore-Render-Spec.*
