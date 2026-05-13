"""
bezier.py — CVN Pitch Curve Interpolation
==========================================
Evaluates the Layer 2 Contour Vector Notation (CVN) bezier pitch curves,
converting a CVNCurve object into a per-sample Hz array.

The CVN curve is a piecewise cubic bezier defined by a sequence of
control points, each with (tick, hz, tension). Between any two adjacent
control points P0 and P1, a cubic bezier segment is computed using the
tension values to derive symmetric tangent handles.

Bezier math
-----------
Given P0 = (t0, hz0) and P1 = (t1, hz1) with tensions k0, k1:

    Handle H0 = hz0 + k0 * (hz1 - hz0) / 3    (outgoing handle from P0)
    Handle H1 = hz1 - k1 * (hz1 - hz0) / 3    (incoming handle at P1)

    B(u) = (1−u)³·hz0 + 3(1−u)²u·H0 + 3(1−u)u²·H1 + u³·hz1

    where u ∈ [0, 1] maps linearly from t0 to t1.

The resulting Hz curve is then resampled from tick-space to sample-space.
"""

from __future__ import annotations

import numpy as np
from .parser import CVNCurve, CVNControlPoint


def _cubic_bezier(
    hz0: float, hz1: float,
    h0: float, h1: float,
    n_points: int,
) -> np.ndarray:
    """Evaluate cubic bezier from hz0→hz1 with handles h0, h1."""
    u = np.linspace(0.0, 1.0, n_points)
    v = 1.0 - u
    return (v**3 * hz0
            + 3 * v**2 * u * h0
            + 3 * v * u**2 * h1
            + u**3 * hz1).astype(np.float32)


class CVNInterpolator:
    """
    Converts a CVNCurve object into a dense per-sample Hz array.

    Parameters
    ----------
    sample_rate : audio sample rate (Hz)
    ppq         : ticks per quarter-note (from CordaFile header)
    bpm         : tempo in beats per minute (from CordaFile header)

    Usage
    -----
        interp = CVNInterpolator(sample_rate=44100, ppq=9600, bpm=120)
        pitch_hz = interp.to_sample_array(curve, tick_onset, tick_offset)
    """

    def __init__(self, sample_rate: int = 44100, ppq: int = 9600, bpm: float = 120.0):
        self.sample_rate = sample_rate
        self.ppq = ppq
        self.bpm = bpm
        self._seconds_per_tick = 60.0 / (bpm * ppq)

    def ticks_to_samples(self, ticks: int) -> int:
        return int(round(ticks * self._seconds_per_tick * self.sample_rate))

    def to_sample_array(
        self,
        curve: CVNCurve,
        tick_onset: int,
        tick_offset: int,
    ) -> np.ndarray:
        """
        Evaluate the curve over [tick_onset, tick_offset] and return
        a per-sample Hz array.

        If the curve has no control points, a flat array at anchor_hz
        is returned. If there is only one control point, it also returns
        a flat array at that Hz value.
        """
        n_samples = self.ticks_to_samples(tick_offset - tick_onset)
        n_samples = max(1, n_samples)

        cps = curve.control_points
        if len(cps) == 0:
            return np.full(n_samples, curve.anchor_hz, dtype=np.float32)
        if len(cps) == 1:
            return np.full(n_samples, cps[0].hz, dtype=np.float32)

        # Build a dense Hz curve in tick-space, then resample to sample-space
        tick_range = tick_offset - tick_onset
        if tick_range <= 0:
            return np.full(n_samples, cps[0].hz, dtype=np.float32)

        # Resolution: evaluate at ~1000 points per second of audio
        n_eval = max(n_samples, 256)
        hz_tick = np.zeros(n_eval, dtype=np.float32)

        # Normalized tick positions of each control point
        cp_t = np.array([
            (cp.tick - tick_onset) / tick_range for cp in cps
        ], dtype=np.float64)
        cp_t = np.clip(cp_t, 0.0, 1.0)

        eval_t = np.linspace(0.0, 1.0, n_eval)

        # Piecewise cubic bezier
        for i in range(len(cps) - 1):
            p0, p1 = cps[i], cps[i + 1]
            t0, t1 = cp_t[i], cp_t[i + 1]
            if t1 <= t0:
                continue

            # Tangent handles (symmetric, tension-scaled)
            dhz = p1.hz - p0.hz
            h0 = p0.hz + p0.tension * dhz / 3.0
            h1 = p1.hz - p1.tension * dhz / 3.0

            # Find eval indices within [t0, t1]
            mask = (eval_t >= t0) & (eval_t < t1)
            seg_t = eval_t[mask]
            if len(seg_t) == 0:
                continue

            u = (seg_t - t0) / (t1 - t0)
            v = 1.0 - u
            hz_seg = (v**3 * p0.hz
                      + 3 * v**2 * u * h0
                      + 3 * v * u**2 * h1
                      + u**3 * p1.hz).astype(np.float32)
            hz_tick[mask] = hz_seg

        # Fill the final control point
        last_mask = eval_t >= cp_t[-1]
        hz_tick[last_mask] = cps[-1].hz

        # Handle leading region before the first control point
        first_mask = eval_t < cp_t[0]
        hz_tick[first_mask] = cps[0].hz

        # Clamp to valid speech range (50 Hz – 1500 Hz)
        hz_tick = np.clip(hz_tick, 50.0, 1500.0)

        # Resample from n_eval points to n_samples
        if n_eval != n_samples:
            hz_tick = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, n_eval),
                hz_tick,
            ).astype(np.float32)

        return hz_tick


def constant_pitch(hz: float, n_samples: int) -> np.ndarray:
    """Convenience: flat pitch array for PEOs without a CVN curve."""
    return np.full(n_samples, hz, dtype=np.float32)


def fallback_pitch(peo_intensity: float, n_samples: int) -> np.ndarray:
    """
    Very rough F0 estimate when no CVN curve exists.
    Uses intensity as a proxy for arousal → slightly higher pitch.
    Covers the case where pitch data is simply absent.
    """
    # Adult neutral speech: ~120 Hz (male) / ~200 Hz (female)
    base_hz = 150.0 + 60.0 * peo_intensity
    return constant_pitch(base_hz, n_samples)
