"""
corda_synth — Corda Protocol (.crd) Speech Synthesis Engine
============================================================
Converts a .crd file back into a synthesized audio waveform.

Public API:

    from corda_synth import CordaSynthesizer

    synth = CordaSynthesizer(sample_rate=44100)
    audio = synth.render("my_file.crd")          # → np.ndarray float32
    synth.save_wav(audio, "output.wav")
"""

from .engine import CordaSynthesizer
from .parser import CordaParser, CordaFile

__all__ = ["CordaSynthesizer", "CordaParser", "CordaFile"]
__version__ = "0.1.0"
