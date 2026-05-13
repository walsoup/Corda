// pyodide.worker.ts
// Web Worker for Pyodide so we don't block the React main thread during heavy DSP rendering.

self.importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js");

let pyodide: any = null;

self.onmessage = async (event: MessageEvent) => {
  const { type, payload, id } = event.data;

  if (type === "INIT") {
    try {
      // @ts-ignore
      pyodide = await loadPyodide();
      
      // Install numpy and scipy (required by corda_synth)
      await pyodide.loadPackage(["numpy", "scipy"]);
      
      // Mount the actual corda_synth python files into the Pyodide virtual filesystem
      pyodide.FS.mkdir("/corda_synth");
      
      const files = [
        "__init__.py", "bezier.py", "engine.py", "filters.py", 
        "neural_vocoder.py", "parser.py", "peo_synth.py", "sources.py"
      ];
      
      for (const file of files) {
        const res = await fetch(`/corda_synth/${file}`);
        if (!res.ok) throw new Error(`Failed to load ${file}`);
        const text = await res.text();
        pyodide.FS.writeFile(`/corda_synth/${file}`, text);
      }
      
      // Initialize the actual engine
      await pyodide.runPythonAsync(`
import sys
import json
sys.path.append("/")

from corda_synth.engine import CordaSynthesizer
from corda_synth.parser import CordaParser

# Using neural mode to simulate Phase 4 enhancement
synth = CordaSynthesizer(sample_rate=44100, mode="neural")
parser = CordaParser()

def render_payload(json_string):
    # Write payload to a virtual file so parser can read it
    with open("/tmp_payload.json", "w") as f:
        f.write(json_string)
        
    corda_file = parser.parse("/tmp_payload.json")
    audio = synth.render(corda_file)
    return audio
      `);
      
      self.postMessage({ id, type: "INIT_SUCCESS" });
    } catch (err: any) {
      self.postMessage({ id, type: "ERROR", error: err.message });
    }
  }

  if (type === "RENDER") {
    try {
      if (!pyodide) throw new Error("Pyodide not initialized");
      
      // Pass the JSON payload to Python
      pyodide.globals.set("json_payload", JSON.stringify(payload));
      
      // Run the actual python render pipeline
      const audioProxy = await pyodide.runPythonAsync(`render_payload(json_payload)`);
      
      // Copy the Float32Array from WASM memory to JS memory
      const audioArray = audioProxy.toJs();
      audioProxy.destroy(); // Free WASM memory
      
      self.postMessage({ id, type: "RENDER_SUCCESS", data: audioArray }, [audioArray.buffer]);
    } catch (err: any) {
      self.postMessage({ id, type: "ERROR", error: err.message });
    }
  }
};
