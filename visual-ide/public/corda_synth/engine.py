"""
engine.py — CordaSynthesizer
============================
The top-level synthesis engine. Takes a parsed CordaFile (or a raw .crd
file path) and produces a rendered audio waveform as a NumPy float32 array.

Pipeline
--------
    parse .crd
        ↓
    sort PEOs by tick_onset
        ↓
    for each PEO:
        synthesize audio chunk (peo_synth.py)
            ↓
        place into master buffer at correct sample offset
        overlap-add with adjacent chunks (coarticulation crossfade)
            ↓
    post-process:
        soft-knee limiter
        DC offset removal
        normalize to -1 dBFS
        ↓
    return float32 numpy array  (or write WAV)

Coarticulation
--------------
Real speech has no clean boundaries between phonemes — each phoneme
bleeds into its neighbors (coarticulation). The engine simulates this by
overlap-adding a short crossfade region between every adjacent PEO pair.
The crossfade length is proportional to the PEO types involved
(e.g., a vowel→consonant transition uses a longer fade than
plosive→fricative).

Usage
-----
    from corda_synth import CordaSynthesizer

    synth = CordaSynthesizer(sample_rate=44100)

    # From a file path
    audio = synth.render("my_recording.crd")

    # From an already-parsed CordaFile
    from corda_synth import CordaParser
    corda = CordaParser().parse("my_recording.crd")
    audio = synth.render(corda)

    # Save to WAV
    synth.save_wav(audio, "output.wav")
"""

from __future__ import annotations

import wave
import struct
from pathlib import Path
from typing import Union

import numpy as np

from .parser import CordaParser, CordaFile, PEO
from .peo_synth import PEOSynthesizer


# Crossfade durations (seconds) at PEO boundaries
# Indexed as (class_a, class_b) — order-independent
_CROSSFADE_TABLE: dict[frozenset, float] = {
    frozenset({"VOICED",    "VOICED"}):    0.020,
    frozenset({"VOICED",    "PLOSIVE"}):   0.008,
    frozenset({"VOICED",    "FRICATIVE"}): 0.012,
    frozenset({"VOICED",    "NASAL"}):     0.015,
    frozenset({"VOICED",    "APPROXIMANT"}):0.018,
    frozenset({"PLOSIVE",   "FRICATIVE"}): 0.004,
    frozenset({"PLOSIVE",   "VOICED"}):    0.008,
    frozenset({"FRICATIVE", "FRICATIVE"}): 0.010,
    frozenset({"HESITATION","VOICED"}):    0.020,
    frozenset({"HESITATION","FRICATIVE"}): 0.010,
}
_DEFAULT_CROSSFADE = 0.006   # seconds


def _crossfade_duration(class_a: str, class_b: str) -> float:
    key = frozenset({class_a, class_b})
    return _CROSSFADE_TABLE.get(key, _DEFAULT_CROSSFADE)


class CordaSynthesizer:
    """
    Main synthesis engine.

    Parameters
    ----------
    sample_rate     : output audio sample rate (default 44100 Hz)
    crossfade       : enable coarticulation crossfade between PEOs
    normalize_db    : target peak level in dBFS (default -1.0)
    mode            : "default", "neural" (Phase 4), or "streaming" (Phase 5)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        crossfade: bool = True,
        normalize_db: float = -1.0,
        mode: str = "default",
    ):
        self.sample_rate = sample_rate
        self.crossfade = crossfade
        self.normalize_db = normalize_db
        self.mode = mode
        self._parser = CordaParser()
        
        # Load the Phase 4 Neural Vocoder Placeholder if requested
        if self.mode in ("neural", "streaming"):
            from .neural_vocoder import HiFiGANPlaceholder
            self.vocoder = HiFiGANPlaceholder(sample_rate=self.sample_rate)
        else:
            self.vocoder = None

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, source: Union[str, Path, CordaFile]) -> np.ndarray:
        """
        Render a .crd file to a float32 NumPy audio array.

        Parameters
        ----------
        source : file path (str / Path) or a pre-parsed CordaFile object.

        Returns
        -------
        np.ndarray, dtype=float32, shape=(n_samples,), values in [-1, 1].
        """
        if isinstance(source, (str, Path)):
            corda = self._parser.parse(source)
        else:
            corda = source

        peo_synth = PEOSynthesizer(
            sample_rate=self.sample_rate,
            ppq=corda.ppq_resolution,
            bpm=corda.bpm,
        )

        # Seconds-per-tick conversion (used throughout rendering)
        spt = 60.0 / (corda.bpm * corda.ppq_resolution)

        # Allocate master buffer
        duration_seconds = corda.duration_ticks * spt
        n_total = max(1, int(np.ceil(duration_seconds * self.sample_rate)))
        buffer = np.zeros(n_total, dtype=np.float32)

        # Sort PEOs by onset tick
        peos = sorted(corda.peos, key=lambda p: p.tick_onset)

        for i, peo in enumerate(peos):
            prev_peo = peos[i - 1] if i > 0 else None
            next_peo = peos[i + 1] if i < len(peos) - 1 else None

            # Synthesize this PEO's audio chunk
            chunk = peo_synth.synthesize(peo, corda, prev_peo=prev_peo, next_peo=next_peo)
            if len(chunk) == 0:
                continue

            # Determine placement in master buffer
            onset_sample = int(round(peo.tick_onset * spt * self.sample_rate))
            end_sample   = onset_sample + len(chunk)

            # Guard buffer bounds
            if onset_sample >= n_total:
                continue
            end_sample = min(end_sample, n_total)
            chunk_trimmed = chunk[: end_sample - onset_sample]

            # Overlap-add (coarticulation crossfade with previous PEO)
            if self.crossfade and i > 0:
                prev_peo = peos[i - 1]
                fade_s = _crossfade_duration(
                    prev_peo.articulation_class, peo.articulation_class
                )
                fade_n = min(int(fade_s * self.sample_rate), len(chunk_trimmed))

                if fade_n > 0:
                    fade_in  = np.linspace(0, 1, fade_n, dtype=np.float32)
                    fade_out = 1.0 - fade_in

                    # Crossfade zone in the master buffer
                    xf_start = onset_sample
                    xf_end   = min(onset_sample + fade_n, n_total)
                    xf_len   = xf_end - xf_start

                    buffer[xf_start:xf_end] *= fade_out[:xf_len]
                    buffer[xf_start:xf_end] += chunk_trimmed[:xf_len] * fade_in[:xf_len]

                    # Write the non-overlapping remainder
                    buffer[xf_end:end_sample] += chunk_trimmed[xf_len:]
                else:
                    buffer[onset_sample:end_sample] += chunk_trimmed
            else:
                buffer[onset_sample:end_sample] += chunk_trimmed

        # Post-processing
        buffer = self._remove_dc(buffer)
        
        # Phase 4 Neural Enhancement (if enabled)
        if self.vocoder is not None:
            buffer = self.vocoder.enhance(buffer)
            
        buffer = self._soft_limiter(buffer, threshold=0.85)
        buffer = self._normalize(buffer, self.normalize_db)
        return buffer

    def stream(self, source: Union[str, Path, CordaFile], chunk_size: int = 1024):
        """
        Phase 5: Streaming API for real-time playback in the Corda IDE.
        Renders the file chunk-by-chunk.
        """
        # In a true real-time scenario, this would maintain filter state across frames.
        # As a placeholder, we use the offline render and yield it in chunks to 
        # simulate the downstream API interface.
        audio = self.render(source)
        
        pos = 0
        while pos < len(audio):
            end = min(pos + chunk_size, len(audio))
            yield audio[pos:end]
            pos = end

    def save_wav(self, audio: np.ndarray, path: str | Path) -> None:
        """
        Write float32 audio to a 16-bit WAV file.

        Parameters
        ----------
        audio : float32 array in [-1, 1], as returned by render().
        path  : output file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to 16-bit PCM
        pcm = np.clip(audio, -1.0, 1.0)
        pcm_int16 = (pcm * 32767).astype(np.int16)

        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)            # mono
            wf.setsampwidth(2)            # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_int16.tobytes())

        print(f"[corda_synth] Saved {len(audio)/self.sample_rate:.2f}s → {path}")

    # ── Post-processing ───────────────────────────────────────────────────────

    def _remove_dc(self, audio: np.ndarray) -> np.ndarray:
        """Remove any DC offset introduced by the synthesis chain."""
        return (audio - np.mean(audio)).astype(np.float32)

    def _soft_limiter(self, audio: np.ndarray, threshold: float = 0.85) -> np.ndarray:
        """
        Soft-knee limiter. Signals above `threshold` are compressed
        smoothly toward 1.0 rather than hard-clipped.

        Transfer function above threshold:
            y = threshold + (1 - threshold) * tanh((x - threshold) / (1 - threshold))
        """
        out = audio.copy()
        above = np.abs(audio) > threshold
        x = audio[above]
        sign = np.sign(x)
        mag  = np.abs(x)
        knee = threshold + (1.0 - threshold) * np.tanh(
            (mag - threshold) / (1.0 - threshold)
        )
        out[above] = sign * knee
        return out.astype(np.float32)

    def _normalize(self, audio: np.ndarray, target_db: float) -> np.ndarray:
        """Normalize peak amplitude to target_db dBFS."""
        peak = np.max(np.abs(audio))
        if peak < 1e-9:
            return audio
        target_linear = 10 ** (target_db / 20.0)
        return (audio * (target_linear / peak)).astype(np.float32)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def render_peo(self, peo_id: str, corda: CordaFile) -> np.ndarray:
        """
        Render a single PEO in isolation. Useful for debugging
        and acoustic inspection in the IDE.
        """
        peo = corda.get_peo(peo_id)
        if peo is None:
            raise KeyError(f"PEO '{peo_id}' not found in CordaFile")

        peo_synth = PEOSynthesizer(
            sample_rate=self.sample_rate,
            ppq=corda.ppq_resolution,
            bpm=corda.bpm,
        )
        chunk = peo_synth.synthesize(peo, corda)
        chunk = self._remove_dc(chunk)
        chunk = self._soft_limiter(chunk)
        chunk = self._normalize(chunk, self.normalize_db)
        return chunk

    def estimate_duration(self, corda: CordaFile) -> float:
        """Returns estimated output duration in seconds."""
        spt = 60.0 / (corda.bpm * corda.ppq_resolution)
        return corda.duration_ticks * spt
