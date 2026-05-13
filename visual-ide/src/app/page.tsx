"use client";

import { useState, useRef } from "react";
import { Box, Typography, Stack, IconButton, Divider } from "@mui/material";
import { ExpressiveButton } from "@/components/ExpressiveButton";
import { ExpressiveCard } from "@/components/ExpressiveCard";
import { usePyodide } from "@/lib/usePyodide";

export default function Home() {
  const { isReady, isRendering, renderAudio } = usePyodide();
  const [status, setStatus] = useState("Initializing Engine...");
  const [fileName, setFileName] = useState<string>("default_payload.json");
  const [selectedPeoId, setSelectedPeoId] = useState<string | null>("peo_041");
  const audioCtxRef = useRef<AudioContext | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Valid Corda v2.0.0 payload for testing the real DSP engine
  const [payload, setPayload] = useState<any>({
    corda_version: "2.0.0",
    duration_ticks: 9600, // 2 seconds at 120BPM
    sample_rate_hz: 44100,
    ppq_resolution: 9600,
    bpm: 120.0,
    mode: "SPEECH",
    peos: [
      {
        peo_id: "peo_041",
        articulation_class: "VOICED",
        tick_onset: 0,
        tick_offset: 9600,
        intensity: 0.8,
        flags: ["NASALIZED"]
      }
    ],
    vectors: {
      layer2_cvn_curves: [],
      layer4_formants: [
        { tick: 0, f1_hz: 600, f2_hz: 1200, f3_hz: 2500, f4_hz: 3200, f5_hz: 4000 }
      ],
      layer4_glottal_curve: [],
      layer4_aspiration_curve: []
    },
    phrases: []
  });

  const selectedPeo = payload?.peos?.find((p: any) => p.peo_id === selectedPeoId) || payload?.peos?.[0];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const json = JSON.parse(evt.target?.result as string);
        setPayload(json);
        setFileName(file.name);
        setStatus(`Loaded ${file.name}`);
      } catch (err: any) {
        setStatus("Error parsing JSON: " + err.message);
      }
    };
    reader.readAsText(file);
  };

  const handleRenderAndPlay = async () => {
    if (!isReady) return;
    setStatus("Rendering DSP in Python (WASM)...");
    
    try {
      const audioArray = await renderAudio(payload);
      setStatus("Playback ready. Playing...");
      
      // Init AudioContext on user interaction
      if (!audioCtxRef.current) {
        audioCtxRef.current = new window.AudioContext({ sampleRate: 44100 });
      }
      
      const audioBuffer = audioCtxRef.current.createBuffer(1, audioArray.length, 44100);
      audioBuffer.copyToChannel(audioArray, 0);
      
      const source = audioCtxRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioCtxRef.current.destination);
      source.start();
      
      source.onended = () => setStatus("Playback finished.");
    } catch (e: any) {
      setStatus("Error: " + e.message);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh", bgcolor: "background.default", p: 2, gap: 2 }}>
      
      {/* Top Bar / Transport */}
      <ExpressiveCard sx={{ p: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h6" color="primary" fontWeight="bold">
          Corda Visual IDE <Typography component="span" variant="caption" color="text.secondary">(v2.0.0)</Typography>
        </Typography>
        
        <Stack direction="row" spacing={2} alignItems="center">
          <input
            type="file"
            accept=".json,.crd"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <ExpressiveButton
            variant="outlined"
            color="secondary"
            onClick={() => fileInputRef.current?.click()}
          >
            Open File
          </ExpressiveButton>
          
          <Divider orientation="vertical" flexItem />

          <Typography variant="body2" color="text.secondary">
            File: {fileName}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Engine: {isReady ? "Ready" : status}
          </Typography>
          <ExpressiveButton 
            variant="contained" 
            color="primary"
            disabled={!isReady || isRendering}
            onClick={handleRenderAndPlay}
          >
            {isRendering ? "Rendering..." : "Render & Play"}
          </ExpressiveButton>
        </Stack>
      </ExpressiveCard>

      {/* Main Workspace */}
      <Box sx={{ display: "flex", flex: 1, gap: 2, minHeight: 0 }}>
        
        {/* Layer Tracks (Canvas Area) */}
        <ExpressiveCard sx={{ flex: 3, display: "flex", flexDirection: "column", p: 2, overflow: "hidden" }}>
          <Typography variant="subtitle2" color="text.secondary" mb={2}>TIMELINE WORKSPACE</Typography>
          
          <Stack spacing={2} sx={{ flex: 1, overflowY: "auto" }}>
            {/* Layer 5 Track */}
            <Box sx={{ height: 60, bgcolor: "rgba(255,255,255,0.05)", borderRadius: 4, borderLeft: "4px solid #d0bcff", p: 2 }}>
              <Typography variant="caption" color="text.secondary">Layer 5: Semantic Syntax (NSS)</Typography>
            </Box>
            
            {/* Layer 2/1 Track */}
            <Box sx={{ height: 200, bgcolor: "rgba(255,255,255,0.05)", borderRadius: 4, borderLeft: "4px solid #ffb4ab", p: 2, position: "relative" }}>
              <Typography variant="caption" color="text.secondary" sx={{ position: "absolute", top: 8, left: 16 }}>
                Layer 2: Pitch (UVS) & Layer 1: Articulation (PAN)
              </Typography>
              
              <Box sx={{ position: "absolute", top: 40, left: 16, right: 16, height: 120, position: "relative" }}>
                {/* Dynamic PEO Blocks */}
                {(payload?.peos || []).map((peo: any) => {
                  const isSelected = peo.peo_id === selectedPeoId;
                  const leftPct = (peo.tick_onset / (payload.duration_ticks || 1)) * 100;
                  const widthPct = ((peo.tick_offset - peo.tick_onset) / (payload.duration_ticks || 1)) * 100;
                  const isVoiced = peo.articulation_class === "VOICED";
                  const bgColor = isVoiced ? "rgba(255,180,171,0.2)" : "rgba(208,188,255,0.2)";
                  const borderColor = isSelected ? "#fff" : (isVoiced ? "#ffb4ab" : "#d0bcff");

                  return (
                    <Box 
                      key={peo.peo_id}
                      onClick={() => setSelectedPeoId(peo.peo_id)}
                      sx={{ 
                        position: "absolute", top: 0, left: `${leftPct}%`, width: `${widthPct}%`, height: "100%", 
                        bgcolor: bgColor, borderRadius: 2, border: `2px solid ${borderColor}`,
                        display: "flex", alignItems: "flex-end", p: 1, cursor: "pointer", transition: "all 0.2s"
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">{peo.ipa_symbol || peo.articulation_class}</Typography>
                    </Box>
                  );
                })}

                {/* Dynamic Pitch Curves */}
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
                  {(payload?.vectors?.layer2_cvn_curves || []).map((curve: any, i: number) => {
                    if (!curve.control_points || curve.control_points.length === 0) return null;
                    const pts = curve.control_points.map((pt: any) => {
                      const x = (pt.tick / (payload.duration_ticks || 1)) * 100;
                      const maxHz = 1000;
                      const y = 100 - Math.min((pt.hz / maxHz) * 100, 100);
                      return `${x},${y}`;
                    });
                    return <path key={i} d={`M ${pts.join(" L ")}`} stroke="#ffb4ab" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />;
                  })}
                </svg>
              </Box>
            </Box>
            
            {/* Layer 4 Track */}
            <Box sx={{ height: 140, bgcolor: "rgba(255,255,255,0.05)", borderRadius: 4, borderLeft: "4px solid #81c995", p: 2 }}>
              <Typography variant="caption" color="text.secondary">Layer 4: Vocal Tract Spectrogram (AVT)</Typography>
            </Box>
          </Stack>
        </ExpressiveCard>

        {/* Sidebar / Inspector */}
        <ExpressiveCard sx={{ flex: 1, p: 2, overflowY: "auto" }}>
          <Typography variant="subtitle2" color="text.secondary" mb={2}>INSPECTOR</Typography>
          
          <Typography variant="body2" color="primary" gutterBottom>Selected PEO: {selectedPeo?.peo_id || "None"}</Typography>
          <Divider sx={{ my: 2 }} />
          
          <Stack spacing={1}>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="caption" color="text.secondary">Class</Typography>
              <Typography variant="caption">{selectedPeo?.articulation_class || "N/A"}</Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="caption" color="text.secondary">IPA</Typography>
              <Typography variant="caption">{selectedPeo?.ipa_symbol || "N/A"}</Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="caption" color="text.secondary">Intensity</Typography>
              <Typography variant="caption">{selectedPeo?.intensity ?? "N/A"}</Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="caption" color="text.secondary">Flags</Typography>
              <Typography variant="caption">{JSON.stringify(selectedPeo?.flags || [])}</Typography>
            </Box>
          </Stack>
          
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="caption" color="text.secondary" display="block" mb={1}>
            Prosodic Stress
          </Typography>
          <Stack direction="row" spacing={1}>
            <ExpressiveButton variant="outlined" size="small" color="secondary">Primary</ExpressiveButton>
            <ExpressiveButton variant="contained" size="small">Unstressed</ExpressiveButton>
          </Stack>

        </ExpressiveCard>
      </Box>
    </Box>
  );
}
