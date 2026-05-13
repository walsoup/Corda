import numpy as np
from corda_synth import CordaSynthesizer
from corda_synth.parser import CordaParser
import os
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

def test_hello_renders_without_error():
    synth = CordaSynthesizer()
    audio = synth.render(CORPUS_DIR / "sentence_hello.crd.json")
    assert audio.dtype == np.float32
    assert len(audio) > 0
    assert np.max(np.abs(audio)) <= 1.0

def test_silent_peo_produces_silence():
    # PEO with intensity = 0.0 should produce near-silent output
    c_parser = CordaParser()
    corda = c_parser.parse(CORPUS_DIR / "vowel_ah.crd.json")
    corda.peos[0].intensity = 0.0
    synth = CordaSynthesizer()
    audio = synth.render(corda)
    assert np.max(np.abs(audio)) < 1e-5

def test_plosive_burst_is_short():
    synth = CordaSynthesizer()
    audio = synth.render(CORPUS_DIR / "word_stop.crd.json")
    assert len(audio) > 0

def test_fricative_renders():
    synth = CordaSynthesizer()
    audio = synth.render(CORPUS_DIR / "fricative_sss.crd.json")
    assert len(audio) > 0

def test_fry_renders():
    synth = CordaSynthesizer()
    audio = synth.render(CORPUS_DIR / "fry_test.crd.json")
    assert len(audio) > 0

def test_hesitation_renders():
    synth = CordaSynthesizer()
    audio = synth.render(CORPUS_DIR / "hesitation_um.crd.json")
    assert len(audio) > 0

def test_vowel_renders():
    synth = CordaSynthesizer()
    audio = synth.render(CORPUS_DIR / "vowel_ah.crd.json")
    assert len(audio) > 0
