"""
peo_synth.py — Per-Articulation-Class PEO Synthesizer
======================================================
Dispatches synthesis for each Phonetic Event Object (PEO) based on its
articulation_class. This is the bridge between the parsed .crd data and
the acoustic source + filter modules.

Each synthesizer method returns a float32 numpy array representing the
audio contribution of that single PEO, which the engine then places into
the master timeline at the correct sample offset.

Synthesis chain per articulation class
---------------------------------------
VOICED      → GlottalSource.train() → FormantFilterBank.apply_dynamic()
PLOSIVE     → PlosiveBurst.generate()  (short, unfiltered by formants)
FRICATIVE   → FricativeNoise.generate()
NASAL       → GlottalSource.train() → nasal resonance filter
APPROXIMANT → GlottalSource.train() → FormantFilterBank (vowel-like)
AFFRICATE   → PlosiveBurst + FricativeNoise (concatenated)
GLOTTAL     → GlottalSource at tension ≥ 0.90 + heavy aspiration
HESITATION  → Low-amplitude VOICED or FRICATIVE depending on type
NON_VERBAL  → Placeholder: aspirated noise (laughter, sighs, etc.)
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from .parser import PEO, CordaFile, FormantFrame
from .sources import GlottalSource, AspirationNoise, FricativeNoise, PlosiveBurst
from .filters import FormantFilterBank, FormantSpec
from .bezier import CVNInterpolator, fallback_pitch


FRAME_SIZE = 441     # 10 ms at 44100 Hz — synthesis frame granularity


class PEOSynthesizer:
    """
    Synthesizes audio for a single PEO.

    One PEOSynthesizer instance is created per synthesis run and reused
    across all PEOs in the file (avoids repeated object allocation).
    """

    def __init__(self, sample_rate: int = 44100, ppq: int = 9600, bpm: float = 120.0):
        self.sample_rate = sample_rate
        self.glottal = GlottalSource()
        self.aspiration = AspirationNoise()
        self.fricative_noise = FricativeNoise()
        self.plosive_burst = PlosiveBurst()
        self.filter_bank = FormantFilterBank(sample_rate)
        self.interp = CVNInterpolator(sample_rate, ppq, bpm)

    def _get_peo_emotion(self, peo: PEO, corda: CordaFile) -> str | None:
        for phrase in corda.phrases:
            if phrase.tick_onset <= peo.tick_onset and phrase.tick_offset >= peo.tick_offset:
                return phrase.emotion_inference
        return None

    def _get_peo_stress(self, peo: PEO, corda: CordaFile) -> str | None:
        for phrase in corda.phrases:
            for wb in phrase.word_boundaries:
                if peo.peo_id in wb.peo_range:
                    return wb.stress
        return None

    def synthesize(self, peo: PEO, corda: CordaFile, prev_peo: PEO | None = None, next_peo: PEO | None = None) -> np.ndarray:
        """
        Dispatch synthesis based on articulation class.
        Returns float32 array of length == PEO duration in samples.
        """
        self.prev_peo = prev_peo
        self.next_peo = next_peo
        self.emotion = self._get_peo_emotion(peo, corda)
        self.stress = self._get_peo_stress(peo, corda)

        n_samples = max(
            1,
            self.interp.ticks_to_samples(peo.tick_offset - peo.tick_onset),
        )
        
        intensity = peo.intensity

        # Phase 3: Prosodic Stress duration/amplitude scaling
        if self.stress == "PRIMARY":
            n_samples = int(n_samples * 1.15)
            intensity *= 1.10
        elif self.stress == "CONTRASTIVE":
            n_samples = int(n_samples * 1.25)
            intensity *= 1.20
        elif self.stress == "UNSTRESSED":
            n_samples = int(n_samples * 0.90)

        # Phase 3: Emotion rate scaling
        if self.emotion == "excitement":
            n_samples = int(n_samples / 1.15)
        elif self.emotion == "grief":
            n_samples = int(n_samples / 0.80)
        elif self.emotion == "sarcasm":
            n_samples = int(n_samples / 0.95)

        n_samples = max(1, n_samples)

        dispatch = {
            "VOICED":      self._synth_voiced,
            "PLOSIVE":     self._synth_plosive,
            "FRICATIVE":   self._synth_fricative,
            "NASAL":       self._synth_nasal,
            "APPROXIMANT": self._synth_approximant,
            "AFFRICATE":   self._synth_affricate,
            "GLOTTAL":     self._synth_glottal,
            "HESITATION":  self._synth_hesitation,
            "NON_VERBAL":  self._synth_non_verbal,
        }

        fn = dispatch.get(peo.articulation_class, self._synth_silence)
        audio = fn(peo, corda, n_samples)

        # Apply master intensity envelope
        audio = self._apply_intensity_envelope(audio, intensity, peo.flags)
        return audio.astype(np.float32)

    # ── VOICED ────────────────────────────────────────────────────────────────

    def _synth_voiced(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """Full LF glottal source → formant cascade."""
        pitch_curve = self._get_pitch_curve(peo, corda, n_samples)
        tension_curve = self._get_tension_curve(peo, corda, n_samples)

        # Glottal source
        source = self.glottal.train(
            n_samples, pitch_curve, tension_curve, self.sample_rate
        )

        # Mix in aspiration noise (breathy phonation)
        asp_ratio_curve = self._get_aspiration_curve(peo, corda, n_samples)
        avg_asp = float(np.mean(asp_ratio_curve))
        if avg_asp > 0.02:
            asp = self.aspiration.generate(n_samples, avg_asp, self.sample_rate)
            source = source * (1.0 - avg_asp) + asp

        # Formant filter
        frame_specs = self._get_formant_specs(peo, corda, n_samples)
        audio = self.filter_bank.apply_dynamic(source, frame_specs, FRAME_SIZE)
        return audio

    # ── PLOSIVE ───────────────────────────────────────────────────────────────

    def _synth_plosive(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        peak_hz = peo.spectral_peak_hz or 2000.0
        voiced_plosives = {"b", "d", "ɡ", "g"}   # IPA
        is_voiced = peo.ipa_symbol.strip() in voiced_plosives

        burst = self.plosive_burst.generate(
            n_samples, peak_hz, self.sample_rate, voiced=is_voiced
        )
        return burst

    # ── FRICATIVE ─────────────────────────────────────────────────────────────

    def _synth_fricative(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        floor = peo.noise_floor_hz or 3000.0
        ceil  = peo.noise_ceiling_hz or 8000.0
        env   = np.array(peo.intensity_curve) if peo.intensity_curve else None

        noise = self.fricative_noise.generate(
            n_samples, floor, ceil, self.sample_rate, intensity_envelope=env
        )

        # Voiced fricatives (/v/, /z/, /ʒ/) add a weak voiced source underneath
        voiced_fric = {"v", "z", "ʒ", "ð", "ɣ"}
        if peo.ipa_symbol.strip() in voiced_fric:
            tension_curve = np.full(n_samples, 0.55, dtype=np.float32)
            pitch_curve   = np.full(n_samples, 130.0, dtype=np.float32)
            voiced_src = self.glottal.train(
                n_samples, pitch_curve, tension_curve, self.sample_rate
            )
            voiced_src *= 0.25    # voiced murmur is quiet under the noise
            noise = noise * 0.75 + voiced_src

        return noise

    # ── NASAL ─────────────────────────────────────────────────────────────────

    def _synth_nasal(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """
        Nasals are voiced with a strongly emphasized F1 (~250 Hz) and
        broad anti-resonances (nasal zeros) that suppress the mid-range.
        """
        pitch_curve   = self._get_pitch_curve(peo, corda, n_samples)
        tension_curve = np.full(n_samples, 0.45, dtype=np.float32)  # soft phonation

        source = self.glottal.train(
            n_samples, pitch_curve, tension_curve, self.sample_rate
        )

        # Nasal formant configuration: boosted low F1, suppressed F2/F3
        nasal_spec = FormantSpec(
            f1=280, f2=1000, f3=2200, f4=3000, f5=4000,
            bw1=60, bw2=600, bw3=600, bw4=400, bw5=400,
        )
        audio = self.filter_bank.apply_static(source, nasal_spec)

        # Soft lowpass to reinforce murmur character (~1 kHz cutoff)
        b, a = signal.butter(2, 1000 / (self.sample_rate / 2.0), btype="low")
        murmur = signal.lfilter(b, a, audio.astype(np.float64)).astype(np.float32)
        return audio * 0.5 + murmur * 0.5

    # ── APPROXIMANT ───────────────────────────────────────────────────────────

    def _synth_approximant(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """Approximants are essentially vowel-like: full formant synthesis."""
        return self._synth_voiced(peo, corda, n_samples)

    # ── AFFRICATE ─────────────────────────────────────────────────────────────

    def _synth_affricate(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """
        Affricate = plosive burst followed immediately by a fricative.
        Split duration roughly 25% burst / 75% frication.
        """
        burst_len = max(1, int(n_samples * 0.25))
        fric_len  = n_samples - burst_len

        peak_hz  = peo.spectral_peak_hz or 3000.0
        burst    = self.plosive_burst.generate(burst_len, peak_hz, self.sample_rate)

        # Derive fricative from affricate IPA (ch→ʃ, j→ʒ approximation)
        floor = peo.noise_floor_hz or 2000.0
        ceil  = peo.noise_ceiling_hz or 7000.0
        fric  = self.fricative_noise.generate(fric_len, floor, ceil, self.sample_rate)

        # Crossfade at junction
        fade = min(64, burst_len, fric_len)
        if fade > 0:
            burst[-fade:] *= np.linspace(1, 0, fade)
            fric[:fade]   *= np.linspace(0, 1, fade)

        return np.concatenate([burst, fric]).astype(np.float32)

    # ── GLOTTAL ───────────────────────────────────────────────────────────────

    def _synth_glottal(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """
        Pure glottal events: fry, creak, glottal stop.
        Very high tension (0.92–1.0) + heavy aspiration.
        No formant filtering (glottal stops approach silence).
        """
        tension  = 0.95 if "VOCAL_FRY" in peo.flags else 1.0
        t_curve  = np.full(n_samples, tension, dtype=np.float32)
        hz_curve = np.full(n_samples, 70.0, dtype=np.float32)   # very low fry F0

        source = self.glottal.train(n_samples, hz_curve, t_curve, self.sample_rate)

        # Mix in aspiration noise for creak quality
        asp = self.aspiration.generate(n_samples, 0.4, self.sample_rate)
        return (source * 0.6 + asp * 0.4).astype(np.float32)

    # ── HESITATION ────────────────────────────────────────────────────────────

    def _synth_hesitation(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        htype = peo.hesitation_type or "FILLER_VOICED"

        if htype == "FILLER_VOICED":           # "um" — low, nasal-ish vowel
            peo_copy = _peo_with_class(peo, "NASAL")
            return self._synth_nasal(peo_copy, corda, n_samples) * 0.5

        elif htype == "FILLER_UNVOICED":       # "uh" — short mid-central vowel
            peo_copy = _peo_with_class(peo, "VOICED")
            return self._synth_voiced(peo_copy, corda, n_samples) * 0.4

        elif htype in ("INHALE_SHARP", "INHALE_SLOW"):
            # Model as aspirated noise with slightly pitched character
            asp = self.aspiration.generate(n_samples, 0.7, self.sample_rate)
            # Apply rising amplitude envelope for inhale
            env = np.linspace(0.1, 0.8, n_samples).astype(np.float32)
            return asp * env

        elif htype == "GLOTTAL_HOLD":
            # Silent except for minimal creak at the margins
            silence = np.zeros(n_samples, dtype=np.float32)
            creak_len = min(n_samples, int(self.sample_rate * 0.01))
            creak = self.glottal.pulse(creak_len, 0.95)
            silence[:creak_len] = creak * 0.15
            return silence

        return np.zeros(n_samples, dtype=np.float32)

    # ── NON_VERBAL ────────────────────────────────────────────────────────────

    def _synth_non_verbal(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """
        Proper synthesis for non-verbal events based on flags.
        Supported flags: LAUGH, SIGH, COUGH, CRY
        """
        flags = [f.upper() for f in peo.flags]

        if "LAUGH" in flags:
            # Laughter: Pulsed aspiration at 4-8 Hz with rising F0
            asp = self.aspiration.generate(n_samples, 0.8, self.sample_rate)
            t = np.linspace(0, n_samples / self.sample_rate, n_samples)
            # Pulsing rate ~ 6 Hz
            mod = (0.5 + 0.5 * np.sin(2 * np.pi * 6.0 * t)).astype(np.float32)
            
            # Rising F0 (pitch curve)
            hz_curve = np.linspace(150.0, 300.0, n_samples).astype(np.float32)
            tension_curve = np.full(n_samples, 0.4, dtype=np.float32)
            voiced = self.glottal.train(n_samples, hz_curve, tension_curve, self.sample_rate)
            
            return (asp * 0.7 + voiced * 0.3) * mod

        elif "SIGH" in flags:
            # Sigh: Long, slow aspiration with falling intensity curve
            asp = self.aspiration.generate(n_samples, 0.9, self.sample_rate)
            # Falling envelope
            env = np.linspace(1.0, 0.1, n_samples).astype(np.float32)
            return asp * env

        elif "COUGH" in flags:
            # Cough: Short high-energy plosive burst + frication
            burst_len = min(int(self.sample_rate * 0.05), n_samples) # 50ms burst
            fric_len = n_samples - burst_len
            
            burst = self.plosive_burst.generate(burst_len, 1500.0, self.sample_rate)
            fric = self.fricative_noise.generate(fric_len, 1000.0, 6000.0, self.sample_rate)
            
            # Rapid decay for the fricative part
            if fric_len > 0:
                env = np.exp(-10.0 * np.linspace(0, 1, fric_len)).astype(np.float32)
                fric *= env
                
            return np.concatenate([burst, fric]).astype(np.float32)

        elif "CRY" in flags:
            # Cry: High-F0 VOICED with trembling glottal curve
            # Base high F0 ~ 400 Hz
            t = np.linspace(0, n_samples / self.sample_rate, n_samples)
            # Tremolo/vibrato ~ 8 Hz
            tremolo = 20.0 * np.sin(2 * np.pi * 8.0 * t)
            hz_curve = (400.0 + tremolo).astype(np.float32)
            
            # Pressed tension, trembling
            tension_curve = (0.8 + 0.1 * np.sin(2 * np.pi * 12.0 * t)).astype(np.float32)
            tension_curve = np.clip(tension_curve, 0.0, 1.0)
            
            source = self.glottal.train(n_samples, hz_curve, tension_curve, self.sample_rate)
            asp = self.aspiration.generate(n_samples, 0.4, self.sample_rate)
            
            return source * 0.7 + asp * 0.3

        # Default fallback
        asp = self.aspiration.generate(n_samples, 0.6, self.sample_rate)
        t = np.linspace(0, n_samples / self.sample_rate, n_samples)
        mod = (0.6 + 0.4 * np.sin(2 * np.pi * 8.0 * t)).astype(np.float32)
        return asp * mod

    # ── Silence fallback ─────────────────────────────────────────────────────

    def _synth_silence(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        return np.zeros(n_samples, dtype=np.float32)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_pitch_curve(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        curve = corda.get_curve_for_peo(peo.peo_id)
        if curve is not None:
            arr = self.interp.to_sample_array(curve, peo.tick_onset, peo.tick_offset)
        else:
            arr = fallback_pitch(peo.intensity, n_samples)

        # Phase 3: Emotion F0 shift
        if self.emotion == "excitement":
            arr *= 1.20
        elif self.emotion == "sudden_realization":
            # +35% spike in the middle
            peak = min(n_samples // 2, n_samples - 1)
            spike = np.ones(n_samples, dtype=np.float32)
            spike[peak] = 1.35
            # Smooth the spike
            spike = np.convolve(spike, np.ones(10)/10, mode='same')
            arr *= spike
        elif self.emotion == "questioning":
            # +15% at the end (final syllable proxy)
            ramp = np.linspace(1.0, 1.15, n_samples).astype(np.float32)
            arr *= ramp
        elif self.emotion == "grief":
            arr *= 0.90
        elif self.emotion == "sarcasm":
            # flat then spike
            arr[:n_samples//2] = np.mean(arr[:n_samples//2])
            arr[n_samples//2:] *= np.linspace(1.0, 1.20, n_samples - n_samples//2)

        # Prosodic Stress F0 shift
        if self.stress == "CONTRASTIVE":
            arr *= 1.15

        # Semantic Spike gesture class handling
        if "SEMANTIC_SPIKE" in peo.flags:
            arr *= 1.25

        return arr.astype(np.float32)

    def _get_tension_curve(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        """Expand glottal_curve from the BSON payload into per-sample resolution."""
        gc = corda.vectors.glottal_curve
        if len(gc) == 0:
            arr = np.full(n_samples, 0.5, dtype=np.float32)
        else:
            # Determine which slice of the global glottal_curve covers this PEO
            start_idx = peo.tick_onset // 4
            end_idx   = peo.tick_offset // 4 + 1
            start_idx = min(start_idx, len(gc) - 1)
            end_idx   = min(end_idx,   len(gc))

            slice_ = gc[start_idx:end_idx]
            if len(slice_) == 0:
                slice_ = np.array([0.5], dtype=np.float32)

            arr = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, len(slice_)),
                slice_,
            ).astype(np.float32)

        # Phase 3: Emotion Tension offsets
        tension_offsets = {
            "excitement": 0.10,
            "sudden_realization": 0.05,
            "questioning": 0.03,
            "grief": -0.05,
            "sarcasm": 0.07,
        }
        if self.emotion in tension_offsets:
            arr += tension_offsets[self.emotion]
            
        return np.clip(arr, 0.0, 1.0)

    def _get_aspiration_curve(self, peo: PEO, corda: CordaFile, n_samples: int) -> np.ndarray:
        ac = corda.vectors.aspiration_curve
        if len(ac) == 0:
            # Default: slight aspiration if tension is low
            avg_tension = float(np.mean(self._get_tension_curve(peo, corda, n_samples)))
            default_asp = max(0.0, 0.3 - avg_tension * 0.5)
            arr = np.full(n_samples, default_asp, dtype=np.float32)
        else:
            start_idx = peo.tick_onset // 4
            end_idx   = peo.tick_offset // 4 + 1
            start_idx = min(start_idx, len(ac) - 1)
            end_idx   = min(end_idx, len(ac))
            slice_ = ac[start_idx:end_idx]
            if len(slice_) == 0:
                slice_ = np.array([0.1], dtype=np.float32)

            arr = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, len(slice_)),
                slice_,
            ).astype(np.float32)

        # Phase 3: Emotion Aspiration offsets
        asp_offsets = {
            "excitement": -0.05,
            "sudden_realization": -0.02,
            "grief": 0.15,
            "sarcasm": -0.04,
        }
        if self.emotion in asp_offsets:
            arr += asp_offsets[self.emotion]
            
        return np.clip(arr, 0.0, 1.0)

    def _get_formant_specs(
        self, peo: PEO, corda: CordaFile, n_samples: int
    ) -> list[FormantSpec]:
        frames = corda.formant_frames_in_range(peo.tick_onset, peo.tick_offset)
        if not frames:
            # Fallback to neutral if no frames exist
            ff_fallback = FormantFrame(peo.tick_onset, 500.0, 1500.0, 2500.0, 3200.0, 4000.0, 0.0)
            frames = [ff_fallback]

        # Extract boundary formants for coarticulation interpolation
        prev_ff = None
        if self.prev_peo is not None:
            pf = corda.formant_frames_in_range(self.prev_peo.tick_onset, self.prev_peo.tick_offset)
            if pf: prev_ff = pf[-1]
            
        next_ff = None
        if self.next_peo is not None:
            nf = corda.formant_frames_in_range(self.next_peo.tick_onset, self.next_peo.tick_offset)
            if nf: next_ff = nf[0]

        avg_tension = float(np.mean(self._get_tension_curve(peo, corda, n_samples)))
        is_nasalized = "NASALIZED" in peo.flags or peo.articulation_class == "NASAL"
        is_aspirated = "ASPIRATED" in peo.flags

        specs = []
        n_frames = len(frames)
        # We blend over the first and last 20% of the frames (or up to 10 frames)
        blend_frames = min(10, max(1, n_frames // 5))

        for i, ff in enumerate(frames):
            f1, f2, f3 = ff.f1_hz, ff.f2_hz, ff.f3_hz
            f4, f5 = ff.f4_hz, ff.f5_hz
            
            # Interpolate from prev_peo using a smooth hermite/bezier step
            if prev_ff is not None and i < blend_frames:
                t = i / blend_frames
                # smoothstep: 3*t^2 - 2*t^3
                blend = t * t * (3.0 - 2.0 * t) 
                f1 = prev_ff.f1_hz * (1 - blend) + f1 * blend
                f2 = prev_ff.f2_hz * (1 - blend) + f2 * blend
                f3 = prev_ff.f3_hz * (1 - blend) + f3 * blend
                f4 = prev_ff.f4_hz * (1 - blend) + f4 * blend
                f5 = prev_ff.f5_hz * (1 - blend) + f5 * blend
                
            # Interpolate towards next_peo
            if next_ff is not None and i >= n_frames - blend_frames:
                t = (n_frames - 1 - i) / blend_frames
                blend = t * t * (3.0 - 2.0 * t)
                f1 = next_ff.f1_hz * (1 - blend) + f1 * blend
                f2 = next_ff.f2_hz * (1 - blend) + f2 * blend
                f3 = next_ff.f3_hz * (1 - blend) + f3 * blend
                f4 = next_ff.f4_hz * (1 - blend) + f4 * blend
                f5 = next_ff.f5_hz * (1 - blend) + f5 * blend

            # Phase 3: Prosodic Stress (Unstressed centralization)
            if self.stress == "UNSTRESSED":
                f1 = f1 * 0.9 + 500.0 * 0.1
                f2 = f2 * 0.9 + 1500.0 * 0.1
                f3 = f3 * 0.9 + 2500.0 * 0.1

            # Phase 3: Semantic Spike formant brightening at apex
            if "SEMANTIC_SPIKE" in peo.flags:
                apex = max(0, n_frames // 2)
                dist = abs(i - apex) / max(1, n_frames / 2.0)
                # +200 Hz bump on F2 in the middle
                f2 += 200.0 * max(0.0, 1.0 - dist * 1.5)

            spec = FormantSpec(
                f1=f1, f2=f2, f3=f3, f4=f4, f5=f5
            )
            
            # High-tension (pressed) voice: narrower F1 bandwidth
            if avg_tension > 0.7:
                # Scale down to 0.6x at max tension
                tension_scale = 1.0 - 0.4 * ((avg_tension - 0.7) / 0.3)
                spec.bw1 *= tension_scale

            # Breathy voice: wider bandwidths across all formants
            eff_asp = ff.aspiration_ratio
            if is_aspirated:
                eff_asp = max(eff_asp, 0.5)
            
            if eff_asp > 0.1:
                broaden = 1.0 + (eff_asp * 2.0)  # up to 3x broader at pure aspiration
                spec.bw1 *= broaden
                spec.bw2 *= broaden
                spec.bw3 *= broaden
                spec.bw4 *= broaden
                spec.bw5 *= broaden

            # Nasals / nasalized vowels: F2/F3 bandwidth × 3-5 (heavy anti-resonance)
            if is_nasalized:
                spec.bw2 *= 4.0
                spec.bw3 *= 4.0

            specs.append(spec)

        return specs

    def _apply_intensity_envelope(
        self, audio: np.ndarray, intensity: float, flags: list[str]
    ) -> np.ndarray:
        """
        Apply a soft onset/offset fade (5 ms) plus the PEO's overall
        intensity scalar. Prevents clicks at PEO boundaries.
        """
        n = len(audio)
        fade_len = min(int(self.sample_rate * 0.005), n // 4)  # 5 ms

        env = np.ones(n, dtype=np.float32)

        if fade_len > 0:
            env[:fade_len]  = np.linspace(0, 1, fade_len)
            env[-fade_len:] = np.linspace(1, 0, fade_len)

        # Phase 3: Semantic Spike intensity dip at onset
        if "SEMANTIC_SPIKE" in flags and n > fade_len:
            dip_len = min(int(self.sample_rate * 0.03), n // 3) # 30ms dip
            if dip_len > 0:
                dip_env = np.linspace(0.4, 1.0, dip_len).astype(np.float32)
                env[:dip_len] *= dip_env

        audio = audio * env
        return audio * float(intensity)


def _peo_with_class(peo: PEO, new_class: str) -> PEO:
    """Return a copy of a PEO with a different articulation_class."""
    import copy
    p = copy.copy(peo)
    p.articulation_class = new_class
    return p
