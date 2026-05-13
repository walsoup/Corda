"""
filters.py — Five-Pole Formant Filter Bank
===========================================
Implements the vocal-tract filter portion of the source-filter model.

Each formant (F1–F5) is a 2nd-order IIR resonator. The five resonators
are chained in cascade (series), which better models the acoustic
coupling of vocal-tract resonances than a parallel arrangement.

Additionally, a lip radiation filter (+6 dB/oct highpass) is applied
at the output to model the high-frequency boost caused by the lips.

Formant bandwidths
------------------
Typical bandwidth values (Hz) used when none are specified in the data:

    F1: 80  Hz  (low, strong resonance — primary vowel energy)
    F2: 120 Hz
    F3: 150 Hz
    F4: 200 Hz  (Singer's Formant cluster)
    F5: 300 Hz  (high-end clarity)

These are narrower for vowels, wider for nasals and fricatives.
"""

from __future__ import annotations

import numpy as np
from scipy import signal
from dataclasses import dataclass


@dataclass
class FormantSpec:
    """Instantaneous formant parameters for one synthesis frame."""
    f1: float = 600.0
    f2: float = 1200.0
    f3: float = 2500.0
    f4: float = 3200.0
    f5: float = 4000.0
    bw1: float = 80.0
    bw2: float = 120.0
    bw3: float = 150.0
    bw4: float = 200.0
    bw5: float = 300.0

    @classmethod
    def neutral(cls) -> "FormantSpec":
        """Schwa-like neutral vocal tract position."""
        return cls(f1=500, f2=1500, f3=2500, f4=3200, f5=4000)

    @classmethod
    def whisper(cls) -> "FormantSpec":
        """
        Whisper shifts F1 upward and broadens all bandwidths significantly
        (open glottis couples noise more uniformly across formants).
        """
        return cls(
            f1=700, f2=1600, f3=2600, f4=3300, f5=4100,
            bw1=300, bw2=400, bw3=500, bw4=600, bw5=700,
        )


def _resonator_coeffs(
    freq_hz: float,
    bandwidth_hz: float,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute 2nd-order IIR resonator coefficients.

    Transfer function (z-domain):
        H(z) = b0 / (1  −  2r·cos(2πf/fs)·z⁻¹  +  r²·z⁻²)

    where r = exp(−π·bw/fs).
    """
    r = np.exp(-np.pi * bandwidth_hz / sample_rate)
    cos_t = 2.0 * r * np.cos(2.0 * np.pi * freq_hz / sample_rate)
    b0 = 1.0 - r
    b = np.array([b0, 0.0, 0.0], dtype=np.float64)
    a = np.array([1.0, -cos_t, r ** 2], dtype=np.float64)
    return b, a


class FormantFilterBank:
    """
    Five-pole cascade formant filter.

    For time-varying formant data (as in Corda), the filter is applied
    frame-by-frame with short crossfade between frames to avoid clicks
    at formant transitions.

    Usage (static formants)
    -----------------------
        bank = FormantFilterBank(sample_rate=44100)
        spec = FormantSpec(f1=730, f2=1090, f3=2440, f4=3200, f5=4000)
        output = bank.apply_static(source_signal, spec)

    Usage (time-varying formants)
    ------------------------------
        frame_specs = [FormantSpec(...), ...]   # one per frame
        output = bank.apply_dynamic(source_signal, frame_specs, frame_size=441)
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def apply_static(
        self,
        source: np.ndarray,
        spec: FormantSpec,
    ) -> np.ndarray:
        """
        Apply a fixed formant configuration to the entire source signal.
        Fastest path — used when formant data is unavailable or constant.
        """
        out = source.astype(np.float64).copy()
        for (f, bw) in [
            (spec.f1, spec.bw1),
            (spec.f2, spec.bw2),
            (spec.f3, spec.bw3),
            (spec.f4, spec.bw4),
            (spec.f5, spec.bw5),
        ]:
            b, a = _resonator_coeffs(f, bw, self.sample_rate)
            out = signal.lfilter(b, a, out)

        out = self._lip_radiation(out)
        return self._normalize(out).astype(np.float32)

    def apply_dynamic(
        self,
        source: np.ndarray,
        frame_specs: list[FormantSpec],
        frame_size: int = 441,    # 10 ms at 44100 Hz
    ) -> np.ndarray:
        """
        Apply time-varying formants by processing frame_size-sample chunks.
        Adjacent frames are crossfaded to eliminate formant-transition clicks.

        frame_specs: list of FormantSpec, one per frame (will be interpolated
                     if fewer specs than frames are provided).
        """
        n_samples = len(source)
        n_frames = (n_samples + frame_size - 1) // frame_size
        output = np.zeros(n_samples, dtype=np.float64)

        # Expand / interpolate frame_specs to match n_frames
        specs = self._interpolate_specs(frame_specs, n_frames)

        # Maintain filter state across frames to avoid discontinuities
        zi_list = [np.zeros((2,)) for _ in range(5)]  # one zi per formant pole
        prev_out = None

        for i, spec in enumerate(specs):
            start = i * frame_size
            end = min(start + frame_size, n_samples)
            chunk = source[start:end].astype(np.float64)

            filtered = chunk.copy()
            coeffs = [
                _resonator_coeffs(spec.f1, spec.bw1, self.sample_rate),
                _resonator_coeffs(spec.f2, spec.bw2, self.sample_rate),
                _resonator_coeffs(spec.f3, spec.bw3, self.sample_rate),
                _resonator_coeffs(spec.f4, spec.bw4, self.sample_rate),
                _resonator_coeffs(spec.f5, spec.bw5, self.sample_rate),
            ]
            new_zi_list = []
            for j, (b, a) in enumerate(coeffs):
                filtered, zi = signal.lfilter(b, a, filtered, zi=zi_list[j])
                new_zi_list.append(zi)
            zi_list = new_zi_list

            # Short crossfade at frame boundaries to smooth transitions
            if prev_out is not None and len(prev_out) > 0:
                fade_len = min(64, len(prev_out), len(filtered))
                fade_in = np.linspace(0, 1, fade_len)
                fade_out = 1 - fade_in
                # Apply crossfade at the boundary of the previous frame
                boundary_start = start - fade_len
                if boundary_start >= 0:
                    output[boundary_start:start] = (
                        output[boundary_start:start] * fade_out + prev_out[-fade_len:] * fade_in
                    )

            output[start:end] = filtered
            prev_out = filtered

        output = self._lip_radiation(output)
        return self._normalize(output).astype(np.float32)

    def _lip_radiation(self, signal_in: np.ndarray) -> np.ndarray:
        """
        Simple first-order highpass approximating lip radiation (+6 dB/oct).
        H(z) = 1 − z⁻¹  (differentiator)
        """
        return np.diff(signal_in, prepend=signal_in[0])

    def _normalize(self, sig: np.ndarray) -> np.ndarray:
        peak = np.max(np.abs(sig))
        if peak > 1e-9:
            return sig / peak
        return sig

    def _interpolate_specs(
        self,
        specs: list[FormantSpec],
        n_frames: int,
    ) -> list[FormantSpec]:
        """
        Linearly interpolate formant specs to exactly n_frames entries.
        """
        if len(specs) == 0:
            return [FormantSpec.neutral()] * n_frames
        if len(specs) == n_frames:
            return specs

        src_t = np.linspace(0, 1, len(specs))
        dst_t = np.linspace(0, 1, n_frames)
        fields = ["f1", "f2", "f3", "f4", "f5", "bw1", "bw2", "bw3", "bw4", "bw5"]

        arrays = {}
        for f in fields:
            src_vals = np.array([getattr(s, f) for s in specs])
            arrays[f] = np.interp(dst_t, src_t, src_vals)

        return [
            FormantSpec(**{f: float(arrays[f][i]) for f in fields})
            for i in range(n_frames)
        ]
