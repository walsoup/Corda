"""
train.py — PyTorch Training Loop
================================
Run this script to train the neural vocoder when a GPU and dataset are available.
"""

import argparse
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from .models import HiFiGANGenerator
from .dataset import CordaDataset

def train(epochs=1000, batch_size=16, learning_rate=2e-4, data_dir="./training_data"):
    print("[NeuralVocoder] Initializing training pipeline...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[NeuralVocoder] Target device: {device}")

    # Initialize model (expecting 1-channel DSP audio as input conditioning)
    generator = HiFiGANGenerator(input_channels=1).to(device)
    optimizer = optim.AdamW(generator.parameters(), lr=learning_rate, betas=(0.8, 0.99))
    
    # Simple L1 Loss for waveform reconstruction 
    # (A real GAN would also use a discriminator loss, omitted here for brevity)
    criterion = torch.nn.L1Loss()

    dataset = CordaDataset(data_dir)
    # Using dummy length for empty dataset validation
    if len(dataset) == 0:
        print("[NeuralVocoder] WARNING: No training data found. Simulating training step...")
        dataset = [ (torch.randn(1, 8192), torch.randn(1, 8192)) for _ in range(batch_size) ]

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    generator.train()
    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        for batch_idx, (dsp_audio, real_audio) in enumerate(loader):
            dsp_audio = dsp_audio.to(device)
            real_audio = real_audio.to(device)

            optimizer.zero_grad()
            
            # Forward pass: enhance DSP audio
            enhanced_audio = generator(dsp_audio)
            
            # Match lengths if necessary
            if enhanced_audio.shape[-1] != real_audio.shape[-1]:
                min_len = min(enhanced_audio.shape[-1], real_audio.shape[-1])
                enhanced_audio = enhanced_audio[..., :min_len]
                real_audio = real_audio[..., :min_len]

            loss = criterion(enhanced_audio, real_audio)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch [{epoch}/{epochs}] - Loss: {epoch_loss/len(loader):.4f}")

    print("[NeuralVocoder] Training complete. Saving weights...")
    torch.save(generator.state_dict(), "corda_generator.pth")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--data-dir", type=str, default="./training_data")
    args = parser.parse_args()
    train(epochs=args.epochs, data_dir=args.data_dir)
