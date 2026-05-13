"""
export.py — ONNX Export Script
==============================
Exports the trained PyTorch model to ONNX so it can be executed in
the web browser IDE (Phase 5) using ONNX Runtime Web, completely
removing the PyTorch dependency for end-users.
"""

import torch
import argparse
from .models import HiFiGANGenerator

def export_onnx(checkpoint_path, output_path):
    print(f"[NeuralVocoder] Loading weights from {checkpoint_path}...")
    
    # Initialize the model structure
    model = HiFiGANGenerator(input_channels=1)
    
    try:
        model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
        print("[NeuralVocoder] Weights loaded successfully.")
    except FileNotFoundError:
        print("[NeuralVocoder] WARNING: Checkpoint not found. Exporting uninitialized model architecture.")
    
    model.eval()

    # Create a dummy input tensor matching the expected shape: (Batch, Channels, Time)
    # Using a 2-second audio frame at 44.1kHz for the dynamic axes trace
    dummy_input = torch.randn(1, 1, 88200)

    print(f"[NeuralVocoder] Exporting ONNX graph to {output_path}...")
    torch.onnx.export(
        model, 
        dummy_input, 
        output_path, 
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["dsp_audio_in"],
        output_names=["enhanced_audio_out"],
        dynamic_axes={
            "dsp_audio_in": {0: "batch_size", 2: "time"},
            "enhanced_audio_out": {0: "batch_size", 2: "time"}
        }
    )
    print("[NeuralVocoder] Export complete! Model is ready for browser WebAssembly inference.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, default="corda_generator.pth")
    parser.add_argument("--output", type=str, default="corda_vocoder.onnx")
    args = parser.parse_args()
    export_onnx(args.checkpoint, args.output)
