"""
parser.py — Corda Protocol File Parser
=======================================
Reads a .crd file (dual-payload: JSON header + BSON vector block)
and deserializes it into strongly-typed Python dataclasses.

.crd binary layout
------------------
Offset 0       : 4 bytes  — magic number b'CRD\x02'
Offset 4       : 4 bytes  — uint32 LE — length of JSON header block
Offset 8       : N bytes  — UTF-8 JSON header
Offset 8+N     : 4 bytes  — uint32 LE — length of BSON vector block
Offset 12+N    : M bytes  — BSON vector payload

For development/testing, .crd files may also be written as pure JSON
(no BSON payload) with the file extension .crd.json.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import numpy as np

# BSON is an optional dependency. If not installed, vector payloads
# must be embedded as JSON arrays in the header (development mode only).
try:
    import bson                          # pip install pymongo
    BSON_AVAILABLE = True
except ImportError:
    BSON_AVAILABLE = False

MAGIC = b"CRD\x02"


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class CVNControlPoint:
    tick: int
    hz: float
    tension: float = 0.5


@dataclass
class CVNCurve:
    curve_id: str
    peo_ref: str
    anchor_hz: float
    control_points: list[CVNControlPoint]
    pitch_confidence: float = 1.0


@dataclass
class FormantFrame:
    """One formant snapshot, sampled every 4 ticks."""
    tick: int
    f1_hz: float
    f2_hz: float
    f3_hz: float
    f4_hz: float
    f5_hz: float
    aspiration_ratio: float = 0.0   # [0.0 = clear, 1.0 = pure breath]


@dataclass
class PEO:
    """Phonetic Event Object — one articulatory event."""
    peo_id: str
    articulation_class: str          # see ArticulationClass enum in design doc
    ipa_symbol: str
    tick_onset: int
    tick_offset: int
    intensity: float = 0.8
    flags: list[str] = field(default_factory=list)

    # Plosive-specific
    burst_duration_ms: Optional[float] = None
    spectral_peak_hz: Optional[float] = None

    # Fricative-specific
    noise_floor_hz: Optional[float] = None
    noise_ceiling_hz: Optional[float] = None
    intensity_curve: Optional[list[float]] = None

    # Hesitation-specific
    hesitation_type: Optional[str] = None


@dataclass
class WordBoundary:
    word: str
    peo_range: list[str]
    tick_onset: int
    stress: Optional[str] = None


@dataclass
class SemanticPhrase:
    phrase_id: str
    text: str
    tick_onset: int
    tick_offset: int
    emotion_inference: Optional[str] = None
    word_boundaries: list[WordBoundary] = field(default_factory=list)


@dataclass
class VectorPayload:
    """Deserialized BSON vector payload."""
    cvn_curves: list[CVNCurve] = field(default_factory=list)
    formant_frames: list[FormantFrame] = field(default_factory=list)
    glottal_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    aspiration_curve: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class CordaFile:
    """Fully parsed .crd file."""
    version: str
    file_uuid: str
    duration_ticks: int
    sample_rate_hz: int
    ppq_resolution: int
    mode: str                          # SPEECH | MELODIC | HYBRID
    language_hint: Optional[str]
    bpm: float                         # default 120 for speech files
    peos: list[PEO]
    phrases: list[SemanticPhrase]
    vectors: VectorPayload

    # Convenience: dict lookup
    _peo_map: dict[str, PEO] = field(default_factory=dict, repr=False)
    _curve_map: dict[str, CVNCurve] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self._peo_map = {p.peo_id: p for p in self.peos}
        self._curve_map = {c.peo_ref: c for c in self.vectors.cvn_curves}

    def get_peo(self, peo_id: str) -> Optional[PEO]:
        return self._peo_map.get(peo_id)

    def get_curve_for_peo(self, peo_id: str) -> Optional[CVNCurve]:
        return self._curve_map.get(peo_id)

    def formant_frames_in_range(self, tick_start: int, tick_end: int) -> list[FormantFrame]:
        return [f for f in self.vectors.formant_frames
                if tick_start <= f.tick <= tick_end]

    def glottal_tension_at(self, tick: int) -> float:
        """
        Returns glottal tension [0.0–1.0] at the given tick.
        The glottal_curve array is sampled every 4 ticks starting at tick 0.
        """
        if len(self.vectors.glottal_curve) == 0:
            return 0.5
        idx = tick // 4
        idx = min(idx, len(self.vectors.glottal_curve) - 1)
        return float(self.vectors.glottal_curve[idx])


# ── Parser ─────────────────────────────────────────────────────────────────────

class CordaParser:
    """
    Reads a .crd or .crd.json file and returns a CordaFile.

    Usage:
        parser = CordaParser()
        corda = parser.parse("recording.crd")
    """

    def parse(self, path: str | Path) -> CordaFile:
        path = Path(path)
        if path.suffix == ".json" or path.name.endswith(".crd.json"):
            return self._parse_json(path)
        return self._parse_binary(path)

    # ── Binary .crd ───────────────────────────────────────────────────────────

    def _parse_binary(self, path: Path) -> CordaFile:
        with open(path, "rb") as f:
            raw = f.read()

        # Magic check
        if raw[:4] != MAGIC:
            raise ValueError(f"Not a valid .crd file (bad magic bytes): {path}")

        # Header block
        header_len = struct.unpack_from("<I", raw, 4)[0]
        header_bytes = raw[8 : 8 + header_len]
        header = json.loads(header_bytes.decode("utf-8"))

        # BSON vector block
        offset = 8 + header_len
        vector_len = struct.unpack_from("<I", raw, offset)[0]
        vector_bytes = raw[offset + 4 : offset + 4 + vector_len]

        vectors = self._deserialize_vectors(vector_bytes, header)
        return self._build_corda_file(header, vectors)

    # ── Pure-JSON .crd.json (dev/test) ────────────────────────────────────────

    def _parse_json(self, path: Path) -> CordaFile:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        # In JSON mode, vector data lives in a top-level "vectors" key
        # as plain Python lists / dicts.
        vectors = self._deserialize_vectors_from_dict(doc.get("vectors", {}))
        return self._build_corda_file(doc, vectors)

    # ── BSON deserialization ──────────────────────────────────────────────────

    def _deserialize_vectors(self, vector_bytes: bytes, header: dict) -> VectorPayload:
        if not BSON_AVAILABLE:
            raise RuntimeError(
                "bson is not installed. Install with: pip install pymongo\n"
                "For development, use .crd.json files instead."
            )
        doc = bson.decode(vector_bytes)
        return self._deserialize_vectors_from_dict(doc)

    def _deserialize_vectors_from_dict(self, doc: dict) -> VectorPayload:
        # CVN curves
        curves = []
        for c in doc.get("layer2_cvn_curves", []):
            cps = [CVNControlPoint(**cp) for cp in c.get("control_points", [])]
            curves.append(CVNCurve(
                curve_id=c["curve_id"],
                peo_ref=c["peo_ref"],
                anchor_hz=c["anchor_hz"],
                control_points=cps,
                pitch_confidence=c.get("pitch_confidence", 1.0),
            ))

        # Formant frames
        frames = []
        for ff in doc.get("layer4_formants", []):
            frames.append(FormantFrame(**ff))
        frames.sort(key=lambda f: f.tick)

        # Glottal + aspiration curves (stored as lists of floats in BSON)
        glottal = np.array(doc.get("layer4_glottal_curve", []), dtype=np.float32)
        aspiration = np.array(doc.get("layer4_aspiration_curve", []), dtype=np.float32)

        return VectorPayload(
            cvn_curves=curves,
            formant_frames=frames,
            glottal_curve=glottal,
            aspiration_curve=aspiration,
        )

    # ── CordaFile assembly ────────────────────────────────────────────────────

    def _build_corda_file(self, header: dict, vectors: VectorPayload) -> CordaFile:
        peos = [self._parse_peo(p) for p in header.get("peos", [])]

        phrases = []
        for ph in header.get("layer5_phrases", []):
            wb = [WordBoundary(**w) for w in ph.get("word_boundaries", [])]
            phrases.append(SemanticPhrase(
                phrase_id=ph.get("phrase_id", ""),
                text=ph.get("text", ""),
                tick_onset=ph["tick_onset"],
                tick_offset=ph["tick_offset"],
                emotion_inference=ph.get("emotion_inference"),
                word_boundaries=wb,
            ))

        return CordaFile(
            version=header.get("corda_version", "2.0.0"),
            file_uuid=header.get("file_uuid", ""),
            duration_ticks=header.get("duration_ticks", 0),
            sample_rate_hz=header.get("sample_rate_hz", 44100),
            ppq_resolution=header.get("ppq_resolution", 9600),
            mode=header.get("mode", "SPEECH"),
            language_hint=header.get("language_hint"),
            bpm=header.get("bpm", 120.0),
            peos=peos,
            phrases=phrases,
            vectors=vectors,
        )

    def _parse_peo(self, p: dict) -> PEO:
        return PEO(
            peo_id=p["peo_id"],
            articulation_class=p["articulation_class"],
            ipa_symbol=p.get("ipa_symbol", ""),
            tick_onset=p["tick_onset"],
            tick_offset=p["tick_offset"],
            intensity=p.get("intensity", 0.8),
            flags=p.get("flags", []),
            burst_duration_ms=p.get("burst_duration_ms"),
            spectral_peak_hz=p.get("spectral_peak_hz"),
            noise_floor_hz=p.get("noise_floor_hz"),
            noise_ceiling_hz=p.get("noise_ceiling_hz"),
            intensity_curve=p.get("intensity_curve"),
            hesitation_type=p.get("hesitation_type"),
        )
