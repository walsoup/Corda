"""
sources.py — Glottal Source Generators
=======================================
Implements the acoustic source signals that drive the formant filter bank.

The human voice is modeled as a source-filter system:
    [Glottal Source] → [Vocal Tract Filter] → [Lip Radiation] → Audio

This module handles the source side. The vocal tract filter is in filters.py.

Source types
------------
- GlottalSource.pulse()     : LF-model glottal pulse for one pitch period
- GlottalSource.train()     : Full pulse train for N samples at given pitch Hz
- AspirationNoise.generate(): Band-limited aspiration noise
- FricativeNoise.generate() : Band-limited turbulence noise (for fricatives)
- PlosiveBurst.generate()   : Transient burst for plosive events

References
----------
Fant, G., Liljencrants, J., & Lin, Q. (1985).
"A four-parameter model of glottal flow." STL-QPSR.
"""

from __future__ import annotations
import numpy as np
from scipy import signal


class GlottalSource:
    """
    Four-parameter Liljencrants-Fant (LF) glottal source model.
    
    The four LF parameters (Rd, Ra, Rk, Rg) give fine-grained control over
    voice quality and map cleanly onto the Corda glottal tension scalar.
    """

    def _tension_to_rd(self, tension: float) -> float:
        """
        Map tension [0.0 - 1.0] to Rd (shape parameter).
        0.0 = 3.0 (breathy)
        0.5 = 1.7 (modal)
        0.8 = 0.9 (pressed)
        1.0 = 0.3 (fry)
        """
        tension = np.clip(tension, 0.0, 1.0)
        # Interpolate based on the table in roadmap
        if tension <= 0.5:
            return 3.0 - (tension / 0.5) * (3.0 - 1.7)
        elif tension <= 0.8:
            return 1.7 - ((tension - 0.5) / 0.3) * (1.7 - 0.9)
        else:
            return 0.9 - ((tension - 0.8) / 0.2) * (0.9 - 0.3)

    def pulse(self, n_samples: int, tension: float) -> np.ndarray:
        """
        Generate a single LF glottal flow derivative pulse of length
        n_samples, shaped by the given tension value.
        """
        tension = float(np.clip(tension, 0.0, 1.0))
        pulse = np.zeros(n_samples, dtype=np.float32)

        if n_samples < 4:
            return pulse

        rd = self._tension_to_rd(tension)
        
        # Approximate LF timing parameters from Rd
        rap = (0.27 * rd) / (0.11 * rd + 1.0) + 0.01  # Ra
        rk = 0.224 + 0.118 * rd                       # Rk
        rg = (rk / 4.0) * (0.5 + 1.2 * rk) / (0.11 * rd + 1.0) # Rg approx
        
        # Timing indices
        t_p = min(max(int((1.0 / (2.0 * rg)) * n_samples), 1), n_samples - 2) # Time of peak derivative
        t_e = min(max(int(t_p + rk * t_p), t_p + 1), n_samples - 1)           # Time of max glottal opening
        
        # 1. Rising phase (0 to t_e): Exponentially growing sine
        # E(t) = E0 * exp(a*t) * sin(w*t)
        # Simplified to match expected shape without complex ODE solving:
        w = np.pi / t_p
        t_rise = np.arange(t_e)
        a = 1.0 / t_p # Growth rate
        pulse[:t_e] = np.exp(a * t_rise) * np.sin(w * t_rise)
        
        # Ensure peak is negative as it's derivative of flow
        peak_val = np.min(pulse[:t_e]) if len(pulse[:t_e]) > 0 else -1.0
        if peak_val < 0:
            pulse[:t_e] /= -peak_val # Normalize falling peak to -1
        
        # 2. Return phase (t_e to n_samples): Exponential decay (return phase)
        # E(t) = -E1 * (exp(-b*(t-t_e)) - exp(-b*(t_c-t_e)))
        t_fall = np.arange(t_e, n_samples)
        b = 1.0 / max((rap * n_samples), 1) # Decay rate based on Ra
        if len(t_fall) > 0:
            decay = np.exp(-b * (t_fall - t_e))
            # Shift to meet 0 at end
            decay = decay - np.exp(-b * (n_samples - t_e))
            pulse[t_e:] = -decay / max(decay[0], 1e-6)

        # Mix in aspiration noise for low tension (breathy)
        if tension < 0.25:
            leak_amp = 0.06 * (0.25 - tension)
            pulse += np.random.normal(0, leak_amp, n_samples).astype(np.float32)

        peak = np.max(np.abs(pulse))
        if peak > 0:
            pulse /= peak

        return pulse

    def train(
        self,
        n_samples: int,
        pitch_hz_curve: np.ndarray,
        tension_curve: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Synthesize a full glottal pulse train of length n_samples.

        Parameters
        ----------
        n_samples        : output length in samples
        pitch_hz_curve   : per-sample pitch in Hz (length == n_samples)
        tension_curve    : per-sample glottal tension [0–1] (length == n_samples)
        sample_rate      : audio sample rate in Hz

        Returns
        -------
        float32 array of length n_samples containing the glottal source signal.

        Vocal fry simulation
        --------------------
        When tension ≥ 0.90 the engine enters "fry mode":
        - Period jitter (±15%) is introduced between consecutive pulses.
        - Every 3rd–5th pulse is suppressed (subharmonic structure typical of fry).
        """
        output = np.zeros(n_samples, dtype=np.float32)
        pos = 0
        pulse_count = 0

        while pos < n_samples:
            # Current pitch and tension (sample-indexed, clamped)
            idx = min(pos, n_samples - 1)
            f0 = float(pitch_hz_curve[idx])
            tension = float(tension_curve[idx])

            if f0 <= 0:
                pos += int(sample_rate / 100)   # ~10ms silence chunk
                continue

            period = sample_rate / f0           # nominal period in samples

            # ── Vocal fry: period jitter and pulse dropout ─────────────────
            if tension >= 0.90:
                jitter = 1.0 + np.random.uniform(-0.15, 0.15)
                period *= jitter
                # Suppress every ~4th pulse (subharmonic structure)
                if pulse_count % 4 == 3:
                    pos += int(period)
                    pulse_count += 1
                    continue

            n_period = max(4, int(round(period)))
            end = min(pos + n_period, n_samples)
            chunk = end - pos

            p = self.pulse(n_period, tension)[:chunk]
            output[pos:end] += p
            pos = end
            pulse_count += 1

        return output


class AspirationNoise:
    """
    Broadband aspiration noise mixed into the glottal source during
    breathy or whispered phonation (glottal tension < ~0.4).
    """

    def generate(
        self,
        n_samples: int,
        aspiration_ratio: float,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Generate aspiration noise of length n_samples.

        aspiration_ratio [0.0–1.0] controls the noise amplitude.
        The noise is shaped by a gentle lowpass (< 8 kHz) to match
        the spectral tilt of real subglottal aspiration.
        """
        noise = np.random.normal(0, 1, n_samples).astype(np.float32)

        # Gentle lowpass to shape spectral tilt (–6 dB / oct above ~4 kHz)
        b, a = signal.butter(1, 8000 / (sample_rate / 2), btype="low")
        noise = signal.lfilter(b, a, noise).astype(np.float32)

        peak = np.max(np.abs(noise))
        if peak > 0:
            noise /= peak

        return noise * float(aspiration_ratio)


class FricativeNoise:
    """
    Band-limited turbulence noise for fricative PEOs.
    The noise is filtered to the [noise_floor_hz, noise_ceiling_hz] band
    specified in the PEO data.
    """

    def generate(
        self,
        n_samples: int,
        floor_hz: float,
        ceiling_hz: float,
        sample_rate: int,
        intensity_envelope: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Generate band-limited fricative noise.

        Parameters
        ----------
        n_samples         : output length
        floor_hz          : lower bound of noise band
        ceiling_hz        : upper bound of noise band
        sample_rate       : audio sample rate
        intensity_envelope: per-sample amplitude [0–1], length == n_samples.
                            If None, flat envelope at 1.0.
        """
        noise = np.random.normal(0, 1, n_samples).astype(np.float32)

        nyq = sample_rate / 2.0
        low = np.clip(floor_hz / nyq, 0.001, 0.999)
        high = np.clip(ceiling_hz / nyq, 0.001, 0.999)

        if low >= high:
            high = min(low + 0.01, 0.999)

        # 4th-order Butterworth bandpass for clean spectral edges
        b, a = signal.butter(4, [low, high], btype="band")
        noise = signal.lfilter(b, a, noise).astype(np.float32)

        peak = np.max(np.abs(noise))
        if peak > 0:
            noise /= peak

        if intensity_envelope is not None:
            env = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, len(intensity_envelope)),
                intensity_envelope,
            ).astype(np.float32)
            noise *= env

        return noise


class PlosiveBurst:
    """
    Transient acoustic burst for plosive PEOs.

    A plosive is modeled as a very short (5–20 ms) noise burst
    centered at spectral_peak_hz, with a fast-attack / fast-decay envelope.
    """

    def generate(
        self,
        n_samples: int,
        spectral_peak_hz: float,
        sample_rate: int,
        voiced: bool = False,
    ) -> np.ndarray:
        """
        Generate a plosive burst of length n_samples.

        spectral_peak_hz: center frequency of the burst energy
        voiced          : True for voiced plosives (/b/, /d/, /g/) —
                          adds a brief low-frequency voiced murmur
                          during the "prevoiced" period.
        """
        noise = np.random.normal(0, 1, n_samples).astype(np.float32)

        # Narrow bandpass around spectral peak
        nyq = sample_rate / 2.0
        bw_hz = 1500.0       # burst bandwidth
        low = np.clip((spectral_peak_hz - bw_hz / 2) / nyq, 0.001, 0.999)
        high = np.clip((spectral_peak_hz + bw_hz / 2) / nyq, 0.001, 0.999)
        if low >= high:
            high = min(low + 0.05, 0.999)

        b, a = signal.butter(3, [low, high], btype="band")
        noise = signal.lfilter(b, a, noise).astype(np.float32)

        # Burst envelope: instant attack, fast exponential decay
        t = np.linspace(0, 1, n_samples)
        envelope = np.exp(-12.0 * t).astype(np.float32)
        burst = noise * envelope

        # Voiced murmur: add a short low-frequency pulse at the start
        if voiced and n_samples > 0:
            murmur_len = min(n_samples, int(sample_rate * 0.015))
            t_m = np.linspace(0, np.pi, murmur_len)
            murmur = (np.sin(t_m) * 0.3).astype(np.float32)
            burst[:murmur_len] += murmur

        peak = np.max(np.abs(burst))
        if peak > 0:
            burst /= peak

        return burst
