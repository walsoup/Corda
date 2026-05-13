<div align="center">
  <img src="https://raw.githubusercontent.com/corda-protocol/assets/main/logo.png" width="120" alt="Corda Logo" />
  <h1>Corda Protocol</h1>
  <p><strong>The Vocal-Tract-Centric Audio Synthesis Engine & IDE</strong></p>
  <p>
    <img src="https://img.shields.io/badge/version-2.0.0-blue.svg" alt="Version 2.0.0">
    <img src="https://img.shields.io/badge/python-3.9%2B-brightgreen.svg" alt="Python 3.9+">
    <img src="https://img.shields.io/badge/react-Next.js%2014-black.svg" alt="Next.js">
    <img src="https://img.shields.io/badge/status-active_development-orange.svg" alt="Status">
  </p>
</div>

---

## 🎙️ Stop Pitching. Start Speaking.

Traditional audio synthesis is built on a fatal flaw: **the Pitch-Centric Model**. It assumes human voices act like pianos, snapping complex biological sounds onto a grid of notes and beats. It works for robotic melodies, but it destroys the nuance of *real* human expression—sarcasm, grief, breathiness, plosive bursts, and vocal fry.

**Corda v2 is different.** 

Corda shifts the paradigm to a **Vocal-Tract-Centric Model**. Instead of asking *"what note is this?"*, Corda asks *"what is the human vocal mechanism physically doing right now?"* 

By mathematically modeling the lungs as an air pressure source, the vocal folds as an oscillating Liljencrants-Fant (LF) valve, and the oral cavity as a 5-pole dynamic resonant filter, Corda achieves unparalleled acoustic fidelity. From a delicate whisper to a death-metal scream—Corda represents it perfectly.

## ✨ Key Features

*   🧬 **Biological DSP Engine:** Full implementations of LF glottal models, aspiration noise generators, and IIR cascade formant filters.
*   📈 **Unanchored Vector Space (UVS):** Continuous cubic Bezier curves for pitch and tension instead of quantized MIDI notes. Perfect glissandos, rubatos, and microtonal inflections.
*   🎭 **Semantic NLP Layer:** Tag phrases with emotions (`grief`, `sarcasm`, `excitement`) and watch Corda autonomously inject acoustic macros like pitch spikes, intensity dips, and formant brightening.
*   🧠 **Neural-Ready Architecture:** Comes with a fully structured PyTorch HiFi-GAN Vocoder repository (`corda_synth.neural`) ready to be trained on your datasets to up-res the DSP output into photorealistic human audio.
*   🖥️ **WebAssembly Visual IDE:** A stunning Material 3 Expressive React/Next.js environment. The Python DSP engine compiles to WebAssembly via Pyodide, rendering your audio live in the browser at 60 FPS without a backend server.

---

## 🚀 Quick Start

### 1. The Python DSP Engine

Install the core python library locally:

```bash
cd corda_synth
pip install -e .
```

Render your first `.crd` file:

```bash
corda-synth render corpus/sentence_hello.crd.json -o hello.wav
```

### 2. The WebAssembly IDE

Launch the Visual IDE to interactively edit and render `.crd` files:

```bash
cd visual-ide
npm install
npm run dev
```

Open `http://localhost:3000`. Click **"Open File"**, select one of the JSON files from the `/corpus` directory, and hit **"Render & Play"**.

---

## 🏗️ Architecture Stack

1.  **Layer 1 (PAN):** Phonetic & Articulation Notation (Ground Truth)
2.  **Layer 2 (UVS):** Unanchored Vector Space (Continuous Pitch Curves)
3.  **Layer 3 (SRM):** Speech-Rhythm Mapping (Prosodic Syllable Density)
4.  **Layer 4 (AVT):** Advanced Vocal Tract Modeling (Glottal physics & Formants)
5.  **Layer 5 (NSS):** NLP Semantic Syntax (Meaning & Emotion)
6.  **Layer 6 (IDE):** Visual Workspace DOM (React/WASM integration)

Read the full exhaustive specification in the [Corda Protocol v2 Design Doc](./Corda_Protocol_v2_Design_Doc.md).

---

## 🤝 Contributing

The Synthesis Wars are over, and Biology won. Help us build the ultimate acoustic representation of the human voice. PRs are welcome for DSP optimizations, new articulation classes, and Visual IDE enhancements.

**License:** MIT
